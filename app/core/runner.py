import asyncio
from typing import List, Optional
from app.core.kernel import Kernel
from app.core.oracle import Oracle
from app.agents.exchange import ExchangeAgent
from app.agents.market_maker import MarketMakerAgent
from app.agents.informed import InformedTrader
from app.agents.liquidity import LiquidityTrader
from app.agents.noise import NoiseTrader


class SimulationRunner:
    def __init__(self):
        self.kernel: Optional[Kernel] = None
        self.oracle: Optional[Oracle] = None
        self.exchange: Optional[ExchangeAgent] = None
        self.agents = []
        self.running = False
        self.task = None

    def reset(self, seed=42):
        self.kernel = Kernel(seed=seed)
        self.kernel.print_logs = False
        self.oracle = Oracle(r_bar=100.0, kappa=0.05, sigma=0.5, seed=seed + 1000)
        self.exchange = ExchangeAgent(agent_id=0, start_price=100.0)
        self.kernel.register(self.exchange)

        self.agents = []
        agent_id = 1

        # Configuration similar to demo
        # 2 Market Makers
        for i in range(5):
            mm = MarketMakerAgent(
                agent_id=agent_id,
                exchange_id=0,
                seed=seed + agent_id,
                wake_interval=3,
                spread=0.80 + i * 0.20,
                order_qty=5,
            )
            self.kernel.register(mm)
            self.agents.append(mm)
            agent_id += 1

        # 10 Informed Traders (Reduced for visual clarity)
        for i in range(10):
            it = InformedTrader(
                agent_id=agent_id,
                exchange_id=0,
                oracle=self.oracle,
                seed=seed + agent_id,
                wake_interval=8,
                noise_std=0.5 + i * 0.3,
            )
            self.kernel.register(it)
            self.agents.append(it)
            agent_id += 1

        # 1 Liquidity Trader (BUY)
        lt = LiquidityTrader(
            agent_id=agent_id,
            exchange_id=0,
            seed=seed + agent_id,
            target_qty=100,
            deadline=8000,
            wake_interval=15,
            side="BUY",
        )
        self.kernel.register(lt)
        self.agents.append(lt)
        agent_id += 1

        # 20 Noise Traders
        for i in range(20):
            nt = NoiseTrader(
                agent_id=agent_id, exchange_id=0, seed=seed + agent_id, wake_interval=5
            )
            self.kernel.register(nt)
            self.agents.append(nt)
            agent_id += 1

        # Latencies
        n = agent_id
        for src in range(n):
            for dst in range(n):
                if src != dst:
                    self.kernel.set_latency(src, dst, self.kernel.rng.randint(1, 10))
                else:
                    self.kernel.set_latency(src, dst, 0)

        # Wake up all agents
        for agent in self.agents:
            self.kernel.wakeup(agent.agent_id, at_time=1)

        print("Simulation Reset Complete")

    def step(self):
        if self.kernel and self.kernel.running:
            return self.kernel.step()
        return False

    def get_state(self):
        if not self.kernel or not self.exchange:
            return {}

        # Simplified LOB for frontend
        bids = sorted(self.exchange.bids, key=lambda x: -x.price)[:10]
        asks = sorted(self.exchange.asks, key=lambda x: x.price)[:10]

        return {
            "time": self.kernel.time,
            "last_price": self.exchange.last_trade,
            "fundamental_value": self.oracle.get_value(self.kernel.time)
            if self.oracle
            else 0.0,
            "bids": [{"price": o.price, "qty": o.qty} for o in bids],
            "asks": [{"price": o.price, "qty": o.qty} for o in asks],
            "history": [
                {"time": t.ts, "price": t.price, "qty": t.qty, "side": t.aggressor_side}
                for t in self.exchange.history[-20:]  # Last 20 trades
            ],
            "events": list(self.kernel.event_history)[-300:],
        }
