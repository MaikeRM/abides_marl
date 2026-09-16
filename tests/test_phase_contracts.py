import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from app.agents.base import HeuristicAgent
from app.agents.exchange import ExchangeAgent
from app.core.runner import DEFAULT_BASELINE_SCENARIO, SimulationRunner
from app.models.types import Message


class RecordingTrader(HeuristicAgent):
    def __init__(self, agent_id, name):
        super().__init__(agent_id, name)
        self.messages = []

    def wakeup(self, now):
        return None

    def receive(self, msg):
        self.messages.append(msg)
        if msg.kind == "ORDER_ACCEPTED":
            self.handle_order_accepted(msg)
        elif msg.kind == "EXECUTION":
            self.handle_execution(msg)
        elif msg.kind == "ORDER_CANCELLED":
            self.handle_order_cancelled(msg)
        elif msg.kind == "ORDER_REJECTED":
            self.handle_order_rejected(msg)


class CoreContractTest(unittest.TestCase):
    def setUp(self):
        from app.core.kernel import Kernel

        self.kernel = Kernel(seed=5)
        self.kernel.print_logs = False
        self.exchange = ExchangeAgent(0)
        self.buyer = RecordingTrader(1, "BUYER")
        self.seller = RecordingTrader(2, "SELLER")
        for agent in (self.exchange, self.buyer, self.seller):
            self.kernel.register(agent)

    def drain(self):
        while self.kernel.has_events:
            self.kernel.step()

    def test_partial_fill_has_both_order_ids_and_trade_id(self):
        self.exchange._handle_new_order(
            Message(1, 0, "NEW_ORDER", {"order_type": "LIMIT", "side": "BUY", "qty": 5, "price": 100})
        )
        self.drain()
        self.exchange._handle_new_order(
            Message(2, 0, "NEW_ORDER", {"order_type": "LIMIT", "side": "SELL", "qty": 2, "price": 100})
        )
        self.drain()

        trade = self.exchange.history[-1]
        self.assertEqual(trade.buyer_order_id, 1)
        self.assertEqual(trade.seller_order_id, 2)
        self.assertEqual(trade.trade_id, 1)
        fills = [msg for msg in self.buyer.messages + self.seller.messages if msg.kind == "EXECUTION"]
        self.assertEqual({msg.data["order_id"] for msg in fills}, {1, 2})
        self.assertEqual({msg.data["trade_id"] for msg in fills}, {1})
        self.exchange.validate_invariants()

    def test_market_order_without_liquidity_is_not_resting(self):
        self.exchange._handle_new_order(
            Message(1, 0, "NEW_ORDER", {"order_type": "MARKET", "side": "BUY", "qty": 3})
        )
        self.assertEqual(self.exchange._order_map, {})
        self.assertEqual(self.exchange.total_trades, 0)
        self.drain()
        self.assertEqual(self.buyer.messages, [])

    def test_invalid_order_does_not_mutate_book(self):
        before = self.exchange.snapshot()
        with self.assertRaises(ValueError):
            self.exchange._handle_new_order(
                Message(1, 0, "NEW_ORDER", {"order_type": "LIMIT", "side": "BUY", "qty": 0, "price": 100})
            )
        self.assertEqual(self.exchange.snapshot(), before)

    def test_reset_clears_exchange_and_kernel_trace(self):
        self.exchange._handle_new_order(
            Message(1, 0, "NEW_ORDER", {"order_type": "LIMIT", "side": "BUY", "qty": 1, "price": 99})
        )
        self.assertTrue(self.kernel.canonical_event_history)
        self.exchange.reset()
        self.kernel.reset(seed=5)
        self.assertEqual(self.exchange.snapshot()["bids"], [])
        self.assertEqual(self.exchange.last_trade, 100.0)
        self.assertEqual(self.kernel.get_canonical_trace(), [])

    def test_baseline_artifact_excludes_wall_clock_timestamp(self):
        scenario = replace(DEFAULT_BASELINE_SCENARIO, max_time=80)
        first = SimulationRunner(scenario).run_artifact()
        second = SimulationRunner(scenario).run_artifact()
        self.assertEqual(first.to_json_bytes(), second.to_json_bytes())
        self.assertTrue(all("timestamp" not in event for event in first.trace))
        with tempfile.TemporaryDirectory() as directory:
            path = first.write(directory)
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                hashlib.sha256(second.write(Path(directory) / "second.json").read_bytes()).hexdigest(),
            )
            payload = json.loads(path.read_text())
            self.assertEqual(payload["trace_hash"], first.trace_hash)


class PhaseContractTest(unittest.TestCase):
    def test_artifact_records_effective_execution_horizon(self):
        scenario = replace(
            DEFAULT_BASELINE_SCENARIO,
            num_market_makers=1,
            num_value_agents=0,
            num_zero_intelligence_agents=0,
            include_liquidity_trader=False,
            max_time=1000,
        )
        artifact = SimulationRunner(scenario).run_artifact(seed=7, max_time=12)
        self.assertEqual(artifact.manifest["horizon"]["max_time"], 12)
        self.assertEqual(artifact.metrics["horizon"]["max_time"], 12)
        self.assertEqual(artifact.manifest["horizon"]["final_time"], artifact.metrics["final_time"])
        self.assertLessEqual(artifact.metrics["final_time"], 12)

    def test_public_runner_and_kernel_snapshots_are_detached(self):
        scenario = replace(
            DEFAULT_BASELINE_SCENARIO,
            num_market_makers=1,
            num_value_agents=0,
            num_zero_intelligence_agents=0,
            include_liquidity_trader=False,
            max_time=20,
        )
        runner = SimulationRunner(scenario)
        runner.reset(seed=8)
        kernel_snapshot = runner.kernel.snapshot()
        self.assertIn(0, kernel_snapshot["registered_agent_ids"])
        market_snapshot = runner.get_market_snapshot(depth=0)
        market_snapshot["economic_policy"]["name"] = "mutated"
        self.assertEqual(runner.economic_policy.name, "legacy_unconstrained")
        runner.run(max_time=5)
        self.assertFalse(runner.is_running)
        self.assertFalse(runner.has_pending_events)


if __name__ == "__main__":
    unittest.main()
