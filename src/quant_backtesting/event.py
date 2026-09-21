from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class EventType(StrEnum):
    MARKET = "MARKET"
    SIGNAL = "SIGNAL"
    ORDER = "ORDER"
    FILL = "FILL"


class SignalType(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    EXIT = "EXIT"


class OrderType(StrEnum):
    MARKET = "MKT"
    LIMIT = "LMT"


class OrderDirection(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class Event:
    type: EventType


@dataclass(slots=True, kw_only=True)
class MarketEvent(Event):
    type: EventType = field(default=EventType.MARKET, init=False)


@dataclass(slots=True, kw_only=True)
class SignalEvent(Event):
    strategy_id: int
    symbol: str
    datetime: datetime
    signal_type: SignalType
    strength: float
    type: EventType = field(default=EventType.SIGNAL, init=False)


@dataclass(slots=True, kw_only=True)
class OrderEvent(Event):
    symbol: str
    order_type: OrderType
    quantity: int
    direction: OrderDirection
    type: EventType = field(default=EventType.ORDER, init=False)

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("order quantity must be positive")

    def print_order(self) -> None:
        print(
            f"Order: Symbol={self.symbol}, Type={self.order_type}, "
            f"Quantity={self.quantity}, Direction={self.direction}"
        )


@dataclass(slots=True, kw_only=True)
class FillEvent(Event):
    timeindex: datetime
    symbol: str
    exchange: str
    quantity: int
    direction: OrderDirection
    fill_cost: float
    commission: float | None = None
    type: EventType = field(default=EventType.FILL, init=False)

    def __post_init__(self) -> None:
        if self.commission is None:
            self.commission = self.calculate_ib_commission()

    def paid_commission(self) -> float:
        return self.commission if self.commission is not None else 0.0

    def calculate_ib_commission(self) -> float:
        rate = 0.013 if self.quantity <= 500 else 0.008
        return max(1.3, rate * self.quantity)
