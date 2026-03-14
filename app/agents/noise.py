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
        self.lambda_a = 1.0 / wake_interval

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
            mid = msg.data.get("last_trade", 100.0)

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
            delta_time = self.rng.expovariate(self.lambda_a)
            self.kernel.wakeup(self.agent_id, now + max(1, int(delta_time)))

        elif msg.kind == "EXECUTION":
            self.handle_execution(msg)
        elif msg.kind == "ORDER_ACCEPTED":
            self.handle_order_accepted(msg)
        elif msg.kind == "ORDER_CANCELLED":
            self.handle_order_cancelled(msg)
