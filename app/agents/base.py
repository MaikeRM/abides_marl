from abc import ABC, abstractmethod
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
        
        # New trading metrics
        self.vwap: float = 0.0
        self.realized_pnl: float = 0.0
        self.active_orders: dict = {}  # order_id -> order details
        self.trade_history: list = []  # List of trades
        self._last_reward_mark: float | None = None

    def get_observation(self) -> list:
        """Default: return empty observation for non-RL agents."""
        return []

    def get_reward(self) -> float:
        """Default: return 0 reward for non-RL agents."""
        return 0.0

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

    def handle_execution(self, msg) -> None:
        """Helper method to handle execution messages and update accounting."""
        raw_qty = msg.data.get("qty", 0)
        if not isinstance(raw_qty, int) or isinstance(raw_qty, bool):
            raise ValueError(f"Execution quantity must be an integer, got {raw_qty!r}")
        qty = raw_qty
        price = float(msg.data.get("price", 0.0))
        side = msg.data.get("side", "BUY")
        order_id = msg.data.get("order_id")

        if qty <= 0:
            raise ValueError(f"Execution quantity must be positive, got {qty}")
        if side not in {"BUY", "SELL"}:
            raise ValueError(f"Unsupported execution side {side!r}")
        if not isfinite(price) or price <= 0:
            raise ValueError(f"Execution price must be finite and positive, got {price}")

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
        self.cash -= trade_qty * price
        
        # Update trade history
        t = self.kernel.time if getattr(self, "kernel", None) else 0
            
        self.trade_history.append({
            "time": t,
            "side": side,
            "qty": qty,
            "price": price,
            "order_id": order_id
        })
        
        # Remove or reduce from active orders
        if order_id is not None and order_id in self.active_orders:
            self.active_orders[order_id]["qty"] -= qty
            if self.active_orders[order_id]["qty"] <= 0:
                del self.active_orders[order_id]

    def handle_order_accepted(self, msg) -> None:
        """Helper to track accepted orders."""
        order_id = msg.data.get("order_id")
        qty = msg.data.get("qty")
        if order_id is None or not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            raise ValueError("ORDER_ACCEPTED must include a positive integer qty and order_id")
        if order_id in self.active_orders:
            raise ValueError(f"Duplicate accepted order id {order_id}")
        if msg.data.get("side") not in {"BUY", "SELL"}:
            raise ValueError("ORDER_ACCEPTED must include a valid side")
        if float(msg.data.get("price", 0.0)) <= 0:
            raise ValueError("ORDER_ACCEPTED must include a positive price")
        if order_id is not None:
            self.active_orders[order_id] = {
                "side": msg.data.get("side"),
                "qty": qty,
                "price": msg.data.get("price", 0.0),
                "time": getattr(self.kernel, "time", 0)
            }
            
    def handle_order_cancelled(self, msg) -> None:
        """Helper to track cancelled orders."""
        order_id = msg.data.get("order_id")
        if order_id in self.active_orders:
            del self.active_orders[order_id]
