import random
from app.agents.base import Agent
from app.core.oracle import Oracle
from app.core.constants import round_to_tick

class InformedTrader(Agent):
    """
    Trades based on private information about the fundamental value.
    Observes the Oracle's value with noise and trades when the market
    price diverges significantly from the fundamental.

    From ABIDES-MARL: informed traders submit orders based on
    "alpha signals" that influence observed price updates.
    """

    def __init__(self, agent_id, exchange_id, oracle: Oracle, seed,
                 wake_interval=8, noise_std=1.0, threshold=0.5):
        super().__init__(agent_id, f"INFORMED_{agent_id}")
        self.exchange_id = exchange_id
        self.oracle = oracle
        self.rng = random.Random(seed)
        self.wake_interval = wake_interval
        self.noise_std = noise_std
        self.threshold = threshold
        self.position = 0
        self.cash = 0.0

    def wakeup(self, now):
        assert self.kernel is not None
        fundamental = self.oracle.get_value(now) + self.rng.gauss(0, self.noise_std)
        exchange = self.kernel._agents[self.exchange_id]
        market_price = exchange.last_trade
        diff = fundamental - market_price

        if abs(diff) > self.threshold:
            side = "BUY" if diff > 0 else "SELL"
            qty = max(1, min(10, int(abs(diff) * 2)))

            if side == "BUY":
                price = round_to_tick(market_price + abs(diff) * self.rng.uniform(0.3, 0.7))
            else:
                price = round_to_tick(market_price - abs(diff) * self.rng.uniform(0.3, 0.7))

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
