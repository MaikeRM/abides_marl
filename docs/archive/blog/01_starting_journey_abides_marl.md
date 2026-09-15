# Market Microstructure Engineering: Building an ABIDES-MARL Simulator from Scratch (Part 1)

**Status:** _Work in Progress_
**Stack:** Python, Discrete Event Simulation, Reinforcement Learning

---

Market simulation has evolved drastically over the last decade. We have moved from static OHLC candle-based backtests to high-fidelity **Agent-Based Modeling (ABM)** environments capable of replicating tick dynamics, network latency, and endogenous market impact.

In this series of articles, I will document the process of reverse-engineering and implementing the framework proposed in the very recent paper **"ABIDES-MARL: A Multi-Agent Reinforcement Learning Environment for Endogenous Price Formation"** (2025).

The goal is not just to "run a backtest", but to build a **Multi-Agent Reinforcement Learning (MARL)** laboratory where autonomous agents (Market Makers, Execution Algos) learn optimal strategies in a live Limit Order Book (LOB).

We will also keep GPU-vectorized execution frameworks like **JAX-LOB** and **JAXMARL** on our radar, as they represent the state of the art in performance for massive training.

---

## 1. The Theoretical Architecture: DEMAS

The foundation of any serious microstructure simulator is **Discrete Event Multi-Agent Simulation (DEMAS)**. Unlike _time-stepping_ simulations (where the clock advances in fixed intervals $t, t+1...$), a DEMAS kernel advances **event by event**.

This is crucial for modeling **latency**. In the real market, the arrival order at the matching engine defines execution priority. If my algorithm in Colocation (1ms) competes with a retail trader (200ms), the simulator needs to respect this exact queue, not group everything into the same "second".

### The Kernel (`v010_abides_poc.py`)

In our v0.1.0 implementation, the Kernel manages global time and a priority queue of messages.

```python
# Discrete Event Kernel Core
def step(self):
    if not self._events:
        return False

    # Time "jumps" to the next scheduled event
    when, _, msg = heapq.heappop(self._events)
    self.time = when

    agent = self._agents[msg.dst]
    if msg.kind == "WAKEUP":
        agent.wakeup(self.time)
    else:
        agent.receive(msg)
    return True
```

Note that there is no `while True: time.sleep(1)` loop. Time is a continuous variable that jumps instantly to the exact moment of the next message delivery or agent wakeup.

---

## 2. Price and Agent Modeling

To create a market that isn't just a Random Walk, we need **heterogeneous agents** with conflicting objectives. We implemented the classic structure from microstructure literature:

### A. The Fundamental Process (Oracle)

The "fair" value of the asset ($V_t$) follows an **Ornstein-Uhlenbeck** (Mean Reverting) process. This simulates the tendency of prices to return to a long-term fundamental value, while suffering stochastic shocks (Brownian Motion).

Mathematically, we implement this in `Oracle.get_value`:
$$ dV_t = \kappa(\bar{r} - V_t)dt + \sigma dW_t $$

This value is invisible to most, except for...

### B. Informed Traders (Alpha Seekers)

These agents possess "privileged information" or superior predictive models. They observe $V_t$ (with some noise $\epsilon$) and aggress the book when the market price diverges from the fundamental value beyond a threshold $\alpha$.

In the code:

```python
# Alpha signal strategy
diff = fundamental - market_price
if abs(diff) > self.threshold:
    # Directional aggression to correct mispricing
    side = "BUY" if diff > 0 else "SELL"
    self.kernel.send(..., "NEW_ORDER", side, ...)
```

### C. Market Makers (Liquidity Providers)

They earn on the spread (Bid-Ask) and lose on adverse selection (when trading with Informed Traders). In our v0.1.0, the `MarketMakerAgent` dynamically manages its inventory. If it accumulates too much of a long position, it "skews" its quotes downwards to encourage selling and discourage new buying.

