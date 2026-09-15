import heapq
from math import isfinite
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
        if not isfinite(float(start_price)) or start_price <= 0:
            raise ValueError("start_price must be finite and positive")
        self.last_trade = float(start_price)
        self.order_id = 1
        self.trade_id = 1
        self.start_price = float(start_price)

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
        self.total_trades = 0
        self.total_traded_qty = 0
        self.total_traded_notional = 0.0

    @property
    def bids(self) -> List[Order]:
        """Return sorted list of bid orders (highest price first)."""
        return [o[3] for o in sorted(self._bids, key=lambda x: (x[0], x[1], x[2]))]

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

    def reset(self, start_price: float | None = None) -> None:
        """Clear all exchange state and restore the initial last-trade price."""

        if start_price is not None:
            if not isfinite(float(start_price)) or start_price <= 0:
                raise ValueError("start_price must be finite and positive")
            self.start_price = float(start_price)
        self.last_trade = self.start_price
        self.order_id = 1
        self.trade_id = 1
        self._bids.clear()
        self._asks.clear()
        self._order_map.clear()
        self.history.clear()
        self.total_trades = 0
        self.total_traded_qty = 0
        self.total_traded_notional = 0.0

    def snapshot(self, depth: int | None = None) -> dict:
        """Return a public, immutable-by-convention view of the order book."""

        bids = self.bids
        asks = self.asks
        if depth is not None:
            if not isinstance(depth, int) or isinstance(depth, bool) or depth < 0:
                raise ValueError("depth must be a non-negative integer or None")
            bids = bids[:depth]
            asks = asks[:depth]
        return {
            "bids": [order.__dict__.copy() for order in bids],
            "asks": [order.__dict__.copy() for order in asks],
            "best_bid": bids[0].price if bids else None,
            "best_ask": asks[0].price if asks else None,
            "last_trade": self.last_trade,
        }

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
        side = msg.data.get("side")
        raw_qty = msg.data.get("qty")
        qty = raw_qty
        order_type = str(msg.data.get("order_type", "LIMIT")).upper()

        if side not in {"BUY", "SELL"}:
            raise ValueError(f"Unsupported side '{side}'")
        if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            raise ValueError(f"Order quantity must be positive, got {qty}")
        if order_type not in {"LIMIT", "MARKET"}:
            raise ValueError(f"Unsupported order type '{order_type}'")

        if order_type == "MARKET":
            price = 1e9 if side == "BUY" else 0.0
        else:
            if "price" not in msg.data:
                raise ValueError("LIMIT orders require a price")
            try:
                raw_price = float(msg.data["price"])
            except (TypeError, ValueError) as exc:
                raise ValueError("LIMIT order price must be numeric") from exc
            if not isfinite(raw_price) or raw_price <= 0:
                raise ValueError("LIMIT order price must be finite and positive")
            price = round_to_tick(raw_price)
            if price <= 0:
                raise ValueError("LIMIT order price rounds to a non-positive tick")

        incoming = Order(
            order_id=self.order_id,
            agent_id=msg.src,
            side=side,
            price=price,
            qty=qty,
            ts=self.kernel.time,
            order_type=order_type,
        )

        self.order_id += 1

        shown_price = "MKT" if order_type == "MARKET" else f"{incoming.price:.2f}"
        src_name = self.kernel._agents[msg.src].name
        self.kernel.log(
            f"EXCH: {order_type} {side} qty={qty} px={shown_price} from {src_name}"
        )
        self._match(incoming)
        self.validate_invariants()

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

        self.validate_invariants()

    def _remove_order(self, order_id: int) -> None:
        """Remove order from heap and map."""
        order = self._order_map.get(order_id)
        if order is None:
            return
        self._order_map.pop(order_id, None)
        side = order.side

        removed = False
        if side == "BUY":
            for i, (_, _, _, o) in enumerate(self._bids):
                if o.order_id == order_id:
                    self._bids.pop(i)
                    heapq.heapify(self._bids)
                    removed = True
                    break
        else:
            for i, (_, _, _, o) in enumerate(self._asks):
                if o.order_id == order_id:
                    self._asks.pop(i)
                    heapq.heapify(self._asks)
                    removed = True
                    break
        if not removed:
            raise ValueError(f"Order {order_id} was mapped but absent from its heap")

    def _book(self, side):
        return self._bids if side == "BUY" else self._asks

    def _opposite(self, side):
        return self._asks if side == "BUY" else self._bids

    def _crossed(self, incoming, resting_price):
        if incoming.side == "BUY":
            return incoming.price >= resting_price
        return incoming.price <= resting_price

    def validate_invariants(self) -> None:
        """Fail fast when the resting book and order map diverge."""
        heap_order_ids = set()

        for neg_price, ts, order_id, order in self._bids:
            if order.side != "BUY":
                raise ValueError(f"Bid heap contains non-buy order {order_id}")
            if order.qty <= 0:
                raise ValueError(f"Bid heap contains non-positive qty for order {order_id}")
            if (-neg_price, ts, order_id) != (order.price, order.ts, order.order_id):
                raise ValueError(f"Bid heap tuple mismatch for order {order_id}")
            heap_order_ids.add(order_id)

        for price, ts, order_id, order in self._asks:
            if order.side != "SELL":
                raise ValueError(f"Ask heap contains non-sell order {order_id}")
            if order.qty <= 0:
                raise ValueError(f"Ask heap contains non-positive qty for order {order_id}")
            if (price, ts, order_id) != (order.price, order.ts, order.order_id):
                raise ValueError(f"Ask heap tuple mismatch for order {order_id}")
            heap_order_ids.add(order_id)

        if heap_order_ids != set(self._order_map):
            raise ValueError("Heap/order_map order ids diverged")

        for order_id, order in self._order_map.items():
            if order.order_id != order_id:
                raise ValueError(f"Order map key mismatch for order {order_id}")
            if order.qty <= 0:
                raise ValueError(f"Order map contains non-positive qty for order {order_id}")
            if not any(entry[3] is order for entry in (self._bids if order.side == "BUY" else self._asks)):
                raise ValueError(f"Order map entry {order_id} is not the heap's resting object")

        if self._bids and self._asks:
            best_bid = -self._bids[0][0]
            best_ask = self._asks[0][0]
            if best_bid >= best_ask:
                raise ValueError(
                    f"Resting book is crossed or locked: best_bid={best_bid}, best_ask={best_ask}"
                )

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
                buyer_order_id=(
                    incoming.order_id if incoming.side == "BUY" else resting.order_id
                ),
                seller_order_id=(
                    incoming.order_id if incoming.side == "SELL" else resting.order_id
                ),
                trade_id=self.trade_id,
            )
            self.trade_id += 1
            self.history.append(trade)
            if len(self.history) > 100:
                self.history.pop(0)
            self.total_trades += 1
            self.total_traded_qty += trade_qty
            self.total_traded_notional += trade_qty * trade_price

            resting_execution = {
                "qty": trade_qty,
                "price": trade_price,
                "order_id": resting.order_id,
                "counterparty_order_id": incoming.order_id,
                "trade_id": trade.trade_id,
                "buyer_order_id": trade.buyer_order_id,
                "seller_order_id": trade.seller_order_id,
                "aggressor_side": incoming.side,
            }
            buy_execution = (
                {"side": "BUY", **resting_execution}
                if incoming.side == "SELL"
                else {
                    "side": "BUY",
                    "qty": trade_qty,
                    "price": trade_price,
                    "order_id": incoming.order_id,
                    "counterparty_order_id": resting.order_id,
                    "trade_id": trade.trade_id,
                    "buyer_order_id": trade.buyer_order_id,
                    "seller_order_id": trade.seller_order_id,
                    "aggressor_side": incoming.side,
                }
            )
            sell_execution = (
                {"side": "SELL", **resting_execution}
                if incoming.side == "BUY"
                else {
                    "side": "SELL",
                    "qty": trade_qty,
                    "price": trade_price,
                    "order_id": incoming.order_id,
                    "counterparty_order_id": resting.order_id,
                    "trade_id": trade.trade_id,
                    "buyer_order_id": trade.buyer_order_id,
                    "seller_order_id": trade.seller_order_id,
                    "aggressor_side": incoming.side,
                }
            )

            self.kernel.send(
                self.agent_id,
                buy_agent,
                "EXECUTION",
                buy_execution,
            )
            self.kernel.send(
                self.agent_id,
                sell_agent,
                "EXECUTION",
                sell_execution,
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
        if incoming.qty > 0 and incoming.order_type == "LIMIT":
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
        # Fully filled and unfilled market orders have no resting lifecycle to
        # acknowledge.  Their executions (when any) are the authoritative
        # result.  Avoiding an extra asynchronous notification preserves the
        # baseline event schedule while keeping the book invariant explicit.

        self.validate_invariants()
