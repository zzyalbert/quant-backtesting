from datetime import datetime
from pathlib import Path

from quant_backtesting.backtest import Backtest
from quant_backtesting.data import HistoricCSVDataHandler
from quant_backtesting.execution import SimulatedExecutionHandler
from quant_backtesting.portfolio import Portfolio
from quant_backtesting.strategies.mac import MovingAverageCrossStrategy
from quant_backtesting.strategies.snp_forecast import SPYDailyForecastStrategy


def _csv_dir() -> str:
    candidates = (Path.cwd() / "csv", Path(__file__).resolve().parents[2] / "csv")
    for path in candidates:
        if path.is_dir():
            return str(path)
    raise FileNotFoundError("csv directory not found")


def run_mac() -> None:
    Backtest(
        csv_dir=_csv_dir(),
        symbol_list=["AAPL"],
        initial_capital=100_000.0,
        start_date=datetime(1990, 1, 1),
        data_handler=HistoricCSVDataHandler,
        execution_handler=SimulatedExecutionHandler,
        portfolio=Portfolio,
        strategy=MovingAverageCrossStrategy,
    ).simulate_trading()


def run_snp_forecast() -> None:
    Backtest(
        csv_dir=_csv_dir(),
        symbol_list=["SPY"],
        initial_capital=100_000.0,
        start_date=datetime(2006, 1, 3),
        data_handler=HistoricCSVDataHandler,
        execution_handler=SimulatedExecutionHandler,
        portfolio=Portfolio,
        strategy=SPYDailyForecastStrategy,
    ).simulate_trading()
