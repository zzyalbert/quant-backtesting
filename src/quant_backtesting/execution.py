from abc import ABC, abstractmethod
from queue import Queue

import pandas as pd

from quant_backtesting.data import DataHandler
from quant_backtesting.event import Event, FillEvent, OrderEvent, OrderType


class ExecutionHandler(ABC):
    @abstractmethod
    def execute_order(self, event: OrderEvent) -> None: ...

    def process_pending_orders(self) -> None:
        return None


class SimulatedExecutionHandler(ExecutionHandler):
    """Fills at the next available bar close to avoid look-ahead bias."""

    def __init__(
        self,
        events: Queue[Event],
        bars: DataHandler,
        exchange: str = "SIM",
    ) -> None:
        self.events = events
        self.bars = bars
        self.exchange = exchange
        self._pending: list[OrderEvent] = []

    def execute_order(self, event: OrderEvent) -> None:
        if event.order_type != OrderType.MARKET:
            raise ValueError(f"unsupported order type: {event.order_type}")
        self._pending.append(event)

    def process_pending_orders(self) -> None:
        pending, self._pending = self._pending, []
        for order in pending:
            try:
                price = self.bars.get_latest_bar_value(order.symbol, "adj_close")
                timeindex = self.bars.get_latest_bar_datetime(order.symbol)
            except KeyError:
                continue
            if pd.isna(price) or price <= 0:
                continue
            self.events.put(
                FillEvent(
                    timeindex=timeindex,
                    symbol=order.symbol,
                    exchange=self.exchange,
                    quantity=order.quantity,
                    direction=order.direction,
                    fill_price=float(price),
                )
            )
