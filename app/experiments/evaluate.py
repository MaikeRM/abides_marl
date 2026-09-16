"""Independent policy and heuristic evaluation."""

from __future__ import annotations

import argparse
import json
import platform
from collections import defaultdict
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np

from app.core.artifacts import sha256_json
from app.core.runner import SimulationRunner
from app.env import AbidesGymEnv
from app.experiments.config import TrainingConfig, load_training_config
from app.experiments.policy import LinearMultiDiscretePolicy
from app.experiments.protocol import (
    EvaluationProtocol,
    file_sha256,
    paired_summary,
    load_evaluation_protocol,
)
from app.experiments.train import run_policy_episode


HEURISTIC_TYPES = ("MarketMakerAgent", "ValueAgent", "ZeroIntelligenceAgent", "LiquidityTrader")


def _package_version() -> str:
    try:
        return version("abides_marl")
    except PackageNotFoundError:
        return "0.2.0"


def _aggregate(values: list[float]) -> dict[str, float]:
    if not values:
        return {"count": 0, "mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
    array = np.asarray(values, dtype=float)
    if not np.isfinite(array).all():
        raise ValueError("evaluation metrics must be finite")
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


def _strategy_action(
    name: str,
    observation: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Return a deterministic action for a named same-API comparator."""

    if name == "HOLD":
        return np.asarray([0, 0, 0], dtype=np.int64)
    if name == "RANDOM" or name == "ZeroIntelligenceAgent":
        return np.asarray(
            [rng.integers(0, 5), rng.integers(0, 20), rng.integers(0, 10)],
            dtype=np.int64,
        )
    position_fraction = float(observation[4])
    if name == "MarketMakerAgent":
        action_type = 2 if position_fraction > 0.05 else 1
        return np.asarray([action_type, 5, 0], dtype=np.int64)
    if name == "ValueAgent":
        return np.asarray([1 if observation[7] < observation[3] else 2, 8, 0], dtype=np.int64)
    if name == "LiquidityTrader":
        return np.asarray([3, 0, 0], dtype=np.int64)
    raise ValueError(f"unsupported comparison strategy {name!r}")


def run_action_strategy_episode(
    strategy: str,
    *,
    seed: int,
    config: TrainingConfig,
    strategy_seed: int,
) -> dict:
    """Run a comparator through exactly the same Gym API as the policy."""

    env = AbidesGymEnv(
        seed=seed,
        max_steps=config.episode_steps,
        rl_step_interval=config.rl_step_interval,
        scenario=config.scenario,
        position_limit=config.position_limit,
    )
    rng = np.random.default_rng(strategy_seed)
    observation, _ = env.reset(seed=seed)
    total_reward = 0.0
    steps = 0
    info = {}
    pnl_path: list[float] = []
    position_path: list[float] = []
    try:
        for step in range(config.episode_steps):
            action = _strategy_action(strategy, observation, rng)
            observation, reward, terminated, truncated, info = env.step(action)
            total_reward += float(reward)
            steps = step + 1
            pnl_path.append(float(info.get("marked_pnl", 0.0)))
            position_path.append(abs(float(info.get("position", 0))))
            if terminated or truncated:
                break
    finally:
        env.close()
    peak = max(pnl_path, default=0.0)
    max_drawdown = max((peak - value for value in pnl_path), default=0.0)
    market = env.runner.get_market_snapshot(depth=0)
    return {
        "seed": seed,
        "return": round(total_reward, 10),
        "steps": steps,
        "position": info.get("position", 0),
        "marked_pnl": info.get("marked_pnl", 0.0),
        "max_drawdown": round(max_drawdown, 10),
        "max_abs_position": round(max(position_path, default=0.0), 10),
        "trade_count": int(market.get("trade_count", 0)),
        "traded_volume": int(market.get("traded_volume", 0)),
        "spread": info.get("spread", 0.0),
        "market_volume": info.get("market_volume", 0),
    }


def evaluate_paired_strategies(
    policy: LinearMultiDiscretePolicy,
    config: TrainingConfig,
    protocol: EvaluationProtocol,
    *,
    split: str = "validation",
) -> dict:
    """Evaluate policy and comparators on the same seed/scenario pairs."""

    seeds = protocol.seeds_for(split)
    paired_config = TrainingConfig(
        schema_version=config.schema_version,
        seeds=seeds,
        iterations=config.iterations,
        population_size=config.population_size,
        elite_fraction=config.elite_fraction,
        episode_steps=protocol.max_steps,
        rl_step_interval=protocol.rl_step_interval,
        position_limit=config.position_limit,
        scenario=config.scenario,
    )
    strategies: dict[str, list[dict]] = {"policy": []}
    for name in protocol.baseline_names:
        strategies[name] = []
    for index, seed in enumerate(seeds):
        strategies["policy"].append(
            run_policy_episode(
                policy,
                seed=seed,
                config=paired_config,
                stochastic=False,
                policy_seed=seed,
            )
        )
        for name in protocol.baseline_names:
            strategies[name].append(
                run_action_strategy_episode(
                    name,
                    seed=seed,
                    config=paired_config,
                    strategy_seed=seed + 10_000 + index,
                )
            )

    comparisons = {}
    for index, name in enumerate(protocol.baseline_names):
        policy_values = [episode[protocol.primary_metric] for episode in strategies["policy"]]
        baseline_values = [episode[protocol.primary_metric] for episode in strategies[name]]
        comparisons[name] = paired_summary(
            policy_values,
            baseline_values,
            protocol=protocol,
            seed=protocol.training_seeds[0] + index,
        )
        comparisons[name]["metric"] = protocol.primary_metric
        comparisons[name]["pairs"] = [
            {
                "seed": seed,
                "policy": strategies["policy"][pair_index][protocol.primary_metric],
                "baseline": strategies[name][pair_index][protocol.primary_metric],
                "difference": strategies["policy"][pair_index][protocol.primary_metric]
                - strategies[name][pair_index][protocol.primary_metric],
            }
            for pair_index, seed in enumerate(seeds)
        ]

    return {
        "split": split,
        "seeds": list(seeds),
        "strategies": {
            name: {
                "episodes": episodes,
                "aggregate": {
                    metric: _aggregate([episode[metric] for episode in episodes])
                    for metric in ("return", "marked_pnl", "max_drawdown", "max_abs_position", "trade_count", "traded_volume")
                },
            }
            for name, episodes in strategies.items()
        },
        "comparisons": comparisons,
        "decision": "inconclusive"
        if any(item["decision"] == "inconclusive" for item in comparisons.values())
        else ("pass" if all(item["decision"] == "pass" for item in comparisons.values()) else "rejected"),
        "comparison_note": "All strategy adapters use the same Gym episode API and paired seeds; no result is a production or economic approval.",
    }


def evaluate_checkpoint(
    checkpoint: str | Path,
    config: TrainingConfig,
    output_dir: str | Path,
    *,
    protocol: EvaluationProtocol | None = None,
    split: str = "validation",
) -> dict:
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output directory {output}")
    output.mkdir(parents=True, exist_ok=True)
    policy = LinearMultiDiscretePolicy.load(checkpoint)
    checkpoint_path = Path(checkpoint)
    checkpoint_hash = file_sha256(checkpoint_path)
    config_hash = sha256_json(config.as_dict())
    training_metadata = checkpoint_path.parent / "training.json"
    if training_metadata.exists():
        metadata = json.loads(training_metadata.read_text(encoding="utf-8"))
        recorded_hash = metadata.get("config_hash")
        if recorded_hash is not None and recorded_hash != config_hash:
            raise ValueError("checkpoint and evaluation config hashes do not match")

    policy_episodes = evaluate_policy(policy, config)
    result = {
        "schema_version": "evaluation-result.v1",
        "config": config.as_dict(),
        "config_hash": config_hash,
        "checkpoint": checkpoint_path.name,
        "checkpoint_sha256": checkpoint_hash,
        "runtime": {
            "package_version": _package_version(),
            "python_version": platform.python_version(),
        },
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
    if protocol is not None:
        paired = evaluate_paired_strategies(policy, config, protocol, split=split)
        result["schema_version"] = "evaluation-result.v2"
        result["protocol"] = protocol.as_dict()
        result["protocol_hash"] = protocol.config_hash
        result["split"] = split
        result["config_seeds"] = list(config.seeds)
        result["seeds"] = list(paired["seeds"])
        result["evaluation_scope"] = {
            "role": protocol.role,
            "split": split,
            "seeds": list(paired["seeds"]),
            "authoritative_metrics": "paired",
        }
        result["paired"] = paired
        result["decision"] = paired["decision"]
        result["comparison_note"] = paired["comparison_note"]
    result["status"] = "completed" if result.get("decision", "inconclusive") != "failed" else "failed"
    (output / "evaluation.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a checkpoint against the heuristic population")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--protocol")
    parser.add_argument("--split", choices=("validation", "holdout", "stress"), default="validation")
    args = parser.parse_args()
    protocol = load_evaluation_protocol(args.protocol) if args.protocol else None
    result = evaluate_checkpoint(
        args.checkpoint,
        load_training_config(args.config),
        args.output_dir,
        protocol=protocol,
        split=args.split,
    )
    print(json.dumps({"seeds": result["seeds"], "heuristics": sorted(result["heuristics"]), "output": str(Path(args.output_dir) / "evaluation.json")}, sort_keys=True))


if __name__ == "__main__":
    main()