```python
# Inventory Skew Logic
inventory_skew = -self.position * risk_aversion_factor
mid_price = last_trade + inventory_skew

# Posting symmetric quotes around the adjusted mid
bid = mid_price - spread/2
ask = mid_price + spread/2
```

---

## 3. Matching Mechanism (The Exchange)

The exchange (`ExchangeAgent`) operates a **Continuous Double Auction (CDA)**.
For v0.1.0, we implemented standard `O(n)` matching logic with **Price-Time** priority:

1.  **Best Price** orders execute first.
2.  Orders at the same price execute in arrival order (FIFO).

The matching engine checks for crossing orders with every new `NEW_ORDER` message received. If there is compatible liquidity, it generates an `EXECUTION` trade; otherwise, the order rests in the LOB (`Limit Order Book`).

---

## 4. Gap Analysis: The Path to ABIDES-MARL

Although our infrastructure supports simulation, we are technically distant from the state-of-the-art **MARL (Multi-Agent Reinforcement Learning)** framework.

I performed a detailed gap analysis (`changelog/v010_analise_abides_marl.md`), identifying:

1.  **Missing Kyle Model**: Our Informed Traders use simple heuristics (`if diff > threshold`). The paper proposes agents that learn Kyle's linear market impact function ($\lambda$), optimizing order size to maximize profit without moving price excessively.
2.  **Observation/Action Spaces (RL)**: Currently, agents are hard-coded. To use RL (PPO - Proximal Policy Optimization), we need to expose the LOB state (depth, prices) as normalized tensors and define discrete or continuous actions for the neural network.
3.  **Synchronization for Training**: An RL environment requires a `step(action) -> reward, next_state` loop. DEMAS is asynchronous. We will need a `StopSignalAgent` or a wrapper compatible with **Gymnasium/PettingZoo** to "freeze" the market and allow the neural network to make decisions.

---

## Technical Roadmap: The Path to v1.0

Our backlog for upcoming sprints is divided into incremental phases, detailed in our gap analysis:

### Phase 1: Agent Formalization (Immediate Priority)

The focus will be aligning our heuristic agents with the formal economic models from the paper.

- **Informed Trader:** Implement Kyle's linear strategy $x(n) = \beta(v - \bar{p})\tau$, replacing the fixed threshold heuristic.
- **Market Maker:** Implement impact-based pricing $\lambda$ ($p(n) = \bar{p} + \lambda q$) and the pro-rata allocation mechanism.
- **Liquidity Trader:** Add the utility function with quadratic risk penalty $\phi Q^2$, essential for creating realistic risk aversion.

### Phase 2: RL Interface (Gymnasium)

Preparing the ground for the AI "brain".

- **Observation Spaces:** Define the normalized tensors that will represent the LOB ($p_{i}, q_{i}$) for the neural network.
- **Wrappers:** Implement the `gym.Env` and `pettingzoo` interface to make the simulator compatible with standard RL libraries (Stable-Baselines3, RLLib).
- **Synchronization:** Create the `StopSignalAgent` to coordinate agent decision-making in a continuous time environment.

### Phase 3: Multi-Agent Training (MARL)

Where the magic happens.

- **Independent PPO (IPPO):** Train multiple agents simultaneously, each optimizing its own reward (profit + risk management).
- **Validation:** Compare learned ("organic") strategies with known analytical solutions from literature to ensure the AI works as expected.

### Phase 4: High-Performance Computing (JAX)

Aiming for massive scale.

- **Vectorization:** Migration of the Kernel to **JAX**, allowing thousands of environments to run in parallel on a single GPU. This is vital to reduce training time from weeks to hours.

The code is available in the repository. I invite other quants and engineers to clone `v0.1.0` and run the simulation.

```bash
python v010_abides_poc.py
```

The output is a real-time TUI showing price formation emerging from the interaction between our noisy and informed agents.

_Stay tuned for the deep dive into the Gymnasium Wrapper implementation in Part 2._
