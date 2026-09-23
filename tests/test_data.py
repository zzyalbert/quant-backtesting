from datetime import datetime
from pathlib import Path
from queue import Queue

import pandas as pd
import pytest

from quant_backtesting.data import HistoricCSVDataHandler
from quant_backtesting.event import Event, MarketEvent


def _write_csv(path: Path, rows: list[tuple[str, float]]) -> None:
    lines = ["Date,Open,High,Low,Close,Volume,Adj Close"]
    for date, price in rows:
        lines.append(f"{date},{price},{price},{price},{price},1000,{price}")
    path.write_text("\n".join(lines) + "\n")


def test_window_size_and_descending_csv(tmp_path: Path) -> None:
    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    _write_csv(
        csv_dir / "aaa.csv",
        [
            ("2020-01-05", 5.0),
            ("2020-01-04", 4.0),
            ("2020-01-03", 3.0),
            ("2020-01-02", 2.0),
            ("2020-01-01", 1.0),
        ],
    )
    events: Queue[Event] = Queue()
    handler = HistoricCSVDataHandler(
        events, csv_dir, ["AAA"], start_date=datetime(2020, 1, 1), window_size=2
    )
    dates: list[datetime] = []
    while handler.continue_backtest:
        handler.update_bars()
        if not handler.continue_backtest:
            break
        dates.append(handler.get_latest_bar_datetime("AAA"))
        assert len(handler.latest_symbol_data["AAA"]) <= 2
        assert isinstance(events.get_nowait(), MarketEvent)

    assert dates == [
        datetime(2020, 1, 1),
        datetime(2020, 1, 2),
        datetime(2020, 1, 3),
        datetime(2020, 1, 4),
        datetime(2020, 1, 5),
    ]
    assert [bar[1].adj_close for bar in handler.get_latest_bars("AAA", 2)] == [4.0, 5.0]


def test_multi_symbol_bars_stay_aligned(tmp_path: Path) -> None:
    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    _write_csv(
        csv_dir / "aaa.csv",
        [("2020-01-01", 1.0), ("2020-01-02", 2.0), ("2020-01-03", 3.0)],
    )
    _write_csv(
        csv_dir / "bbb.csv",
        [("2020-01-02", 20.0), ("2020-01-03", 30.0)],
    )
    events: Queue[Event] = Queue()
    handler = HistoricCSVDataHandler(events, csv_dir, ["AAA", "BBB"], window_size=10)

    handler.update_bars()
    assert handler.get_latest_bar_datetime("AAA") == handler.get_latest_bar_datetime("BBB")
    assert handler.get_latest_bar_value("AAA", "adj_close") == 1.0
    assert pd.isna(handler.get_latest_bar_value("BBB", "adj_close"))

    handler.update_bars()
    assert handler.get_latest_bar_value("AAA", "adj_close") == 2.0
    assert handler.get_latest_bar_value("BBB", "adj_close") == 20.0

    handler.update_bars()
    assert handler.get_latest_bar_value("AAA", "adj_close") == 3.0
    assert handler.get_latest_bar_value("BBB", "adj_close") == 30.0
    assert handler.continue_backtest

    handler.update_bars()
    assert handler.continue_backtest is False


def test_returns_use_pre_start_price(tmp_path: Path) -> None:
    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    _write_csv(
        csv_dir / "aaa.csv",
        [("2019-12-31", 10.0), ("2020-01-01", 11.0), ("2020-01-02", 12.1)],
    )
    events: Queue[Event] = Queue()
    handler = HistoricCSVDataHandler(
        events, csv_dir, ["AAA"], start_date=datetime(2020, 1, 1), window_size=10
    )
    handler.update_bars()
    assert handler.get_latest_bar_value("AAA", "returns") == pytest.approx(0.1)
    handler.update_bars()
    assert handler.get_latest_bar_value("AAA", "returns") == pytest.approx(0.1)
