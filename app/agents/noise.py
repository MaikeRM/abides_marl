import random
from app.agents.base import HeuristicAgent
from app.core.constants import round_to_tick


class NoiseTrader(HeuristicAgent):
    """
    Zero-Intelligence trader that generates random exogenous orders.
    Uses tick-aligned prices centered around current market mid.
    """

    def __init__(self, agent_id, exchange_id, seed, wake_interval=5):
        super().__init__(agent_id, f"NOISE_{agent_id}")
        self.exchange_id = exchange_id
        self.rng = random.Random(seed)
        self.wake_interval = wake_interval

    def wakeup(self, now):
        assert self.kernel is not None
        exchange = self.kernel._agents[self.exchange_id]
        mid = exchange.last_trade

        side = "BUY" if self.rng.random() < 0.5 else "SELL"
        qty = self.rng.randint(1, 5)

        if self.rng.random() < 0.15:
            order = {"order_type": "MARKET", "side": side, "qty": qty}
        else:
            offset = self.rng.uniform(0.0, 3.0)
            if side == "BUY":
                price = round_to_tick(mid - offset)
            else:
                price = round_to_tick(mid + offset)
            order = {"order_type": "LIMIT", "side": side, "qty": qty, "price": price}

        self.kernel.send(self.agent_id, self.exchange_id, "NEW_ORDER", order)
        jitter = self.rng.randint(0, 3)
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
