# Quant Backtesting

Event-driven quantitative backtesting framework for Python 3.11+.

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

CSV data is loaded from `./csv` or `QUANT_BACKTESTING_CSV_DIR`.

## Architecture

- `DataHandler` emits `MarketEvent`
- `Strategy` consumes `MarketEvent` and emits `SignalEvent`
- `Portfolio` consumes `SignalEvent` and emits `OrderEvent`
- `ExecutionHandler` consumes `OrderEvent` and emits `FillEvent`
- Simulated fills occur on the next bar close to reduce look-ahead bias
- Fills are cash-checked at the fill price; oversized orders are reduced or rejected

## Notes and limitations

- Multi-symbol backtests share a union calendar. Shorter histories are
  forward-filled onto later dates; bars before a symbol's first listing
  are price NaN (no trading, zero market value).
- `HistoricCSVDataHandler` keeps only the most recent `window_size` bars
  (default 400) in memory. Raise it via `Backtest(..., window_size=N)`
  if your strategy needs a longer lookback.
- Buy, short, and short-cover sizes are capped so notional plus IB
  commission fits in cash at both signal time and fill time.
- `FillEvent.fill_price` is the per-share fill price.
