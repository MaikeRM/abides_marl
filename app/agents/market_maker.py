import random
from typing import List, Optional
from app.agents.base import HeuristicAgent
from app.core.constants import round_to_tick


class MarketMakerAgent(HeuristicAgent):
    """
    Posts symmetric bid/ask quotes around the mid-price with
    inventory-skewed adjustment. Uses order-specific cancellation
    instead of cancel_all to avoid canceling other agents' orders.
    """

    def __init__(
        self,
        agent_id,
        exchange_id,
        seed,
        wake_interval=3,
        spread=1.0,
        order_qty=5,
        max_inventory=50,
    ):
        super().__init__(agent_id, f"MM_{agent_id}")
        self.exchange_id = exchange_id
        self.rng = random.Random(seed)
        self.wake_interval = wake_interval
        self.spread = spread
        self.order_qty = order_qty
        self.max_inventory = max_inventory
        self.pending_orders: List[int] = []  # Track order_ids for selective cancel

    def wakeup(self, now):
        assert self.kernel is not None

        # Cancel only specific orders we know about (not cancel_all)
        for order_id in self.pending_orders:
            self.kernel.send(
                self.agent_id, self.exchange_id, "CANCEL_ORDER", {"order_id": order_id}
            )
        self.pending_orders.clear()

        exchange = self.kernel._agents[self.exchange_id]
        mid = exchange.last_trade

        # Inventory skew: shift quotes to reduce exposure
        inventory_skew = -self.position * 0.02
        adjusted_mid = mid + inventory_skew
        half = self.spread / 2.0

        bid_price = round_to_tick(adjusted_mid - half)
        ask_price = round_to_tick(adjusted_mid + half)

        if self.position < self.max_inventory:
            self.kernel.send(
                self.agent_id,
                self.exchange_id,
                "NEW_ORDER",
                {
                    "order_type": "LIMIT",
                    "side": "BUY",
                    "qty": self.order_qty,
                    "price": bid_price,
                },
            )

        if self.position > -self.max_inventory:
            self.kernel.send(
                self.agent_id,
                self.exchange_id,
                "NEW_ORDER",
                {
                    "order_type": "LIMIT",
                    "side": "SELL",
                    "qty": self.order_qty,
                    "price": ask_price,
                },
            )

        jitter = self.rng.randint(0, 1)
        self.kernel.wakeup(self.agent_id, now + self.wake_interval + jitter)

    def receive(self, msg):
        if msg.kind == "EXECUTION":
            qty = int(msg.data["qty"])
            price = float(msg.data["price"])
            if msg.data["side"] == "BUY":
                self.position += qty
                self.cash -= qty * price
            else:
                self.position -= qty
                self.cash += qty * price
        elif msg.kind == "ORDER_ACCEPTED":
            self.pending_orders.append(msg.data["order_id"])
        elif msg.kind == "ORDER_CANCELLED":
            order_id = msg.data.get("order_id")
            if order_id in self.pending_orders:
                self.pending_orders.remove(order_id)
