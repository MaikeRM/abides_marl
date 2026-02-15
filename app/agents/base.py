from typing import Optional

class Agent:
    def __init__(self, agent_id, name):
        self.agent_id = agent_id
        self.name = name
        self.kernel = None  # To be set by Kernel

    def wakeup(self, now):
        pass

    def receive(self, msg):
        pass
