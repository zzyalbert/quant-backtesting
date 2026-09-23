from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import TypeAlias, cast

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from pandas import Index, Timestamp

from quant_backtesting.event import Event, MarketEvent

BarRow: TypeAlias = tuple[datetime | Timestamp, pd.Series]


def csv_path_for(csv_dir: str | Path, symbol: str) -> Path:
    base = Path(csv_dir)
    for name in (symbol.lower(), symbol):
        path = base / f"{name}.csv"
        if path.exists():
            return path
    raise FileNotFoundError(f"CSV for {symbol} not found in {base}")


def load_symbol_frame(csv_dir: str | Path, symbol: str) -> pd.DataFrame:
    """Load one symbol's CSV, normalize columns and sort by date."""
    frame = pd.read_csv(csv_path_for(csv_dir, symbol), header=0, index_col=0, parse_dates=True)
    frame.columns = [col.strip().lower().replace(" ", "_") for col in frame.columns]
    return frame.sort_index()


class DataHandler(ABC):
    symbol_list: list[str]
    continue_backtest: bool
    latest_symbol_data: dict[str, list[BarRow]]

    def __init__(
        self,
        events: Queue[Event],
        csv_dir: str | Path,
        symbol_list: list[str],
        start_date: datetime | None = None,
        window_size: int = 400,
    ) -> None:
        self.events = events
        self.csv_dir = Path(csv_dir)
        self.symbol_list = symbol_list
        self.start_date = start_date
        self.window_size = max(1, window_size)

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
        window_size: int = 400,
    ) -> None:
        super().__init__(events, csv_dir, symbol_list, start_date, window_size)
        self.symbol_frames: dict[str, pd.DataFrame] = {}
        self.latest_symbol_data: dict[str, list[BarRow]] = {}
        self._index = 0
        self._n_bars = 0
        self.continue_backtest = True
        self._open_convert_csv_files()

    def _open_convert_csv_files(self) -> None:
        frames: dict[str, pd.DataFrame] = {}
        comb_index: Index | None = None

        for symbol in self.symbol_list:
            frame = load_symbol_frame(self.csv_dir, symbol)
            frames[symbol] = frame
            comb_index = frame.index if comb_index is None else comb_index.union(frame.index)

        if comb_index is None:
            raise ValueError("no CSV data loaded")

        full_index = comb_index.sort_values()
        used_index = full_index
        if self.start_date is not None:
            used_index = full_index[full_index >= self.start_date]

        price_cols = ("open", "high", "low", "close", "adj_close", "volume")
        for symbol in self.symbol_list:
            aligned = frames[symbol].reindex(index=full_index)
            present = [col for col in price_cols if col in aligned.columns]
            aligned[present] = aligned[present].ffill()
            if "adj_close" in aligned.columns:
                aligned["returns"] = aligned["adj_close"].pct_change().fillna(0.0)
            aligned = aligned.loc[used_index]
            self.symbol_frames[symbol] = aligned
            self.latest_symbol_data[symbol] = []

        self._n_bars = len(used_index)
        self.continue_backtest = self._n_bars > 0

    def get_latest_bar(self, symbol: str) -> BarRow:
        bars = self.latest_symbol_data[symbol]
        if not bars:
            raise KeyError(f"no bars available for {symbol}")
        return bars[-1]

    def get_latest_bars(self, symbol: str, n: int = 1) -> list[BarRow]:
        bars = self.latest_symbol_data.get(symbol)
        if bars is None:
            raise KeyError(f"{symbol} is not available in the historical data set")
        return bars[-n:]

    def get_latest_bar_datetime(self, symbol: str) -> datetime:
        timestamp = self.get_latest_bar(symbol)[0]
        return timestamp.to_pydatetime() if isinstance(timestamp, Timestamp) else timestamp

    def get_latest_bar_value(self, symbol: str, val_type: str) -> float:
        return float(getattr(self.get_latest_bar(symbol)[1], val_type))

    def get_latest_bars_values(
        self, symbol: str, val_type: str, n: int = 1
    ) -> NDArray[np.float64]:
        bars = self.get_latest_bars(symbol, n)
        return np.array(
            [float(getattr(bar[1], val_type)) for bar in bars],
            dtype=np.float64,
        )

    def update_bars(self) -> None:
        if self._index >= self._n_bars:
            self.continue_backtest = False
            return

        for symbol in self.symbol_list:
            frame = self.symbol_frames[symbol]
            timestamp = frame.index[self._index]
            row = frame.iloc[self._index]
            bars = self.latest_symbol_data[symbol]
            bars.append((cast(datetime | Timestamp, timestamp), row))
            if len(bars) > self.window_size:
                del bars[0]

        self._index += 1
        self.events.put(MarketEvent())
