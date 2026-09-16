"""Stable, JSON-serializable artifacts for reproducible simulations.

The simulator also keeps a wall-clock timestamp for the dashboard.  That
timestamp is deliberately excluded from the canonical artifact in this
module: it is useful for observability, but it is not evidence of a
reproducible experiment.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ARTIFACT_SCHEMA_VERSION = "baseline-artifact.v1"
TRACE_SCHEMA_VERSION = "canonical-trace.v1"


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize a JSON value with stable ordering and separators."""

    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    """Return the SHA-256 digest of a canonical JSON value."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class BaselineArtifact:
    """Complete deterministic output of one baseline execution."""

    manifest: dict[str, Any]
    metrics: dict[str, Any]
    trace: list[dict[str, Any]]

    def __post_init__(self) -> None:
        if not isinstance(self.manifest, dict) or not isinstance(self.metrics, dict):
            raise ValueError("manifest and metrics must be dictionaries")
        if not isinstance(self.trace, list):
            raise ValueError("trace must be a list")
        manifest_horizon = self.manifest.get("horizon")
        metric_horizon = self.metrics.get("horizon")
        if not isinstance(manifest_horizon, dict) or not isinstance(metric_horizon, dict):
            raise ValueError("artifact must declare manifest and metric horizons")
        for field in ("max_time", "max_events", "final_time"):
            if manifest_horizon.get(field) != metric_horizon.get(field):
                raise ValueError(f"artifact horizon mismatch for {field}")
        if manifest_horizon["final_time"] > manifest_horizon["max_time"]:
            raise ValueError("artifact final_time exceeds its effective max_time")

    @property
    def trace_hash(self) -> str:
        return sha256_json(self.trace)

    def as_dict(self) -> dict[str, Any]:
        """Return the artifact payload used for persistence and comparison."""

        return {
            "manifest": self.manifest,
            "metrics": self.metrics,
            "trace": self.trace,
            "trace_hash": self.trace_hash,
        }

    def to_json_bytes(self) -> bytes:
        """Return byte-stable UTF-8 JSON, including a final newline."""

        return canonical_json_bytes(self.as_dict()) + b"\n"

    def write(self, destination: str | Path) -> Path:
        """Write ``baseline.json`` into *destination* and return its path."""

        path = Path(destination)
        if path.suffix.lower() == ".json":
            output_path = path
            output_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            path.mkdir(parents=True, exist_ok=True)
            output_path = path / "baseline.json"
        output_path.write_bytes(self.to_json_bytes())
        return output_path
