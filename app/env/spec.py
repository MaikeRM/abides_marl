"""Versioned public contract for the single-agent episode."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any

import numpy as np

from app.core.constants import TICK_SIZE, round_to_tick


EPISODE_SPEC_VERSION = "single-agent-episode.v1"
ACTION_BRANCHES = (5, 20, 10)
OBSERVATION_NAMES = (
    "best_bid_return",
    "best_ask_return",
    "spread_ticks_scaled",
    "mid_return",
    "position_fraction",
    "marked_pnl_scaled",
    "vwap_return",
    "last_trade_return",
)
ACTION_NAMES = ("HOLD", "BUY_LIMIT", "SELL_LIMIT", "BUY_MARKET", "SELL_MARKET")


@dataclass(frozen=True, slots=True)
class EpisodeSpec:
    """All non-learned episode semantics required to reproduce a run."""

    schema_version: str = EPISODE_SPEC_VERSION
    max_steps: int = 500
    sim_time_horizon: int = 1000
    rl_step_interval: int = 20
    position_limit: int = 100
    price_scale: float = 100.0
    reward_scale: float = 100.0
    price_tick_size: float = TICK_SIZE
    truncated_precedence: bool = True

    def __post_init__(self) -> None:
        if self.schema_version != EPISODE_SPEC_VERSION:
            raise ValueError(f"unsupported episode spec {self.schema_version!r}")
        for field in ("max_steps", "sim_time_horizon", "rl_step_interval", "position_limit"):
            value = getattr(self, field)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{field} must be a positive integer")
        for field in ("price_scale", "reward_scale", "price_tick_size"):
            value = float(getattr(self, field))
            if not isfinite(value) or value <= 0:
                raise ValueError(f"{field} must be finite and positive")

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["action_branches"] = list(ACTION_BRANCHES)
        payload["action_names"] = list(ACTION_NAMES)
        payload["observation_names"] = list(OBSERVATION_NAMES)
        return payload

    def validate_action(self, action: Any) -> tuple[int, int, int]:
        """Validate and normalize one action without mutating an environment."""

        candidate = np.asarray(action)
        if candidate.shape != (3,) or not np.issubdtype(candidate.dtype, np.integer):
            raise ValueError(f"action must be an integer vector with shape (3,), got {action!r}")
        values = tuple(int(value) for value in candidate.tolist())
        if any(value < 0 or value >= size for value, size in zip(values, ACTION_BRANCHES)):
            raise ValueError(f"action is outside MultiDiscrete({list(ACTION_BRANCHES)}): {action!r}")
        return values

    def action_order(self, action: Any, *, mid_price: float) -> dict[str, Any] | None:
        """Map an action to a core order; HOLD is the only no-op."""

        action_type, price_ticks, qty_bin = self.validate_action(action)
        if not isfinite(float(mid_price)) or mid_price <= 0:
            raise ValueError("mid_price must be finite and positive")
        qty = qty_bin + 1
        offset = price_ticks * self.price_tick_size
        if action_type == 0:
            return None
        if action_type == 1:
            return {
                "order_type": "LIMIT",
                "side": "BUY",
                "qty": qty,
                "price": round_to_tick(mid_price - offset),
            }
        if action_type == 2:
            return {
                "order_type": "LIMIT",
                "side": "SELL",
                "qty": qty,
                "price": round_to_tick(mid_price + offset),
            }
        return {
            "order_type": "MARKET",
            "side": "BUY" if action_type == 3 else "SELL",
            "qty": qty,
        }
