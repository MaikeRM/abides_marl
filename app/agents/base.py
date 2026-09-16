from abc import ABC, abstractmethod
from copy import deepcopy
from math import isfinite


class Agent(ABC):
    """
    Abstract base class for all agents in the simulation.

    Provides the core interface required for both heuristic and RL agents.
    Subclasses must implement all @abstractmethod decorated methods.
    """

    def __init__(self, agent_id: int, name: str):
        if not isinstance(agent_id, int) or isinstance(agent_id, bool):
            raise ValueError("agent_id must be an integer")
        if not isinstance(name, str) or not name:
            raise ValueError("agent name must be a non-empty string")
        self.agent_id = agent_id
        self.name = name
        self.kernel = None  # To be set by Kernel

    @abstractmethod
    def wakeup(self, now: int) -> None:
        """Called when agent receives a WAKEUP message."""
        pass

    @abstractmethod
    def receive(self, msg) -> None:
        """Called when agent receives any message (NEW_ORDER, EXECUTION, etc.)."""
        pass

    @abstractmethod
    def get_observation(self) -> list:
        """
        Returns the current observation for RL training.
        Shape and content depends on agent type.
        """
        pass

    @abstractmethod
    def get_reward(self) -> float:
        """
        Returns the reward signal for RL training.
        Should reflect agent's performance (PnL, execution quality, etc.).
        """
        pass

    def kernelStopping(self) -> None:
        """Called automatically at the end of the simulation."""
        pass

    def reset(self) -> None:
        """Reset agent state for new episode. Override in subclass if needed."""
        pass


    def get_info(self) -> dict:
        """Returns additional info for logging/debugging."""
        return {"agent_id": self.agent_id, "name": self.name}


