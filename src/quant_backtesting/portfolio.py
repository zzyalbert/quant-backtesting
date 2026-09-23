from datetime import datetime
from queue import Queue
from typing import TypeAlias

import pandas as pd

from quant_backtesting.data import DataHandler
from quant_backtesting.event import (
    Event,
    FillEvent,
    OrderDirection,
    OrderEvent,
    OrderType,
    SignalEvent,
    SignalType,
    ib_commission,
)
from quant_backtesting.performance import create_drawdowns, create_sharpe_ratio

LedgerRow: TypeAlias = dict[str, datetime | int | float]


def max_shares_for_cash(cash: float, price: float, max_size: int) -> int:
    """Largest share count whose notional plus IB commission fits in cash."""
    if cash <= 0 or price <= 0 or max_size <= 0:
        return 0
    size = min(max_size, int(cash // price))
    while size > 0 and size * price + ib_commission(size) > cash:
        size -= 1
    return size


def max_cash_secured_short(cash: float, price: float, max_size: int) -> int:
    """Largest short whose notional fits in cash and whose commission is payable."""
    if cash <= 0 or price <= 0 or max_size <= 0:
        return 0
    size = min(max_size, int(cash // price))
    while size > 0 and ib_commission(size) > cash:
        size -= 1
    return size


class Portfolio:
    def __init__(
        self,
        bars: DataHandler,
        events: Queue[Event],
        start_date: datetime,
        initial_capital: float = 100_000.0,
        periods: int = 252,
        default_quantity: int = 100,
    ) -> None:
        self.bars = bars
        self.events = events
        self.symbol_list = self.bars.symbol_list
        self.start_date = start_date
        self.initial_capital = initial_capital
        self.periods = periods
        self.default_quantity = default_quantity
        self.all_positions = self.construct_all_positions()
        self.current_positions: dict[str, int] = dict.fromkeys(self.symbol_list, 0)
        self.all_holdings = self.construct_all_holdings()
        self.current_holdings = self.construct_current_holdings()
        self.equity_curve = pd.DataFrame()

    def construct_all_positions(self) -> list[LedgerRow]:
        return [{**dict.fromkeys(self.symbol_list, 0), "datetime": self.start_date}]

    def construct_all_holdings(self) -> list[LedgerRow]:
        return [
            {
                **dict.fromkeys(self.symbol_list, 0.0),
                "datetime": self.start_date,
                "cash": self.initial_capital,
                "commission": 0.0,
                "total": self.initial_capital,
            }
        ]

    def construct_current_holdings(self) -> dict[str, float]:
        return {
            **dict.fromkeys(self.symbol_list, 0.0),
            "cash": self.initial_capital,
            "commission": 0.0,
            "total": self.initial_capital,
        }

    def _market_value(self, symbol: str) -> float:
        price = self.bars.get_latest_bar_value(symbol, "adj_close")
        return 0.0 if pd.isna(price) else self.current_positions[symbol] * price

    def update_timeindex(self) -> None:
        latest_datetime = self.bars.get_latest_bar_datetime(self.symbol_list[0])
        positions: LedgerRow = {
            **{symbol: self.current_positions[symbol] for symbol in self.symbol_list},
            "datetime": latest_datetime,
        }
        self.all_positions.append(positions)

        cash = self.current_holdings["cash"]
        total = cash
        holdings: LedgerRow = {
            "datetime": latest_datetime,
            "cash": cash,
            "commission": self.current_holdings["commission"],
        }
        for symbol in self.symbol_list:
            market_value = self._market_value(symbol)
            holdings[symbol] = market_value
            total += market_value
        holdings["total"] = total
        self.current_holdings["total"] = float(total)
        self.all_holdings.append(holdings)

    def update_positions_from_fill(self, fill: FillEvent) -> None:
        fill_dir = 1 if fill.direction is OrderDirection.BUY else -1
        self.current_positions[fill.symbol] += fill_dir * fill.quantity

    def update_holdings_from_fill(self, fill: FillEvent) -> None:
        fill_dir = 1 if fill.direction is OrderDirection.BUY else -1
        cost = fill_dir * fill.fill_price * fill.quantity
        commission = fill.paid_commission()
        self.current_holdings[fill.symbol] += cost
        self.current_holdings["commission"] += commission
        self.current_holdings["cash"] -= cost + commission
        self.current_holdings["total"] = self.current_holdings["cash"] + sum(
            self._market_value(symbol) for symbol in self.symbol_list
        )

    def _constrain_fill(self, fill: FillEvent) -> FillEvent | None:
        price = fill.fill_price
        if pd.isna(price) or price <= 0:
            return None

        cash = self.current_holdings["cash"]
        position = self.current_positions[fill.symbol]

        if fill.direction is OrderDirection.BUY:
            max_size = min(fill.quantity, abs(position)) if position < 0 else fill.quantity
            size = max_shares_for_cash(cash, price, max_size)
            if size <= 0:
                return None
            return fill if size == fill.quantity else fill.with_quantity(size)

        if position > 0:
            size = min(fill.quantity, position)
            if size <= 0:
                return None
            if cash + size * price < ib_commission(size):
                return None
            return fill if size == fill.quantity else fill.with_quantity(size)

        size = max_cash_secured_short(cash, price, fill.quantity)
        if size <= 0:
            return None
        return fill if size == fill.quantity else fill.with_quantity(size)

    def update_fill(self, event: FillEvent) -> bool:
        fill = self._constrain_fill(event)
        if fill is None:
            return False
        self.update_positions_from_fill(fill)
        self.update_holdings_from_fill(fill)
        return True

    def generate_naive_order(self, signal: SignalEvent) -> OrderEvent | None:
        symbol = signal.symbol
        quantity = max(1, int(self.default_quantity * signal.strength))
        current_quantity = self.current_positions[symbol]
        cash = self.current_holdings["cash"]
        price = self.bars.get_latest_bar_value(symbol, "adj_close")
        if pd.isna(price) or price <= 0:
            return None

        match signal.signal_type:
            case SignalType.LONG if current_quantity == 0:
                size = max_shares_for_cash(cash, price, quantity)
                if size <= 0:
                    return None
                return OrderEvent(
                    symbol=symbol,
                    order_type=OrderType.MARKET,
                    quantity=size,
                    direction=OrderDirection.BUY,
                )
            case SignalType.SHORT if current_quantity == 0:
                size = max_cash_secured_short(cash, price, quantity)
                if size <= 0:
                    return None
                return OrderEvent(
                    symbol=symbol,
                    order_type=OrderType.MARKET,
                    quantity=size,
                    direction=OrderDirection.SELL,
                )
            case SignalType.EXIT if current_quantity > 0:
                return OrderEvent(
                    symbol=symbol,
                    order_type=OrderType.MARKET,
                    quantity=abs(current_quantity),
                    direction=OrderDirection.SELL,
                )
            case SignalType.EXIT if current_quantity < 0:
                size = max_shares_for_cash(cash, price, abs(current_quantity))
                if size <= 0:
                    return None
                return OrderEvent(
                    symbol=symbol,
                    order_type=OrderType.MARKET,
                    quantity=size,
                    direction=OrderDirection.BUY,
                )
            case _:
                return None

    def update_signal(self, event: SignalEvent) -> None:
        if order_event := self.generate_naive_order(event):
            self.events.put(order_event)

    def create_equity_curve_dataframe(self) -> None:
        curve = pd.DataFrame(self.all_holdings).set_index("datetime")
        curve["returns"] = curve["total"].pct_change().fillna(0.0)
        curve["equity_curve"] = (1.0 + curve["returns"]).cumprod()
        self.equity_curve = curve

    def output_summary_stats(self, output_path: str = "equity.csv") -> list[tuple[str, str]]:
        if self.equity_curve.empty:
            self.create_equity_curve_dataframe()

        total_return = float(self.equity_curve["equity_curve"].iloc[-1])
        returns = self.equity_curve["returns"]
        pnl = self.equity_curve["equity_curve"]
        sharpe_ratio = create_sharpe_ratio(returns, periods=self.periods)
        drawdown, max_dd, dd_duration = create_drawdowns(pnl)
        self.equity_curve["drawdown"] = drawdown
        self.equity_curve.to_csv(output_path)
        return [
            ("Total Return", f"{(total_return - 1.0) * 100.0:0.2f}%"),
            ("Sharpe Ratio", f"{sharpe_ratio:0.2f}"),
            ("Max Drawdown", f"{max_dd * 100.0:0.2f}%"),
            ("Drawdown Duration", f"{dd_duration:d}"),
        ]
