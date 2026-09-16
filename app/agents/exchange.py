import heapq
from copy import deepcopy
from math import isfinite
from typing import List, Tuple
from app.agents.base import Agent
from app.core.economic import EconomicPolicy, EconomicPolicyError, resolve_economic_policy
from app.models.types import ORDER_STATUSES, Order, Trade
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

    def __init__(
        self,
        agent_id,
        name="EXCHANGE",
        start_price=100.0,
        economic_policy: EconomicPolicy | str | None = None,
    ):
        super().__init__(agent_id, name)
        if not isfinite(float(start_price)) or start_price <= 0:
            raise ValueError("start_price must be finite and positive")
        self._start_price = float(start_price)
        self.last_trade = float(start_price)
        self.order_id = 1
        self.trade_id = 1
        self.start_price = float(start_price)
        self.economic_policy = resolve_economic_policy(economic_policy)

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
        self._order_lifecycle: dict[int, dict] = {}
        self._order_reservations: dict[int, dict] = {}
        self.rejections: list[dict] = []
        self.last_order_result: dict | None = None

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
        self._order_lifecycle.clear()
        self._order_reservations.clear()
        self.rejections.clear()
        self.last_order_result = None

    @property
    def order_lifecycle(self) -> list[dict]:
        """Return all accepted orders and their terminal/current states."""

        return [deepcopy(self._order_lifecycle[oid]) for oid in sorted(self._order_lifecycle)]

    @property
    def trades(self) -> list[dict]:
        """Return a detached public trade log with stable identifiers."""

        return [
            {
                "trade_id": trade.trade_id,
                "price": trade.price,
                "qty": trade.qty,
                "buyer_id": trade.buyer_id,
                "seller_id": trade.seller_id,
                "buyer_order_id": trade.buyer_order_id,
                "seller_order_id": trade.seller_order_id,
                "ts": trade.ts,
                "aggressor_side": trade.aggressor_side,
            }
            for trade in self.history
        ]

    def get_order_lifecycle(self, order_id: int) -> dict | None:
        """Return one lifecycle record, or ``None`` for an unknown ID."""

        record = self._order_lifecycle.get(order_id)
        return deepcopy(record) if record is not None else None

    def get_trade(self, trade_id: int) -> dict | None:
        """Return one public trade record, or ``None`` if it is not retained."""

        for trade in self.trades:
            if trade["trade_id"] == trade_id:
                return trade
        return None

    def expire_all_orders(self) -> list[dict]:
        """Expire every resting order at the end of an episode."""

        expired_ids = list(self._order_map)
        for order_id in expired_ids:
            self._remove_order(order_id, status="EXPIRED")
        self.validate_invariants()
        result = [self.get_order_lifecycle(order_id) for order_id in expired_ids]
        self.last_order_result = {"status": "EXPIRED", "order_ids": expired_ids}
        return result

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
            "order_lifecycle": self.order_lifecycle,
            "trade_count": self.total_trades,
            "traded_volume": self.total_traded_qty,
            "economic_policy": self.economic_policy.as_dict(),
        }

    def receive(self, msg):
        assert self.kernel is not None
        if msg.kind == "NEW_ORDER":
            try:
                self._handle_new_order(msg)
            except (TypeError, ValueError) as exc:
                self._notify_rejection(msg, reason=str(exc))
        elif msg.kind == "CANCEL_ORDER":
            self._handle_cancel(msg)
        elif msg.kind == "QUERY_MKT_DATA":
            self._handle_query_mkt_data(msg)
        elif msg.kind == "QUERY_SPREAD":
            self._handle_query_spread(msg)
        elif msg.kind == "QUERY_LAST_TRADE":
            self._handle_query_last_trade(msg)
        else:
            self._record_rejection(agent_id=msg.src, reason=f"unsupported message kind {msg.kind!r}")

    def _handle_query_mkt_data(self, msg):
        best_bid = self.bids[0].price if self.bids else None
        best_ask = self.asks[0].price if self.asks else None
        data = {
            "best_bid": best_bid,
            "best_ask": best_ask,
            "last_trade": self.last_trade,
        }
        if msg.data.get("include_volume", False):
            data.update({"traded_volume": self.total_traded_qty, "trade_count": self.total_trades})
        self.kernel.send(
            self.agent_id,
            msg.src,
            "MKT_DATA",
            data,
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

    def _record_rejection(self, *, agent_id: int, reason: str, order_id: int | None = None) -> dict:
        """Keep a structured rejection record without mutating the order book."""

        result = {
            "status": "REJECTED",
            "order_id": order_id,
            "agent_id": agent_id,
            "reason": reason,
            "time": self.kernel.time if self.kernel else 0,
        }
        self.rejections.append(deepcopy(result))
        self.last_order_result = deepcopy(result)
        return result

    def _notify_rejection(self, msg, *, reason: str, order_id: int | None = None) -> dict:
        """Record a rejection and notify a known requester asynchronously."""

        result = self._record_rejection(
            agent_id=msg.src,
            order_id=order_id,
            reason=reason,
        )
        if self.kernel is not None and self.kernel.get_agent(msg.src) is not None:
            self.kernel.send(self.agent_id, msg.src, "ORDER_REJECTED", result)
        return result

    def _validate_economic_order(self, msg, *, side: str, qty: int, order_type: str, price: float) -> None:
        """Validate optional cash, inventory, and self-trade constraints."""

        if self.kernel is None:
            raise RuntimeError("exchange must be registered with a kernel")
        owner = self.kernel.get_agent(msg.src)
        if owner is None:
            raise ValueError(f"unknown order owner {msg.src}")
        policy = self.economic_policy
        pending_position, pending_cash = self._pending_accounting(msg.src)

        incoming = Order(0, msg.src, side, price, qty, self.kernel.time, order_type)
        if not policy.allow_self_trade:
            opposite_orders = self.asks if side == "BUY" else self.bids
            for resting in opposite_orders:
                if not self._crossed(incoming, resting.price):
                    break
                if resting.agent_id == msg.src:
                    raise EconomicPolicyError("self-trade is disabled by economic policy")

        if policy.enforce_cash and side == "BUY":
            reserved = sum(
                item["price"] * item["remaining_qty"]
                for item in self._order_reservations.values()
                if item["agent_id"] == msg.src and item["side"] == "BUY"
            )
            if order_type == "MARKET":
                required = 0.0
                remaining = qty
                for ask in self.asks:
                    fill_qty = min(remaining, ask.qty)
                    required += fill_qty * ask.price
                    remaining -= fill_qty
                    if remaining == 0:
                        break
            else:
                required = price * qty
            available = float(getattr(owner, "cash", 0.0)) + pending_cash - reserved
            if available + 1e-12 < required:
                raise EconomicPolicyError(
                    f"insufficient cash for order: required {required:.8f}, available {available:.8f}"
                )

        if side == "SELL" and not policy.allow_short:
            reserved = sum(
                item["remaining_qty"]
                for item in self._order_reservations.values()
                if item["agent_id"] == msg.src and item["side"] == "SELL"
            )
            available = int(getattr(owner, "position", 0)) + pending_position - reserved
            if qty > available:
                raise EconomicPolicyError(
                    f"insufficient inventory for order: required {qty}, available {available}"
                )

        if policy.position_limit is not None:
            reserved_same_side = sum(
                item["remaining_qty"]
                for item in self._order_reservations.values()
                if item["agent_id"] == msg.src and item["side"] == side
            )
            current_position = int(getattr(owner, "position", 0)) + pending_position
            projected_position = (
                current_position + reserved_same_side + qty
                if side == "BUY"
                else current_position - reserved_same_side - qty
            )
            if abs(projected_position) > policy.position_limit:
                raise EconomicPolicyError(
                    f"position limit {policy.position_limit} exceeded: "
                    f"projected {projected_position}"
                )

    def _pending_accounting(self, agent_id: int) -> tuple[int, float]:
        """Return exchange fills not yet reflected in an agent's trade log.

        The kernel delivers fills asynchronously.  Risk checks therefore need
        to account for matches already recorded by the exchange but whose
        ``EXECUTION`` messages have not reached the participant yet.
        """

        if self.kernel is None:
            return 0, 0.0
        owner = self.kernel.get_agent(agent_id)
        accounted_trade_ids = {
            trade.get("trade_id")
            for trade in getattr(owner, "trade_history", [])
            if trade.get("trade_id") is not None
        }
        pending_position = 0
        pending_cash = 0.0
        for lifecycle in self._order_lifecycle.values():
            if lifecycle["agent_id"] != agent_id:
                continue
            signed = 1 if lifecycle["side"] == "BUY" else -1
            for fill in lifecycle["fills"]:
                trade_id = fill.get("trade_id")
                if trade_id is not None and trade_id in accounted_trade_ids:
                    continue
                fill_qty = int(fill["qty"])
                notional = fill_qty * float(fill["price"])
                fee = float(fill.get("fee", 0.0))
                pending_position += signed * fill_qty
                pending_cash -= signed * notional + fee
        return pending_position, pending_cash

    def _create_lifecycle(self, order: Order) -> None:
        self._order_lifecycle[order.order_id] = {
            "order_id": order.order_id,
            "agent_id": order.agent_id,
            "side": order.side,
            "order_type": order.order_type,
            "price": None if order.order_type == "MARKET" else order.price,
            "original_qty": order.qty,
            "remaining_qty": order.qty,
            "status": "RECEIVED",
            "created_time": order.ts,
            "updated_time": order.ts,
            "fills": [],
        }

    def _update_lifecycle(self, order_id: int, *, remaining_qty: int, status: str) -> None:
        if status not in ORDER_STATUSES:
            raise ValueError(f"unsupported order lifecycle status {status!r}")
        record = self._order_lifecycle.get(order_id)
        if record is None:
            raise ValueError(f"missing lifecycle for order {order_id}")
        record["remaining_qty"] = remaining_qty
        record["status"] = status
        record["updated_time"] = self.kernel.time if self.kernel else record["updated_time"]

    def _record_fill(self, order_id: int, *, trade: Trade, fee: float, remaining_qty: int) -> None:
        record = self._order_lifecycle.get(order_id)
        if record is None:
            raise ValueError(f"missing lifecycle for order {order_id}")
        record["fills"].append(
            {
                "trade_id": trade.trade_id,
                "qty": trade.qty,
                "price": trade.price,
                "fee": fee,
            }
        )
        self._update_lifecycle(
            order_id,
            remaining_qty=remaining_qty,
            status="FILLED" if remaining_qty == 0 else "PARTIALLY_FILLED",
        )

    def _reserve_order(self, order: Order) -> None:
        if not (
            self.economic_policy.enforce_cash
            or self.economic_policy.enforce_inventory
            or self.economic_policy.position_limit is not None
            or not self.economic_policy.allow_short
        ):
            return
        self._order_reservations[order.order_id] = {
            "agent_id": order.agent_id,
            "side": order.side,
            "price": order.price,
            "remaining_qty": order.qty,
        }

    def _release_reservation(self, order_id: int, filled_qty: int | None = None) -> None:
        reservation = self._order_reservations.get(order_id)
        if reservation is None:
            return
        if filled_qty is None:
            self._order_reservations.pop(order_id, None)
            return
        reservation["remaining_qty"] -= filled_qty
        if reservation["remaining_qty"] <= 0:
            self._order_reservations.pop(order_id, None)

    def try_submit_order(self, msg):
        """Submit an order and return a structured result instead of raising."""

        try:
            self._handle_new_order(msg)
        except (TypeError, ValueError) as exc:
            return self._notify_rejection(msg, reason=str(exc))
        order_id = self.order_id - 1
        return self.get_order_lifecycle(order_id)

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

        self._validate_economic_order(
            msg,
            side=side,
            qty=qty,
            order_type=order_type,
            price=price,
        )

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
        self._create_lifecycle(incoming)

        shown_price = "MKT" if order_type == "MARKET" else f"{incoming.price:.2f}"
        owner = self.kernel.get_agent(msg.src)
        src_name = owner.name if owner is not None else str(msg.src)
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
                    self._remove_order(oid, status="CANCELLED")
                    cancelled.append(oid)
        elif order_id is not None:
            order = self._order_map.get(order_id)
            if order is None:
                return self._notify_rejection(
                    msg,
                    order_id=order_id,
                    reason="unknown order",
                )
            if order.agent_id != agent_id:
                self.kernel.log(
                    f"EXCH: reject cancel order_id={order_id} from agent={agent_id} (owner={order.agent_id})"
                )
                return self._notify_rejection(
                    msg,
                    order_id=order_id,
                    reason="cancel requester is not the order owner",
                )
            self._remove_order(order_id, status="CANCELLED")
            cancelled.append(order_id)

        for oid in cancelled:
            self.kernel.send(
                self.agent_id,
                agent_id,
                "ORDER_CANCELLED",
                {
                    "order_id": oid,
                    "status": "CANCELLED",
                    "remaining_qty": self._order_lifecycle[oid]["remaining_qty"],
                },
            )

        self.validate_invariants()
        result = {"status": "CANCELLED", "order_ids": cancelled, "agent_id": agent_id}
        self.last_order_result = deepcopy(result)
        return result

    def _remove_order(self, order_id: int, *, status: str | None = None) -> None:
        """Remove order from heap and map."""
        order = self._order_map.get(order_id)
        if order is None:
            return
        self._order_map.pop(order_id, None)
        if status is not None:
            self._update_lifecycle(order_id, remaining_qty=order.qty, status=status)
        self._release_reservation(order_id)
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
            lifecycle = self._order_lifecycle.get(order_id)
            if lifecycle is None:
                raise ValueError(f"Missing lifecycle for resting order {order_id}")
            if lifecycle["remaining_qty"] != order.qty:
                raise ValueError(f"Lifecycle quantity mismatch for order {order_id}")

        for order_id, lifecycle in self._order_lifecycle.items():
            if lifecycle["status"] not in ORDER_STATUSES:
                raise ValueError(f"Invalid lifecycle status for order {order_id}")
            if lifecycle["remaining_qty"] < 0:
                raise ValueError(f"Negative lifecycle quantity for order {order_id}")
            if lifecycle["status"] in {"RESTING", "PARTIALLY_FILLED"} and order_id not in self._order_map:
                raise ValueError(f"Active lifecycle order {order_id} is absent from the book")

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
            incoming_remaining = incoming.qty - trade_qty
            resting_remaining = resting.qty - trade_qty

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

            notional = trade_qty * trade_price
            incoming_liquidity = "taker"
            resting_liquidity = "maker"
            buyer_fee = self.economic_policy.fee(
                notional,
                liquidity=incoming_liquidity
                if incoming.side == "BUY"
                else resting_liquidity,
            )
            seller_fee = self.economic_policy.fee(
                notional,
                liquidity=incoming_liquidity
                if incoming.side == "SELL"
                else resting_liquidity,
            )
            self._record_fill(
                incoming.order_id,
                trade=trade,
                fee=buyer_fee if incoming.side == "BUY" else seller_fee,
                remaining_qty=incoming_remaining,
            )
            self._record_fill(
                resting.order_id,
                trade=trade,
                fee=buyer_fee if incoming.side != "BUY" else seller_fee,
                remaining_qty=resting_remaining,
            )

            resting_execution = {
                "qty": trade_qty,
                "price": trade_price,
                "order_id": resting.order_id,
                "counterparty_order_id": incoming.order_id,
                "trade_id": trade.trade_id,
                "buyer_order_id": trade.buyer_order_id,
                "seller_order_id": trade.seller_order_id,
                "aggressor_side": incoming.side,
                "remaining_qty": resting_remaining,
                "liquidity": resting_liquidity,
            }
            buy_execution = (
                {
                    "side": "BUY",
                    **resting_execution,
                    "fee": buyer_fee,
                    "liquidity": resting_liquidity,
                }
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
                    "remaining_qty": incoming_remaining,
                    "fee": buyer_fee,
                    "liquidity": incoming_liquidity,
                }
            )
            sell_execution = (
                {
                    "side": "SELL",
                    **resting_execution,
                    "fee": seller_fee,
                    "liquidity": resting_liquidity,
                }
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
                    "remaining_qty": incoming_remaining,
                    "fee": seller_fee,
                    "liquidity": incoming_liquidity,
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

            buyer = self.kernel.get_agent(buy_agent)
            seller = self.kernel.get_agent(sell_agent)
            b_name = buyer.name if buyer is not None else str(buy_agent)
            s_name = seller.name if seller is not None else str(sell_agent)
            self.kernel.log(
                f"TRADE px={trade_price:.2f} qty={trade_qty} ({b_name} ← {s_name})"
            )

            incoming.qty = incoming_remaining
            resting.qty = resting_remaining
            if resting.qty == 0:
                heapq.heappop(opp)
                self._order_map.pop(resting.order_id, None)
            self._release_reservation(resting.order_id, filled_qty=trade_qty)

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
            self._update_lifecycle(
                incoming.order_id,
                remaining_qty=incoming.qty,
                status=(
                    "PARTIALLY_FILLED"
                    if incoming.qty < self._order_lifecycle[incoming.order_id]["original_qty"]
                    else "RESTING"
                ),
            )
            self._reserve_order(incoming)
            self.kernel.send(
                self.agent_id,
                incoming.agent_id,
                "ORDER_ACCEPTED",
                {
                    "order_id": incoming.order_id,
                    "side": incoming.side,
                    "qty": incoming.qty,
                    "price": incoming.price,
                    "original_qty": self._order_lifecycle[incoming.order_id]["original_qty"],
                    "remaining_qty": incoming.qty,
                    "status": self._order_lifecycle[incoming.order_id]["status"],
                    "order_type": incoming.order_type,
                },
            )
        elif incoming.qty == 0:
            self._update_lifecycle(incoming.order_id, remaining_qty=0, status="FILLED")
        else:
            self._update_lifecycle(
                incoming.order_id,
                remaining_qty=incoming.qty,
                status="NO_LIQUIDITY",
            )
        self.last_order_result = self.get_order_lifecycle(incoming.order_id)
        # Fully filled and unfilled market orders have no resting lifecycle to
        # acknowledge.  Their executions (when any) are the authoritative
        # result.  Avoiding an extra asynchronous notification preserves the
        # baseline event schedule while keeping the book invariant explicit.

        self.validate_invariants()
