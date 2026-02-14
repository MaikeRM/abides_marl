# Multi-Agent Market Simulator (ABIDES-MARL Implementation)

This project implements a Proof of Concept (PoC) for a high-fidelity multi-agent market simulation environment, based on the ABIDES research papers. The goal is to facilitate Multi-Agent Reinforcement Learning (MARL) research in financial markets.

**References:**

- _ABIDES: Towards High-Fidelity Multi-Agent Market Simulation_ (Byrd et al. 2020)
- _ABIDES-MARL: A Multi-Agent Reinforcement Learning Environment_ (Nov 2025)

---

## Current Status: v0.1.0 (Proof of Concept)

The current version (`v010_abides_poc.py`) implements the core **DEMAS (Discrete Event Multi-Agent Simulation) architecture** and the fundamental components required for a functional market simulation. The Reinforcement Learning layer is currently in development.

### Implemented Features

Based on the analysis in `changelog/v010_analise_abides_marl.md`:

1.  **Discrete Event Kernel**
    - Priority queue (`heapq`) for event management.
    - Agent registry and wakeup scheduling mechanisms.
    - Message passing system with simulated asymmetric latency between agent pairs.

2.  **Exchange & Matching Engine**
    - Full **Limit Order Book (LOB)** with Bid/Ask sides.
    - Price-Time Priority matching algorithm.
    - Support for LIMIT and MARKET orders, as well as order cancellation.
    - Trade tape history and discrete tick size enforcement.

3.  **Fundamental Value Oracle**
    - **Ornstein-Uhlenbeck (OU)** process simulating the fundamental asset value.
    - Configurable parameters: long-term mean (`r_bar`), mean reversion speed (`kappa`), and volatility (`sigma`).

4.  **Agents (Heuristic Implementations)**
    - **Noise Trader**: Generates exogenous random order flow.
    - **Informed Trader**: Observes fundamental value (with noise) and trades on significant distortions.
    - **Market Maker**: Provides liquidity on both sides of the book (symmetric spread + inventory skew).
    - **Liquidity Trader**: Executes a target quantity using a TWAP strategy with increasing urgency.

5.  **Visualization (TUI)**
    - Terminal-based interface (Bloomberg style) displaying the LOB, trade tape, and agent positions in real-time.

---

## Gap Analysis

Relative to the **ABIDES-MARL** paper, version v0.1.0 is approximately **54% complete**. The primary missing components are:

- **RL Framework**: No integration with OpenAI Gym/PettingZoo or PPO training implementation.
- **Formal Kyle Model**: Agents currently use simple heuristics rather than the optimal equilibrium formulations (beta, lambda, etc.) described in the literature.
- **Pro-Rata Mechanism**: The exchange currently utilizes a classic Continuous Double Auction instead of the pro-rata mechanism for Market Makers.

---

## Execution

### Prerequisites

- Python 3.8+
- No heavy external dependencies (standard libraries + `curses` for TUI).

### Running the Simulation

To execute the simulation with the real-time terminal visualization:

```bash
python3 simple_abides_poc.py
```

Runtime display includes:

- **Order Book**: Market depth (Bids/Asks).
- **Tape**: Recent trade executions.
- **Agents**: Position, cash, and Mark-to-Market (MtM) for each agent.

To run in headless mode (final results only):

```bash
python3 -c "import simple_abides_poc as s; s.run_demo(visualize=False)"
```

---

## Roadmap

### Phase 1: Agent Formalization (v0.2.0)

- Implement **Informed Trader** with Kyle model (`beta`).
- Refine **Market Maker** to use flow-based pricing (`lambda`).
- Add inventory risk penalty (`phi`) to **Liquidity Trader**.

### Phase 2: RL Interface (v0.3.0)

- Create **StopSignalAgent** for synchronization.
- Implement wrappers for **Gymnasium** and **PettingZoo**.
- Define formal observation and action spaces.

### Phase 3: MARL Training (v0.4.0)

- Integration with **Stable-Baselines3** or **RLlib**.
- Training with **Independent PPO (IPPO)**.
- Validation of price convergence and discovery.

---

## Project Structure

- `simple_abides_poc.py`: Single source file containing the v0.1.0 implementation (Kernel, Agents, Exchange, TUI).
- `changelog/`: Detailed documentation of analyses and version changes.
- `papers/`: Theoretical references (ABIDES PDFs).