class HeuristicAgent(Agent):
    """
    Base class for heuristic (non-RL) agents.
    Provides default implementations that can be overridden.
    """

    def __init__(
        self,
        agent_id: int,
        name: str,
        *,
        initial_cash: float = 0.0,
        position_limit: int | None = None,
        allow_short: bool = True,
    ):
        super().__init__(agent_id, name)
        if not isfinite(float(initial_cash)):
            raise ValueError("initial_cash must be finite")
        if position_limit is not None and (
            not isinstance(position_limit, int)
            or isinstance(position_limit, bool)
            or position_limit <= 0
        ):
            raise ValueError("position_limit must be a positive integer or None")
        self.position: int = 0
        self.initial_cash = float(initial_cash)
        self.cash: float = self.initial_cash
        self.position_limit = position_limit
        self.allow_short = bool(allow_short)
        self.pnl_history: list[float] = []
        self.state: str = "ACTIVE"

        # Trading metrics
        self.vwap: float = 0.0
        self.realized_pnl: float = 0.0
        self.active_orders: dict = {}  # order_id -> order details
        self.trade_history: list = []  # List of trades
        self._last_reward_mark: float | None = None
        self.fees_paid: float = 0.0
        self.last_action_status: str = "RESET"
        self.last_rejection: dict | None = None
        self.maker_fee_rate: float = 0.0
        self.taker_fee_rate: float = 0.0
        self.economic_policy_name: str = "legacy_unconstrained"
        self._terminal_cash_adjustment: float = 0.0
        self._terminal_position_adjustment: int = 0
        self._early_execution_remaining: dict[int, int] = {}
        self._completed_order_ids: set[int] = set()

        # Cached market data (updated on each MKT_DATA message)
        self._last_mkt: dict = {"best_bid": None, "best_ask": None, "last_trade": 0.0}
        # PnL at the last get_reward() call — used to compute incremental reward
        self._last_reward_pnl: float = 0.0

    def _update_mkt_cache(self, msg) -> None:
        """Cache the latest market data from a MKT_DATA message."""
        self._last_mkt = {
            "best_bid": msg.data.get("best_bid"),
            "best_ask": msg.data.get("best_ask"),
            "last_trade": msg.data.get("last_trade", self._last_mkt["last_trade"]),
        }

    def get_observation(self) -> list:
        """Default: return empty observation for non-RL agents."""
        return []

    def get_reward(self) -> float:
        """Incremental realized PnL since the last call. Override for richer signals."""
        reward = self.realized_pnl - self._last_reward_pnl
        self._last_reward_pnl = self.realized_pnl
        return reward

    def compute_pnl(self, current_market_price: float = 0.0) -> float:
        """Compute current realized + unrealized PnL."""
        return self.realized_pnl + self.compute_unrealized_pnl(current_market_price)
        
    def compute_unrealized_pnl(self, current_market_price: float) -> float:
        """Compute unrealized PnL based on current market price."""
        if current_market_price <= 0:
            return 0.0
        if self.position > 0:
            return self.position * (current_market_price - self.vwap)
        elif self.position < 0:
            return abs(self.position) * (self.vwap - current_market_price)
        return 0.0

    def marked_equity(self, current_market_price: float) -> float:
        """Return cash plus the marked value of the current position."""

        if not isfinite(float(current_market_price)) or current_market_price <= 0:
            raise ValueError("current_market_price must be finite and positive")
        return self.cash + self.position * float(current_market_price)

    def reset(self) -> None:
        """Restore the accounting state while retaining strategy parameters."""

        self.position = 0
        self.cash = self.initial_cash
        self.pnl_history.clear()
        self.state = "ACTIVE"
        self.vwap = 0.0
        self.realized_pnl = 0.0
        self.active_orders.clear()
        self.trade_history.clear()
        self._last_reward_mark = None
        self.fees_paid = 0.0
        self.last_action_status = "RESET"
        self.last_rejection = None
        self._terminal_cash_adjustment = 0.0
        self._terminal_position_adjustment = 0
        self._early_execution_remaining.clear()
        self._completed_order_ids.clear()

    def configure_economic_policy(self, policy) -> None:
        """Apply a validated policy while retaining the strategy parameters."""

        self.initial_cash = float(policy.initial_cash)
        self.cash = self.initial_cash
        self.allow_short = bool(policy.allow_short)
        if policy.position_limit is not None:
            self.position_limit = policy.position_limit
        self.maker_fee_rate = float(policy.maker_fee_rate)
        self.taker_fee_rate = float(policy.taker_fee_rate)
        self.economic_policy_name = policy.name

    def accounting_snapshot(self, mark_price: float | None = None) -> dict:
        """Return a detached, public view of the account state."""

        snapshot = {
            "agent_id": self.agent_id,
            "name": self.name,
            "position": self.position,
            "cash": self.cash,
            "initial_cash": self.initial_cash,
            "vwap": self.vwap,
            "realized_pnl": self.realized_pnl,
            "fees_paid": self.fees_paid,
            "active_orders": deepcopy(self.active_orders),
            "trade_history": deepcopy(self.trade_history),
            "economic_policy": self.economic_policy_name,
        }
        if mark_price is not None:
            snapshot["marked_equity"] = self.marked_equity(mark_price)
            snapshot["unrealized_pnl"] = self.compute_unrealized_pnl(mark_price)
            snapshot["total_pnl"] = self.compute_pnl(mark_price)
        return snapshot

    def handle_execution(self, msg) -> None:
        """Helper method to handle execution messages and update accounting."""
        raw_qty = msg.data.get("qty", 0)
        if not isinstance(raw_qty, int) or isinstance(raw_qty, bool):
            raise ValueError(f"Execution quantity must be an integer, got {raw_qty!r}")
        qty = raw_qty
        price = float(msg.data.get("price", 0.0))
        side = msg.data.get("side", "BUY")
        order_id = msg.data.get("order_id")
        raw_fee = msg.data.get("fee", 0.0)

        if qty <= 0:
            raise ValueError(f"Execution quantity must be positive, got {qty}")
        if side not in {"BUY", "SELL"}:
            raise ValueError(f"Unsupported execution side {side!r}")
        if not isfinite(price) or price <= 0:
            raise ValueError(f"Execution price must be finite and positive, got {price}")
        try:
            fee = float(raw_fee)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Execution fee must be numeric, got {raw_fee!r}") from exc
        if not isfinite(fee) or fee < 0:
            raise ValueError(f"Execution fee must be finite and non-negative, got {fee}")

        trade_qty = qty if side == "BUY" else -qty
        new_position = self.position + trade_qty
        if self.position_limit is not None and abs(new_position) > self.position_limit:
            raise ValueError(
                f"Execution would exceed position limit {self.position_limit}: {new_position}"
            )
        if not self.allow_short and new_position < 0:
            raise ValueError("Execution would create a short position")
        
        # Determine trade sign

        # Calculate Realized PnL and VWAP
        if (self.position > 0 and trade_qty < 0) or (self.position < 0 and trade_qty > 0):
            # Closing or partially closing position
            closing_qty = min(abs(self.position), abs(trade_qty))
            
            # PnL realized = closing_qty * (Sell Price - Buy Price)
            if self.position > 0:
                self.realized_pnl += closing_qty * (price - self.vwap)
            else:
                self.realized_pnl += closing_qty * (self.vwap - price)
            
            # If trade flips position, update vwap for remainder
            if abs(trade_qty) > abs(self.position):
                self.vwap = price
            # If position becomes 0, vwap resets
            elif abs(trade_qty) == abs(self.position):
                self.vwap = 0.0
        else:
            # Increasing position
            new_position_abs = abs(self.position) + abs(trade_qty)
            if new_position_abs > 0:
                self.vwap = ((self.vwap * abs(self.position)) + (price * abs(trade_qty))) / new_position_abs

        # Update position and cash
        self.position += trade_qty
        self.cash -= trade_qty * price + fee
        self.fees_paid += fee
        self.realized_pnl -= fee
        
        # Update trade history
        t = self.kernel.time if getattr(self, "kernel", None) else 0
            
        self.trade_history.append({
            "time": t,
            "side": side,
            "qty": qty,
            "price": price,
            "order_id": order_id,
            "counterparty_order_id": msg.data.get("counterparty_order_id"),
            "trade_id": msg.data.get("trade_id"),
            "fee": fee,
        })
        
        # Remove or reduce from active orders
        remaining_qty = msg.data.get("remaining_qty")
        has_remaining = (
            isinstance(remaining_qty, int)
            and not isinstance(remaining_qty, bool)
            and remaining_qty >= 0
        )
        if order_id is not None:
            if order_id in self.active_orders:
                self.active_orders[order_id]["qty"] -= qty
                if self.active_orders[order_id]["qty"] <= 0:
                    del self.active_orders[order_id]
            if has_remaining and remaining_qty == 0:
                self._completed_order_ids.add(order_id)
                self._early_execution_remaining.pop(order_id, None)
            elif order_id not in self.active_orders and has_remaining:
                previous = self._early_execution_remaining.get(order_id)
                self._early_execution_remaining[order_id] = (
                    remaining_qty if previous is None else min(previous, remaining_qty)
                )

        self.reconcile_accounting()

    def handle_order_accepted(self, msg) -> None:
        """Helper to track accepted orders."""
        order_id = msg.data.get("order_id")
        qty = msg.data.get("qty")
        if order_id is None or not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            raise ValueError("ORDER_ACCEPTED must include a positive integer qty and order_id")
        if order_id in self._completed_order_ids:
            return
        if order_id in self.active_orders:
            raise ValueError(f"Duplicate accepted order id {order_id}")
        if msg.data.get("side") not in {"BUY", "SELL"}:
            raise ValueError("ORDER_ACCEPTED must include a valid side")
        if float(msg.data.get("price", 0.0)) <= 0:
            raise ValueError("ORDER_ACCEPTED must include a positive price")
        early_remaining = self._early_execution_remaining.pop(order_id, None)
        if early_remaining is not None:
            qty = min(qty, early_remaining)
            if qty <= 0:
                self._completed_order_ids.add(order_id)
                return
        if order_id is not None:
            self.active_orders[order_id] = {
                "side": msg.data.get("side"),
                "qty": qty,
                "price": msg.data.get("price", 0.0),
                "time": getattr(self.kernel, "time", 0),
                "order_type": msg.data.get("order_type", "LIMIT"),
                "original_qty": msg.data.get("original_qty", qty),
            }
            
    def handle_order_cancelled(self, msg) -> None:
        """Helper to track cancelled orders."""
        order_id = msg.data.get("order_id")
        if order_id in self.active_orders:
            del self.active_orders[order_id]
        self._early_execution_remaining.pop(order_id, None)
        self._completed_order_ids.discard(order_id)

    def handle_order_rejected(self, msg) -> None:
        """Record a structured exchange rejection without mutating the account."""

        self.last_action_status = "REJECTED"
        self.last_rejection = deepcopy(msg.data)

    def expire_active_orders(self, order_ids) -> None:
        """Remove resting orders when the simulation reaches terminal state."""

        for order_id in order_ids:
            self.active_orders.pop(order_id, None)
            self._early_execution_remaining.pop(order_id, None)
        if order_ids:
            self.last_action_status = "EXPIRED"

    def reconcile_accounting(self, *, tolerance: float = 1e-9) -> dict:
        """Reconcile cash and position with the fills received by this account."""

        expected_position = 0
        expected_cash = self.initial_cash
        for trade in self.trade_history:
            qty = int(trade["qty"])
            signed_qty = qty if trade["side"] == "BUY" else -qty
            expected_position += signed_qty
            expected_cash -= signed_qty * float(trade["price"]) + float(trade.get("fee", 0.0))
        expected_position += self._terminal_position_adjustment
        expected_cash += self._terminal_cash_adjustment
        if expected_position != self.position:
            raise ValueError(
                f"position reconciliation failed: expected {expected_position}, got {self.position}"
            )
        if abs(expected_cash - self.cash) > tolerance:
            raise ValueError(
                f"cash reconciliation failed: expected {expected_cash}, got {self.cash}"
            )
        return {
            "position": self.position,
            "cash": self.cash,
            "expected_position": expected_position,
            "expected_cash": expected_cash,
            "trade_count": len(self.trade_history),
        }

    def settle_terminal(self, mark_price: float, *, method: str = "mark_only") -> dict:
        """Apply the explicitly selected terminal treatment to open inventory."""

        if method not in {"mark_only", "mark_to_market"}:
            raise ValueError(f"unsupported terminal settlement {method!r}")
        if not isfinite(float(mark_price)) or mark_price <= 0:
            raise ValueError("mark_price must be finite and positive")
        if method == "mark_to_market" and self.position:
            position_before_settlement = self.position
            settlement_cash = position_before_settlement * float(mark_price)
            self.realized_pnl += position_before_settlement * (float(mark_price) - self.vwap)
            self.cash += settlement_cash
            self.position = 0
            self.vwap = 0.0
            self._terminal_cash_adjustment += settlement_cash
            self._terminal_position_adjustment -= position_before_settlement
        self.reconcile_accounting()
        return self.accounting_snapshot(float(mark_price))
