"""Versioned configuration for the lightweight experiment pipeline."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

from app.core.runner import BaselineScenario, DEFAULT_BASELINE_SCENARIO


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    schema_version: str = "training-config.v1"
    seeds: tuple[int, ...] = (11, 22, 33)
    iterations: int = 1
    population_size: int = 4
    elite_fraction: float = 0.5
    episode_steps: int = 4
    rl_step_interval: int = 5
    position_limit: int = 100
    scenario: BaselineScenario = field(
        default_factory=lambda: replace(
            DEFAULT_BASELINE_SCENARIO,
            num_market_makers=1,
            num_value_agents=1,
            num_zero_intelligence_agents=1,
            include_liquidity_trader=True,
            liquidity_target_qty=10,
            liquidity_deadline=160,
            market_maker_wake_interval=8,
            value_agent_wake_interval=12,
            zero_intelligence_wake_interval=10,
            liquidity_wake_interval=15,
            max_time=160,
        )
    )

    def __post_init__(self) -> None:
        if self.schema_version != "training-config.v1":
            raise ValueError(f"unsupported training config {self.schema_version!r}")
        if not self.seeds or any(not isinstance(seed, int) for seed in self.seeds):
            raise ValueError("seeds must contain at least one integer")
        if self.iterations <= 0 or self.population_size < 2:
            raise ValueError("iterations must be positive and population_size at least two")
        if not 0 < self.elite_fraction <= 1:
            raise ValueError("elite_fraction must be in (0, 1]")
        if self.episode_steps <= 0 or self.rl_step_interval <= 0 or self.position_limit <= 0:
            raise ValueError("episode and position limits must be positive")

    @property
    def elite_count(self) -> int:
        return max(1, min(self.population_size, int(self.population_size * self.elite_fraction)))

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["seeds"] = list(self.seeds)
        return payload


def load_training_config(path: str | Path) -> TrainingConfig:
    """Load a JSON config and validate every scenario field."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    scenario_payload = payload.pop("scenario", {})
    scenario = BaselineScenario(**scenario_payload)
    payload["seeds"] = tuple(payload.get("seeds", ()))
    return TrainingConfig(scenario=scenario, **payload)


def write_training_config(path: str | Path, config: TrainingConfig) -> None:
    Path(path).write_text(
        json.dumps(config.as_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
