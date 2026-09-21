from abc import ABC, abstractmethod
from queue import Queue
from typing import override

from quant_backtesting.data import DataHandler
from quant_backtesting.event import Event, FillEvent, OrderEvent, OrderType


class ExecutionHandler(ABC):
    @abstractmethod
    def execute_order(self, event: OrderEvent) -> None: ...


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

    @override
    def execute_order(self, event: OrderEvent) -> None:
        if event.order_type != OrderType.MARKET:
            raise ValueError(f"unsupported order type: {event.order_type}")
        self._pending.append(event)

    def process_pending_orders(self) -> None:
        pending, self._pending = self._pending, []
        for order in pending:
            self.events.put(
                FillEvent(
                    timeindex=self.bars.get_latest_bar_datetime(order.symbol),
                    symbol=order.symbol,
                    exchange=self.exchange,
                    quantity=order.quantity,
                    direction=order.direction,
                    fill_cost=self.bars.get_latest_bar_value(order.symbol, "adj_close"),
                )
            )
