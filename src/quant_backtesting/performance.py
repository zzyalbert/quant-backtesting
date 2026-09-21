import numpy as np
import pandas as pd


def create_sharpe_ratio(returns: pd.Series, periods: int = 252) -> float:
    std = float(returns.std(ddof=1))
    if std == 0.0 or np.isnan(std):
        return 0.0
    return float(np.sqrt(periods) * returns.mean() / std)


def create_drawdowns(equity_curve: pd.Series) -> tuple[pd.Series, float, int]:
    if equity_curve.empty:
        return pd.Series(dtype=float), 0.0, 0

    running_max = equity_curve.cummax()
    drawdown = ((running_max - equity_curve) / running_max.replace(0, np.nan)).fillna(0.0)

    underwater = drawdown.gt(0).to_numpy()
    duration = np.zeros(len(underwater), dtype=int)
    current = 0
    for i, is_dd in enumerate(underwater):
        current = current + 1 if is_dd else 0
        duration[i] = current

    duration_series = pd.Series(duration, index=equity_curve.index)
    return drawdown, float(drawdown.max()), int(duration_series.max())
