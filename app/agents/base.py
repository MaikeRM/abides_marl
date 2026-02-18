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

    def get_observation(self) -> list:
        """Default: return empty observation for non-RL agents."""
        return []

    def get_reward(self) -> float:
        """Default: return 0 reward for non-RL agents."""
        return 0.0

    def compute_pnl(self) -> float:
        """Compute current unrealized + realized PnL."""
        return self.cash  # Simplified - doesn't account for position value
