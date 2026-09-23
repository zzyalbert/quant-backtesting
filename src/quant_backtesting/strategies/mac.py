import logging
from queue import Queue

import numpy as np

from quant_backtesting.data import DataHandler
from quant_backtesting.event import Event, MarketEvent, MarketPosition, SignalEvent, SignalType
from quant_backtesting.strategy import Strategy

logger = logging.getLogger(__name__)


class MovingAverageCrossStrategy(Strategy):
    def __init__(
        self,
        bars: DataHandler,
        events: Queue[Event],
        short_window: int = 100,
        long_window: int = 400,
    ) -> None:
        super().__init__(bars, events)
        self.symbol_list = self.bars.symbol_list
        self.short_window = short_window
        self.long_window = long_window
        self.bought = dict.fromkeys(self.symbol_list, MarketPosition.FLAT)

    def calculate_signals(self, event: MarketEvent) -> None:
        for symbol in self.symbol_list:
            bars = self.bars.get_latest_bars_values(symbol, "adj_close", n=self.long_window)
            if bars.size < self.long_window or np.isnan(bars).any():
                continue

            short_sma = float(np.mean(bars[-self.short_window :]))
            long_sma = float(np.mean(bars[-self.long_window :]))
            bar_date = self.bars.get_latest_bar_datetime(symbol)

            match (short_sma > long_sma, self.bought[symbol]):
                case (True, MarketPosition.FLAT):
                    logger.info("LONG: %s", bar_date)
                    self.events.put(
                        SignalEvent(
                            strategy_id=1,
                            symbol=symbol,
                            datetime=bar_date,
                            signal_type=SignalType.LONG,
                            strength=1.0,
                        )
                    )
                    self.bought[symbol] = MarketPosition.LONG
                case (False, MarketPosition.LONG):
                    logger.info("EXIT: %s", bar_date)
                    self.events.put(
                        SignalEvent(
                            strategy_id=1,
                            symbol=symbol,
                            datetime=bar_date,
                            signal_type=SignalType.EXIT,
                            strength=1.0,
                        )
                    )
                    self.bought[symbol] = MarketPosition.FLAT
                case _:
                    continue
