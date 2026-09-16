"""Measure the event loop without starting the DearPyGui dashboard."""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import time
from dataclasses import asdict, replace
from pathlib import Path

try:
    import resource
except ImportError:  # pragma: no cover - platform-specific fallback
    resource = None

from app.core.runner import DEFAULT_BASELINE_SCENARIO, SimulationRunner


def _max_rss_bytes() -> int | None:
    """Return the process high-water RSS in bytes where the platform exposes it."""

    if resource is None:
        return None
    try:
        value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except (AttributeError, OSError):
        return None
    # macOS reports bytes; Linux and the BSDs commonly report KiB.
    return value if platform.system() == "Darwin" else value * 1024


def run_benchmark(*, runs: int = 3, max_events: int = 2_000, warmup_runs: int = 1) -> dict:
    if runs <= 0 or max_events <= 0 or warmup_runs < 0:
        raise ValueError("runs and max_events must be positive; warmup_runs cannot be negative")
    scenario = replace(DEFAULT_BASELINE_SCENARIO, max_time=max_events)
    for index in range(warmup_runs):
        runner = SimulationRunner(scenario=scenario)
        runner.run_artifact(seed=scenario.seed + index, max_events=max_events)

    observations = []
    rss_before = _max_rss_bytes()
    for index in range(runs):
        runner = SimulationRunner(scenario=scenario)
        started = time.perf_counter()
        artifact = runner.run_artifact(seed=scenario.seed + index, max_events=max_events)
        metrics = artifact.metrics
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
                "traded_volume": metrics["traded_volume"],
                "final_time": metrics["final_time"],
                "artifact_bytes": len(artifact.to_json_bytes()),
            }
        )
    rss_after = _max_rss_bytes()
    rss_delta = None
    if rss_before is not None and rss_after is not None:
        rss_delta = max(0, rss_after - rss_before)
    return {
        "schema_version": "core-benchmark.v2",
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "configuration": {
            "runs": runs,
            "warmup_runs": warmup_runs,
            "max_events": max_events,
            "scenario": asdict(scenario),
        },
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
            "mean_artifact_bytes": round(
                statistics.mean(item["artifact_bytes"] for item in observations), 3
            ),
            "max_rss_delta_bytes": rss_delta,
        },
        "resource_budget": {
            "max_events_per_run": max_events,
            "max_rss_bytes": None,
            "max_elapsed_seconds": None,
            "status": "not_configured",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark the headless simulation core")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--max-events", type=int, default=2_000)
    parser.add_argument("--warmup-runs", type=int, default=1)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = run_benchmark(
        runs=args.runs,
        max_events=args.max_events,
        warmup_runs=args.warmup_runs,
    )
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
