import asyncio
from typing import List, Optional
from app.core.kernel import Kernel
from app.core.oracle import Oracle
from app.agents.exchange import ExchangeAgent
from app.agents.market_maker import MarketMakerAgent
from app.agents.value_agent import ValueAgent
from app.agents.zi_agent import ZeroIntelligenceAgent
from app.agents.liquidity import LiquidityTrader


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

        if self.agents:
            # Reuse existing agent instances (RL training path): reset state and re-register.
            self.exchange.reset()
            self.exchange.kernel = None
            self.kernel.register(self.exchange)
            for agent in self.agents:
                agent.reset()
                agent.kernel = None
                self.kernel.register(agent)
        else:
            # First initialisation: create all agent instances.
            self.exchange = ExchangeAgent(agent_id=0, start_price=100.0)
            self.kernel.register(self.exchange)

            agent_id = 1

            # 5 Market Makers
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

            # 10 Value Agents (Bayesian)
            for i in range(10):
                va = ValueAgent(
                    agent_id=agent_id,
                    exchange_id=0,
                    oracle=self.oracle,
                    seed=seed + agent_id,
                    wake_interval=8,
                    kappa=0.05,
                    sigma_s=0.5,
                    sigma_n=1.0 + i * 0.1,
                    theta=(self.kernel.rng.gauss(0, 1.0)),
                )
                self.kernel.register(va)
                self.agents.append(va)
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

            # 20 ZI Agents
            for i in range(20):
                zi = ZeroIntelligenceAgent(
                    agent_id=agent_id,
                    exchange_id=0,
                    seed=seed + agent_id,
                    wake_interval=5,
                    base_value=100.0,
                    theta_std=2.0 + i * 0.1,
                )
                self.kernel.register(zi)
                self.agents.append(zi)
                agent_id += 1

        # Latencies
        all_agents = [self.exchange] + self.agents
        n = len(all_agents)
        for src_agent in all_agents:
            for dst_agent in all_agents:
                if src_agent.agent_id != dst_agent.agent_id:
                    self.kernel.set_latency(
                        src_agent.agent_id, dst_agent.agent_id,
                        self.kernel.rng.randint(1, 10)
                    )
                else:
                    self.kernel.set_latency(src_agent.agent_id, dst_agent.agent_id, 0)

        # Wake up all non-exchange agents
        for agent in self.agents:
            self.kernel.wakeup(agent.agent_id, at_time=1)

        print("Simulation Reset Complete")

    def stop(self):
        if not self.kernel:
            return

        final_fund_price = self.oracle.get_value(self.kernel.time) if self.oracle else 0.0

        for agent in self.agents:
            agent.kernelStopping()

            if hasattr(agent, 'position') and hasattr(agent, 'cash'):
                surplus = (agent.position * final_fund_price) + agent.cash
                self.kernel.log(f"FINAL_VALUATION: {agent.name} Surplus = {surplus:.2f} (Pos: {agent.position}, Cash: {agent.cash:.2f})")

        self.running = False


    def step(self):
        if self.kernel and self.kernel.running:
            return self.kernel.step()
        return False

    def get_state(self):
        if not self.kernel or not self.exchange:
            return {}

        # Aggregate LOB heavily for frontend (group by price level)
        from collections import defaultdict
        
        bid_levels = defaultdict(int)
        for o in self.exchange.bids:
            bid_levels[o.price] += o.qty
            
        ask_levels = defaultdict(int)
        for o in self.exchange.asks:
            ask_levels[o.price] += o.qty

        best_bids = sorted([{"price": p, "qty": q} for p, q in bid_levels.items()], key=lambda x: -x["price"])[:40]
        best_asks = sorted([{"price": p, "qty": q} for p, q in ask_levels.items()], key=lambda x: x["price"])[:40]
        
        agent_states = {}
        for agent in self.agents:
            agent_states[agent.agent_id] = {
                "name": getattr(agent, "name", str(agent.agent_id)),
                "type": type(agent).__name__,
                "position": getattr(agent, "position", 0),
                "cash": getattr(agent, "cash", 0.0),
                "vwap": getattr(agent, "vwap", 0.0),
                "realized_pnl": getattr(agent, "realized_pnl", 0.0),
                "active_orders": getattr(agent, "active_orders", {}),
                "trade_history": getattr(agent, "trade_history", []),
            }

        return {
            "time": self.kernel.time,
            "last_price": self.exchange.last_trade,
            "fundamental_value": self.oracle.get_value(self.kernel.time)
            if self.oracle
            else 0.0,
            "bids": best_bids,
            "asks": best_asks,
            "history": [
                {"time": t.ts, "price": t.price, "qty": t.qty, "side": t.aggressor_side}
                for t in self.exchange.history[-20:]
            ],
            "events": list(self.kernel.event_history)[-300:],
            "agents": agent_states,
        }
