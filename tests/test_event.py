from datetime import datetime

import pytest

from quant_backtesting.event import FillEvent, OrderDirection, OrderEvent, OrderType, ib_commission


def test_ib_commission_floor_and_tiers() -> None:
    assert ib_commission(1) == 1.3
    assert ib_commission(100) == pytest.approx(1.3)
    assert ib_commission(500) == pytest.approx(6.5)
    assert ib_commission(501) == pytest.approx(4.008)


def test_fill_event_defaults_commission_from_quantity() -> None:
    fill = FillEvent(
        timeindex=datetime(2020, 1, 2),
        symbol="AAPL",
        exchange="SIM",
        quantity=100,
        direction=OrderDirection.BUY,
        fill_price=10.0,
    )
    assert fill.paid_commission() == pytest.approx(ib_commission(100))
    resized = fill.with_quantity(10)
    assert resized.quantity == 10
    assert resized.fill_price == 10.0
    assert resized.paid_commission() == pytest.approx(ib_commission(10))


def test_order_and_fill_reject_non_positive_quantity() -> None:
    with pytest.raises(ValueError):
        OrderEvent(
            symbol="AAPL",
            order_type=OrderType.MARKET,
            quantity=0,
            direction=OrderDirection.BUY,
        )
    with pytest.raises(ValueError):
        FillEvent(
            timeindex=datetime(2020, 1, 2),
            symbol="AAPL",
            exchange="SIM",
            quantity=0,
            direction=OrderDirection.BUY,
            fill_price=10.0,
        )
