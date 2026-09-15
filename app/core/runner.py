import json
import platform
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, replace
from importlib.metadata import PackageNotFoundError, version
from math import isfinite
from typing import Optional

from app.agents.exchange import ExchangeAgent
from app.agents.liquidity import LiquidityTrader
from app.agents.market_maker import MarketMakerAgent
from app.agents.value_agent import ValueAgent
from app.agents.zi_agent import ZeroIntelligenceAgent
from app.core.kernel import Kernel
from app.core.oracle import Oracle
from app.core.artifacts import (
    ARTIFACT_SCHEMA_VERSION,
    TRACE_SCHEMA_VERSION,
    BaselineArtifact,
    sha256_json,
)


@dataclass(frozen=True, slots=True)
class BaselineScenario:
    seed: int = 42
    start_price: float = 100.0
    num_market_makers: int = 5
    num_value_agents: int = 10
    num_zero_intelligence_agents: int = 20
    include_liquidity_trader: bool = True
    market_maker_wake_interval: int = 3
    value_agent_wake_interval: int = 8
    zero_intelligence_wake_interval: int = 5
    liquidity_wake_interval: int = 15
    liquidity_target_qty: int = 100
    liquidity_deadline: int = 8000
    max_time: int = 1000
    latency_min: int = 1
    latency_max: int = 10

    def __post_init__(self) -> None:
        if not isinstance(self.seed, int) or isinstance(self.seed, bool):
            raise ValueError("seed must be an integer")
        if not isfinite(float(self.start_price)) or self.start_price <= 0:
            raise ValueError("start_price must be finite and positive")
        for name in (
            "num_market_makers",
            "num_value_agents",
            "num_zero_intelligence_agents",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        for name in (
            "market_maker_wake_interval",
            "value_agent_wake_interval",
            "zero_intelligence_wake_interval",
            "liquidity_wake_interval",
            "liquidity_target_qty",
            "liquidity_deadline",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if not isinstance(self.max_time, int) or isinstance(self.max_time, bool) or self.max_time < 0:
            raise ValueError("max_time must be a non-negative integer")
        if (
            not isinstance(self.latency_min, int)
            or not isinstance(self.latency_max, int)
            or self.latency_min < 0
            or self.latency_max < self.latency_min
        ):
            raise ValueError("latency bounds must be integers with 0 <= min <= max")


DEFAULT_BASELINE_SCENARIO = BaselineScenario()


class SimulationRunner:
    def __init__(self, scenario: BaselineScenario = DEFAULT_BASELINE_SCENARIO):
        self.scenario = scenario
        self.kernel: Optional[Kernel] = None
        self.oracle: Optional[Oracle] = None
        self.exchange: Optional[ExchangeAgent] = None
        self.agents = []
        self.running = False
        self.events_processed = 0
        self._stopped = False

    def reset(
        self,
        seed: int | None = None,
        scenario: BaselineScenario | None = None,
    ) -> None:
        baseline = scenario or self.scenario
        if seed is not None:
            baseline = replace(baseline, seed=seed)
        self.scenario = baseline

        self.kernel = Kernel(seed=baseline.seed)
        self.kernel.print_logs = False
        self.oracle = Oracle(
            r_bar=baseline.start_price,
            kappa=0.05,
            sigma=0.5,
            seed=baseline.seed + 1000,
        )
        self.exchange = ExchangeAgent(agent_id=0, start_price=baseline.start_price)
        self.kernel.register(self.exchange)

        self.agents = []
        self.running = True
        self.events_processed = 0
        self._stopped = False

        agent_id = 1

        for i in range(baseline.num_market_makers):
            mm = MarketMakerAgent(
                agent_id=agent_id,
                exchange_id=0,
                seed=baseline.seed + agent_id,
                wake_interval=baseline.market_maker_wake_interval,
                spread=0.80 + i * 0.20,
                order_qty=5,
            )
            self.kernel.register(mm)
            self.agents.append(mm)
            agent_id += 1

        for i in range(baseline.num_value_agents):
            va = ValueAgent(
                agent_id=agent_id,
                exchange_id=0,
                oracle=self.oracle,
                seed=baseline.seed + agent_id,
                wake_interval=baseline.value_agent_wake_interval,
                kappa=0.05,
                sigma_s=0.5,
                sigma_n=1.0 + i * 0.1,
                theta=self.kernel.rng.gauss(0, 1.0),
            )
            self.kernel.register(va)
            self.agents.append(va)
            agent_id += 1

        if baseline.include_liquidity_trader:
            lt = LiquidityTrader(
                agent_id=agent_id,
                exchange_id=0,
                seed=baseline.seed + agent_id,
                target_qty=baseline.liquidity_target_qty,
                deadline=baseline.liquidity_deadline,
                wake_interval=baseline.liquidity_wake_interval,
                side="BUY",
            )
            self.kernel.register(lt)
            self.agents.append(lt)
            agent_id += 1

        for i in range(baseline.num_zero_intelligence_agents):
            zi = ZeroIntelligenceAgent(
                agent_id=agent_id,
                exchange_id=0,
                seed=baseline.seed + agent_id,
                wake_interval=baseline.zero_intelligence_wake_interval,
                base_value=baseline.start_price,
                theta_std=2.0 + i * 0.1,
            )
            self.kernel.register(zi)
            self.agents.append(zi)
            agent_id += 1

        for src in range(agent_id):
            for dst in range(agent_id):
                if src == dst:
                    self.kernel.set_latency(src, dst, 0)
                else:
                    self.kernel.set_latency(
                        src,
                        dst,
                        self.kernel.rng.randint(
                            baseline.latency_min,
                            baseline.latency_max,
                        ),
                    )

        for agent in self.agents:
            self.kernel.wakeup(agent.agent_id, at_time=1)

    def register_agent(self, agent, *, first_wakeup: int | None = 1) -> None:
        """Register an additional agent through the runner's public API."""

        if self.kernel is None:
            raise RuntimeError("reset the runner before registering an agent")
        self.kernel.register(agent)
        for existing_id in list(self.kernel._agents):
            if existing_id == agent.agent_id:
                continue
            self.kernel.set_latency(agent.agent_id, existing_id, 2)
            self.kernel.set_latency(existing_id, agent.agent_id, 2)
        self.kernel.set_latency(agent.agent_id, agent.agent_id, 0)
        if first_wakeup is not None:
            self.kernel.wakeup(agent.agent_id, at_time=first_wakeup)
        self.agents.append(agent)

    def reset_agent(self, agent) -> None:
        """Reset a registered agent without reaching into environment internals."""

        agent.reset()

    def stop(self) -> None:
        if not self.kernel or self._stopped:
            return

        final_fund_price = self.oracle.get_value(self.kernel.time) if self.oracle else 0.0

        for agent in self.agents:
            agent.kernelStopping()

            if hasattr(agent, "position") and hasattr(agent, "cash"):
                surplus = (agent.position * final_fund_price) + agent.cash
                self.kernel.log(
                    f"FINAL_VALUATION: {agent.name} Surplus = {surplus:.2f} "
                    f"(Pos: {agent.position}, Cash: {agent.cash:.2f})"
                )

        self.running = False
        self.kernel.running = False
        self._stopped = True

    def step(self) -> bool:
        if self.kernel and self.kernel.running:
            stepped = self.kernel.step()
            if stepped:
                self.events_processed += 1
            return stepped
        return False

    def run(
        self,
        max_time: int | None = None,
        max_events: int | None = None,
    ) -> dict:
        if not self.kernel:
            self.reset()

        time_limit = self.scenario.max_time if max_time is None else max_time

        while self.kernel and self.kernel.running and self.kernel.has_events:
            next_delivery = self.kernel.next_delivery_time
            if time_limit is not None and next_delivery > time_limit:
                break
            if max_events is not None and self.events_processed >= max_events:
                break
            if not self.step():
                break

        self.stop()
        return self.get_metrics()

    def build_artifact(self) -> BaselineArtifact:
        """Build a reproducible artifact for the most recent execution."""

        if not self.kernel:
            raise RuntimeError("run or reset the runner before building an artifact")
        metrics = self.get_metrics()
        trace = self.kernel.get_canonical_trace()
        manifest = {
            "schema_version": ARTIFACT_SCHEMA_VERSION,
            "trace_schema_version": TRACE_SCHEMA_VERSION,
            "project_version": _project_version(),
            "python_version": platform.python_version(),
            "seed": self.scenario.seed,
            "horizon": {"max_time": self.scenario.max_time},
            "scenario": asdict(self.scenario),
            "metric_keys": sorted(metrics),
            "trace_hash": sha256_json(trace),
        }
        return BaselineArtifact(manifest=manifest, metrics=metrics, trace=trace)

    def run_artifact(
        self,
        *,
        seed: int | None = None,
        max_time: int | None = None,
        max_events: int | None = None,
    ) -> BaselineArtifact:
        """Reset, execute, and return a complete canonical baseline artifact."""

        self.reset(seed=seed)
        self.run(max_time=max_time, max_events=max_events)
        return self.build_artifact()

    def run_baseline(
        self,
        seed: int | None = None,
        max_time: int | None = None,
        max_events: int | None = None,
    ) -> dict:
        self.reset(seed=seed, scenario=DEFAULT_BASELINE_SCENARIO)
        return self.run(max_time=max_time, max_events=max_events)

    def get_metrics(self) -> dict:
        if not self.kernel or not self.exchange:
            return {}

        best_bid = self.exchange.bids[0].price if self.exchange.bids else None
        best_ask = self.exchange.asks[0].price if self.exchange.asks else None
        spread = round(best_ask - best_bid, 2) if best_bid is not None and best_ask is not None else None
        reference_price = self.exchange.last_trade
        fundamental_value = self.oracle.get_value(self.kernel.time) if self.oracle else 0.0

        agent_type_counts = Counter(type(agent).__name__ for agent in self.agents)
        agent_metrics = []
        for agent in self.agents:
            total_pnl = (
                agent.compute_pnl(reference_price)
                if hasattr(agent, "compute_pnl")
                else 0.0
            )
            agent_metrics.append(
                {
                    "agent_id": agent.agent_id,
                    "name": getattr(agent, "name", str(agent.agent_id)),
                    "type": type(agent).__name__,
                    "position": getattr(agent, "position", 0),
                    "cash": round(getattr(agent, "cash", 0.0), 2),
                    "realized_pnl": round(getattr(agent, "realized_pnl", 0.0), 2),
                    "total_pnl": round(total_pnl, 2),
                    "active_orders": len(getattr(agent, "active_orders", {})),
                    "trade_count": len(getattr(agent, "trade_history", [])),
                }
            )

        liquidity_summary = None
        for agent in self.agents:
            if isinstance(agent, LiquidityTrader):
                filled_qty = agent.target_qty - agent.remaining_qty
                liquidity_summary = {
                    "agent_id": agent.agent_id,
                    "target_qty": agent.target_qty,
                    "filled_qty": filled_qty,
                    "remaining_qty": agent.remaining_qty,
                    "fill_ratio": round(filled_qty / agent.target_qty, 4)
                    if agent.target_qty
                    else 0.0,
                }
                break

        return {
            "scenario": asdict(self.scenario),
            "final_time": self.kernel.time,
            "events_processed": self.events_processed,
            "last_trade": round(self.exchange.last_trade, 2),
            "fundamental_value": round(fundamental_value, 2),
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread": spread,
            "resting_bid_qty": sum(order.qty for order in self.exchange.bids),
            "resting_ask_qty": sum(order.qty for order in self.exchange.asks),
            "trade_count": self.exchange.total_trades,
            "traded_volume": self.exchange.total_traded_qty,
            "traded_notional": round(self.exchange.total_traded_notional, 2),
            "agent_type_counts": dict(agent_type_counts),
            "liquidity_trader": liquidity_summary,
            "agents": agent_metrics,
        }

    def get_state(self):
        if not self.kernel or not self.exchange:
            return {}

        bid_levels = defaultdict(int)
        for order in self.exchange.bids:
            bid_levels[order.price] += order.qty

        ask_levels = defaultdict(int)
        for order in self.exchange.asks:
            ask_levels[order.price] += order.qty

        best_bids = sorted(
            [{"price": price, "qty": qty} for price, qty in bid_levels.items()],
            key=lambda item: -item["price"],
        )[:40]
        best_asks = sorted(
            [{"price": price, "qty": qty} for price, qty in ask_levels.items()],
            key=lambda item: item["price"],
        )[:40]

        agent_states = {}
        for agent in self.agents:
            agent_states[agent.agent_id] = {
                "name": getattr(agent, "name", str(agent.agent_id)),
                "type": type(agent).__name__,
                "position": getattr(agent, "position", 0),
                "cash": getattr(agent, "cash", 0.0),
                "vwap": getattr(agent, "vwap", 0.0),
                "realized_pnl": getattr(agent, "realized_pnl", 0.0),
                "active_orders": getattr(agent, "active_orders", {}),
                "trade_history": getattr(agent, "trade_history", []),
            }

        return {
            "time": self.kernel.time,
            "last_price": self.exchange.last_trade,
            "fundamental_value": self.oracle.get_value(self.kernel.time)
            if self.oracle
            else 0.0,
            "bids": best_bids,
            "asks": best_asks,
            "history": [
                {"time": trade.ts, "price": trade.price, "qty": trade.qty, "side": trade.aggressor_side}
                for trade in self.exchange.history[-20:]
            ],
            "events": list(self.kernel.event_history)[-300:],
            "agents": agent_states,
        }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run the deterministic baseline scenario")
    parser.add_argument("--artifact-dir", help="write a stable baseline.json artifact")
    parser.add_argument("--max-time", type=int, default=None)
    parser.add_argument("--max-events", type=int, default=None)
    args = parser.parse_args()

    runner = SimulationRunner()
    runner.reset()
    metrics = runner.run(max_time=args.max_time, max_events=args.max_events)
    if args.artifact_dir:
        path = runner.build_artifact().write(args.artifact_dir)
        print(f"artifact={path}")
    print(json.dumps(metrics, indent=2, sort_keys=True))


def _project_version() -> str:
    try:
        return version("abides_marl")
    except PackageNotFoundError:
        return "0.2.0"


if __name__ == "__main__":
    main()
