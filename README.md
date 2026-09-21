# Quant Backtesting

Event-driven quantitative backtesting framework for Python 3.14+.

Managed with [uv](https://docs.astral.sh/uv/).

## Setup

```bash
uv sync
```

## Run

```bash
uv run python examples/run_mac.py
uv run python examples/run_snp_forecast.py
```

After a backtest finishes, `equity.csv` is written to the working directory.

```bash
uv run python examples/plot_performance.py
```

## Architecture

- `DataHandler` emits `MarketEvent`
- `Strategy` consumes `MarketEvent` and emits `SignalEvent`
- `Portfolio` consumes `SignalEvent` and emits `OrderEvent`
- `ExecutionHandler` consumes `OrderEvent` and emits `FillEvent`
- Simulated fills occur on the next bar close to reduce look-ahead bias

## Notes and limitations

- Multi-symbol backtests end when the first symbol's data is exhausted;
  shorter histories are forward-filled onto the combined index, and bars
  before a symbol's first listing are treated as price NaN (no trading,
  zero market value).
- `HistoricCSVDataHandler` keeps only the most recent `window_size` bars
  (default 400) in memory. Raise it if your strategy needs a longer
  lookback.
- Buy orders are capped by available cash including IB commission.

