"""Versioned, paired and fail-closed evaluation protocol utilities."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from math import isfinite
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from app.core.artifacts import sha256_json


PROTOCOL_SCHEMA_VERSION = "evaluation-protocol.v1"
VALID_SPLITS = ("validation", "holdout", "stress")


def _validate_seed_group(name: str, values: Iterable[int]) -> tuple[int, ...]:
    result = tuple(values)
    if not result or any(not isinstance(seed, int) or isinstance(seed, bool) for seed in result):
        raise ValueError(f"{name} must contain at least one integer seed")
    if len(set(result)) != len(result):
        raise ValueError(f"{name} must not contain duplicate seeds")
    return result


@dataclass(frozen=True, slots=True)
class EvaluationProtocol:
    """All choices needed to audit one policy-versus-baseline campaign."""

    schema_version: str = PROTOCOL_SCHEMA_VERSION
    protocol_id: str = "single-agent-paired-v1"
    role: str = "execution_agent"
    training_seeds: tuple[int, ...] = (11, 22, 33)
    validation_seeds: tuple[int, ...] = (101, 102, 103)
    holdout_seeds: tuple[int, ...] = (201, 202, 203)
    stress_seeds: tuple[int, ...] = (301, 302, 303)
    max_steps: int = 20
    rl_step_interval: int = 5
    primary_metric: str = "marked_pnl"
    secondary_metrics: tuple[str, ...] = (
        "return",
        "max_drawdown",
        "max_abs_position",
        "trade_count",
        "traded_volume",
    )
    baseline_names: tuple[str, ...] = (
        "HOLD",
        "RANDOM",
        "MarketMakerAgent",
        "ValueAgent",
        "ZeroIntelligenceAgent",
        "LiquidityTrader",
    )
    confidence_level: float = 0.95
    bootstrap_samples: int = 2000
    minimum_sample_size: int = 3
    minimum_effect: float | None = None
    multiple_testing: str = "bonferroni"

    def __post_init__(self) -> None:
        if self.schema_version != PROTOCOL_SCHEMA_VERSION:
            raise ValueError(f"unsupported evaluation protocol {self.schema_version!r}")
        if not self.protocol_id or not self.role:
            raise ValueError("protocol_id and role must be non-empty")
        training = _validate_seed_group("training_seeds", self.training_seeds)
        validation = _validate_seed_group("validation_seeds", self.validation_seeds)
        holdout = _validate_seed_group("holdout_seeds", self.holdout_seeds)
        stress = _validate_seed_group("stress_seeds", self.stress_seeds)
        groups = {"validation": validation, "holdout": holdout, "stress": stress}
        for name, values in groups.items():
            if set(values) & set(training):
                raise ValueError(f"{name} seeds overlap training seeds")
        for left_name, left in groups.items():
            for right_name, right in groups.items():
                if left_name < right_name and set(left) & set(right):
                    raise ValueError(f"{left_name} seeds overlap {right_name} seeds")
        object.__setattr__(self, "training_seeds", training)
        object.__setattr__(self, "validation_seeds", validation)
        object.__setattr__(self, "holdout_seeds", holdout)
        object.__setattr__(self, "stress_seeds", stress)
        if (
            not isinstance(self.max_steps, int)
            or isinstance(self.max_steps, bool)
            or not isinstance(self.rl_step_interval, int)
            or isinstance(self.rl_step_interval, bool)
            or self.max_steps <= 0
            or self.rl_step_interval <= 0
        ):
            raise ValueError("max_steps and rl_step_interval must be positive")
        if not isinstance(self.secondary_metrics, tuple) or any(
            not isinstance(metric, str) or not metric for metric in self.secondary_metrics
        ):
            raise ValueError("secondary_metrics must contain non-empty strings")
        if len(set(self.secondary_metrics)) != len(self.secondary_metrics):
            raise ValueError("secondary_metrics must not contain duplicates")
        if not isinstance(self.baseline_names, tuple) or any(
            not isinstance(name, str) or not name for name in self.baseline_names
        ):
            raise ValueError("baseline_names must contain non-empty strings")
        if len(set(self.baseline_names)) != len(self.baseline_names):
            raise ValueError("baseline_names must not contain duplicates")
        try:
            confidence_level = float(self.confidence_level)
        except (TypeError, ValueError) as exc:
            raise ValueError("confidence_level must be numeric") from exc
        if not isfinite(confidence_level) or not 0 < confidence_level < 1:
            raise ValueError("confidence_level must be in (0, 1)")
        if (
            not isinstance(self.bootstrap_samples, int)
            or isinstance(self.bootstrap_samples, bool)
            or not isinstance(self.minimum_sample_size, int)
            or isinstance(self.minimum_sample_size, bool)
            or self.bootstrap_samples < 100
            or self.minimum_sample_size < 2
        ):
            raise ValueError("bootstrap_samples must be >= 100 and sample size >= 2")
        if self.minimum_effect is not None and not isfinite(float(self.minimum_effect)):
            raise ValueError("minimum_effect must be finite or None")
        if self.multiple_testing not in {"none", "bonferroni"}:
            raise ValueError("multiple_testing must be 'none' or 'bonferroni'")
        if not self.primary_metric or not self.baseline_names:
            raise ValueError("primary_metric and baseline_names must be non-empty")
        object.__setattr__(self, "confidence_level", confidence_level)

    @property
    def effective_confidence_level(self) -> float:
        comparisons = max(1, len(self.baseline_names))
        if self.multiple_testing == "bonferroni":
            return 1.0 - (1.0 - self.confidence_level) / comparisons
        return self.confidence_level

    def seeds_for(self, split: str) -> tuple[int, ...]:
        if split == "training":
            return self.training_seeds
        if split == "validation":
            return self.validation_seeds
        if split == "holdout":
            return self.holdout_seeds
        if split == "stress":
            return self.stress_seeds
        raise ValueError(f"unsupported evaluation split {split!r}")

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("training_seeds", "validation_seeds", "holdout_seeds", "stress_seeds", "secondary_metrics", "baseline_names"):
            payload[key] = list(payload[key])
        payload["effective_confidence_level"] = self.effective_confidence_level
        return payload

    @property
    def config_hash(self) -> str:
        return sha256_json(self.as_dict())


def load_evaluation_protocol(path: str | Path) -> EvaluationProtocol:
    import json

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("training_seeds", "validation_seeds", "holdout_seeds", "stress_seeds", "secondary_metrics", "baseline_names"):
        if key in payload:
            payload[key] = tuple(payload[key])
    payload.pop("effective_confidence_level", None)
    return EvaluationProtocol(**payload)


def file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _finite_values(values: Iterable[float]) -> np.ndarray:
    array = np.asarray(list(values), dtype=np.float64)
    if array.ndim != 1 or array.size == 0 or not np.isfinite(array).all():
        raise ValueError("metric values must be a non-empty finite vector")
    return array


def bootstrap_mean_interval(
    values: Iterable[float],
    *,
    confidence_level: float = 0.95,
    samples: int = 2000,
    seed: int = 0,
) -> tuple[float, float]:
    """Return a deterministic percentile bootstrap CI for a sample mean."""

    array = _finite_values(values)
    if not 0 < confidence_level < 1 or samples < 100:
        raise ValueError("invalid bootstrap parameters")
    if array.size < 2:
        return float(array[0]), float(array[0])
    rng = np.random.default_rng(seed)
    draws = rng.choice(array, size=(samples, array.size), replace=True).mean(axis=1)
    alpha = (1.0 - confidence_level) / 2.0
    return float(np.quantile(draws, alpha)), float(np.quantile(draws, 1.0 - alpha))


def paired_summary(
    policy_values: Iterable[float],
    baseline_values: Iterable[float],
    *,
    protocol: EvaluationProtocol,
    seed: int = 0,
) -> dict[str, Any]:
    """Summarize paired observations and classify them without hidden judgment."""

    policy = _finite_values(policy_values)
    baseline = _finite_values(baseline_values)
    if policy.size != baseline.size:
        raise ValueError("paired policy and baseline samples must have equal length")
    if policy.size < protocol.minimum_sample_size:
        return {
            "count": int(policy.size),
            "decision": "inconclusive",
            "reason": "insufficient_sample",
            "policy_mean": float(policy.mean()),
            "baseline_mean": float(baseline.mean()),
        }
    differences = policy - baseline
    ci_low, ci_high = bootstrap_mean_interval(
        differences,
        confidence_level=protocol.effective_confidence_level,
        samples=protocol.bootstrap_samples,
        seed=seed,
    )
    effect = float(differences.mean())
    if protocol.minimum_effect is None:
        decision = "inconclusive"
        reason = "minimum_effect_not_configured"
    elif ci_low >= protocol.minimum_effect:
        decision = "pass"
        reason = "paired_effect_meets_threshold"
    elif ci_high < protocol.minimum_effect:
        decision = "rejected"
        reason = "paired_effect_below_threshold"
    else:
        decision = "inconclusive"
        reason = "confidence_interval_crosses_threshold"
    return {
        "count": int(policy.size),
        "policy_mean": float(policy.mean()),
        "baseline_mean": float(baseline.mean()),
        "effect_mean": effect,
        "effect_std": float(differences.std(ddof=1)),
        "confidence_level": protocol.effective_confidence_level,
        "confidence_interval": {"low": ci_low, "high": ci_high},
        "minimum_effect": protocol.minimum_effect,
        "decision": decision,
        "reason": reason,
    }
