from datetime import datetime
from queue import Queue

import pandas as pd

from quant_backtesting.data import DataHandler
from quant_backtesting.event import Event, FillEvent, OrderDirection, OrderEvent, OrderType
from quant_backtesting.execution import SimulatedExecutionHandler


class StubBars(DataHandler):
    def __init__(self, price: float) -> None:
        self.price = price
        self.symbol_list = ["AAA"]
        self.continue_backtest = True
        self.latest_symbol_data = {}

    def get_latest_bar(self, symbol: str):
        raise NotImplementedError

    def get_latest_bars(self, symbol: str, n: int = 1):
        raise NotImplementedError

    def get_latest_bar_datetime(self, symbol: str) -> datetime:
        return datetime(2020, 1, 2)

    def get_latest_bar_value(self, symbol: str, val_type: str) -> float:
        return self.price

    def get_latest_bars_values(self, symbol: str, val_type: str, n: int = 1):
        raise NotImplementedError

    def update_bars(self) -> None:
        return None


def test_market_order_fills_at_latest_close() -> None:
    events: Queue[Event] = Queue()
    handler = SimulatedExecutionHandler(events, StubBars(12.5))
    handler.execute_order(
        OrderEvent(
            symbol="AAA",
            order_type=OrderType.MARKET,
            quantity=7,
            direction=OrderDirection.BUY,
        )
    )
    handler.process_pending_orders()
    fill = events.get_nowait()
    assert isinstance(fill, FillEvent)
    assert fill.fill_price == 12.5
    assert fill.quantity == 7


def test_nan_price_skips_fill() -> None:
    events: Queue[Event] = Queue()
    handler = SimulatedExecutionHandler(events, StubBars(float("nan")))
    handler.execute_order(
        OrderEvent(
            symbol="AAA",
            order_type=OrderType.MARKET,
            quantity=7,
            direction=OrderDirection.BUY,
        )
    )
    handler.process_pending_orders()
    assert events.empty()
    assert pd.isna(float("nan"))
