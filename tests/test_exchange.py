import unittest

from app.agents.base import HeuristicAgent
from app.agents.exchange import ExchangeAgent
from app.core.kernel import Kernel
from app.models.types import Message


class PassiveTrader(HeuristicAgent):
    def wakeup(self, now: int) -> None:
        pass

    def receive(self, msg) -> None:
        if msg.kind == "EXECUTION":
            self.handle_execution(msg)
        elif msg.kind == "ORDER_ACCEPTED":
            self.handle_order_accepted(msg)
        elif msg.kind == "ORDER_CANCELLED":
            self.handle_order_cancelled(msg)


class ExchangeSanityTest(unittest.TestCase):
    def setUp(self):
        self.kernel = Kernel(seed=13)
        self.kernel.print_logs = False
        self.exchange = ExchangeAgent(agent_id=0)
        self.buyer = PassiveTrader(1, "BUYER")
        self.seller = PassiveTrader(2, "SELLER")
        self.other = PassiveTrader(3, "OTHER")

        for agent in (self.exchange, self.buyer, self.seller, self.other):
            self.kernel.register(agent)

    def drain_events(self):
        while self.kernel._events:
            self.kernel.step()

    def test_cancel_owner_validation_preserves_book_invariants(self):
        self.exchange._handle_new_order(
            Message(
                src=1,
                dst=0,
                kind="NEW_ORDER",
                data={"order_type": "LIMIT", "side": "BUY", "qty": 5, "price": 100.0},
            )
        )
        self.exchange._handle_new_order(
            Message(
                src=2,
                dst=0,
                kind="NEW_ORDER",
                data={"order_type": "LIMIT", "side": "SELL", "qty": 7, "price": 101.0},
            )
        )
        self.drain_events()

        self.assertEqual(set(self.exchange._order_map), {1, 2})
        self.exchange._handle_cancel(
            Message(src=2, dst=0, kind="CANCEL_ORDER", data={"order_id": 1})
        )
        self.assertEqual(set(self.exchange._order_map), {1, 2})

        self.exchange._handle_cancel(
            Message(src=1, dst=0, kind="CANCEL_ORDER", data={"order_id": 1})
        )
        self.assertEqual(set(self.exchange._order_map), {2})
        self.exchange.validate_invariants()

    def test_resting_execution_updates_order_tracking(self):
        self.exchange._handle_new_order(
            Message(
                src=1,
                dst=0,
                kind="NEW_ORDER",
                data={"order_type": "LIMIT", "side": "BUY", "qty": 10, "price": 100.0},
            )
        )
        self.drain_events()
        self.assertEqual(self.buyer.active_orders[1]["qty"], 10)

        self.exchange._handle_new_order(
            Message(
                src=2,
                dst=0,
                kind="NEW_ORDER",
                data={"order_type": "LIMIT", "side": "SELL", "qty": 4, "price": 100.0},
            )
        )
        self.drain_events()

        self.assertEqual(self.exchange._order_map[1].qty, 6)
        self.assertEqual(self.buyer.active_orders[1]["qty"], 6)
        self.assertEqual(self.exchange.total_trades, 1)
        self.assertEqual(self.exchange.total_traded_qty, 4)

        self.exchange._handle_new_order(
            Message(
                src=2,
                dst=0,
                kind="NEW_ORDER",
                data={"order_type": "LIMIT", "side": "SELL", "qty": 6, "price": 100.0},
            )
        )
        self.drain_events()

        self.assertNotIn(1, self.exchange._order_map)
        self.assertEqual(self.buyer.active_orders, {})
        self.assertEqual(self.buyer.position, 10)
        self.assertEqual(self.exchange.total_trades, 2)
        self.assertEqual(self.exchange.total_traded_qty, 10)
        self.exchange.validate_invariants()


if __name__ == "__main__":
    unittest.main()
