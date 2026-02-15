import random
from app.agents.base import Agent
from app.core.constants import round_to_tick

class LiquidityTrader(Agent):
    """
    Has an execution goal: acquire (or sell) Q units by deadline T.
    Uses a TWAP-like strategy with increasing urgency near deadline.

    From ABIDES-MARL: the liquidity trader's optimization problem
    is embedded within the strategic trading environment.
    Observation: [t, last_price, remaining_qty]
    """

    def __init__(self, agent_id, exchange_id, seed, target_qty=100,
                 deadline=8000, wake_interval=20, side="BUY"):
        super().__init__(agent_id, f"LIQ_{agent_id}")
        self.exchange_id = exchange_id
        self.rng = random.Random(seed)
        self.target_qty = target_qty
        self.remaining_qty = target_qty
        self.deadline = deadline
        self.wake_interval = wake_interval
        self.side = side
        self.position = 0
        self.cash = 0.0

    def wakeup(self, now):
        assert self.kernel is not None
        if self.remaining_qty <= 0 or now >= self.deadline:
            return

        remaining_time = max(1, self.deadline - now)
        remaining_steps = max(1, remaining_time // self.wake_interval)
        qty = max(1, min(self.remaining_qty, self.remaining_qty // remaining_steps))

        urgency = 1.0 - (remaining_time / self.deadline)
        exchange = self.kernel._agents[self.exchange_id]
        mid = exchange.last_trade

        if self.rng.random() < urgency * 0.6:
            order = {"order_type": "MARKET", "side": self.side, "qty": qty}
        else:
            offset = self.rng.uniform(0.0, 0.5)
            if self.side == "BUY":
                price = round_to_tick(mid - offset)
            else:
                price = round_to_tick(mid + offset)
            order = {"order_type": "LIMIT", "side": self.side,
                     "qty": qty, "price": price}

        self.kernel.send(self.agent_id, self.exchange_id, "NEW_ORDER", order)
        jitter = self.rng.randint(0, 5)
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
            self.remaining_qty -= qty
