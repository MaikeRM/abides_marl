import random
from app.agents.base import HeuristicAgent
from app.core.oracle import Oracle
from app.core.constants import round_to_tick


class ValueAgent(HeuristicAgent):
    """
    Value Agent that maintains a Bayesian estimate of the fundamental value.
    Trades when it can capture a required surplus R given its private benefit theta.
    """

    def __init__(
        self,
        agent_id,
        exchange_id,
        oracle: Oracle,
        seed,
        wake_interval=8,
        kappa=0.05,
        sigma_s=0.5,
        sigma_n=1.0,
        r_bar=100.0,
        theta=0.0,
        min_surplus=0.5,
        max_surplus=1.5,
    ):
        super().__init__(agent_id, f"VALUE_{agent_id}")
        self.exchange_id = exchange_id
        self.oracle = oracle
        self.rng = random.Random(seed)
        self.lambda_a = 1.0 / wake_interval

        # Agent's Bayesian params
        self.kappa = kappa
        self.sigma_s = sigma_s  # Standard deviation of fundamental process shocks
        self.sigma_n = sigma_n  # Standard deviation of observation noise
        self.r_bar = r_bar

        # State of Bayesian filter
        self.r_est = r_bar
        self.r_var = sigma_s**2
        self.last_update_time = 0

        # Agent preferences
        self.theta = theta  # Private benefit
        self.min_surplus = min_surplus
        self.max_surplus = max_surplus

    def updateEstimates(self, t: int, observation: float):
        """Bayesian calibration of Fundamental Value r_t."""
        steps = t - self.last_update_time
        if steps > 0:
            # Time update (prior)
            for _ in range(steps):
                self.r_est += self.kappa * (self.r_bar - self.r_est)
                self.r_var = ((1 - self.kappa) ** 2) * self.r_var + self.sigma_s**2
            self.last_update_time = t

        # Measurement update (posterior)
        kalman_gain = self.r_var / (self.r_var + self.sigma_n**2) if (self.r_var + self.sigma_n**2) > 0 else 0
        self.r_est = self.r_est + kalman_gain * (observation - self.r_est)
        self.r_var = (1 - kalman_gain) * self.r_var

    def wakeup(self, now):
        assert self.kernel is not None

        if self.state == "AWAITING_DATA":
            return

        self.state = "AWAITING_DATA"
        # Request data before acting (Phase 2 requirement)
        self.kernel.send(self.agent_id, self.exchange_id, "QUERY_MKT_DATA", {})

    def receive(self, msg):
        if msg.kind == "MKT_DATA" and self.state == "AWAITING_DATA":
            self.state = "ACTIVE"
            now = self.kernel.time

            # 1. Observe noisy fundamental
            true_value = self.oracle.get_value(now)
            observation = true_value + self.rng.gauss(0, self.sigma_n)

            # 2. Update Bayesian belief
            self.updateEstimates(now, observation)

            # 3. Decision making focused on Requested Surplus (R) and Private Benefit (\theta)
            # Valuation V = r_est + theta
            v = self.r_est + self.theta
            R = self.rng.uniform(self.min_surplus, self.max_surplus)

            # Compare Valuation with Market mid or use randomized limit orders based on V
            # MKT_DATA query typically sends last_trade, best_bid, best_ask if we query those,
            # but wait, ExchangeAgent implements QUERY_MKT_DATA sending last_trade.
            market_price = msg.data.get("last_trade", self.r_bar)
            
            # The agent randomly decides to try a buy or sell if it has a symmetric model,
            # or maybe evaluates both.
            # ABIDES Value agent typically enters orders depending on its inventory or side it chooses.
            side = "BUY" if self.rng.random() < 0.5 else "SELL"
            qty = self.rng.randint(1, 10)

            if side == "BUY":
                # Max price agent is willing to pay: v - R
                target_price = v - R
                if target_price > market_price - 2.0: # arbitrary check if it's somewhat realistic to buy
                    price = round_to_tick(target_price)
                    order = {"order_type": "LIMIT", "side": "BUY", "qty": qty, "price": price}
                    self.kernel.send(self.agent_id, self.exchange_id, "NEW_ORDER", order)
            else:
                # Min price agent is willing to accept: v + R
                target_price = v + R
                if target_price < market_price + 2.0:
                    price = round_to_tick(target_price)
                    order = {"order_type": "LIMIT", "side": "SELL", "qty": qty, "price": price}
                    self.kernel.send(self.agent_id, self.exchange_id, "NEW_ORDER", order)

            # Poisson arrival for next action (Phase 3 requirement)
            delta_time = self.rng.expovariate(self.lambda_a)
            self.kernel.wakeup(self.agent_id, now + max(1, int(delta_time)))

        elif msg.kind == "EXECUTION":
            self.handle_execution(msg)
        elif msg.kind == "ORDER_ACCEPTED":
            self.handle_order_accepted(msg)
        elif msg.kind == "ORDER_CANCELLED":
            self.handle_order_cancelled(msg)
