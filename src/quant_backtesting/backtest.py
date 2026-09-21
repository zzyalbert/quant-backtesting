from datetime import datetime
from pprint import pprint
from queue import Empty, Queue

from quant_backtesting.data import DataHandler, HistoricCSVDataHandler
from quant_backtesting.event import (
    Event,
    FillEvent,
    MarketEvent,
    OrderEvent,
    SignalEvent,
)
from quant_backtesting.execution import SimulatedExecutionHandler
from quant_backtesting.portfolio import Portfolio
from quant_backtesting.strategy import Strategy


class Backtest:
    def __init__(
        self,
        csv_dir: str,
        symbol_list: list[str],
        initial_capital: float,
        start_date: datetime,
        data_handler: type[HistoricCSVDataHandler],
        execution_handler: type[SimulatedExecutionHandler],
        portfolio: type[Portfolio],
        strategy: type[Strategy],
        periods: int = 252,
    ) -> None:
        self.csv_dir = csv_dir
        self.symbol_list = symbol_list
        self.initial_capital = initial_capital
        self.start_date = start_date
        self.data_handler_cls = data_handler
        self.execution_handler_cls = execution_handler
        self.portfolio_cls = portfolio
        self.strategy_cls = strategy
        self.periods = periods
        self.events: Queue[Event] = Queue()
        self.signals = 0
        self.orders = 0
        self.fills = 0
        self._generate_trading_instances()

    def _generate_trading_instances(self) -> None:
        print("Creating DataHandler, Strategy, Portfolio and ExecutionHandler")
        self.data_handler: DataHandler = self.data_handler_cls(
            self.events, self.csv_dir, self.symbol_list, self.start_date
        )
        self.strategy = self.strategy_cls(self.data_handler, self.events)
        self.portfolio = self.portfolio_cls(
            self.data_handler,
            self.events,
            self.start_date,
            self.initial_capital,
            periods=self.periods,
        )
        self.execution_handler = self.execution_handler_cls(self.events, self.data_handler)

    def _drain_events(self) -> list[Event]:
        drained: list[Event] = []
        while True:
            try:
                drained.append(self.events.get_nowait())
            except Empty:
                return drained

    def _handle_event(self, event: Event) -> None:
        match event:
            case MarketEvent():
                self.strategy.calculate_signals(event)
            case SignalEvent():
                self.signals += 1
                self.portfolio.update_signal(event)
            case OrderEvent():
                self.orders += 1
                self.execution_handler.execute_order(event)
            case FillEvent():
                self.fills += 1
                self.portfolio.update_fill(event)

    def _run_backtest(self) -> None:
        while self.data_handler.continue_backtest:
            self.data_handler.update_bars()
            self.execution_handler.process_pending_orders()
            events = self._drain_events()
            fills = [event for event in events if isinstance(event, FillEvent)]
            others = [event for event in events if not isinstance(event, FillEvent)]
            for event in fills:
                self._handle_event(event)
            saw_market = False
            for event in others:
                saw_market = saw_market or isinstance(event, MarketEvent)
                self._handle_event(event)
            while leftover := self._drain_events():
                for event in leftover:
                    self._handle_event(event)
            if saw_market:
                self.portfolio.update_timeindex()

    def _output_performance(self) -> None:
        self.portfolio.create_equity_curve_dataframe()
        print("Creating summary stats...")
        stats = self.portfolio.output_summary_stats()
        print("Creating equity curve...")
        print(self.portfolio.equity_curve.tail(10))
        pprint(stats)
        print(f"Signals: {self.signals}")
        print(f"Orders: {self.orders}")
        print(f"Fills: {self.fills}")

    def simulate_trading(self) -> None:
        self._run_backtest()
        self._output_performance()
