from typing import List
from app.agents.base import Agent
from app.models.types import Order, Trade
from app.core.constants import round_to_tick

class ExchangeAgent(Agent):
    """
    Continuous Double Auction exchange with:
    - Price-time priority matching
    - LIMIT and MARKET order support
    - CANCEL_ORDER support (by order_id or cancel_all from agent)
    - ORDER_ACCEPTED notifications
    - Discrete tick sizes
    """

    def __init__(self, agent_id, name="EXCHANGE", start_price=100.0):
        super().__init__(agent_id, name)
        self.last_trade = float(start_price)
        self.order_id = 1
        self.bids: List[Order] = []
        self.asks: List[Order] = []
        self.history: List[Trade] = []

    def receive(self, msg):
        assert self.kernel is not None
        if msg.kind == "NEW_ORDER":
            self._handle_new_order(msg)
        elif msg.kind == "CANCEL_ORDER":
            self._handle_cancel(msg)

    def _handle_new_order(self, msg):
        side = msg.data["side"]
        qty = int(msg.data["qty"])
        order_type = msg.data.get("order_type", "LIMIT")

        if order_type == "MARKET":
            price = 1e9 if side == "BUY" else 0.0
        else:
            price = round_to_tick(float(msg.data["price"]))

        incoming = Order(
            order_id=self.order_id, agent_id=msg.src,
            side=side, price=price, qty=qty, ts=self.kernel.time,
        )
        self.order_id += 1

        shown_price = "MKT" if order_type == "MARKET" else f"{incoming.price:.2f}"
        src_name = self.kernel._agents[msg.src].name
        self.kernel.log(
            f"EXCH: {order_type} {side} qty={qty} px={shown_price} from {src_name}"
        )
        self._match(incoming)

    def _handle_cancel(self, msg):
        agent_id = msg.src
        order_id = msg.data.get("order_id")
        cancel_all = msg.data.get("cancel_all", False)
        cancelled = []

        if cancel_all:
            for book in [self.bids, self.asks]:
                to_remove = [o for o in book if o.agent_id == agent_id]
                for o in to_remove:
                    book.remove(o)
                    cancelled.append(o.order_id)
        elif order_id is not None:
            for book in [self.bids, self.asks]:
                for i, o in enumerate(book):
                    if o.order_id == order_id and o.agent_id == agent_id:
                        book.pop(i)
                        cancelled.append(order_id)
                        break

        for oid in cancelled:
            self.kernel.send(
                self.agent_id, agent_id, "ORDER_CANCELLED", {"order_id": oid}
            )

    def _book(self, side):
        return self.bids if side == "BUY" else self.asks

    def _opposite(self, side):
        return self.asks if side == "BUY" else self.bids

    def _best_index(self, orders, side):
        best_i = 0
        for i in range(1, len(orders)):
            a, b = orders[i], orders[best_i]
            if side == "BUY":
                if (a.price > b.price) or (a.price == b.price and a.ts < b.ts):
                    best_i = i
            else:
                if (a.price < b.price) or (a.price == b.price and a.ts < b.ts):
                    best_i = i
        return best_i

    def _crossed(self, incoming, resting):
        if incoming.side == "BUY":
            return incoming.price >= resting.price
        return incoming.price <= resting.price

    def _match(self, incoming):
        assert self.kernel is not None
        opp = self._opposite(incoming.side)

        while incoming.qty > 0 and opp:
            target_side = "SELL" if incoming.side == "BUY" else "BUY"
            j = self._best_index(opp, target_side)
            resting = opp[j]

            if not self._crossed(incoming, resting):
                break

            trade_qty = min(incoming.qty, resting.qty)
            trade_price = resting.price
            self.last_trade = trade_price

            buy_agent = incoming.agent_id if incoming.side == "BUY" else resting.agent_id
            sell_agent = incoming.agent_id if incoming.side == "SELL" else resting.agent_id

            trade = Trade(
                price=trade_price, qty=trade_qty,
                buyer_id=buy_agent, seller_id=sell_agent,
                ts=self.kernel.time, aggressor_side=incoming.side,
            )
            self.history.append(trade)
            if len(self.history) > 100:
                self.history.pop(0)

            self.kernel.send(
                self.agent_id, buy_agent, "EXECUTION",
                {"side": "BUY", "qty": trade_qty, "price": trade_price},
            )
            self.kernel.send(
                self.agent_id, sell_agent, "EXECUTION",
                {"side": "SELL", "qty": trade_qty, "price": trade_price},
            )

            b_name = self.kernel._agents[buy_agent].name
            s_name = self.kernel._agents[sell_agent].name
            self.kernel.log(
                f"TRADE px={trade_price:.2f} qty={trade_qty} ({b_name} ← {s_name})"
            )

            incoming.qty -= trade_qty
            resting.qty -= trade_qty
            if resting.qty == 0:
                opp.pop(j)

        # Remaining limit order → add to book + notify
        if incoming.qty > 0 and incoming.price not in (0.0, 1e9):
            self._book(incoming.side).append(incoming)
            self.kernel.send(
                self.agent_id, incoming.agent_id, "ORDER_ACCEPTED",
                {"order_id": incoming.order_id, "side": incoming.side,
                 "qty": incoming.qty, "price": incoming.price},
            )
