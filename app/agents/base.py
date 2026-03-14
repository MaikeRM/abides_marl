from abc import ABC, abstractmethod
from typing import Any, Optional


class Agent(ABC):
    """
    Abstract base class for all agents in the simulation.

    Provides the core interface required for both heuristic and RL agents.
    Subclasses must implement all @abstractmethod decorated methods.
    """

    def __init__(self, agent_id: int, name: str):
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

    def __init__(self, agent_id: int, name: str):
        super().__init__(agent_id, name)
        self.position: int = 0
        self.cash: float = 0.0
        self.pnl_history: list[float] = []
        self.state: str = "ACTIVE"

        # Trading metrics
        self.vwap: float = 0.0
        self.realized_pnl: float = 0.0
        self.active_orders: dict = {}  # order_id -> order details
        self.trade_history: list = []  # List of trades

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

    def reset(self) -> None:
        """Reset all episode state. Call super().reset() in subclasses."""
        self.position = 0
        self.cash = 0.0
        self.pnl_history = []
        self.state = "ACTIVE"
        self.vwap = 0.0
        self.realized_pnl = 0.0
        self.active_orders = {}
        self.trade_history = []
        self._last_mkt = {"best_bid": None, "best_ask": None, "last_trade": 0.0}
        self._last_reward_pnl = 0.0

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

    def handle_execution(self, msg) -> None:
        """Helper method to handle execution messages and update accounting."""
        qty = int(msg.data.get("qty", 0))
        price = float(msg.data.get("price", 0.0))
        side = msg.data.get("side", "BUY")
        order_id = msg.data.get("order_id")
        
        # Determine trade sign
        trade_qty = qty if side == "BUY" else -qty
        
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
        if order_id and order_id in self.active_orders:
            self.active_orders[order_id]["qty"] -= qty
            if self.active_orders[order_id]["qty"] <= 0:
                del self.active_orders[order_id]

    def handle_order_accepted(self, msg) -> None:
        """Helper to track accepted orders."""
        order_id = msg.data.get("order_id")
        if order_id:
            self.active_orders[order_id] = {
                "side": msg.data.get("side"),
                "qty": msg.data.get("qty"),
                "price": msg.data.get("price", 0.0),
                "time": getattr(self.kernel, "time", 0)
            }
            
    def handle_order_cancelled(self, msg) -> None:
        """Helper to track cancelled orders."""
        order_id = msg.data.get("order_id")
        if order_id in self.active_orders:
            del self.active_orders[order_id]
