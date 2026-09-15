"""Small NumPy policy used by the smoke-sized training pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


ACTION_BRANCHES = (5, 20, 10)
OBSERVATION_DIM = 8
PARAMETER_SHAPE = (sum(ACTION_BRANCHES), OBSERVATION_DIM + 1)


@dataclass
class LinearMultiDiscretePolicy:
    """Independent linear logits for the three action branches."""

    weights: np.ndarray

    def __post_init__(self) -> None:
        self.weights = np.asarray(self.weights, dtype=np.float64)
        if self.weights.shape != PARAMETER_SHAPE:
            raise ValueError(f"weights must have shape {PARAMETER_SHAPE}, got {self.weights.shape}")
        if not np.isfinite(self.weights).all():
            raise ValueError("policy weights must be finite")

    @classmethod
    def random(cls, seed: int) -> "LinearMultiDiscretePolicy":
        rng = np.random.default_rng(seed)
        return cls(rng.normal(0.0, 0.05, size=PARAMETER_SHAPE))

    def copy(self) -> "LinearMultiDiscretePolicy":
        return type(self)(self.weights.copy())

    def _logits(self, observation) -> np.ndarray:
        obs = np.asarray(observation, dtype=np.float64)
        if obs.shape != (OBSERVATION_DIM,):
            raise ValueError(f"observation must have shape ({OBSERVATION_DIM},), got {obs.shape}")
        features = np.concatenate([np.clip(obs, -1.0, 1.0), [1.0]])
        return self.weights @ features

    def action(self, observation, *, rng: np.random.Generator | None = None, stochastic: bool = False) -> np.ndarray:
        logits = self._logits(observation)
        result = []
        offset = 0
        for size in ACTION_BRANCHES:
            branch = logits[offset : offset + size]
            if stochastic:
                assert rng is not None
                shifted = branch - np.max(branch)
                probabilities = np.exp(shifted)
                probabilities /= probabilities.sum()
                result.append(int(rng.choice(size, p=probabilities)))
            else:
                result.append(int(np.argmax(branch)))
            offset += size
        return np.asarray(result, dtype=np.int64)

    def save(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(output, weights=self.weights, action_branches=np.asarray(ACTION_BRANCHES))
        return output

    @classmethod
    def load(cls, path: str | Path) -> "LinearMultiDiscretePolicy":
        with np.load(path) as payload:
            branches = tuple(int(value) for value in payload["action_branches"])
            if branches != ACTION_BRANCHES:
                raise ValueError(f"unsupported action branches {branches}")
            return cls(payload["weights"])
