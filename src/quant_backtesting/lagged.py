from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from quant_backtesting.data import load_symbol_frame


def load_price_frame(symbol: str, csv_dir: str | Path = "csv") -> pd.DataFrame:
    return load_symbol_frame(csv_dir, symbol)


def create_lagged_series(
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    lags: int = 5,
    csv_dir: str | Path = "csv",
) -> pd.DataFrame:
    ts = load_price_frame(symbol, csv_dir)
    warmup = start_date - timedelta(days=365)
    ts = ts.loc[(ts.index >= warmup) & (ts.index <= end_date)].copy()
    if ts.empty:
        raise ValueError(f"no price data for {symbol} between {warmup} and {end_date}")

    tslag = pd.DataFrame(index=ts.index)
    tslag["today"] = ts["adj_close"]
    tslag["volume"] = ts["volume"]
    for lag in range(1, lags + 1):
        tslag[f"lag{lag}"] = ts["adj_close"].shift(lag)

    tsret = pd.DataFrame(index=tslag.index)
    tsret["volume"] = tslag["volume"]
    tsret["today"] = tslag["today"].pct_change() * 100.0
    tsret["today"] = tsret["today"].mask(tsret["today"].abs() < 0.0001, 0.0001)
    for lag in range(1, lags + 1):
        tsret[f"lag{lag}"] = tslag[f"lag{lag}"].pct_change() * 100.0
    tsret["direction"] = np.sign(tsret["today"])
    return tsret.loc[tsret.index >= start_date].dropna()
