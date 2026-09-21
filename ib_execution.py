"""Interactive Brokers live execution is not part of this Python 3 port.

The original handler depended on IbPy and Python 2 dict.has_key.
Use SimulatedExecutionHandler for backtests.
"""

from quant_backtesting.execution import SimulatedExecutionHandler

__all__ = ["SimulatedExecutionHandler"]
