# Market Microstructure Engineering: Building an ABIDES-MARL Simulator from Scratch (Part 2)

**Status:** _Work in Progress_
**Stack:** Python, Discrete Event Simulation, DearPyGui

---

> In [Part 1](./01_starting_journey_abides_marl.md), we established the foundational architecture of a Discrete Event Multi-Agent Simulation (DEMAS) to mirror the framework proposed in the **ABIDES-MARL** paper. We built a basic `v0.1.0` Proof of Concept (PoC) with a simple matching engine and heuristic agents.
>
> Moving from a basic PoC to a production-ready, modular engine meant throwing out the shortcuts. Not a fork of the original J.P. Morgan code, nor just a wrapper. A full reimplementation from the ground up. This article is the story of what I learned, what broke, and what eventually clicked across four intense release cycles (v0.1.2 to v0.1.5) as we laid the formal groundwork before plugging in the neural networks.

---

## Table of Contents

0. [Most recent Dashboard made with DearPyGui](#0-most-recent-dashboard-made-with-dearpygui)
1. [From PoC to a Robust Engine](#1-from-poc-to-a-robust-engine)
2. [v0.1.2 — The Matching Engine That Kept Crashing](#2-v012--the-matching-engine-that-kept-crashing)
3. [v0.1.3 — Making Time Feel Real](#3-v013--making-time-feel-real)
4. [v0.1.4 — Phase 1: Formalizing Agents and Deleting Direct Access](#4-v014--phase-1-formalizing-agents-and-deleting-direct-access)
5. [v0.1.5 — When the Terminal Couldn't Keep Up](#5-v015--when-the-terminal-couldnt-keep-up)
6. [Where It Stands Now](#6-where-it-stands-now)
7. [What's Next: The RL Interface](#7-whats-next-the-rl-interface)

---

## 0. Most recent Dashboard made with DearPyGui

Before we dive into the chronological journey of rebuilding the underlying simulation components, let's take a look at the result. To monitor agents and visualize complex high-frequency interactions efficiently, I built a fast C++-backed UI using **DearPyGui** instead of a slow textual terminal interface.

Here are some glimpses of the simulator in action, handling continuous data streams, rendering Limit Order Book (LOB) heatmaps, and tracking agent PnL at over 60 FPS:

> **[TODO: Insert videos/GIFs of the v0.1.5 DearPyGui Dashboard in action here]**

---

## 1. From PoC to a Robust Engine

In Part 1, I showed a minimal `v0.1.0` implementation. It worked, but it was fragile. ABIDES is an impressive piece of academic software, but trying to scale the initial naive PoC for my own MARL experiments led me to hit walls. The code was tightly coupled, hard to extend, and—most importantly—I didn't _understand_ deeply enough every invariant and subtle interaction between the matching engine and the agents.

If I was going to train Reinforcement Learning (RL) agents in this environment, I needed an engine that could handle asynchronous delays, realistic network latency, and sophisticated heuristic agents (like Bayesian Value Agents and Adaptive Market Makers) that act as the true "market context."

What follows is a chronicle of migrating our PoC into a modular, high-performance engine, fulfilling the **Phase 1: Agent Formalization** of our roadmap, told release by release.

---

## 2. v0.1.2 — The Matching Engine That Kept Crashing

### The First Bug That Humbled Me

I started where any market simulator must start: the order book and matching engine. I chose Python's `heapq` for the bid/ask heaps—it seemed like the obvious choice. Min-heap for asks (lowest price first), max-heap for bids (via negated prices). Simple, right?

My initial heap tuple looked like this:

```python
# My first attempt (broken)
heapq.heappush(self._asks, (order.price, order.ts, order))
```

It worked beautifully... until two orders arrived at the exact same price and timestamp. Python tried to compare the `Order` objects as a tiebreaker and threw a `TypeError`. My simulation crashed after a few hundred steps in any high-activity scenario.

The fix was embarrassingly simple once I understood the problem. I added `order_id`—a monotonically increasing integer—as the third element of the tuple, guaranteeing a total ordering without ever comparing `Order` objects:

```python
# Fixed: deterministic tie-breaking with order_id
# Bids: max-heap (negated price)
# Format: (-price, timestamp, order_id, order)
self._bids: List[Tuple[float, int, int, Order]] = []

# Asks: min-heap
# Format: (price, timestamp, order_id, order)
self._asks: List[Tuple[float, int, int, Order]] = []
```

The priority for asks becomes a lexicographic comparison:

$$
\text{Priority}_{\text{ask}} = (p_i,\ t_i,\ \text{id}_i)
$$

$$
\text{Priority}_{\text{bid}} = (-p_i,\ t_i,\ \text{id}_i) \quad \text{(negation gives max-heap behavior)}
$$

This tiny change—adding one integer to a tuple—eliminated an entire class of crashes. It was my first lesson from this project: **in matching engines, there is no room for ambiguity.**

### Writing the Matching Loop

With the heap structure solid, I wrote the core matching algorithm. This is the heart of the entire simulator—every trade that happens passes through this function:

```python
def _match(self, incoming):
    opp = self._opposite(incoming.side)

    while incoming.qty > 0 and opp:
        # Peek at best resting order — O(1)
        if incoming.side == "BUY":
            best_price, _, _, resting = opp[0]
        else:
            neg_price, _, _, resting = opp[0]
            best_price = -neg_price

        # Do prices cross?
        if not self._crossed(incoming, best_price):
            break

        # Execute at resting order's price (price-time priority)
        trade_qty = min(incoming.qty, resting.qty)
        trade_price = resting.price

        # Notify both agents
        self.kernel.send(self.agent_id, buy_agent, "EXECUTION",
            {"side": "BUY", "qty": trade_qty, "price": trade_price})
        self.kernel.send(self.agent_id, sell_agent, "EXECUTION",
            {"side": "SELL", "qty": trade_qty, "price": trade_price})

        incoming.qty -= trade_qty
        resting.qty -= trade_qty
        if resting.qty == 0:
            heapq.heappop(opp)                           # O(log n)
            self._order_map.pop(resting.order_id, None)  # O(1)

    # Leftover qty becomes a resting limit order
    if incoming.qty > 0 and incoming.price not in (0.0, 1e9):
        if incoming.side == "BUY":
            heapq.heappush(self._bids,
                (-incoming.price, incoming.ts, incoming.order_id, incoming))
        else:
            heapq.heappush(self._asks,
                (incoming.price, incoming.ts, incoming.order_id, incoming))
        self._order_map[incoming.order_id] = incoming
```

I was proud of this. It's clean, it's correct, and the complexity is exactly what you'd expect:

| Operation              | Complexity                 |
| ---------------------- | -------------------------- |
| Best price lookup      | O(1)                       |
| Single trade execution | O(log n)                   |
| Order insertion        | O(log n)                   |
| Cancellation by ID     | O(1) lookup + O(n) removal |

The `_order_map` dictionary was another early win. Without it, cancelling an order meant scanning the entire heap—O(n). With it, I could look up any order by ID in O(1). This matters enormously when market makers cancel and replace hundreds of orders per second.

### Designing the Agent Hierarchy

The second big decision in `v0.1.2` was the agent class hierarchy. I knew from the start that this simulator needed to support both hand-coded heuristic agents _and_ RL agents. So I designed a two-tier inheritance structure:

```python
class Agent(ABC):
    """The contract every agent must fulfill."""

    @abstractmethod
    def wakeup(self, now: int) -> None: ...

    @abstractmethod
    def receive(self, msg) -> None: ...

    @abstractmethod
    def get_observation(self) -> list: ...   # RL interface

    @abstractmethod
    def get_reward(self) -> float: ...       # RL interface

    def kernelStopping(self) -> None: ...    # End-of-sim cleanup


class HeuristicAgent(Agent):
    """Pre-built accounting for non-RL agents."""

    def __init__(self, agent_id, name):
        super().__init__(agent_id, name)
        self.position: int = 0
        self.cash: float = 0.0
        self.vwap: float = 0.0
        self.realized_pnl: float = 0.0
        self.active_orders: dict = {}
        self.trade_history: list = []
        self.state: str = "ACTIVE"
```

The idea is that `Agent` defines the _simulation interface_—what the Kernel needs to interact with any participant. `HeuristicAgent` adds the _trading mechanics_—position tracking, PnL, VWAP—that heuristic agents share. When I eventually plug in an RL agent, it will inherit directly from `Agent` and implement `get_observation()` and `get_reward()` with real logic. The Kernel won't know the difference.

```
┌─────────────────────────────────────┐
│            Agent (ABC)              │
│  ┌─────────┐  ┌──────────────────┐  │
│  │ wakeup  │  │ get_observation  │  │
│  │ receive │  │ get_reward       │  │
│  └─────────┘  └──────────────────┘  │
│   Simulation     RL Interface       │
└──────────┬──────────────────────────┘
           │
    ┌──────┴──────┐
    │             │
┌───▼───┐   ┌────▼────┐
│Heuris-│   │   RL    │
│tic    │   │  Agent  │
│Agent  │   │ (future)│
└───┬───┘   └─────────┘
    │
┌───┴────────────────────────────┐
│  ValueAgent  │  MarketMaker   │
│  ZIAgent     │  Liquidity     │
└────────────────────────────────┘
```

Looking back, this was one of the best architectural decisions I made early on. Every agent I built after this—market makers, liquidity traders, Bayesian value agents—all inherited from `HeuristicAgent` without duplicating a single line of accounting code.

---

## 3. v0.1.3 — Making Time Feel Real

### The Synchrony Problem

My first simulation runs had a peculiar artifact: all agents of the same type would act at exactly the same tick. Five market makers, all quoting simultaneously. Ten noise traders, all submitting at tick 100, 200, 300. The order book would swing violently at regular intervals and then go dead silent between them.

The problem was obvious once I thought about it: I was using fixed wakeup intervals. Every market maker woke up every 5 ticks. Every noise trader woke up every 10 ticks. This created an artificial synchrony that doesn't exist in real markets.

### Introducing Poisson Arrivals

Real market participants don't operate on synchronized clocks. Their actions are better modeled as a **Poisson process**—events arriving independently at a random rate. The mathematical model is elegant:

$$
\Delta t \sim \text{Exponential}(\lambda_a)
$$

$$
f(\Delta t) = \lambda_a \cdot e^{-\lambda_a \cdot \Delta t}, \quad \Delta t \geq 0
$$

The expected inter-arrival time is $E[\Delta t] = 1/\lambda_a$. In Python, one line does the job:

```python
# Every agent now schedules its next wakeup stochastically
delta_time = self.rng.expovariate(self.lambda_a)
self.kernel.wakeup(self.agent_id, now + max(1, int(delta_time)))
```

The `max(1, ...)` guard is important—without it, an agent could schedule itself at the current tick, creating an infinite loop. After this change, my simulations immediately looked more realistic. The artificial bursts disappeared, replaced by a natural flow of asynchronous activity.

### Building Latency into the Kernel

But Poisson arrivals were only half the story. I also needed **network latency**. In real markets, messages take time to travel between participants and the exchange, and that time varies.

I redesigned the Kernel's message-passing system to inject stochastic delay:

```python
class Kernel:
    def __init__(self, seed=42):
        self.agent_current_times = {}         # Each agent's local clock
        self.agent_computation_delays = {}    # Processing cost per agent

    def _delay(self, src, dst):
        base_latency = self.latency.get((src, dst), 1)
        # Add jitter for cross-network communication
        noise = self.rng.randint(0, 3) if src != dst and src != -1 else 0
        return base_latency + noise

    def send(self, src, dst, kind, data=None):
        msg = Message(src=src, dst=dst, kind=kind, data=data)
        # Departure time = agent's LOCAL clock, not global sim time
        sent_time = (self.time if src == -1
                     else self.agent_current_times.get(src, self.time))
        delivery = sent_time + self._delay(src, dst)
        heapq.heappush(self._events, (delivery, seq, msg))
```

There's a subtle but important detail here: the departure time is the **agent's local clock**, not the simulation's global clock. This means if an agent just spent 3 ticks "computing" (its local clock is ahead), its outgoing messages depart from that advanced timestamp. The agent is penalized for being slow—just like in real HFT.

### The Computational Delay Mechanism

This led me to implement something I'm particularly proud of: the **temporal blocking** mechanism in `Kernel.step()`. After an agent processes any event, its local clock advances by a `computation_delay`. If a new event arrives _before_ the agent has "finished thinking," the event is deferred:

```python
def step(self):
    when, seq, msg = heapq.heappop(self._events)
    self.time = when

    # Is the agent still "busy" from a previous action?
    agent_time = self.agent_current_times.get(msg.dst, 0)
    if agent_time > when:
        # Agent hasn't caught up yet — re-enqueue for later
        heapq.heappush(self._events, (agent_time, seq, msg))
        return True

    self.agent_current_times[msg.dst] = when

    if msg.kind == "WAKEUP":
        agent.wakeup(self.time)
    else:
        agent.receive(msg)

    # Advance agent's local clock (computation penalty)
    delay = self.agent_computation_delays.get(msg.dst, 1)
    self.agent_current_times[msg.dst] += delay
```

This creates a beautifully realistic dynamic: a "slow" agent (high computation delay) literally misses market events while processing:

```
Global Timeline
──────────────────────────────────────────────►
t=100        t=103     t=104        t=107

Agent A (delay=1):
  ▓░░░░░▓░░░░░▓░░░░░
  act   act   act         ← fast, catches everything

Agent B (delay=3):
  ▓▓▓▓▓▓░░░░░░▓▓▓▓▓▓
  act (busy...)  act      ← slow, events at t=103 & t=104 deferred!
```

When I ran the first simulation with this in place, I could actually see slower agents making worse decisions because they were trading on stale information. It felt _right_.

### Tracking VWAP and Realized PnL

With multiple agents trading continuously, I needed a way to track each agent's performance accurately. I implemented VWAP (Volume Weighted Average Price) tracking directly in the `HeuristicAgent` base class, so every agent automatically gets it:

$$
\text{VWAP}_{\text{new}} = \frac{\text{VWAP}_{\text{old}} \times |Q_{\text{old}}| + P_{\text{trade}} \times |Q_{\text{trade}}|}{|Q_{\text{old}}| + |Q_{\text{trade}}|}
$$

And when closing a position:

$$
\text{PnL}_{\text{realized}} = Q_{\text{closing}} \times (P_{\text{exit}} - \text{VWAP})
$$

```python
def handle_execution(self, msg):
    qty = int(msg.data.get("qty", 0))
    price = float(msg.data.get("price", 0.0))
    side = msg.data.get("side", "BUY")
    trade_qty = qty if side == "BUY" else -qty

    if (self.position > 0 and trade_qty < 0) or \
       (self.position < 0 and trade_qty > 0):
        # Closing (or partially closing) a position
        closing_qty = min(abs(self.position), abs(trade_qty))

        if self.position > 0:
            self.realized_pnl += closing_qty * (price - self.vwap)
        else:
            self.realized_pnl += closing_qty * (self.vwap - price)

        if abs(trade_qty) > abs(self.position):
            self.vwap = price   # Flipped sides — new entry price
        elif abs(trade_qty) == abs(self.position):
            self.vwap = 0.0     # Flat — reset
    else:
        # Increasing position — update rolling VWAP
        new_total = abs(self.position) + abs(trade_qty)
        if new_total > 0:
            self.vwap = (
                (self.vwap * abs(self.position)) + (price * abs(trade_qty))
            ) / new_total

    self.position += trade_qty
    self.cash -= trade_qty * price
```

This was the version where the simulator started to _feel_ like a real trading system. Agents woke up at random times, messages traveled with latency, computations cost time, and I could track every agent's P&L accurately. But there was a massive design flaw I hadn't addressed yet.

---

## 4. v0.1.4 — Phase 1: Formalizing Agents and Deleting Direct Access

### The Omniscience Problem

Here's a confession: in my early versions, agents could directly access the exchange's internal state. A market maker could literally call `self.exchange.bids` and see the entire order book instantly, with zero latency, at any time. Every agent was effectively omniscient.

This is the kind of shortcut that feels harmless during prototyping but completely undermines the simulation's validity. In real markets, the _information asymmetry_ between participants is one of the most important dynamics. A market maker doesn't have instant access to the exchange's memory. They receive data feeds with delays, they pay for faster connections, and they never see the full internal state.

The day I deleted all direct exchange references from the agents was painful. Half my codebase broke. But it was the right decision.

### The Request-Response Protocol

I replaced direct access with an asynchronous message-passing protocol. Agents must now explicitly request data from the exchange and wait for a response:

```
┌──────────┐                        ┌──────────────┐
│  Agent   │  ── QUERY_MKT_DATA ──► │   Exchange   │
│          │                        │              │
│ state:   │  ◄──── MKT_DATA ────── │  _bids, _asks│
│ AWAITING │      (with latency!)   │  last_trade  │
│  _DATA   │                        └──────────────┘
│          │
│ state:   │
│ ACTIVE   │──► NOW make trading decision
└──────────┘
```

The exchange handles three query types:

```python
def receive(self, msg):
    if msg.kind == "NEW_ORDER":
        self._handle_new_order(msg)
    elif msg.kind == "CANCEL_ORDER":
        self._handle_cancel(msg)
    elif msg.kind == "QUERY_MKT_DATA":
        self._handle_query_mkt_data(msg)
    elif msg.kind == "QUERY_SPREAD":
        self._handle_query_spread(msg)
    elif msg.kind == "QUERY_LAST_TRADE":
        self._handle_query_last_trade(msg)
```

And the response travels through the Kernel—with stochastic latency, just like any other message:

```python
def _handle_query_mkt_data(self, msg):
    best_bid = self.bids[0].price if self.bids else None
    best_ask = self.asks[0].price if self.asks else None
    self.kernel.send(
        self.agent_id, msg.src, "MKT_DATA",
        {
            "best_bid": best_bid,
            "best_ask": best_ask,
            "last_trade": self.last_trade
        }
    )
```

### The Agent State Machine

This architectural change forced every agent to become _asynchronous_. An agent can't just query the exchange and immediately use the data—the response arrives later, in a completely separate method call. I solved this with a simple two-state machine:

```python
def wakeup(self, now):
    if self.state == "AWAITING_DATA":
        return  # Still waiting for exchange response, ignore this wakeup
    self.state = "AWAITING_DATA"
    self.kernel.send(self.agent_id, self.exchange_id, "QUERY_MKT_DATA", {})

def receive(self, msg):
    if msg.kind == "MKT_DATA" and self.state == "AWAITING_DATA":
        self.state = "ACTIVE"
        # NOW I have data and can trade
        self._make_trading_decision(msg.data)
```

```
Agent State Machine
═══════════════════

  ┌──────────┐  wakeup()    ┌────────────────┐
  │  ACTIVE  │─────────────►│ AWAITING_DATA  │
  │          │  send QUERY  │                │
  └──────────┘              └───────┬────────┘
       ▲                            │
       │    receive(MKT_DATA)       │
       └────────────────────────────┘
              act on data
```

This pattern is now universal across every agent in the simulator. It's a small state machine, but it enforces a fundamentally important property: **agents can only act on information they've explicitly requested and waited for**.

### Fixing Cancellation Security

While refactoring the exchange, I noticed another problem: any agent could cancel any order, regardless of who placed it. In a real exchange, you can only cancel your own orders. The fix was a simple ownership check:

```python
def _handle_cancel(self, msg):
    agent_id = msg.src
    order_id = msg.data.get("order_id")

    if order_id is not None:
        order = self._order_map.get(order_id)
        if order is None:
            return
        # Reject if the caller doesn't own this order
        if order.agent_id != agent_id:
            self.kernel.log(
                f"EXCH: reject cancel order_id={order_id} "
                f"from agent={agent_id} (owner={order.agent_id})"
            )
            return
        self._remove_order(order_id)
```

Small change, big implications. Without this, a rogue RL agent could learn to manipulate the market by cancelling competitors' orders—a "strategy" that would never transfer to the real world.

### The Value Agent: My First Bayesian Filter

With the infrastructure solid, it was time to tackle **Phase 1: Agent Formalization** from our roadmap—replacing simple heuristic thresholds with formal economic models. The `ValueAgent` (our informed tracker) was the most intellectually rewarding part of this entire project. It maintains a Bayesian belief about the asset's fundamental value, which follows a mean-reverting Ornstein-Uhlenbeck process:

$$
r_{t+1} = r_t + \kappa \cdot (\bar{r} - r_t) + \epsilon_t, \quad \epsilon_t \sim \mathcal{N}(0, \sigma_s^2)
$$

Where:

- $\kappa$ = mean-reversion speed
- $\bar{r}$ = long-run fundamental value
- $\sigma_s$ = shock volatility

The agent doesn't observe $r_t$ directly. It receives a **noisy signal**:

$$
z_t = r_t + \eta_t, \quad \eta_t \sim \mathcal{N}(0, \sigma_n^2)
$$

To estimate the true fundamental from noisy observations, I implemented a **Kalman Filter**:

**Predict (Time Update):**

$$
\hat{r}_{t|t-1} = \hat{r}_{t-1} + \kappa(\bar{r} - \hat{r}_{t-1})
$$

$$
P_{t|t-1} = (1 - \kappa)^2 P_{t-1} + \sigma_s^2
$$

**Update (Measurement):**

$$
K_t = \frac{P_{t|t-1}}{P_{t|t-1} + \sigma_n^2}
$$

$$
\hat{r}_t = \hat{r}_{t|t-1} + K_t(z_t - \hat{r}_{t|t-1})
$$

$$
P_t = (1 - K_t) P_{t|t-1}
$$

Translating this into code was one of those moments where math and engineering converge perfectly:

```python
class ValueAgent(HeuristicAgent):
    def __init__(self, ..., kappa=0.05, sigma_s=0.5, sigma_n=1.0,
                 r_bar=100.0, theta=0.0, min_surplus=0.5, max_surplus=1.5):
        self.r_est = r_bar       # Current belief r̂
        self.r_var = sigma_s**2  # Current uncertainty P

    def updateEstimates(self, t: int, observation: float):
        """Bayesian update of fundamental value belief."""
        steps = t - self.last_update_time
        if steps > 0:
            # Time update — propagate belief forward
            for _ in range(steps):
                self.r_est += self.kappa * (self.r_bar - self.r_est)
                self.r_var = ((1 - self.kappa) ** 2) * self.r_var + self.sigma_s**2
            self.last_update_time = t

        # Measurement update — incorporate noisy observation
        K = self.r_var / (self.r_var + self.sigma_n**2)
        self.r_est = self.r_est + K * (observation - self.r_est)
        self.r_var = (1 - K) * self.r_var
```

The trading logic uses a **surplus model** from classical microstructure theory. The agent's valuation is its estimate plus a private benefit:

$$
V = \hat{r}_t + \theta
$$

And it requires a minimum surplus $R$ to trade:

- **Buy limit** at price $V - R$ (max willing to pay)
- **Sell limit** at price $V + R$ (min willing to accept)

```python
def receive(self, msg):
    if msg.kind == "MKT_DATA" and self.state == "AWAITING_DATA":
        self.state = "ACTIVE"
        now = self.kernel.time

        # 1. Observe noisy fundamental
        true_value = self.oracle.get_value(now)
        observation = true_value + self.rng.gauss(0, self.sigma_n)

        # 2. Bayesian belief update
        self.updateEstimates(now, observation)

        # 3. Valuation = belief + private benefit, with required surplus R
        v = self.r_est + self.theta
        R = self.rng.uniform(self.min_surplus, self.max_surplus)

        side = "BUY" if self.rng.random() < 0.5 else "SELL"
        if side == "BUY":
            price = round_to_tick(v - R)
        else:
            price = round_to_tick(v + R)

        order = {"order_type": "LIMIT", "side": side,
                 "qty": self.rng.randint(1, 10), "price": price}
        self.kernel.send(self.agent_id, self.exchange_id, "NEW_ORDER", order)
```

Watching the ValueAgent trade for the first time was mesmerizing. Its estimates converged toward the true fundamental value, and its limit orders clustered around that estimate with a surplus buffer. It was doing exactly what a rational, informed trader _should_ do.

### The Zero-Intelligence Agent: The Null Hypothesis

To validate that the Value Agent was actually doing something intelligent, I needed a controlled baseline. That's the role of the `ZeroIntelligenceAgent`—a trader that submits random limit orders constrained only by a private valuation:

$$
V_{\text{ZI}} = P_{\text{market}} + \theta, \quad \theta \sim \mathcal{N}(0, \sigma_\theta^2)
$$

```python
class ZeroIntelligenceAgent(HeuristicAgent):
    def receive(self, msg):
        if msg.kind == "MKT_DATA" and self.state == "AWAITING_DATA":
            self.state = "ACTIVE"
            market_price = msg.data.get("last_trade", self.base_value)

            theta = self.rng.gauss(0, self.theta_std)
            v = market_price + theta
            R = self.rng.uniform(self.min_surplus, self.max_surplus)

            side = "BUY" if self.rng.random() < 0.5 else "SELL"
            price = round_to_tick(v - R) if side == "BUY" else round_to_tick(v + R)

            order = {"order_type": "LIMIT", "side": side,
                     "qty": self.rng.randint(1, 5), "price": price}
            self.kernel.send(self.agent_id, self.exchange_id, "NEW_ORDER", order)
```

The difference between the two agents is precisely the Kalman Filter. The ZI agent is anchored on the last market price (reactive). The Value agent maintains an evolving probabilistic model of fundamentals (predictive). Comparing their performance is a direct test of whether Bayesian estimation adds value in the simulation.

### The Adaptive Market Maker: Inventory Skew

Market makers face a dilemma I find endlessly fascinating: they _must_ quote both sides of the book to earn the spread, but doing so exposes them to inventory risk. If they accumulate too much long inventory, a price drop wipes them out.

My `AdaptiveMarketMakerAgent` handles this with a **sigmoid-based inventory skew**. The core idea: as inventory grows, asymmetrically increase the size on the side that reduces exposure.

$$
\sigma_{\text{sell}} = \frac{1}{1 + e^{-\beta \cdot Q}}
$$

Where $Q$ is the current position and $\beta$ controls sensitivity:

```python
def sigmoid(x: float, beta: float) -> float:
    try:
        return 1.0 / (1.0 + math.exp(-beta * x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0
```

The allocation logic:

```python
qty = self.min_order_size * 2
proportion_sell = sigmoid(self.position, self.skew_beta)
sell_size = math.ceil(proportion_sell * qty)
buy_size  = math.floor((1 - proportion_sell) * qty)
```

```
Sigmoid Inventory Skew (β = 0.05)
──────────────────────────────────

sell %  │
  100%  │                          ●●●●●●
        │                     ●●●●
   75%  │                 ●●●
        │              ●●●
   50%  │ ─ ─ ─ ─ ─ ●● ─ ─ ─ ─ ─ ─ ─ ─   ← neutral
        │          ●●
   25%  │       ●●●
        │    ●●●
    0%  │●●●●
        └──────────────────────────────────
         -40  -20   0   +20  +40
                Inventory Q
```

When position is zero, the market maker quotes symmetrically. At +30 inventory, it aggressively skews sell sizes up and buy sizes down. It's an elegant, continuous approach that avoids the jarring behavior of discrete "skew by one tick" strategies.

The Adaptive MM also uses the Chakraborty-Kearns ladder strategy, placing orders at multiple price levels around the midpoint:

```python
def handle_mkt_data(self, msg):
    # ... cancel previous orders, compute mid ...

    # Anchor the ladder around the midpoint
    highest_bid = round_to_tick(mid - (0.5 * self.window_size))
    lowest_ask  = round_to_tick(mid + (0.5 * self.window_size))

    lowest_bid  = round_to_tick(highest_bid - (self.num_ticks * self.tick_increment))
    highest_ask = round_to_tick(lowest_ask  + (self.num_ticks * self.tick_increment))

    # Place bid ladder (skewed by inventory)
    current_bid = highest_bid
    while current_bid >= lowest_bid:
        self.kernel.send(self.agent_id, self.exchange_id, "NEW_ORDER",
            {"order_type": "LIMIT", "side": "BUY",
             "qty": self.buy_order_size, "price": current_bid})
        current_bid -= self.tick_increment
        current_bid = round_to_tick(current_bid)

    # Place ask ladder (skewed by inventory)
    current_ask = lowest_ask
    while current_ask <= highest_ask:
        self.kernel.send(self.agent_id, self.exchange_id, "NEW_ORDER",
            {"order_type": "LIMIT", "side": "SELL",
             "qty": self.sell_order_size, "price": current_ask})
        current_ask += self.tick_increment
        current_ask = round_to_tick(current_ask)

    # Next wakeup: Poisson
    delta_time = self.rng.expovariate(self.lambda_a)
    self.kernel.wakeup(self.agent_id, now + max(1, int(delta_time)))
```

### The Liquidity Trader: Urgency Under Pressure

Also as planned in Phase 1, the `LiquidityTrader` models institutional execution constraint by a quadratic risk penalty $\phi$. It must acquire $Q$ units by a deadline $T$, balancing execution quality against the risk of not completing. I modeled urgency as:

$$
\text{urgency} = \min\left(1.0,\ \left(1 - \frac{t_{\text{remaining}}}{T}\right) + \phi \cdot \frac{Q_{\text{remaining}}}{Q_{\text{target}}}\right)
$$

Where $\phi$ is an inventory risk penalty. As time runs out and remaining quantity stays high, urgency approaches 1.0 and the agent switches from limit orders to market orders:

```python
time_fraction = remaining_time / self.deadline
risk_penalty = self.phi * (self.remaining_qty / self.target_qty)
urgency = min(1.0, (1.0 - time_fraction) + risk_penalty)

if self.rng.random() < urgency * 0.6:
    # Desperate: use market order
    order = {"order_type": "MARKET", "side": self.side, "qty": qty}
else:
    # Patient: use limit order near mid
    offset = self.rng.uniform(0.0, 0.5)
    price = round_to_tick(mid - offset) if self.side == "BUY" \
            else round_to_tick(mid + offset)
    order = {"order_type": "LIMIT", "side": self.side,
             "qty": qty, "price": price}
```

Watching a liquidity trader panic-buy with market orders in the final 10% of its deadline while a calm market maker picks off the spread on the other side—that's when I knew the simulator was capturing something real.

---

## 5. v0.1.5 — When the Terminal Couldn't Keep Up

### Hitting the Rendering Wall

By this point, the simulation backend was running at thousands of ticks per second with dozens of agents trading asynchronously. The problem was no longer the engine—it was the _visualization_. I was using `Textual`, a Python TUI framework, to render the order book and basic charts in the terminal. It worked, but it couldn't keep up.

Rendering a LOB heatmap as ASCII art at 5 FPS while the backend runs at 1000+ ticks/second is futile. I needed something that could actually handle high-frequency graphical updates.

### The DearPyGui Migration

After evaluating Dash, Streamlit, PyQt, and a full-stack web approach, I chose **DearPyGui (DPG)**. It's a Python wrapper around Dear ImGui, with a C++ rendering backend. The performance difference was night and day:

| Feature           | Textual (old)         | DearPyGui (new)        |
| ----------------- | --------------------- | ---------------------- |
| Rendering backend | Python terminal codes | C++ / GPU              |
| Refresh rate      | ~5-10 FPS             | 60+ FPS                |
| Chart types       | ASCII art             | Native plots, heatmaps |
| Interaction       | Keyboard-only         | Mouse + keyboard       |

### The LOB Heatmap: From Scatter to Continuous

The LOB heatmap—a visualization of order density across price levels over time—was the main reason I needed a better rendering stack. My original implementation plotted each order as a discrete point, creating a sparse scatter plot that was hard to interpret:

```
OLD (Scatter/Discrete)              NEW (Continuous Heatmap)

Price │  ·  ·    ·                  Price │████████░░░░░░░
      │    ·  ·  · ·                     │███████████░░░░
      │  ·  ·· ·                         │██████████████░
      │ ·   · ·    ·                     │███████████████
      │·  · ·  ·                         │█████████░░░░░░
      └──────────────                    └──────────────
             Time                               Time
```

The new DPG implementation allowed me to compute continuous density fields and render them as proper heatmaps. I added X-axis preset buttons (100, 500, 1000 intervals) for quick zoom levels.

### The Ghost Trail Bug

One frustrating bug in the initial DPG version: the heatmap would accumulate "ghost trails" from previous render states. Old data wasn't being fully cleared before the new frame was drawn, creating overlapping artifacts. The fix was ensuring complete buffer invalidation on each render cycle—a classic double-buffering oversight.

### The Dashboard Layout

With DPG's flexibility, I built a proper multi-tab dashboard:

```
┌─────────────────────────────────────────────────┐
│            Dashboard – Order Book                │
├──────────┬──────────┬──────────┬────────────────┤
│  Bid Qty │ Bid Px   │ Ask Px   │ Ask Qty        │
├──────────┼──────────┼──────────┼────────────────┤
│     150  │  99.97   │ 100.03   │   120          │  ◄ BBO
│     200  │  99.96   │ 100.04   │    85          │
│      75  │  99.95   │ 100.05   │   210          │
│     310  │  99.94   │ 100.06   │    45          │
│     180  │  99.93   │ 100.07   │   160          │
│      90  │  99.92   │ 100.08   │    95          │
│     ...  │  ...     │  ...     │   ...          │
├──────────┴──────────┴──────────┴────────────────┤
│  Tabs: [Dashboard] [LOB Heatmap] [Agent Tracker]│
└─────────────────────────────────────────────────┘
```

Best Bid and Best Ask always pinned at the top. Column alignment matching Bloomberg/Reuters conventions. Configurable depth. It's not flashy, but it lets me read the market at a glance while the simulation runs—which is exactly what I needed for debugging agent behavior.

---

## 6. Where It Stands Now

Four versions in, here's what the complete architecture looks like:

```
┌─────────────────────────────────────────────────────────────────┐
│                        KERNEL (Event Loop)                       │
│  ┌──────────┐  ┌──────────────────────────────────────────────┐ │
│  │ Event    │  │  Per-Agent State                             │ │
│  │ Priority │  │  • agent_current_times[id] → local clock    │ │
│  │ Queue    │  │  • agent_computation_delays[id] → cost      │ │
│  │ (heap)   │  │  • latency[(src,dst)] → base network delay  │ │
│  └──────────┘  └──────────────────────────────────────────────┘ │
│         │                    ▲                                   │
│    step()                send()                                  │
│         │         (+ stochastic jitter)                          │
│         ▼                    │                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                     MESSAGE BUS                            │  │
│  │  NEW_ORDER │ CANCEL_ORDER │ EXECUTION │ ORDER_ACCEPTED     │  │
│  │  QUERY_MKT_DATA │ QUERY_SPREAD │ MKT_DATA │ WAKEUP        │  │
│  └────────────────────────────────────────────────────────────┘  │
│         │              │              │               │          │
│    ┌────▼────┐   ┌─────▼─────┐  ┌────▼─────┐  ┌─────▼────┐    │
│    │Exchange │   │  Value    │  │ Adaptive │  │Liquidity │    │
│    │  Agent  │   │  Agent   │  │    MM    │  │ Trader   │    │
│    │         │   │(Bayesian)│  │(Sigmoid) │  │ (TWAP)   │    │
│    │ _bids   │   │ Kalman   │  │ Skew β   │  │ Urgency  │    │
│    │ _asks   │   │ Filter   │  │          │  │ φ-risk   │    │
│    │ _match  │   └──────────┘  └──────────┘  └──────────┘    │
│    └─────────┘         │              │              │         │
│                   ┌────▼──────────────▼──────────────▼───┐     │
│                   │          Oracle (r_t generator)       │     │
│                   └──────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   DearPyGui GUI    │
                    │  • Order Book      │
                    │  • LOB Heatmap     │
                    │  • Agent Tracker   │
                    └────────────────────┘
```

Here's a summary of what each version contributed:

| Version | Theme                   | What I Built                                                                                                    |
| ------- | ----------------------- | --------------------------------------------------------------------------------------------------------------- |
| v0.1.2  | **Determinism**         | Heap tie-breaking, O(1) cancel map, Agent ABC hierarchy                                                         |
| v0.1.3  | **Temporal Realism**    | Poisson arrivals, stochastic latency, computational delays, VWAP                                                |
| v0.1.4  | **Information Opacity** | Request-Response protocol, Phase 1 Agent Formalization (Kalman, Urgency), state machines, cancellation security |
| v0.1.5  | **Visualization**       | DearPyGui migration, continuous LOB heatmap, real-time order book display                                       |

---

## 7. What's Next: The RL Interface

The architecture is deliberately designed for what comes next in our roadmap (**Phase 2: RL Interface**): **reinforcement learning agents**. The `Agent` ABC already exposes `get_observation()` and `get_reward()`—abstract methods waiting for a real implementation.

When I drop in a PPO or SAC algorithm via a Gymnasium Wrapper, the agent will inherit from `Agent` directly, receive the same async messages through the same Kernel, and trade against the formal heuristic population I've spent four versions building and hardening.

That's the whole point of this rebuild. I didn't fork ABIDES to add a feature. I _reconstructed_ it from first principles so that every component—from the heap tuple format to the Kalman gain equation—is something I understand deeply enough to explain, debug, and extend.

The matching engine is hardened. The heuristic agents are formalized. The visualization is live.

Now that the simulator is robust, we are ready to build the Gymnasium environment. _Stay tuned for Part 3, where we will bridge this discrete-event system with standard Deep RL libraries._
