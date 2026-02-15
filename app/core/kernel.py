import heapq
import random
from collections import deque
from datetime import datetime
from app.models.types import Message


class Kernel:
    def __init__(self, seed=42):
        self.time = 0
        self._seq = 0
        self._events = []
        self._agents = {}
        self.latency = {}
        self.rng = random.Random(seed)
        self.running = True
        self.logs = deque(maxlen=50)
        self.event_history = deque(maxlen=1000)
        self.print_logs = True

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
        self.event_history.append(
            {
                "timestamp": self._timestamp(),
                "sim_time": sim_time,
                "phase": phase,
                "kind": kind,
                "seq": seq,
                "delivery": delivery,
                "src": src,
                "src_name": self._actor_name(src),
                "dst": dst,
                "dst_name": self._actor_name(dst),
                "data": dict(data),
            }
        )

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
        self._agents[agent.agent_id] = agent
        agent.kernel = self

    def set_latency(self, src, dst, delay):
        self.latency[(src, dst)] = max(0, int(delay))

    def _delay(self, src, dst):
        return self.latency.get((src, dst), 1)

    def send(self, src, dst, kind, data=None):
        if data is None:
            data = {}
        msg = Message(src=src, dst=dst, kind=kind, data=data)
        delivery = self.time + self._delay(src, dst)
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
        if msg.kind == "WAKEUP":
            agent.wakeup(self.time)
        else:
            agent.receive(msg)
        return True
