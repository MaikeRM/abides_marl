import random

class Oracle:
    """
    Generates a fundamental value time series using an Ornstein-Uhlenbeck
    (mean-reverting) process. This is the "true" value of the asset.

    From the ABIDES paper:
    - r_bar: long-run mean (equilibrium price)
    - kappa: mean-reversion speed
    - sigma: volatility of the process
    """

    def __init__(self, r_bar=100.0, kappa=0.05, sigma=0.5, seed=42):
        self.r_bar = r_bar
        self.kappa = kappa
        self.sigma = sigma
        self.value = r_bar
        self.rng = random.Random(seed)
        self._last_t = 0

    def get_value(self, t: int) -> float:
        """Get fundamental value at time t (lazily advances from last query)."""
        steps = t - self._last_t
        if steps > 0:
            for _ in range(steps):
                self.value += self.kappa * (self.r_bar - self.value) + \
                              self.sigma * self.rng.gauss(0, 1)
            self._last_t = t
        return self.value
