import unittest

from app.agents.base import Agent
from app.core.kernel import Kernel


class RecordingAgent(Agent):
    def __init__(self, agent_id: int, name: str):
        super().__init__(agent_id, name)
        self.events = []

    def wakeup(self, now: int) -> None:
        self.events.append(("WAKEUP", now))

    def receive(self, msg) -> None:
        self.events.append((msg.kind, self.kernel.time, dict(msg.data)))

    def get_observation(self) -> list:
        return []

    def get_reward(self) -> float:
        return 0.0


class KernelSanityTest(unittest.TestCase):
    def test_same_delivery_uses_fifo_sequence(self):
        kernel = Kernel(seed=7)
        kernel.print_logs = False
        agent = RecordingAgent(1, "REC")
        kernel.register(agent)
        kernel.set_latency(-1, 1, 0)

        kernel.send(-1, 1, "FIRST", {"value": 1})
        kernel.send(-1, 1, "SECOND", {"value": 2})

        self.assertTrue(kernel.step())
        self.assertTrue(kernel.step())
        self.assertTrue(kernel.step())

        self.assertEqual(
            agent.events,
            [
                ("FIRST", 0, {"value": 1}),
                ("SECOND", 1, {"value": 2}),
            ],
        )

    def test_busy_agent_requeues_future_delivery(self):
        kernel = Kernel(seed=11)
        kernel.print_logs = False
        agent = RecordingAgent(1, "REC")
        kernel.register(agent)
        kernel.agent_computation_delays[1] = 5
        kernel.set_latency(-1, 1, 1)

        kernel.send(-1, 1, "PING", {"value": 1})
        kernel.wakeup(1, at_time=2)

        self.assertTrue(kernel.step())
        self.assertEqual(agent.events, [("PING", 1, {"value": 1})])
        self.assertEqual(kernel.agent_current_times[1], 6)

        self.assertTrue(kernel.step())
        self.assertEqual(agent.events, [("PING", 1, {"value": 1})])
        self.assertEqual(kernel.time, 2)

        self.assertTrue(kernel.step())
        self.assertEqual(
            agent.events,
            [
                ("PING", 1, {"value": 1}),
                ("WAKEUP", 6),
            ],
        )


if __name__ == "__main__":
    unittest.main()
