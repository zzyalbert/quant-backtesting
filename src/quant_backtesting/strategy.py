from abc import ABC, abstractmethod
from queue import Queue

from quant_backtesting.data import DataHandler
from quant_backtesting.event import Event, MarketEvent


class Strategy(ABC):
    def __init__(self, bars: DataHandler, events: Queue[Event]) -> None:
        self.bars = bars
        self.events = events

    @abstractmethod
    def calculate_signals(self, event: MarketEvent) -> None: ...
