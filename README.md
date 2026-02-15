# Multi-Agent Market Simulator (ABIDES-MARL Implementation)

This project implements a Proof of Concept (PoC) for a high-fidelity multi-agent market simulation environment, based on the ABIDES research papers. The goal is to facilitate Multi-Agent Reinforcement Learning (MARL) research in financial markets.

**References:**

- _ABIDES: Towards High-Fidelity Multi-Agent Market Simulation_ (Byrd et al. 2020)
- _ABIDES-MARL: A Multi-Agent Reinforcement Learning Environment_ (Nov 2025)

---

## Current Status: v0.1.1 (Textual TUI)

The current version (`app/main.py`) implements the core **DEMAS (Discrete Event Multi-Agent Simulation) architecture** with a modern **Textual-based TUI**.

### Implemented Features

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

5.  **Visualization (Textual TUI)**
    - **Rich Terminal Interface**: Real-time dashboard with:
      - **Price Chart**: Live plotting of price history using `plotext`.
      - **Order Book**: Dynamic table showing top bid/ask levels.
      - **Trades Tape**: Rolling list of recent market executions.
      - **Market Stats**: Key metrics (Time, Last Price, Fundamental Value).
      - **Logs Tab**: Real-time inspection of kernel events and agent actions.

---

## Gap Analysis

Relative to the **ABIDES-MARL** paper, version v0.1.1 is approximately **55% complete**. The primary missing components are:

- **RL Framework**: No integration with OpenAI Gym/PettingZoo or PPO training implementation.
- **Formal Kyle Model**: Agents currently use simple heuristics rather than the optimal equilibrium formulations (beta, lambda, etc.) described in the literature.
- **Pro-Rata Mechanism**: The exchange currently utilizes a classic Continuous Double Auction instead of the pro-rata mechanism for Market Makers.

---

## Execution

### Prerequisites

- Python 3.12+
- Dependencies: `textual`, `textual-plotext`, `rich`, `plotext`.

### Running the Simulation

To execute the simulation with the new Textual TUI:

```bash
# Using uv (recommended)
uv run python -m app.main

# OR using standard python (after activating venv)
python -m app.main
```

### Controls

- **SPACE**: Step the simulation (or Pause/Resume if running).
- **S**: Start/Stop the continuous simulation.
- **R**: Reset the simulation.
- **Q**: Quit the application.

---

## Logs Tab: Column Definitions

The `Logs` table in the TUI is populated from `Kernel.event_history` (`app/core/kernel.py`) and rendered in `app/main.py`.

Important behavior:
- The UI filters out events where `phase == "LOG"` or `kind == "LOG"`.
- Because of this filter, textual `kernel.log(...)` rows are not shown in this table.

### Columns

| Column | Source in Event | Exact Meaning | Typical Values / Notes |
|---|---|---|---|
| `Timestamp` | `event["timestamp"]` | Wall-clock time when the event record was created (not simulation time). | Format `YYYY-MM-DD HH:MM:SS.mmm`. |
| `Sim Time` | `event["sim_time"]` | Discrete simulation clock time associated with this record. | Integer-like values (`t` in kernel). |
| `Phase` | `event["phase"]` | Lifecycle stage of the message/event. | `ENQUEUED` (scheduled) or `PROCESSED` (popped and delivered). |
| `Kind` | `event["kind"]` | Message type being scheduled/processed. | `NEW_ORDER`, `CANCEL_ORDER`, `ORDER_ACCEPTED`, `ORDER_CANCELLED`, `EXECUTION` (and `LOG`, `WAKEUP`, but filtered out). |
| `Seq` | `event["seq"]` | Global monotonic sequence number assigned on enqueue; also used as heap tie-breaker for equal delivery times. | Same message keeps same `seq` in both `ENQUEUED` and `PROCESSED` rows. |
| `Delivery` | `event["delivery"]` | Scheduled delivery simulation time for the message. | In `ENQUEUED`: future time (`current_time + latency` or explicit wakeup time). In `PROCESSED`: equals current processed time. |
| `Source` | `event["src_name"]` (fallback `src`) | Sender actor name/id. | Format `NAME(id)`, or `KERNEL` for id `-1`. |
| `Destination` | `event["dst_name"]` (fallback `dst`) | Receiver actor name/id. | Format `NAME(id)`, or `KERNEL` for id `-1`. |
| `Order Type` | `event["data"]["order_type"]` | Order type carried in message data. | Usually `LIMIT` or `MARKET`; empty when not applicable. |
| `Side` | `event["data"]["side"]` | Trade/order side in message data. | Usually `BUY` or `SELL`; empty when not applicable. |
| `Qty` | `event["data"]["qty"]` | Quantity in message data. | Integer quantity; empty when not applicable. |
| `Price` | `event["data"]["price"]` | Price in message data. | For limit/execution messages; empty when not applicable. |
| `Order ID` | `event["data"]["order_id"]` | Exchange-generated or referenced order identifier in message data. | Present in `ORDER_ACCEPTED`, `ORDER_CANCELLED`, and targeted cancels. |
| `Cancel All` | `event["data"]["cancel_all"]` | Boolean cancel-all flag from cancel requests. | `True`/`False` (stringified in UI); empty when not applicable. |
| `Text` | `event["data"]["text"]` | Free text payload for log records. | Normally empty in this table because `LOG` and `WAKEUP` events are filtered out by the UI. |

### Event Semantics

- `ENQUEUED`: created when `kernel.send(...)` or `kernel.wakeup(...)` places a message in the priority queue.
- `PROCESSED`: created when that queued message is popped from the queue and delivered to destination agent logic.

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
