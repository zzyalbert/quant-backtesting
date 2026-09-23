from datetime import datetime
from queue import Queue

import numpy as np
import pandas as pd
from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis

from quant_backtesting.data import DataHandler, HistoricCSVDataHandler
from quant_backtesting.event import Event, MarketEvent, SignalEvent, SignalType
from quant_backtesting.lagged import create_lagged_series
from quant_backtesting.strategy import Strategy


class SPYDailyForecastStrategy(Strategy):
    def __init__(
        self,
        bars: DataHandler,
        events: Queue[Event],
        csv_dir: str | None = None,
        model_start_date: datetime | None = None,
        model_end_date: datetime | None = None,
        model_start_test_date: datetime | None = None,
    ) -> None:
        super().__init__(bars, events)
        self.symbol_list = self.bars.symbol_list
        handler_csv_dir = (
            str(bars.csv_dir) if isinstance(bars, HistoricCSVDataHandler) else "csv"
        )
        self.csv_dir = csv_dir or handler_csv_dir
        self.model_start_date = model_start_date or datetime(2001, 1, 10)
        self.model_end_date = model_end_date or datetime(2005, 12, 31)
        self.model_start_test_date = model_start_test_date or datetime(2005, 1, 1)
        self.long_market = False
        self.bar_index = 0
        self.model = self.create_symbol_forecast_model()

    def create_symbol_forecast_model(self) -> QuadraticDiscriminantAnalysis:
        snpret = create_lagged_series(
            self.symbol_list[0],
            self.model_start_date,
            self.model_end_date,
            lags=5,
            csv_dir=self.csv_dir,
        )
        x = snpret[["lag1", "lag2"]]
        y = snpret["direction"]
        start_test = self.model_start_test_date
        model = QuadraticDiscriminantAnalysis()
        model.fit(x.loc[x.index < start_test], y.loc[y.index < start_test])
        return model

    def calculate_signals(self, event: MarketEvent) -> None:
        self.bar_index += 1
        if self.bar_index <= 5:
            return

        symbol = self.symbol_list[0]
        lags = self.bars.get_latest_bars_values(symbol, "returns", n=3)
        if lags.size < 3 or np.isnan(lags).any():
            return

        pred_frame = pd.DataFrame({"lag1": [lags[-2] * 100.0], "lag2": [lags[-3] * 100.0]})
        pred = float(self.model.predict(pred_frame)[0])
        bar_date = self.bars.get_latest_bar_datetime(symbol)

        match (pred > 0, self.long_market):
            case (True, False):
                self.long_market = True
                self.events.put(
                    SignalEvent(
                        strategy_id=1,
                        symbol=symbol,
                        datetime=bar_date,
                        signal_type=SignalType.LONG,
                        strength=1.0,
                    )
                )
            case (False, True) if pred < 0:
                self.long_market = False
                self.events.put(
                    SignalEvent(
                        strategy_id=1,
                        symbol=symbol,
                        datetime=bar_date,
                        signal_type=SignalType.EXIT,
                        strength=1.0,
                    )
                )
            case _:
                return
