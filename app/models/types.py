from dataclasses import dataclass

@dataclass
class Message:
    src: int
    dst: int
    kind: str
    data: dict


@dataclass
class Order:
    order_id: int
    agent_id: int
    side: str
    price: float
    qty: int
    ts: int


@dataclass
class Trade:
    price: float
    qty: int
    buyer_id: int
    seller_id: int
    ts: int
    aggressor_side: str
