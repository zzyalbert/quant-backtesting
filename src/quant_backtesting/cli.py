import logging
import os
from datetime import datetime
from pathlib import Path

from quant_backtesting.backtest import Backtest
from quant_backtesting.data import HistoricCSVDataHandler
from quant_backtesting.execution import SimulatedExecutionHandler
from quant_backtesting.portfolio import Portfolio
from quant_backtesting.strategies.mac import MovingAverageCrossStrategy
from quant_backtesting.strategies.snp_forecast import SPYDailyForecastStrategy


def _csv_dir() -> str:
    env = os.environ.get("QUANT_BACKTESTING_CSV_DIR")
    if env:
        path = Path(env)
        if path.is_dir():
            return str(path)
        raise FileNotFoundError(f"QUANT_BACKTESTING_CSV_DIR is not a directory: {path}")
    cwd = Path.cwd() / "csv"
    if cwd.is_dir():
        return str(cwd)
    raise FileNotFoundError(
        "csv directory not found; set QUANT_BACKTESTING_CSV_DIR or run from the repo root"
    )


def _configure_logging() -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def run_mac() -> None:
    _configure_logging()
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
    _configure_logging()
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
