import random
from app.agents.base import HeuristicAgent
from app.core.constants import round_to_tick


class LiquidityTrader(HeuristicAgent):
    """
    Has an execution goal: acquire (or sell) Q units by deadline T.
    Uses a TWAP-like strategy with increasing urgency near deadline.

    From ABIDES-MARL: the liquidity trader's optimization problem
    is embedded within the strategic trading environment.
    Observation: [t, last_price, remaining_qty]
    """

    def __init__(
        self,
        agent_id,
        exchange_id,
        seed,
        target_qty=100,
        deadline=8000,
        wake_interval=20,
        side="BUY",
        phi=0.5,
    ):
        super().__init__(agent_id, f"LIQ_{agent_id}")
        self.exchange_id = exchange_id
        self.rng = random.Random(seed)
        self.target_qty = target_qty
        self.remaining_qty = target_qty
        self.deadline = deadline
        self.lambda_a = 1.0 / wake_interval
        self.side = side
        self.phi = phi

    def wakeup(self, now):
        assert self.kernel is not None
        if self.remaining_qty <= 0 or now >= self.deadline:
            return

        if self.state == "AWAITING_DATA":
            return

        self.state = "AWAITING_DATA"
        self.kernel.send(self.agent_id, self.exchange_id, "QUERY_MKT_DATA", {})

    def receive(self, msg):
        if msg.kind == "MKT_DATA" and self.state == "AWAITING_DATA":
            self.state = "ACTIVE"
            now = self.kernel.time
            mid = msg.data.get("last_trade", 100.0)

            remaining_time = max(1, self.deadline - now)
            expected_interval = 1.0 / self.lambda_a
            remaining_steps = max(1, int(remaining_time / expected_interval))
            qty = max(1, min(self.remaining_qty, self.remaining_qty // remaining_steps))

            time_fraction = remaining_time / self.deadline
            # Base urgency derived from time, increased by inventory penalty (phi)
            risk_penalty = self.phi * (self.remaining_qty / self.target_qty)
            urgency = min(1.0, (1.0 - time_fraction) + risk_penalty)

            if self.rng.random() < urgency * 0.6:
                order = {"order_type": "MARKET", "side": self.side, "qty": qty}
            else:
                offset = self.rng.uniform(0.0, 0.5)
                if self.side == "BUY":
                    price = round_to_tick(mid - offset)
                else:
                    price = round_to_tick(mid + offset)
                order = {
                    "order_type": "LIMIT",
                    "side": self.side,
                    "qty": qty,
                    "price": price,
                }

            self.kernel.send(self.agent_id, self.exchange_id, "NEW_ORDER", order)
            delta_time = self.rng.expovariate(self.lambda_a)
            self.kernel.wakeup(self.agent_id, now + max(1, int(delta_time)))

        elif msg.kind == "EXECUTION":
            self.handle_execution(msg)
            self.remaining_qty -= int(msg.data["qty"])
        elif msg.kind == "ORDER_ACCEPTED":
            self.handle_order_accepted(msg)
        elif msg.kind == "ORDER_CANCELLED":
            self.handle_order_cancelled(msg)
