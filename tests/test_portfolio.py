from datetime import datetime
from queue import Queue

import pandas as pd
import pytest

from quant_backtesting.data import DataHandler
from quant_backtesting.event import (
    Event,
    FillEvent,
    OrderDirection,
    SignalEvent,
    SignalType,
    ib_commission,
)
from quant_backtesting.portfolio import Portfolio, max_cash_secured_short, max_shares_for_cash


class StubBars(DataHandler):
    def __init__(self, prices: dict[str, float], symbol_list: list[str] | None = None) -> None:
        self.prices = prices
        self.symbol_list = symbol_list or list(prices)
        self.continue_backtest = True
        self.latest_symbol_data = {}
        self._dt = datetime(2020, 1, 2)

    def get_latest_bar(self, symbol: str):
        raise NotImplementedError

    def get_latest_bars(self, symbol: str, n: int = 1):
        raise NotImplementedError

    def get_latest_bar_datetime(self, symbol: str) -> datetime:
        return self._dt

    def get_latest_bar_value(self, symbol: str, val_type: str) -> float:
        return self.prices[symbol]

    def get_latest_bars_values(self, symbol: str, val_type: str, n: int = 1):
        raise NotImplementedError

    def update_bars(self) -> None:
        return None


def _portfolio(cash: float, price: float, symbol: str = "AAA") -> Portfolio:
    return Portfolio(
        StubBars({symbol: price}),
        Queue(),
        datetime(2020, 1, 1),
        initial_capital=cash,
        default_quantity=100,
    )


def test_max_shares_accounts_for_commission() -> None:
    price = 10.0
    cash = 20.0 + ib_commission(2) - 0.01
    assert max_shares_for_cash(cash, price, 10) == 1
    assert max_shares_for_cash(21.3, price, 10) == 2
    assert max_cash_secured_short(20.0, price, 10) == 2
    assert max_cash_secured_short(1.0, price, 10) == 0


def test_long_order_capped_by_cash_including_commission() -> None:
    port = _portfolio(cash=21.3, price=10.0)
    order = port.generate_naive_order(
        SignalEvent(
            strategy_id=1,
            symbol="AAA",
            datetime=datetime(2020, 1, 1),
            signal_type=SignalType.LONG,
            strength=1.0,
        )
    )
    assert order is not None
    assert order.quantity == 2
    assert order.direction is OrderDirection.BUY


def test_fill_gap_up_reduces_size_so_cash_stays_non_negative() -> None:
    port = _portfolio(cash=21.3, price=10.0)
    port.update_fill(
        FillEvent(
            timeindex=datetime(2020, 1, 2),
            symbol="AAA",
            exchange="SIM",
            quantity=2,
            direction=OrderDirection.BUY,
            fill_price=20.0,
        )
    )
    assert port.current_positions["AAA"] == 1
    assert port.current_holdings["cash"] == pytest.approx(21.3 - 20.0 - ib_commission(1))
    assert port.current_holdings["cash"] >= 0


def test_fill_gap_up_rejects_when_even_one_share_does_not_fit() -> None:
    port = _portfolio(cash=21.3, price=10.0)
    port.update_fill(
        FillEvent(
            timeindex=datetime(2020, 1, 2),
            symbol="AAA",
            exchange="SIM",
            quantity=2,
            direction=OrderDirection.BUY,
            fill_price=30.0,
        )
    )
    assert port.current_positions["AAA"] == 0
    assert port.current_holdings["cash"] == pytest.approx(21.3)


def test_short_requires_cash_secured_notional() -> None:
    port = _portfolio(cash=50.0, price=10.0)
    order = port.generate_naive_order(
        SignalEvent(
            strategy_id=1,
            symbol="AAA",
            datetime=datetime(2020, 1, 1),
            signal_type=SignalType.SHORT,
            strength=1.0,
        )
    )
    assert order is not None
    assert order.quantity == 5
    assert order.direction is OrderDirection.SELL

    port.update_fill(
        FillEvent(
            timeindex=datetime(2020, 1, 2),
            symbol="AAA",
            exchange="SIM",
            quantity=5,
            direction=OrderDirection.SELL,
            fill_price=10.0,
        )
    )
    assert port.current_positions["AAA"] == -5
    assert port.current_holdings["cash"] == pytest.approx(50.0 + 50.0 - ib_commission(5))


def test_short_cover_capped_when_price_gaps_up() -> None:
    port = _portfolio(cash=50.0, price=10.0)
    port.update_fill(
        FillEvent(
            timeindex=datetime(2020, 1, 2),
            symbol="AAA",
            exchange="SIM",
            quantity=5,
            direction=OrderDirection.SELL,
            fill_price=10.0,
        )
    )
    port.bars.prices["AAA"] = 40.0
    port.update_fill(
        FillEvent(
            timeindex=datetime(2020, 1, 3),
            symbol="AAA",
            exchange="SIM",
            quantity=5,
            direction=OrderDirection.BUY,
            fill_price=40.0,
        )
    )
    assert port.current_positions["AAA"] == -3
    assert port.current_holdings["cash"] >= 0


def test_nan_price_skips_order() -> None:
    port = _portfolio(cash=1000.0, price=float("nan"))
    order = port.generate_naive_order(
        SignalEvent(
            strategy_id=1,
            symbol="AAA",
            datetime=datetime(2020, 1, 1),
            signal_type=SignalType.LONG,
            strength=1.0,
        )
    )
    assert order is None
    assert pd.isna(port.bars.get_latest_bar_value("AAA", "adj_close"))
