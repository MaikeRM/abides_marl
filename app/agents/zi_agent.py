import random
from app.agents.base import HeuristicAgent
from app.core.constants import round_to_tick


class ZeroIntelligenceAgent(HeuristicAgent):
    """
    Zero Intelligence (ZI) Agent.
    Submits random orders without tracking the fundamental value bayesianly.
    Uses its own valuation V base value plus some private benefit/noise and a requested surplus R.
    """

    def __init__(
        self,
        agent_id,
        exchange_id,
        seed,
        wake_interval=5,
        base_value=100.0,
        theta_std=2.0,
        min_surplus=0.1,
        max_surplus=1.5,
    ):
        super().__init__(agent_id, f"ZI_{agent_id}")
        self.exchange_id = exchange_id
        self.rng = random.Random(seed)
        self.lambda_a = 1.0 / wake_interval

        self.base_value = base_value
        self.theta_std = theta_std
        self.min_surplus = min_surplus
        self.max_surplus = max_surplus

    def wakeup(self, now):
        assert self.kernel is not None

        if self.state == "AWAITING_DATA":
            return

        self.state = "AWAITING_DATA"
        self.kernel.send(self.agent_id, self.exchange_id, "QUERY_MKT_DATA", {})

    def get_observation(self) -> list:
        """Minimal market + inventory features.

        Features (4):
          [last_trade, position, realized_pnl, vwap]
        """
        last = self._last_mkt["last_trade"] or 0.0
        return [last, float(self.position), self.realized_pnl, self.vwap]

    def receive(self, msg):
        if msg.kind == "MKT_DATA" and self.state == "AWAITING_DATA":
            self.state = "ACTIVE"
            self._update_mkt_cache(msg)
            now = self.kernel.time
            market_price = msg.data.get("last_trade", self.base_value)

            # Generate random private benefit
            theta = self.rng.gauss(0, self.theta_std)
            # Valuation V = market_price + theta (anchored on market price for ZI)
            v = market_price + theta

            R = self.rng.uniform(self.min_surplus, self.max_surplus)

            side = "BUY" if self.rng.random() < 0.5 else "SELL"
            qty = self.rng.randint(1, 5)

            if side == "BUY":
                # Buy price: V - R
                price = round_to_tick(v - R)
            else:
                # Sell price: V + R
                price = round_to_tick(v + R)

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
