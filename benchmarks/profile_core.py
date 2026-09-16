"""Profile the headless event loop without starting the dashboard."""

from __future__ import annotations

import argparse
import cProfile
import json
import pstats
import time
from pathlib import Path

from app.core.runner import DEFAULT_BASELINE_SCENARIO, SimulationRunner


def profile_core(*, max_events: int = 2_000, top: int = 20) -> dict:
    if max_events <= 0 or top <= 0:
        raise ValueError("max_events and top must be positive")
    runner = SimulationRunner(DEFAULT_BASELINE_SCENARIO)
    profiler = cProfile.Profile()
    started = time.perf_counter()
    profiler.enable()
    artifact = runner.run_artifact(max_events=max_events)
    profiler.disable()
    elapsed = time.perf_counter() - started

    stats = pstats.Stats(profiler)
    rows = []
    for (filename, line, function), values in sorted(
        stats.stats.items(), key=lambda item: item[1][3], reverse=True
    )[:top]:
        primitive_calls, total_calls, total_time, cumulative_time, _callers = values
        rows.append(
            {
                "file": filename,
                "line": line,
                "function": function,
                "primitive_calls": primitive_calls,
                "calls": total_calls,
                "total_seconds": round(total_time, 9),
                "cumulative_seconds": round(cumulative_time, 9),
            }
        )

    return {
        "schema_version": "core-profile.v1",
        "configuration": {"max_events": max_events, "top": top},
        "elapsed_seconds": round(elapsed, 9),
        "events_processed": artifact.metrics["events_processed"],
        "trace_events": len(artifact.trace),
        "artifact_bytes": len(artifact.to_json_bytes()),
        "trace_hash": artifact.trace_hash,
        "top_functions": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile the headless simulation core")
    parser.add_argument("--max-events", type=int, default=2_000)
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = profile_core(max_events=args.max_events, top=args.top)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
