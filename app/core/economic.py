"""Explicit economic policies used by the laboratory simulator.

The historical scenario intentionally keeps the old unconstrained accounting
semantics.  The policy object makes that choice observable and provides a
separate constrained profile for experiments without changing the default
baseline implicitly.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any


ECONOMIC_POLICY_SCHEMA_VERSION = "economic-policy.v1"
MARKING_METHODS = {"last_trade", "mid"}
TERMINAL_SETTLEMENTS = {"mark_only", "mark_to_market"}


class EconomicPolicyError(ValueError):
    """A valid order rejected by the selected economic policy."""


@dataclass(frozen=True, slots=True)
class EconomicPolicy:
    """Named accounting and risk semantics for one simulation profile."""

    name: str = "legacy_unconstrained"
    initial_cash: float = 0.0
    allow_short: bool = True
    allow_self_trade: bool = True
    enforce_cash: bool = False
    enforce_inventory: bool = False
    position_limit: int | None = None
    maker_fee_rate: float = 0.0
    taker_fee_rate: float = 0.0
    marking: str = "last_trade"
    terminal_settlement: str = "mark_only"
    schema_version: str = ECONOMIC_POLICY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != ECONOMIC_POLICY_SCHEMA_VERSION:
            raise ValueError(f"unsupported economic policy schema {self.schema_version!r}")
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("economic policy name must be a non-empty string")
        if not isfinite(float(self.initial_cash)):
            raise ValueError("initial_cash must be finite")
        if self.position_limit is not None and (
            not isinstance(self.position_limit, int)
            or isinstance(self.position_limit, bool)
            or self.position_limit <= 0
        ):
            raise ValueError("position_limit must be a positive integer or None")
        for field in ("maker_fee_rate", "taker_fee_rate"):
            rate = float(getattr(self, field))
            if not isfinite(rate) or rate < 0:
                raise ValueError(f"{field} must be finite and non-negative")
        if self.marking not in MARKING_METHODS:
            raise ValueError(f"unsupported marking method {self.marking!r}")
        if self.terminal_settlement not in TERMINAL_SETTLEMENTS:
            raise ValueError(f"unsupported terminal settlement {self.terminal_settlement!r}")

    @classmethod
    def from_name(cls, name: str) -> "EconomicPolicy":
        """Resolve a versioned policy name without accepting implicit defaults."""

        if name == "legacy_unconstrained":
            return cls()
        if name == "cash_inventory_constrained":
            return cls(
                name=name,
                initial_cash=100_000.0,
                allow_short=False,
                allow_self_trade=False,
                enforce_cash=True,
                enforce_inventory=True,
                position_limit=100,
                maker_fee_rate=0.0001,
                taker_fee_rate=0.0005,
                marking="mid",
                terminal_settlement="mark_to_market",
            )
        raise ValueError(f"unknown economic policy {name!r}")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def fee(self, notional: float, *, liquidity: str) -> float:
        """Return the non-negative fee for one fill."""

        if not isfinite(float(notional)) or notional < 0:
            raise ValueError("notional must be finite and non-negative")
        if liquidity not in {"maker", "taker"}:
            raise ValueError("liquidity must be 'maker' or 'taker'")
        rate = self.maker_fee_rate if liquidity == "maker" else self.taker_fee_rate
        return float(notional) * rate

    def mark_price(
        self,
        *,
        last_trade: float,
        best_bid: float | None = None,
        best_ask: float | None = None,
    ) -> float:
        """Return the policy's mark, falling back safely when the book is empty."""

        if self.marking == "mid" and best_bid is not None and best_ask is not None:
            candidate = (float(best_bid) + float(best_ask)) / 2.0
        else:
            candidate = float(last_trade)
        if not isfinite(candidate) or candidate <= 0:
            raise ValueError("mark price must be finite and positive")
        return candidate


def resolve_economic_policy(
    policy: str | EconomicPolicy | None,
) -> EconomicPolicy:
    """Resolve a scenario/configuration value into a validated policy."""

    if policy is None:
        return EconomicPolicy.from_name("legacy_unconstrained")
    if isinstance(policy, EconomicPolicy):
        return policy
    if isinstance(policy, str):
        return EconomicPolicy.from_name(policy)
    raise TypeError("economic policy must be a name, EconomicPolicy, or None")
