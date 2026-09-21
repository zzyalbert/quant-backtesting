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
