from dataclasses import dataclass
from math import isfinite


def _require_int(value, field: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field} must be an integer")


@dataclass
class Message:
    src: int
    dst: int
    kind: str
    data: dict

    def __post_init__(self) -> None:
        _require_int(self.src, "src")
        _require_int(self.dst, "dst")
        if not isinstance(self.kind, str) or not self.kind:
            raise ValueError("kind must be a non-empty string")
        if not isinstance(self.data, dict):
            raise ValueError("data must be a dictionary")


@dataclass
class Order:
    order_id: int
    agent_id: int
    side: str
    price: float
    qty: int
    ts: int
    order_type: str = "LIMIT"

    def __post_init__(self) -> None:
        _require_int(self.order_id, "order_id")
        _require_int(self.agent_id, "agent_id")
        _require_int(self.qty, "qty")
        _require_int(self.ts, "ts")
        if self.side not in {"BUY", "SELL"}:
            raise ValueError(f"unsupported order side {self.side!r}")
        if self.order_type not in {"LIMIT", "MARKET"}:
            raise ValueError(f"unsupported order type {self.order_type!r}")
        if self.qty <= 0:
            raise ValueError("order quantity must be positive")
        if not isfinite(float(self.price)) or self.price < 0:
            raise ValueError("order price must be finite and non-negative")


@dataclass
class Trade:
    price: float
    qty: int
    buyer_id: int
    seller_id: int
    ts: int
    aggressor_side: str
    buyer_order_id: int | None = None
    seller_order_id: int | None = None
    trade_id: int | None = None

    def __post_init__(self) -> None:
        if not isfinite(float(self.price)) or self.price <= 0:
            raise ValueError("trade price must be finite and positive")
        _require_int(self.qty, "qty")
        _require_int(self.buyer_id, "buyer_id")
        _require_int(self.seller_id, "seller_id")
        _require_int(self.ts, "ts")
        if self.qty <= 0:
            raise ValueError("trade quantity must be positive")
        if self.aggressor_side not in {"BUY", "SELL"}:
            raise ValueError(f"unsupported aggressor side {self.aggressor_side!r}")
