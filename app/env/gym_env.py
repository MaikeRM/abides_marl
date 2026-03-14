"""
Single-agent Gymnasium wrapper for ABIDES-MARL market simulation.

Usage example::

    from app.env import AbidesGymEnv

    env = AbidesGymEnv(seed=42, max_steps=500)
    obs, info = env.reset()

    for _ in range(500):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        if terminated or truncated:
            break

    env.close()

Observation space (8 continuous features)::

    [best_bid, best_ask, spread, mid_price, position, realized_pnl, vwap, last_trade]

Action space: MultiDiscrete([5, 20, 10])::

    dim 0 — action_type : 0=HOLD, 1=BUY_LIMIT, 2=SELL_LIMIT, 3=BUY_MARKET, 4=SELL_MARKET
    dim 1 — price_ticks : offset from mid in ticks (0 = best, 19 = 19 ticks away)
    dim 2 — qty_bin     : quantity = qty_bin + 1  (range 1–10 units)

The RL agent (RLMarketAgent) is inserted into the existing SimulationRunner.
All other agents (MarketMakers, ValueAgents, ZI, LiquidityTrader) act as
heuristic background agents.

Episode terminates when:
  - Kernel has no more events (simulation exhausted), OR
  - `max_steps` RL steps have elapsed (truncated=True).
"""

import numpy as np

try:
    import gymnasium
    from gymnasium import spaces
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "gymnasium is required for AbidesGymEnv. "
        "Install it with: pip install gymnasium"
    ) from exc

from app.agents.base import HeuristicAgent
from app.core.constants import TICK_SIZE, round_to_tick
from app.core.runner import SimulationRunner


class RLMarketAgent(HeuristicAgent):
    """
    Proxy agent that bridges the RL policy and the ABIDES event loop.

    The Gym env sets ``pending_action`` before each step; the agent
    translates it to an order when it receives its next MKT_DATA reply.

    ``observation_ready`` is set to True once market data arrives so that
    the Gym env knows when to collect the next observation.
    """

    N_OBS: int = 8  # [best_bid, best_ask, spread, mid, position, realized_pnl, vwap, last_trade]

    def __init__(self, agent_id: int, exchange_id: int, wake_interval: int = 20):
        super().__init__(agent_id, "RL_AGENT")
        self.exchange_id = exchange_id
        self.wake_interval = wake_interval
        self.pending_action = None  # Set by AbidesGymEnv.step() before the next wakeup
        self.observation_ready: bool = False  # Flipped to True each time MKT_DATA arrives

    def reset(self) -> None:
        super().reset()
        self.pending_action = None
        self.observation_ready = False

    # ------------------------------------------------------------------
    # Gym interface
    # ------------------------------------------------------------------

    def get_observation(self) -> list:
        """Returns the 8-dimensional market + inventory observation vector."""
        last = self._last_mkt["last_trade"] or 0.0
        best_bid = self._last_mkt["best_bid"] if self._last_mkt["best_bid"] is not None else last
        best_ask = self._last_mkt["best_ask"] if self._last_mkt["best_ask"] is not None else last
        spread = best_ask - best_bid
        mid = (best_bid + best_ask) / 2.0
        return [best_bid, best_ask, spread, mid, float(self.position), self.realized_pnl, self.vwap, last]

    # ------------------------------------------------------------------
    # Simulation callbacks
    # ------------------------------------------------------------------

    def wakeup(self, now: int) -> None:
        assert self.kernel is not None
        if self.state == "AWAITING_DATA":
            return
        self.state = "AWAITING_DATA"
        self.kernel.send(self.agent_id, self.exchange_id, "QUERY_MKT_DATA", {})

    def receive(self, msg) -> None:
        if msg.kind == "MKT_DATA" and self.state == "AWAITING_DATA":
            self.state = "ACTIVE"
            self._update_mkt_cache(msg)
            now = self.kernel.time

            # Execute the action that the Gym env queued
            if self.pending_action is not None:
                action_type, price_ticks, qty_bin = self.pending_action
                self._execute_action(int(action_type), int(price_ticks), int(qty_bin))
                self.pending_action = None

            # Signal that fresh observation data is available
            self.observation_ready = True

            # Schedule the next RL wakeup
            self.kernel.wakeup(self.agent_id, now + self.wake_interval)

        elif msg.kind == "EXECUTION":
            self.handle_execution(msg)
        elif msg.kind == "ORDER_ACCEPTED":
            self.handle_order_accepted(msg)
        elif msg.kind == "ORDER_CANCELLED":
            self.handle_order_cancelled(msg)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute_action(self, action_type: int, price_ticks: int, qty_bin: int) -> None:
        qty = qty_bin + 1
        last = self._last_mkt["last_trade"] or 100.0
        best_bid = self._last_mkt["best_bid"] or last
        best_ask = self._last_mkt["best_ask"] or last
        mid = (best_bid + best_ask) / 2.0
        offset = price_ticks * TICK_SIZE

        if action_type == 0:  # HOLD
            return
        elif action_type == 1:  # BUY LIMIT
            price = round_to_tick(mid - offset)
            self.kernel.send(
                self.agent_id, self.exchange_id, "NEW_ORDER",
                {"order_type": "LIMIT", "side": "BUY", "qty": qty, "price": price},
            )
        elif action_type == 2:  # SELL LIMIT
            price = round_to_tick(mid + offset)
            self.kernel.send(
                self.agent_id, self.exchange_id, "NEW_ORDER",
                {"order_type": "LIMIT", "side": "SELL", "qty": qty, "price": price},
            )
        elif action_type == 3:  # BUY MARKET
            self.kernel.send(
                self.agent_id, self.exchange_id, "NEW_ORDER",
                {"order_type": "MARKET", "side": "BUY", "qty": qty},
            )
        elif action_type == 4:  # SELL MARKET
            self.kernel.send(
                self.agent_id, self.exchange_id, "NEW_ORDER",
                {"order_type": "MARKET", "side": "SELL", "qty": qty},
            )


