from datetime import datetime
from pathlib import Path
from queue import Queue

from quant_backtesting.backtest import Backtest
from quant_backtesting.data import HistoricCSVDataHandler
from quant_backtesting.event import Event, MarketEvent, SignalEvent, SignalType, ib_commission
from quant_backtesting.execution import SimulatedExecutionHandler
from quant_backtesting.portfolio import Portfolio
from quant_backtesting.strategy import Strategy


def _write_csv(path: Path, rows: list[tuple[str, float]]) -> None:
    lines = ["Date,Open,High,Low,Close,Volume,Adj Close"]
    for date, price in rows:
        lines.append(f"{date},{price},{price},{price},{price},1000,{price}")
    path.write_text("\n".join(lines) + "\n")


class BuyOnceStrategy(Strategy):
    def __init__(self, bars, events: Queue[Event]) -> None:
        super().__init__(bars, events)
        self.sent = False

    def calculate_signals(self, event: MarketEvent) -> None:
        if self.sent:
            return
        symbol = self.bars.symbol_list[0]
        self.events.put(
            SignalEvent(
                strategy_id=1,
                symbol=symbol,
                datetime=self.bars.get_latest_bar_datetime(symbol),
                signal_type=SignalType.LONG,
                strength=1.0,
            )
        )
        self.sent = True


class AlwaysLongStrategy(Strategy):
    def calculate_signals(self, event: MarketEvent) -> None:
        symbol = self.bars.symbol_list[0]
        self.events.put(
            SignalEvent(
                strategy_id=1,
                symbol=symbol,
                datetime=self.bars.get_latest_bar_datetime(symbol),
                signal_type=SignalType.LONG,
                strength=1.0,
            )
        )


def _backtest(
    csv_dir: Path,
    strategy: type[Strategy],
    capital: float = 100_000.0,
    symbols: list[str] | None = None,
) -> Backtest:
    return Backtest(
        csv_dir=str(csv_dir),
        symbol_list=symbols or ["AAA"],
        initial_capital=capital,
        start_date=datetime(2020, 1, 1),
        data_handler=HistoricCSVDataHandler,
        execution_handler=SimulatedExecutionHandler,
        portfolio=Portfolio,
        strategy=strategy,
        window_size=10,
    )


def test_fill_uses_next_bar_close(tmp_path: Path) -> None:
    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    _write_csv(
        csv_dir / "aaa.csv",
        [("2020-01-01", 10.0), ("2020-01-02", 12.0), ("2020-01-03", 13.0)],
    )
    bt = _backtest(csv_dir, BuyOnceStrategy)
    bt._run_backtest()
    assert bt.signals == 1
    assert bt.orders == 1
    assert bt.fills == 1
    assert bt.portfolio.current_positions["AAA"] == 100
    assert bt.portfolio.current_holdings["AAA"] == 12.0 * 100
    assert bt.portfolio.current_holdings["cash"] == 100_000.0 - 1_200.0 - ib_commission(100)


def test_gap_up_fill_does_not_go_cash_negative(tmp_path: Path) -> None:
    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    _write_csv(
        csv_dir / "aaa.csv",
        [("2020-01-01", 10.0), ("2020-01-02", 1000.0)],
    )
    bt = _backtest(csv_dir, AlwaysLongStrategy, capital=100.0)
    bt.portfolio.default_quantity = 100
    bt._run_backtest()
    assert bt.portfolio.current_holdings["cash"] >= 0
    assert bt.portfolio.current_positions["AAA"] == 0
    assert bt.fills == 0


def test_last_bar_order_does_not_fill(tmp_path: Path) -> None:
    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    _write_csv(csv_dir / "aaa.csv", [("2020-01-01", 10.0)])
    bt = _backtest(csv_dir, BuyOnceStrategy)
    bt._run_backtest()
    assert bt.signals == 1
    assert bt.orders == 1
    assert bt.fills == 0
    assert bt.portfolio.current_positions["AAA"] == 0


def test_multi_symbol_backtest_consumes_union_calendar(tmp_path: Path) -> None:
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

    class Quiet(Strategy):
        def calculate_signals(self, event: MarketEvent) -> None:
            return None

    bt = _backtest(csv_dir, Quiet, symbols=["AAA", "BBB"])
    bt._run_backtest()
    dates = [row["datetime"] for row in bt.portfolio.all_positions[1:]]
    assert dates == [datetime(2020, 1, 1), datetime(2020, 1, 2), datetime(2020, 1, 3)]
    assert bt.data_handler.get_latest_bar_datetime("AAA") == bt.data_handler.get_latest_bar_datetime(
        "BBB"
    )
