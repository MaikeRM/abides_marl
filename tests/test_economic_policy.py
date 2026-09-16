import unittest
from dataclasses import replace

from app.agents.base import HeuristicAgent
from app.agents.exchange import ExchangeAgent
from app.core.economic import EconomicPolicy
from app.core.kernel import Kernel
from app.models.types import Message


class PassivePolicyAgent(HeuristicAgent):
    def wakeup(self, now: int) -> None:
        pass

    def receive(self, msg) -> None:
        if msg.kind == "EXECUTION":
            self.handle_execution(msg)
        elif msg.kind == "ORDER_ACCEPTED":
            self.handle_order_accepted(msg)
        elif msg.kind == "ORDER_CANCELLED":
            self.handle_order_cancelled(msg)
        elif msg.kind == "ORDER_REJECTED":
            self.handle_order_rejected(msg)


class EconomicPolicyTest(unittest.TestCase):
    def setUp(self):
        self.policy = EconomicPolicy.from_name("cash_inventory_constrained")
        self.kernel = Kernel(seed=3)
        self.kernel.print_logs = False
        self.exchange = ExchangeAgent(0, economic_policy=self.policy)
        self.agent = PassivePolicyAgent(1, "TRADER")
        self.agent.configure_economic_policy(self.policy)
        self.kernel.register(self.exchange)
        self.kernel.register(self.agent)

    def drain(self):
        while self.kernel.has_events:
            self.kernel.step()

    def test_cash_inventory_and_self_trade_rejections_are_structured(self):
        self.agent.cash = 0.0
        cash_result = self.exchange.try_submit_order(
            Message(src=1, dst=0, kind="NEW_ORDER", data={"side": "BUY", "qty": 1, "price": 100.0})
        )
        self.assertEqual(cash_result["status"], "REJECTED")
        self.assertIn("cash", cash_result["reason"])
        self.drain()
        self.assertEqual(self.agent.last_action_status, "REJECTED")
        self.assertEqual(self.agent.last_rejection["order_id"], None)

        self.agent.cash = self.agent.initial_cash
        inventory_result = self.exchange.try_submit_order(
            Message(src=1, dst=0, kind="NEW_ORDER", data={"side": "SELL", "qty": 1, "price": 100.0})
        )
        self.assertEqual(inventory_result["status"], "REJECTED")
        self.assertIn("inventory", inventory_result["reason"])

        self.exchange._handle_new_order(
            Message(src=1, dst=0, kind="NEW_ORDER", data={"side": "BUY", "qty": 1, "price": 100.0})
        )
        self.drain()
        self_trade_result = self.exchange.try_submit_order(
            Message(src=1, dst=0, kind="NEW_ORDER", data={"side": "SELL", "qty": 1, "price": 100.0})
        )
        self.assertEqual(self_trade_result["status"], "REJECTED")
        self.assertIn("self-trade", self_trade_result["reason"])
        self.exchange.validate_invariants()

    def test_partial_fill_and_cancel_release_only_the_remaining_reservation(self):
        reservation_policy = replace(self.policy, allow_short=True, enforce_inventory=False)
        self.exchange.economic_policy = reservation_policy
        self.agent.configure_economic_policy(reservation_policy)
        self.exchange._handle_new_order(
            Message(src=1, dst=0, kind="NEW_ORDER", data={"side": "BUY", "qty": 10, "price": 100.0})
        )
        self.assertEqual(self.exchange._order_reservations[1]["remaining_qty"], 10)

        other = PassivePolicyAgent(2, "OTHER")
        other.configure_economic_policy(reservation_policy)
        self.kernel.register(other)
        self.kernel.set_latency(2, 0, 0)
        self.kernel.set_latency(0, 2, 0)
        self.exchange._handle_new_order(
            Message(src=2, dst=0, kind="NEW_ORDER", data={"side": "SELL", "qty": 4, "price": 100.0})
        )
        self.assertEqual(self.exchange._order_reservations[1]["remaining_qty"], 6)
        self.exchange._handle_cancel(
            Message(src=1, dst=0, kind="CANCEL_ORDER", data={"order_id": 1})
        )
        self.assertNotIn(1, self.exchange._order_reservations)

    def test_risk_checks_include_matches_waiting_for_account_delivery(self):
        policy = replace(
            self.policy,
            allow_short=True,
            enforce_inventory=False,
            position_limit=1,
        )
        self.exchange.economic_policy = policy
        self.agent.configure_economic_policy(policy)

        self.exchange._handle_new_order(
            Message(src=1, dst=0, kind="NEW_ORDER", data={"side": "BUY", "qty": 1, "price": 100.0})
        )
        self.drain()
        seller = PassivePolicyAgent(2, "SELLER")
        seller.configure_economic_policy(policy)
        self.kernel.register(seller)
        self.exchange._handle_new_order(
            Message(src=2, dst=0, kind="NEW_ORDER", data={"side": "SELL", "qty": 1, "price": 100.0})
        )
        pending_result = self.exchange.try_submit_order(
            Message(src=1, dst=0, kind="NEW_ORDER", data={"side": "BUY", "qty": 1, "order_type": "MARKET"})
        )
        self.assertEqual(pending_result["status"], "REJECTED")
        self.assertIn("position limit", pending_result["reason"])
        self.assertEqual(self.agent.position, 0)
        self.drain()
        self.assertEqual(self.agent.position, 1)


if __name__ == "__main__":
    unittest.main()
