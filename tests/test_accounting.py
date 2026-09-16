import unittest

from app.agents.base import HeuristicAgent
from app.models.types import Message


class DummyHeuristicAgent(HeuristicAgent):
    def wakeup(self, now: int) -> None:
        pass

    def receive(self, msg) -> None:
        pass


class AccountingSanityTest(unittest.TestCase):
    def test_execution_accounting_handles_partial_close_and_flip(self):
        agent = DummyHeuristicAgent(1, "ACC")

        agent.handle_order_accepted(
            Message(
                src=0,
                dst=1,
                kind="ORDER_ACCEPTED",
                data={"order_id": 10, "side": "BUY", "qty": 10, "price": 100.0},
            )
        )
        agent.handle_execution(
            Message(
                src=0,
                dst=1,
                kind="EXECUTION",
                data={"side": "BUY", "qty": 10, "price": 100.0, "order_id": 10},
            )
        )

        self.assertEqual(agent.position, 10)
        self.assertEqual(agent.cash, -1000.0)
        self.assertEqual(agent.vwap, 100.0)
        self.assertEqual(agent.active_orders, {})

        agent.handle_execution(
            Message(
                src=0,
                dst=1,
                kind="EXECUTION",
                data={"side": "SELL", "qty": 4, "price": 110.0},
            )
        )
        self.assertEqual(agent.position, 6)
        self.assertEqual(agent.cash, -560.0)
        self.assertEqual(agent.realized_pnl, 40.0)
        self.assertEqual(agent.vwap, 100.0)

        agent.handle_execution(
            Message(
                src=0,
                dst=1,
                kind="EXECUTION",
                data={"side": "SELL", "qty": 8, "price": 90.0},
            )
        )
        self.assertEqual(agent.position, -2)
        self.assertEqual(agent.cash, 160.0)
        self.assertEqual(agent.realized_pnl, -20.0)
        self.assertEqual(agent.vwap, 90.0)
        self.assertEqual(agent.compute_pnl(90.0), -20.0)

    def test_fees_and_terminal_mark_to_market_reconcile(self):
        agent = DummyHeuristicAgent(1, "ACC")
        agent.handle_execution(
            Message(
                src=0,
                dst=1,
                kind="EXECUTION",
                data={"side": "BUY", "qty": 2, "price": 100.0, "fee": 0.2, "trade_id": 1},
            )
        )
        self.assertEqual(agent.fees_paid, 0.2)
        self.assertAlmostEqual(agent.cash, -200.2)
        self.assertAlmostEqual(agent.realized_pnl, -0.2)

        account = agent.settle_terminal(105.0, method="mark_to_market")
        self.assertEqual(account["position"], 0)
        self.assertAlmostEqual(account["cash"], 9.8)
        self.assertAlmostEqual(account["realized_pnl"], 9.8)
        self.assertAlmostEqual(account["total_pnl"], 9.8)
        self.assertEqual(agent.reconcile_accounting()["trade_count"], 1)

    def test_execution_before_acceptance_does_not_resurrect_filled_order(self):
        agent = DummyHeuristicAgent(1, "ACC")
        agent.handle_execution(
            Message(
                src=0,
                dst=1,
                kind="EXECUTION",
                data={
                    "side": "BUY",
                    "qty": 2,
                    "price": 100.0,
                    "order_id": 10,
                    "trade_id": 1,
                    "remaining_qty": 0,
                },
            )
        )
        agent.handle_order_accepted(
            Message(
                src=0,
                dst=1,
                kind="ORDER_ACCEPTED",
                data={
                    "order_id": 10,
                    "side": "BUY",
                    "qty": 2,
                    "original_qty": 2,
                    "price": 100.0,
                },
            )
        )
        self.assertEqual(agent.position, 2)
        self.assertEqual(agent.active_orders, {})


if __name__ == "__main__":
    unittest.main()
