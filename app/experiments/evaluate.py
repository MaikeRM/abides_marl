"""Independent policy and heuristic evaluation."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from app.core.runner import SimulationRunner
from app.experiments.config import TrainingConfig, load_training_config
from app.experiments.policy import LinearMultiDiscretePolicy
from app.experiments.train import run_policy_episode


HEURISTIC_TYPES = ("MarketMakerAgent", "ValueAgent", "ZeroIntelligenceAgent", "LiquidityTrader")


def _aggregate(values: list[float]) -> dict[str, float]:
    if not values:
        return {"count": 0, "mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
    array = np.asarray(values, dtype=float)
    return {
        "count": int(array.size),
        "mean": round(float(array.mean()), 10),
        "std": round(float(array.std()), 10),
        "min": round(float(array.min()), 10),
        "max": round(float(array.max()), 10),
    }


def evaluate_policy(policy: LinearMultiDiscretePolicy, config: TrainingConfig) -> list[dict]:
    return [
        run_policy_episode(
            policy,
            seed=seed,
            config=config,
            stochastic=False,
            policy_seed=seed,
        )
        for seed in config.seeds
    ]


def evaluate_heuristics(config: TrainingConfig) -> dict[str, dict[str, float]]:
    by_type: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for seed in config.seeds:
        runner = SimulationRunner(scenario=config.scenario)
        runner.reset(seed=seed, scenario=config.scenario)
        runner.run(max_time=config.scenario.max_time)
        for agent in runner.get_metrics().get("agents", []):
            agent_type = agent["type"]
            if agent_type not in HEURISTIC_TYPES:
                continue
            for metric in ("total_pnl", "realized_pnl", "trade_count", "position"):
                by_type[agent_type][metric].append(float(agent[metric]))
    result = {}
    for agent_type in HEURISTIC_TYPES:
        result[agent_type] = {
            metric: _aggregate(values)["mean"] for metric, values in by_type[agent_type].items()
        }
        result[agent_type]["seed_count"] = len(config.seeds)
    return result


def evaluate_checkpoint(checkpoint: str | Path, config: TrainingConfig, output_dir: str | Path) -> dict:
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output directory {output}")
    output.mkdir(parents=True, exist_ok=True)
    policy = LinearMultiDiscretePolicy.load(checkpoint)
    policy_episodes = evaluate_policy(policy, config)
    result = {
        "schema_version": "evaluation-result.v1",
        "config": config.as_dict(),
        "seeds": list(config.seeds),
        "policy": {
            "episodes": policy_episodes,
            "return": _aggregate([episode["return"] for episode in policy_episodes]),
            "marked_pnl": _aggregate([episode["marked_pnl"] for episode in policy_episodes]),
            "risk": {
                "max_drawdown": _aggregate([episode["max_drawdown"] for episode in policy_episodes]),
                "max_abs_position": _aggregate([episode["max_abs_position"] for episode in policy_episodes]),
            },
            "market": {
                "trade_count": _aggregate([episode["trade_count"] for episode in policy_episodes]),
                "traded_volume": _aggregate([episode["traded_volume"] for episode in policy_episodes]),
                "spread": _aggregate([episode["spread"] for episode in policy_episodes]),
            },
        },
        "heuristics": evaluate_heuristics(config),
        "comparison_note": "Policy and heuristics use the same seeds and scenario; this is a smoke comparison, not a claim of superiority.",
    }
    (output / "evaluation.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a checkpoint against the heuristic population")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    result = evaluate_checkpoint(args.checkpoint, load_training_config(args.config), args.output_dir)
    print(json.dumps({"seeds": result["seeds"], "heuristics": sorted(result["heuristics"]), "output": str(Path(args.output_dir) / "evaluation.json")}, sort_keys=True))


if __name__ == "__main__":
    main()
