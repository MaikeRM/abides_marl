# Changelog

## v0.1.1 (2026-02-14)


### Added

#### Real-time TUI Dashboard
- **Price Chart**: Live line chart of asset prices using `plotext`.
- **Order Book**: Dynamic view of Bids and Asks.
- **Tape**: Rolling history of executed trades.
- **Logs**: Tabbed view to inspect simulation kernel logs.
- **Controls**:
  - `SPACE`: Step/Pause/Resume.
  - `S`: Start/Stop auto-run.
  - `R`: Reset simulation.
  - `Q`: Quit.

#### Discrete Event Kernel (`app/core/kernel.py`)
- **Priority Queue**: Uses `heapq` for efficient event scheduling.
- **Agent Registry**: Dynamic registration of agents with unique IDs.
- **Event History**: Maintains rolling window of 1000 events for debugging.
- **Latency Simulation**: Configurable network delay between agents.
- **Message Types**:
  - `NEW_ORDER`: Submit limit or market orders.
  - `CANCEL_ORDER`: Cancel orders by ID or cancel all from agent.
  - `ORDER_ACCEPTED`: Confirmation from exchange.
  - `ORDER_CANCELLED`: Confirmation of cancellation.
  - `EXECUTION`: Trade execution notification.
  - `WAKEUP`: Agent wakeup signal.
  - `LOG`: Internal logging events.

#### Exchange Agent (`app/agents/exchange.py`)
- **Continuous Double Auction**: Price-time priority matching.
- **Order Types**: LIMIT and MARKET orders supported.
- **Order Book**: Separate bid/ask books with dynamic updates.
- **Trade History**: Rolling window of 100 recent trades.
- **Notifications**: Sends ORDER_ACCEPTED, ORDER_CANCELLED, and EXECUTION messages.

#### Market Maker Agent (`app/agents/market_maker.py`)
- **Symmetric Quotes**: Posts bid/ask around mid-price.
- **Inventory Skew**: Adjusts quotes based on current position (0.02 per unit).
- **Cancel & Repost**: Cancels all orders before placing new ones.
- **Configurable Parameters**: spread, order_qty, max_inventory, wake_interval.

#### Informed Trader (`app/agents/informed.py`)
- **Oracle Access**: Uses price oracle to predict future fundamental value.
- **Directional Trading**: Buys when above fundamental, sells when below.
- **Noise Component**: Adds random component to trading decisions.

#### Liquidity Trader (`app/agents/liquidity.py`)
- **TWAP Strategy**: Executes target quantity over deadline.
- **Increasing Urgency**: Linearly increases order size over time.
- **Side Support**: Can be configured for BUY or SELL.

#### Noise Trader (`app/agents/noise.py`)
- **Random Trading**: Generates random buy/sell orders.
- **Liquidity Provision**: Adds randomness to market.

#### Oracle (`app/core/oracle.py`)
- **Mean-Reverting Process**: Fundamental value follows Ornstein-Uhlenbeck process.
- **Parameters**: r_bar (long-term mean), kappa (mean-reversion speed), sigma (volatility).

#### Simulation Runner (`app/core/runner.py`)
- **Default Configuration**:
  - 5 Market Makers (spread 0.80-1.60)
  - 10 Informed Traders
  - 1 Liquidity Trader (BUY side)
  - 20 Noise Traders
- **Latency**: Random delay 1-10 ticks between agents.
- **State Extraction**: Provides simplified state for UI rendering.

#### Type Definitions (`app/models/types.py`)
- **Message**: Inter-agent communication (src, dst, kind, data).
- **Order**: Order representation (order_id, agent_id, side, price, qty, ts).
- **Trade**: Trade record (price, qty, buyer_id, seller_id, ts, aggressor_side).

### Fixed

- Addressed `AttributeError` related to `is_running` property conflict in Textual App.

### Created Structure

The following directory structure was created for the new Textual-based TUI:

```
app/
├── main.py                 # Main entry point with Textual TUI
├── agents/
│   ├── base.py             # Base Agent class (interface)
│   ├── exchange.py         # Exchange agent (order matching engine)
│   ├── informed.py         # Informed trader (oracle-based)
│   ├── liquidity.py        # Liquidity trader (TWAP)
│   ├── market_maker.py     # Market maker (symmetric quotes + inventory skew)
│   └── noise.py           # Noise trader (random)
├── core/
│   ├── constants.py       # Simulation constants (tick size)
│   ├── kernel.py          # Discrete event kernel (heapq-based scheduler)
│   ├── oracle.py          # Price oracle (Ornstein-Uhlenbeck process)
│   └── runner.py          # Simulation runner (agent orchestration)
└── models/
    └── types.py           # Type definitions (Message, Order, Trade)
```

### Modified Files

- **README.md**: Updated to reflect v0.1.1 with Textual TUI changes.
- **pyproject.toml**: Updated dependencies (removed FastAPI/uvicorn, added textual).
- **v010_abides_poc.py**: Legacy file kept for reference (superseded by app/).

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     SimulationApp (Textual TUI)             │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ PriceChart  │  │  OrderBook   │  │   Trades Tape     │  │
│  │  (plotext)  │  │  (DataTable) │  │   (DataTable)    │  │
│  └─────────────┘  └──────────────┘  └───────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │               Events Log (DataTable)                 │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    SimulationRunner                         │
│  ┌────────────┐  ┌────────────┐  ┌───────────────────────┐ │
│  │   Kernel   │  │  Oracle    │  │  Exchange Agent       │ │
│  │ (Scheduler)│  │ (r_bar)    │  │  (Order Matching)    │ │
│  └────────────┘  └────────────┘  └───────────────────────┘ │
│                              │                              │
│         ┌────────────────────┼────────────────────┐        │
│         ▼                    ▼                    ▼        │
│  ┌─────────────┐      ┌─────────────┐      ┌───────────┐   │
│  │ MarketMaker│      │InformedTrader│     │NoiseTrader│   │
│  └─────────────┘      └─────────────┘      └───────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Key Features

1. **Event-Driven Architecture**: All agents communicate via asynchronous messages.
2. **Real-time Visualization**: 10 FPS update rate with 20 simulation steps per tick.
3. **Flexible Agent System**: Easy to add new agent types by extending Agent base class.
4. **Configurable Latency**: Network delay simulation between agents.
5. **Comprehensive Logging**: Event history for debugging and analysis.