class AbidesGymEnv(gymnasium.Env):
    """
    Single-agent Gymnasium-compatible environment wrapping ABIDES-MARL.

    Parameters
    ----------
    seed : int
        Master seed forwarded to SimulationRunner and numpy RNG.
    max_steps : int
        Maximum number of RL steps per episode (truncation threshold).
    rl_step_interval : int
        Number of simulation ticks between consecutive RL agent wakeups.
        Lower values = more frequent decisions, denser reward signal.

    Observation space
    -----------------
    Box(8,) — continuous, unbounded:
        [best_bid, best_ask, spread, mid_price,
         position, realized_pnl, vwap, last_trade]

    Action space
    ------------
    MultiDiscrete([5, 20, 10]):
        dim 0 — action_type : 0=HOLD, 1=BUY_LIMIT, 2=SELL_LIMIT,
                               3=BUY_MARKET, 4=SELL_MARKET
        dim 1 — price_ticks : 0–19 ticks offset from mid
        dim 2 — qty_bin     : qty = qty_bin + 1  (1–10 units)
    """

    metadata = {"render_modes": []}

    # RL agent is placed at a high agent_id to avoid collisions with the
    # runner's heuristic agents (which currently use ids 0–36).
    RL_AGENT_ID: int = 100

    def __init__(
        self,
        seed: int = 42,
        max_steps: int = 500,
        rl_step_interval: int = 20,
    ):
        super().__init__()
        self._seed = seed
        self.max_steps = max_steps
        self.rl_step_interval = rl_step_interval

        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(RLMarketAgent.N_OBS,),
            dtype=np.float32,
        )
        self.action_space = spaces.MultiDiscrete([5, 20, 10])

        self._runner = SimulationRunner()
        self._rl_agent: RLMarketAgent | None = None
        self._steps: int = 0

    # ------------------------------------------------------------------
    # Gymnasium API
    # ------------------------------------------------------------------

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        if seed is not None:
            self._seed = seed

        self._runner.reset(seed=self._seed)
        self._rl_agent = self._build_and_register_rl_agent()
        self._steps = 0

        # Run until the RL agent has received its first market data
        self._advance_to_next_observation()

        obs = np.array(self._rl_agent.get_observation(), dtype=np.float32)
        info = {"sim_time": self._runner.kernel.time}
        return obs, info

    def step(self, action):
        assert self._rl_agent is not None, "Call reset() before step()"

        # Queue the action; it will be executed on the agent's next MKT_DATA handler
        self._rl_agent.pending_action = tuple(int(a) for a in action)

        # Advance the simulation until the RL agent gets its next observation
        self._advance_to_next_observation()
        self._steps += 1

        obs = np.array(self._rl_agent.get_observation(), dtype=np.float32)
        reward = float(self._rl_agent.get_reward())
        terminated = not self._runner.kernel.running
        truncated = self._steps >= self.max_steps
        info = {
            "sim_time": self._runner.kernel.time,
            "position": self._rl_agent.position,
            "realized_pnl": self._rl_agent.realized_pnl,
            "active_orders": len(self._rl_agent.active_orders),
        }
        return obs, reward, terminated, truncated, info

    def render(self):
        """Not implemented — use the DearPyGui dashboard (app/main.py) for visualisation."""
        pass

    def close(self):
        if self._runner.kernel:
            self._runner.stop()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_and_register_rl_agent(self) -> RLMarketAgent:
        """Instantiate RLMarketAgent, register it in the kernel, and schedule wakeup."""
        rl = RLMarketAgent(
            agent_id=self.RL_AGENT_ID,
            exchange_id=0,
            wake_interval=self.rl_step_interval,
        )
        self._runner.kernel.register(rl)

        # Set symmetric latency between RL agent and all existing agents
        for aid in list(self._runner.kernel._agents.keys()):
            if aid != self.RL_AGENT_ID:
                self._runner.kernel.set_latency(self.RL_AGENT_ID, aid, 2)
                self._runner.kernel.set_latency(aid, self.RL_AGENT_ID, 2)
        self._runner.kernel.set_latency(self.RL_AGENT_ID, self.RL_AGENT_ID, 0)

        # First wakeup at t=1 (same as heuristic agents)
        self._runner.kernel.wakeup(self.RL_AGENT_ID, at_time=1)
        return rl

    def _advance_to_next_observation(self) -> None:
        """
        Step the kernel forward until the RL agent has fresh market data
        (i.e. its ``observation_ready`` flag is set) or the simulation ends.
        """
        if self._rl_agent is None:
            return
        self._rl_agent.observation_ready = False
        while self._runner.kernel.running and not self._rl_agent.observation_ready:
            self._runner.step()
