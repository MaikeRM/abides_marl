import random
from typing import List
from app.agents.base import Agent
from app.core.constants import round_to_tick

class MarketMakerAgent(Agent):
    """
    Posts symmetric bid/ask quotes around the mid-price with
    inventory-skewed adjustment. Cancels and reposts every wakeup.

    From ABIDES-MARL: market makers compete to quote prices and
    provide liquidity, balancing profit with inventory control.
    """

    def __init__(self, agent_id, exchange_id, seed, wake_interval=3,
                 spread=1.0, order_qty=5, max_inventory=50):
        super().__init__(agent_id, f"MM_{agent_id}")
        self.exchange_id = exchange_id
        self.rng = random.Random(seed)
        self.wake_interval = wake_interval
        self.spread = spread
        self.order_qty = order_qty
        self.max_inventory = max_inventory
        self.position = 0
        self.cash = 0.0
        self.active_order_ids: List[int] = []

    def wakeup(self, now):
        assert self.kernel is not None

        # Cancel all previous orders before reposting
        if self.active_order_ids:
            self.kernel.send(
                self.agent_id, self.exchange_id, "CANCEL_ORDER",
                {"cancel_all": True}
            )
            self.active_order_ids.clear()

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
                self.agent_id, self.exchange_id, "NEW_ORDER",
                {"order_type": "LIMIT", "side": "BUY",
                 "qty": self.order_qty, "price": bid_price}
            )

        if self.position > -self.max_inventory:
            self.kernel.send(
                self.agent_id, self.exchange_id, "NEW_ORDER",
                {"order_type": "LIMIT", "side": "SELL",
                 "qty": self.order_qty, "price": ask_price}
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
            self.active_order_ids.append(msg.data["order_id"])
