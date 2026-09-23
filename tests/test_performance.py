import pandas as pd
import pytest

from quant_backtesting.performance import create_drawdowns, create_sharpe_ratio


def test_sharpe_zero_when_flat() -> None:
    returns = pd.Series([0.0, 0.0, 0.0])
    assert create_sharpe_ratio(returns) == 0.0


def test_drawdown_empty_and_peak_to_trough() -> None:
    empty_dd, empty_max, empty_dur = create_drawdowns(pd.Series(dtype=float))
    assert empty_dd.empty
    assert empty_max == 0.0
    assert empty_dur == 0

    equity = pd.Series([1.0, 1.2, 0.9, 0.9, 1.3])
    drawdown, max_dd, duration = create_drawdowns(equity)
    assert max_dd == pytest.approx(0.25)
    assert duration == 2
    assert drawdown.iloc[2] == pytest.approx(0.25)
