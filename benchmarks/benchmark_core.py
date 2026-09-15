"""Measure the event loop without starting the DearPyGui dashboard."""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import time
from dataclasses import asdict, replace
from pathlib import Path

from app.core.runner import DEFAULT_BASELINE_SCENARIO, SimulationRunner


def run_benchmark(*, runs: int = 3, max_events: int = 2_000) -> dict:
    if runs <= 0 or max_events <= 0:
        raise ValueError("runs and max_events must be positive")
    scenario = replace(DEFAULT_BASELINE_SCENARIO, max_time=max_events)
    observations = []
    for index in range(runs):
        runner = SimulationRunner(scenario=scenario)
        started = time.perf_counter()
        runner.reset(seed=scenario.seed + index)
        metrics = runner.run(max_events=max_events)
        elapsed = time.perf_counter() - started
        observations.append(
            {
                "run": index,
                "seed": scenario.seed + index,
                "elapsed_seconds": round(elapsed, 9),
                "events_processed": metrics["events_processed"],
                "events_per_second": round(metrics["events_processed"] / elapsed, 3)
                if elapsed > 0
                else 0.0,
                "trade_count": metrics["trade_count"],
            }
        )
    return {
        "schema_version": "core-benchmark.v1",
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "configuration": {"runs": runs, "max_events": max_events, "scenario": asdict(scenario)},
        "observations": observations,
        "summary": {
            "mean_events_per_second": round(
                statistics.mean(item["events_per_second"] for item in observations), 3
            ),
            "min_events_per_second": round(
                min(item["events_per_second"] for item in observations), 3
            ),
            "max_events_per_second": round(
                max(item["events_per_second"] for item in observations), 3
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark the headless simulation core")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--max-events", type=int, default=2_000)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = run_benchmark(runs=args.runs, max_events=args.max_events)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
