from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import override, cast

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from pandas import Index, Timestamp

from quant_backtesting.event import Event, MarketEvent

type BarRow = tuple[datetime | Timestamp, pd.Series]


class DataHandler(ABC):
    symbol_list: list[str]
    continue_backtest: bool
    latest_symbol_data: dict[str, list[BarRow]]

    @abstractmethod
    def get_latest_bar(self, symbol: str) -> BarRow: ...

    @abstractmethod
    def get_latest_bars(self, symbol: str, n: int = 1) -> list[BarRow]: ...

    @abstractmethod
    def get_latest_bar_datetime(self, symbol: str) -> datetime: ...

    @abstractmethod
    def get_latest_bar_value(self, symbol: str, val_type: str) -> float: ...

    @abstractmethod
    def get_latest_bars_values(
        self, symbol: str, val_type: str, n: int = 1
    ) -> NDArray[np.float64]: ...

    @abstractmethod
    def update_bars(self) -> None: ...


class HistoricCSVDataHandler(DataHandler):
    def __init__(
        self,
        events: Queue[Event],
        csv_dir: str | Path,
        symbol_list: list[str],
        start_date: datetime | None = None,
    ) -> None:
        self.events = events
        self.csv_dir = Path(csv_dir)
        self.symbol_list = symbol_list
        self.start_date = start_date
        self.symbol_data: dict[str, Iterator[BarRow]] = {}
        self.latest_symbol_data: dict[str, list[BarRow]] = {}
        self.continue_backtest = True
        self._open_convert_csv_files()

    def _csv_path(self, symbol: str) -> Path:
        for name in (symbol.lower(), symbol):
            path = self.csv_dir / f"{name}.csv"
            if path.exists():
                return path
        raise FileNotFoundError(f"CSV for {symbol} not found in {self.csv_dir}")

    def _open_convert_csv_files(self) -> None:
        frames: dict[str, pd.DataFrame] = {}
        comb_index: Index | None = None

        for symbol in self.symbol_list:
            frame = pd.read_csv(self._csv_path(symbol), header=0, index_col=0, parse_dates=True)
            frame.columns = [col.strip().lower().replace(" ", "_") for col in frame.columns]
            frame = frame.sort_index()
            if "adj_close" in frame.columns:
                frame["returns"] = frame["adj_close"].pct_change().fillna(0.0)
            frames[symbol] = frame
            comb_index = frame.index if comb_index is None else comb_index.union(frame.index)

        if comb_index is None:
            raise ValueError("no CSV data loaded")

        for symbol in self.symbol_list:
            aligned = frames[symbol].reindex(index=comb_index).ffill()
            if self.start_date is not None:
                aligned = aligned.loc[aligned.index >= self.start_date]
            self.symbol_data[symbol] = cast(Iterator[BarRow], aligned.iterrows())
            self.latest_symbol_data[symbol] = []

    @override
    def get_latest_bar(self, symbol: str) -> BarRow:
        bars = self.latest_symbol_data[symbol]
        if not bars:
            raise KeyError(f"no bars available for {symbol}")
        return bars[-1]

    @override
    def get_latest_bars(self, symbol: str, n: int = 1) -> list[BarRow]:
        bars = self.latest_symbol_data.get(symbol)
        if bars is None:
            raise KeyError(f"{symbol} is not available in the historical data set")
        return bars[-n:]

    @override
    def get_latest_bar_datetime(self, symbol: str) -> datetime:
        timestamp = self.get_latest_bar(symbol)[0]
        return timestamp.to_pydatetime() if isinstance(timestamp, Timestamp) else timestamp

    @override
    def get_latest_bar_value(self, symbol: str, val_type: str) -> float:
        return float(getattr(self.get_latest_bar(symbol)[1], val_type))

    @override
    def get_latest_bars_values(
        self, symbol: str, val_type: str, n: int = 1
    ) -> NDArray[np.float64]:
        bars = self.get_latest_bars(symbol, n)
        return np.array(
            [float(getattr(bar[1], val_type)) for bar in bars],
            dtype=np.float64,
        )

    @override
    def update_bars(self) -> None:
        got_bar = False
        for symbol in self.symbol_list:
            try:
                bar = next(self.symbol_data[symbol])
            except StopIteration:
                self.continue_backtest = False
            else:
                self.latest_symbol_data[symbol].append(bar)
                got_bar = True
        if got_bar:
            self.events.put(MarketEvent())
        else:
            self.continue_backtest = False
