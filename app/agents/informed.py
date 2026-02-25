import random
from app.agents.base import HeuristicAgent
from app.core.oracle import Oracle
from app.core.constants import round_to_tick


class InformedTrader(HeuristicAgent):
    """
    Trades based on private information about the fundamental value.
    Observes the Oracle's value with noise and trades when the market
    price diverges significantly from the fundamental.

    From ABIDES-MARL: informed traders submit orders based on
    "alpha signals" that influence observed price updates.
    """

    def __init__(
        self,
        agent_id,
        exchange_id,
        oracle: Oracle,
        seed,
        wake_interval=8,
        noise_std=1.0,
        threshold=0.5,
        beta=2.0,
    ):
        super().__init__(agent_id, f"INFORMED_{agent_id}")
        self.exchange_id = exchange_id
        self.oracle = oracle
        self.rng = random.Random(seed)
        self.lambda_a = 1.0 / wake_interval
        self.noise_std = noise_std
        self.threshold = threshold
        self.beta = beta

    def wakeup(self, now):
        assert self.kernel is not None

        if self.state == "AWAITING_DATA":
            return

        self.state = "AWAITING_DATA"
        self.kernel.send(self.agent_id, self.exchange_id, "QUERY_MKT_DATA", {})

    def receive(self, msg):
        if msg.kind == "MKT_DATA" and self.state == "AWAITING_DATA":
            self.state = "ACTIVE"
            now = self.kernel.time
            fundamental = self.oracle.get_value(now) + self.rng.gauss(0, self.noise_std)

            market_price = msg.data.get("last_trade", 100.0)
            diff = fundamental - market_price

            if abs(diff) > self.threshold:
                side = "BUY" if diff > 0 else "SELL"
                qty = max(1, min(100, int(abs(diff) * self.beta)))

                if side == "BUY":
                    price = round_to_tick(
                        market_price + abs(diff) * self.rng.uniform(0.3, 0.7)
                    )
                else:
                    price = round_to_tick(
                        market_price - abs(diff) * self.rng.uniform(0.3, 0.7)
                    )

                order = {"order_type": "LIMIT", "side": side, "qty": qty, "price": price}
                self.kernel.send(self.agent_id, self.exchange_id, "NEW_ORDER", order)

            delta_time = self.rng.expovariate(self.lambda_a)
            self.kernel.wakeup(self.agent_id, now + max(1, int(delta_time)))

        elif msg.kind == "EXECUTION":
            self.handle_execution(msg)
        elif msg.kind == "ORDER_ACCEPTED":
            self.handle_order_accepted(msg)
        elif msg.kind == "ORDER_CANCELLED":
            self.handle_order_cancelled(msg)
