import heapq
from typing import List, Tuple
from app.agents.base import Agent
from app.models.types import Order, Trade
from app.core.constants import round_to_tick


class ExchangeAgent(Agent):
    """
    Continuous Double Auction exchange with:
    - Price-time priority matching
    - LIMIT and MARKET order support
    - CANCEL_ORDER support (by order_id)
    - ORDER_ACCEPTED notifications
    - Discrete tick sizes

    Uses heaps for O(log n) best price lookup.
    """

    def __init__(self, agent_id, name="EXCHANGE", start_price=100.0):
        super().__init__(agent_id, name)
        self.last_trade = float(start_price)
        self.order_id = 1

        # Heaps for O(log n) best price lookup
        # Bids: max-heap (store negative price for max behavior)
        # Format: (-price, timestamp, order_id, order)
        self._bids: List[Tuple[float, int, int, Order]] = []
        # Asks: min-heap
        # Format: (price, timestamp, order_id, order)
        self._asks: List[Tuple[float, int, int, Order]] = []

        # Map order_id -> order for O(1) lookup on cancel
        self._order_map: dict[int, Order] = {}

        self.history: List[Trade] = []

    @property
    def bids(self) -> List[Order]:
        """Return sorted list of bid orders (highest price first)."""
        return [o[3] for o in sorted(self._bids, key=lambda x: (-x[0], x[1], x[2]))]

    @property
    def asks(self) -> List[Order]:
        """Return sorted list of ask orders (lowest price first)."""
        return [o[3] for o in sorted(self._asks, key=lambda x: (x[0], x[1], x[2]))]

    def wakeup(self, now: int) -> None:
        """Exchange doesn't use wakeup for trading."""
        pass

    def get_observation(self) -> list:
        """Exchange doesn't produce observations."""
        return []

    def get_reward(self) -> float:
        """Exchange doesn't have rewards."""
        return 0.0

    def receive(self, msg):
        assert self.kernel is not None
        if msg.kind == "NEW_ORDER":
            self._handle_new_order(msg)
        elif msg.kind == "CANCEL_ORDER":
            self._handle_cancel(msg)
        elif msg.kind == "QUERY_MKT_DATA":
            self._handle_query_mkt_data(msg)
        elif msg.kind == "QUERY_SPREAD":
            self._handle_query_spread(msg)
        elif msg.kind == "QUERY_LAST_TRADE":
            self._handle_query_last_trade(msg)

    def _handle_query_mkt_data(self, msg):
        best_bid = self.bids[0].price if self.bids else None
        best_ask = self.asks[0].price if self.asks else None
        self.kernel.send(
            self.agent_id,
            msg.src,
            "MKT_DATA",
            {
                "best_bid": best_bid,
                "best_ask": best_ask,
                "last_trade": self.last_trade
            }
        )

    def _handle_query_spread(self, msg):
        best_bid = self.bids[0].price if self.bids else None
        best_ask = self.asks[0].price if self.asks else None
        self.kernel.send(
            self.agent_id,
            msg.src,
            "SPREAD_DATA",
            {"best_bid": best_bid, "best_ask": best_ask}
        )

    def _handle_query_last_trade(self, msg):
        self.kernel.send(
            self.agent_id,
            msg.src,
            "LAST_TRADE_DATA",
            {"last_trade": self.last_trade}
        )

    def _handle_new_order(self, msg):
        side = msg.data["side"]
        qty = int(msg.data["qty"])
        order_type = msg.data.get("order_type", "LIMIT")

        if order_type == "MARKET":
            price = 1e9 if side == "BUY" else 0.0
        else:
            price = round_to_tick(float(msg.data["price"]))

        incoming = Order(
            order_id=self.order_id,
            agent_id=msg.src,
            side=side,
            price=price,
            qty=qty,
            ts=self.kernel.time,
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
            # Cancel all orders from this agent
            for oid, order in list(self._order_map.items()):
                if order.agent_id == agent_id:
                    self._remove_order(oid)
                    cancelled.append(oid)
        elif order_id is not None:
            order = self._order_map.get(order_id)
            if order is None:
                return
            if order.agent_id != agent_id:
                self.kernel.log(
                    f"EXCH: reject cancel order_id={order_id} from agent={agent_id} (owner={order.agent_id})"
                )
                return
            self._remove_order(order_id)
            cancelled.append(order_id)

        for oid in cancelled:
            self.kernel.send(
                self.agent_id, agent_id, "ORDER_CANCELLED", {"order_id": oid}
            )

    def _remove_order(self, order_id: int) -> None:
        """Remove order from heap and map."""
        order = self._order_map.get(order_id)
        if order is None:
            return
        self._order_map.pop(order_id, None)
        side = order.side

        if side == "BUY":
            for i, (_, _, _, o) in enumerate(self._bids):
                if o.order_id == order_id:
                    self._bids.pop(i)
                    heapq.heapify(self._bids)
                    break
        else:
            for i, (_, _, _, o) in enumerate(self._asks):
                if o.order_id == order_id:
                    self._asks.pop(i)
                    heapq.heapify(self._asks)
                    break

    def _book(self, side):
        return self._bids if side == "BUY" else self._asks

    def _opposite(self, side):
        return self._asks if side == "BUY" else self._bids

    def _crossed(self, incoming, resting_price):
        if incoming.side == "BUY":
            return incoming.price >= resting_price
        return incoming.price <= resting_price

    def _match(self, incoming):
        assert self.kernel is not None
        opp = self._opposite(incoming.side)

        while incoming.qty > 0 and opp:
            if incoming.side == "BUY":
                best_price, _, _, resting = opp[0]
            else:
                neg_price, _, _, resting = opp[0]
                best_price = -neg_price

            if not self._crossed(incoming, best_price):
                break

            trade_qty = min(incoming.qty, resting.qty)
            trade_price = resting.price
            self.last_trade = trade_price

            buy_agent = (
                incoming.agent_id if incoming.side == "BUY" else resting.agent_id
            )
            sell_agent = (
                incoming.agent_id if incoming.side == "SELL" else resting.agent_id
            )

            trade = Trade(
                price=trade_price,
                qty=trade_qty,
                buyer_id=buy_agent,
                seller_id=sell_agent,
                ts=self.kernel.time,
                aggressor_side=incoming.side,
            )
            self.history.append(trade)
            if len(self.history) > 100:
                self.history.pop(0)

            self.kernel.send(
                self.agent_id,
                buy_agent,
                "EXECUTION",
                {"side": "BUY", "qty": trade_qty, "price": trade_price},
            )
            self.kernel.send(
                self.agent_id,
                sell_agent,
                "EXECUTION",
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
                heapq.heappop(opp)
                self._order_map.pop(resting.order_id, None)

        # Remaining limit order → add to book + notify
        if incoming.qty > 0 and incoming.price not in (0.0, 1e9):
            if incoming.side == "BUY":
                heapq.heappush(
                    self._bids,
                    (-incoming.price, incoming.ts, incoming.order_id, incoming),
                )
            else:
                heapq.heappush(
                    self._asks,
                    (incoming.price, incoming.ts, incoming.order_id, incoming),
                )
            self._order_map[incoming.order_id] = incoming
            self.kernel.send(
                self.agent_id,
                incoming.agent_id,
                "ORDER_ACCEPTED",
                {
                    "order_id": incoming.order_id,
                    "side": incoming.side,
                    "qty": incoming.qty,
                    "price": incoming.price,
                },
            )
