"""Reproducible short-horizon policy training."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from app.core.artifacts import sha256_json
from app.env import AbidesGymEnv
from app.experiments.config import TrainingConfig, load_training_config
from app.experiments.policy import LinearMultiDiscretePolicy


def run_policy_episode(
    policy: LinearMultiDiscretePolicy,
    *,
    seed: int,
    config: TrainingConfig,
    stochastic: bool,
    policy_seed: int,
) -> dict:
    env = AbidesGymEnv(
        seed=seed,
        max_steps=config.episode_steps,
        rl_step_interval=config.rl_step_interval,
        scenario=config.scenario,
        position_limit=config.position_limit,
    )
    rng = np.random.default_rng(policy_seed)
    observation, _ = env.reset(seed=seed)
    total_reward = 0.0
    steps = 0
    info = {}
    pnl_path = []
    position_path = []
    try:
        for step in range(config.episode_steps):
            action = policy.action(observation, rng=rng, stochastic=stochastic)
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
    return {
        "seed": seed,
        "return": round(total_reward, 10),
        "steps": steps,
        "position": info.get("position", 0),
        "marked_pnl": info.get("marked_pnl", 0.0),
        "max_drawdown": round(max_drawdown, 10),
        "max_abs_position": round(max(position_path, default=0.0), 10),
        "trade_count": env.runner.exchange.total_trades if env.runner.exchange else 0,
        "traded_volume": env.runner.exchange.total_traded_qty if env.runner.exchange else 0,
        "spread": info.get("spread", 0.0),
        "market_volume": info.get("market_volume", 0),
    }


def train_policy(config: TrainingConfig, output_dir: str | Path) -> dict:
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output directory {output}")
    output.mkdir(parents=True, exist_ok=True)

    master_rng = np.random.default_rng(config.seeds[0])
    policy = LinearMultiDiscretePolicy.random(config.seeds[0])
    sigma = 0.25
    iteration_records = []
    for iteration in range(config.iterations):
        candidates = []
        for candidate_index in range(config.population_size):
            noise = master_rng.normal(0.0, sigma, size=policy.weights.shape)
            candidates.append(policy.weights + noise)
        scored = []
        for candidate_index, weights in enumerate(candidates):
            candidate = LinearMultiDiscretePolicy(weights)
            episodes = [
                run_policy_episode(
                    candidate,
                    seed=seed,
                    config=config,
                    stochastic=True,
                    policy_seed=config.seeds[0] + iteration * 1000 + candidate_index * 100 + index,
                )
                for index, seed in enumerate(config.seeds)
            ]
            scored.append({"candidate": candidate_index, "score": float(np.mean([episode["return"] for episode in episodes])), "episodes": episodes})
        scored.sort(key=lambda item: (-item["score"], item["candidate"]))
        elite = scored[: config.elite_count]
        policy = LinearMultiDiscretePolicy(np.mean([candidates[item["candidate"]] for item in elite], axis=0))
        sigma = max(0.05, sigma * 0.7)
        iteration_records.append({"iteration": iteration, "sigma": sigma, "candidates": scored, "elite": [item["candidate"] for item in elite]})

    checkpoint = policy.save(output / "checkpoint.npz")
    result = {
        "schema_version": "training-result.v1",
        "config": config.as_dict(),
        "seeds": list(config.seeds),
        "iterations": iteration_records,
        "final_weight_hash": sha256_json(policy.weights.tolist()),
        "checkpoint": checkpoint.name,
    }
    (output / "training.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a short reproducible CEM policy training job")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    result = train_policy(load_training_config(args.config), args.output_dir)
    print(json.dumps({"checkpoint": result["checkpoint"], "seeds": result["seeds"], "iterations": len(result["iterations"])}, sort_keys=True))


if __name__ == "__main__":
    main()
