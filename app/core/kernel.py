import heapq
import random
from copy import deepcopy
from collections import deque
from datetime import datetime
from app.models.types import Message


class Kernel:
    def __init__(self, seed=42):
        self.seed = int(seed)
        self.time = 0
        self._seq = 0
        self._events = []
        self._agents = {}
        self.latency = {}
        self.rng = random.Random(self.seed)
        self.running = True
        self.logs = deque(maxlen=50)
        self.event_history = deque(maxlen=1000)
        self.canonical_event_history = []
        self.print_logs = True
        
        self.agent_current_times = {}
        self.agent_computation_delays = {}

    def _actor_name(self, agent_id):
        if agent_id == -1:
            return "KERNEL"
        agent = self._agents.get(agent_id)
        if agent is None:
            return str(agent_id)
        return f"{agent.name}({agent_id})"

    def _timestamp(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def _record_event(
        self, phase, kind, src, dst, data=None, sim_time=None, delivery=None, seq=None
    ):
        if data is None:
            data = {}
        if sim_time is None:
            sim_time = self.time
        stable_event = {
            "sim_time": sim_time,
            "phase": phase,
            "kind": kind,
            "seq": seq,
            "delivery": delivery,
            "src": src,
            "src_name": self._actor_name(src),
            "dst": dst,
            "dst_name": self._actor_name(dst),
            "data": deepcopy(data),
        }
        self.canonical_event_history.append(deepcopy(stable_event))
        observability_event = {"timestamp": self._timestamp(), **stable_event}
        self.event_history.append(observability_event)

    def log(self, text):
        self.logs.append(f"[t={self.time:04d}] {text}")
        self._record_event(
            phase="LOG",
            kind="LOG",
            src=-1,
            dst=-1,
            data={"text": text},
            sim_time=self.time,
        )
        if self.print_logs:
            print(f"[t={self.time:04d}] {text}")

    def register(self, agent):
        if agent.agent_id in self._agents:
            raise ValueError(f"Agent id {agent.agent_id} is already registered")
        self._agents[agent.agent_id] = agent
        agent.kernel = self
        self.agent_current_times[agent.agent_id] = 0
        self.agent_computation_delays[agent.agent_id] = 1

    def set_latency(self, src, dst, delay):
        if not isinstance(delay, int) or isinstance(delay, bool) or delay < 0:
            raise ValueError("latency delay must be a non-negative integer")
        self.latency[(src, dst)] = delay

    def _delay(self, src, dst):
        base_latency = self.latency.get((src, dst), 1)
        # Latency noise only if it is communicating across network
        noise = self.rng.randint(0, 3) if src != dst and src != -1 and dst != -1 else 0
        return base_latency + noise

    def send(self, src, dst, kind, data=None):
        if dst not in self._agents:
            raise ValueError(f"Cannot deliver message to unknown agent {dst}")
        if data is None:
            data = {}
        msg = Message(src=src, dst=dst, kind=kind, data=data)
        
        # Consider the agent's current time if it's sending a message
        sent_time = self.time if src == -1 else self.agent_current_times.get(src, self.time)
        delivery = sent_time + self._delay(src, dst)
        
        seq = self._seq
        heapq.heappush(self._events, (delivery, seq, msg))
        self._record_event(
            phase="ENQUEUED",
            kind=kind,
            src=src,
            dst=dst,
            data=data,
            sim_time=self.time,
            delivery=delivery,
            seq=seq,
        )
        self._seq += 1

    def wakeup(self, agent_id, at_time):
        if agent_id not in self._agents:
            raise ValueError(f"Cannot wake unknown agent {agent_id}")
        if not isinstance(at_time, int) or isinstance(at_time, bool) or at_time < 0:
            raise ValueError("wakeup time must be a non-negative integer")
        msg = Message(src=-1, dst=agent_id, kind="WAKEUP", data={})
        seq = self._seq
        delivery = int(at_time)
        heapq.heappush(self._events, (delivery, seq, msg))
        self._record_event(
            phase="ENQUEUED",
            kind="WAKEUP",
            src=-1,
            dst=agent_id,
            data={},
            sim_time=self.time,
            delivery=delivery,
            seq=seq,
        )
        self._seq += 1

    @property
    def has_events(self) -> bool:
        """Whether at least one event is pending."""

        return bool(self._events)

    @property
    def registered_agent_ids(self) -> tuple[int, ...]:
        """Return registered agent identifiers in deterministic order.

        Consumers should use this view instead of reaching into ``_agents``.
        The tuple prevents callers from mutating the kernel registry while an
        episode is running.
        """

        return tuple(sorted(self._agents))

    def get_agent(self, agent_id: int):
        """Return a registered agent or ``None`` without exposing the map."""

        return self._agents.get(agent_id)

    def snapshot(self) -> dict:
        """Return the public execution state needed by adapters and tooling."""

        return {
            "time": self.time,
            "running": self.running,
            "pending_events": len(self._events),
            "next_delivery_time": self.next_delivery_time,
            "registered_agent_ids": list(self.registered_agent_ids),
        }

    def stop(self, *, clear_pending_events: bool = True) -> None:
        """Stop consumption and optionally discard events beyond the episode."""

        self.running = False
        if clear_pending_events:
            self._events.clear()

    @property
    def next_delivery_time(self) -> int | None:
        """Return the next delivery time without exposing the heap."""

        return self._events[0][0] if self._events else None

    def get_canonical_trace(self) -> list[dict]:
        """Return a copy of the trace without wall-clock fields."""

        return deepcopy(self.canonical_event_history)

    def reset(self, seed: int | None = None) -> None:
        """Reset kernel state while preserving registered agent objects."""

        if seed is not None:
            self.seed = int(seed)
        self.time = 0
        self._seq = 0
        self._events.clear()
        self.rng = random.Random(self.seed)
        self.running = True
        self.logs.clear()
        self.event_history.clear()
        self.canonical_event_history.clear()
        for agent in self._agents.values():
            agent.reset()
        for agent_id in self._agents:
            self.agent_current_times[agent_id] = 0

    def step(self):
        if not self._events:
            self.running = False
            return False
        when, seq, msg = heapq.heappop(self._events)
        self.time = when
        self._record_event(
            phase="PROCESSED",
            kind=msg.kind,
            src=msg.src,
            dst=msg.dst,
            data=msg.data,
            sim_time=when,
            delivery=when,
            seq=seq,
        )
        agent = self._agents[msg.dst]
        
        # Agent is in the future, delay message delivery
        agent_time = self.agent_current_times.get(msg.dst, 0)
        if agent_time > when:
            heapq.heappush(self._events, (agent_time, seq, msg))
            return True

        self.agent_current_times[msg.dst] = when

        if msg.kind == "WAKEUP":
            agent.wakeup(self.time)
        else:
            agent.receive(msg)
            
        # Apply computation penalty
        delay = self.agent_computation_delays.get(msg.dst, 1)
        self.agent_current_times[msg.dst] += delay
        
        return True
