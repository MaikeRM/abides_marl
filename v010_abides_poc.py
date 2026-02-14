from __future__ import annotations

import heapq
import random
import time
import curses
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Optional, List

# ─── Constants ───────────────────────────────────────────────────────────────

TICK_SIZE = 0.01  # Minimum price increment (discrete tick)


def round_to_tick(price: float) -> float:
    """Round price to the nearest tick."""
    return round(price / TICK_SIZE) * TICK_SIZE


# ─── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class Message:
    src: int
    dst: int
    kind: str
    data: dict


@dataclass
class Order:
    order_id: int
    agent_id: int
    side: str
    price: float
    qty: int
    ts: int


@dataclass
class Trade:
    price: float
    qty: int
    buyer_id: int
    seller_id: int
    ts: int
    aggressor_side: str


# ─── Oracle (Fundamental Value via Ornstein-Uhlenbeck) ───────────────────────

class Oracle:
    """
    Generates a fundamental value time series using an Ornstein-Uhlenbeck
    (mean-reverting) process. This is the "true" value of the asset.

    From the ABIDES paper:
    - r_bar: long-run mean (equilibrium price)
    - kappa: mean-reversion speed
    - sigma: volatility of the process
    """

    def __init__(self, r_bar=100.0, kappa=0.05, sigma=0.5, seed=42):
        self.r_bar = r_bar
        self.kappa = kappa
        self.sigma = sigma
        self.value = r_bar
        self.rng = random.Random(seed)
        self._last_t = 0

    def get_value(self, t: int) -> float:
        """Get fundamental value at time t (lazily advances from last query)."""
        steps = t - self._last_t
        if steps > 0:
            for _ in range(steps):
                self.value += self.kappa * (self.r_bar - self.value) + \
                              self.sigma * self.rng.gauss(0, 1)
            self._last_t = t
        return self.value


# ─── Kernel ──────────────────────────────────────────────────────────────────

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

    def log(self, text):
        self.logs.append(f"[t={self.time:04d}] {text}")

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
        heapq.heappush(self._events, (delivery, self._seq, msg))
        self._seq += 1

    def wakeup(self, agent_id, at_time):
        msg = Message(src=-1, dst=agent_id, kind="WAKEUP", data={})
        heapq.heappush(self._events, (int(at_time), self._seq, msg))
        self._seq += 1

    def step(self):
        if not self._events:
            self.running = False
            return False
        when, _, msg = heapq.heappop(self._events)
        self.time = when
        agent = self._agents[msg.dst]
        if msg.kind == "WAKEUP":
            agent.wakeup(self.time)
        else:
            agent.receive(msg)
        return True


# ─── Agent Base ──────────────────────────────────────────────────────────────

class Agent:
    def __init__(self, agent_id, name):
        self.agent_id = agent_id
        self.name = name
        self.kernel: Optional[Kernel] = None

    def wakeup(self, now):
        pass

    def receive(self, msg):
        pass


# ─── Exchange Agent ──────────────────────────────────────────────────────────

class ExchangeAgent(Agent):
    """
    Continuous Double Auction exchange with:
    - Price-time priority matching
    - LIMIT and MARKET order support
    - CANCEL_ORDER support (by order_id or cancel_all from agent)
    - ORDER_ACCEPTED notifications
    - Discrete tick sizes
    """

    def __init__(self, agent_id, name="EXCHANGE", start_price=100.0):
        super().__init__(agent_id, name)
        self.last_trade = float(start_price)
        self.order_id = 1
        self.bids: List[Order] = []
        self.asks: List[Order] = []
        self.history: List[Trade] = []

    def receive(self, msg):
        assert self.kernel is not None
        if msg.kind == "NEW_ORDER":
            self._handle_new_order(msg)
        elif msg.kind == "CANCEL_ORDER":
            self._handle_cancel(msg)

    def _handle_new_order(self, msg):
        side = msg.data["side"]
        qty = int(msg.data["qty"])
        order_type = msg.data.get("order_type", "LIMIT")

        if order_type == "MARKET":
            price = 1e9 if side == "BUY" else 0.0
        else:
            price = round_to_tick(float(msg.data["price"]))

        incoming = Order(
            order_id=self.order_id, agent_id=msg.src,
            side=side, price=price, qty=qty, ts=self.kernel.time,
        )
        self.order_id += 1

        shown_price = "MKT" if order_type == "MARKET" else f"{incoming.price:.2f}"
        src_name = self.kernel._agents[msg.src].name
        self.kernel.log(
            f"EXCH: {order_type} {side} qty={qty} px={shown_price} from {src_name}"
        )
        self._match(incoming)

    def _handle_cancel(self, msg):
        agent_id = msg.src
        order_id = msg.data.get("order_id")
        cancel_all = msg.data.get("cancel_all", False)
        cancelled = []

        if cancel_all:
            for book in [self.bids, self.asks]:
                to_remove = [o for o in book if o.agent_id == agent_id]
                for o in to_remove:
                    book.remove(o)
                    cancelled.append(o.order_id)
        elif order_id is not None:
            for book in [self.bids, self.asks]:
                for i, o in enumerate(book):
                    if o.order_id == order_id and o.agent_id == agent_id:
                        book.pop(i)
                        cancelled.append(order_id)
                        break

        for oid in cancelled:
            self.kernel.send(
                self.agent_id, agent_id, "ORDER_CANCELLED", {"order_id": oid}
            )

    def _book(self, side):
        return self.bids if side == "BUY" else self.asks

    def _opposite(self, side):
        return self.asks if side == "BUY" else self.bids

    def _best_index(self, orders, side):
        best_i = 0
        for i in range(1, len(orders)):
            a, b = orders[i], orders[best_i]
            if side == "BUY":
                if (a.price > b.price) or (a.price == b.price and a.ts < b.ts):
                    best_i = i
            else:
                if (a.price < b.price) or (a.price == b.price and a.ts < b.ts):
                    best_i = i
        return best_i

    def _crossed(self, incoming, resting):
        if incoming.side == "BUY":
            return incoming.price >= resting.price
        return incoming.price <= resting.price

    def _match(self, incoming):
        assert self.kernel is not None
        opp = self._opposite(incoming.side)

        while incoming.qty > 0 and opp:
            target_side = "SELL" if incoming.side == "BUY" else "BUY"
            j = self._best_index(opp, target_side)
            resting = opp[j]

            if not self._crossed(incoming, resting):
                break

            trade_qty = min(incoming.qty, resting.qty)
            trade_price = resting.price
            self.last_trade = trade_price

            buy_agent = incoming.agent_id if incoming.side == "BUY" else resting.agent_id
            sell_agent = incoming.agent_id if incoming.side == "SELL" else resting.agent_id

            trade = Trade(
                price=trade_price, qty=trade_qty,
                buyer_id=buy_agent, seller_id=sell_agent,
                ts=self.kernel.time, aggressor_side=incoming.side,
            )
            self.history.append(trade)
            if len(self.history) > 100:
                self.history.pop(0)

            self.kernel.send(
                self.agent_id, buy_agent, "EXECUTION",
                {"side": "BUY", "qty": trade_qty, "price": trade_price},
            )
            self.kernel.send(
                self.agent_id, sell_agent, "EXECUTION",
                {"side": "SELL", "qty": trade_qty, "price": trade_price},
            )

            b_name = self.kernel._agents[buy_agent].name
            s_name = self.kernel._agents[sell_agent].name
            self.kernel.log(
                f"TRADE px={trade_price:.2f} qty={trade_qty} ({b_name} ← {s_name})"
            )

            incoming.qty -= trade_qty
            resting.qty -= trade_qty
            if resting.qty == 0:
                opp.pop(j)

        # Remaining limit order → add to book + notify
        if incoming.qty > 0 and incoming.price not in (0.0, 1e9):
            self._book(incoming.side).append(incoming)
            self.kernel.send(
                self.agent_id, incoming.agent_id, "ORDER_ACCEPTED",
                {"order_id": incoming.order_id, "side": incoming.side,
                 "qty": incoming.qty, "price": incoming.price},
            )


# ─── Noise Trader (ZI-C like) ───────────────────────────────────────────────

class NoiseTrader(Agent):
    """
    Zero-Intelligence trader that generates random exogenous orders.
    Uses tick-aligned prices centered around current market mid.
    """

    def __init__(self, agent_id, exchange_id, seed, wake_interval=5):
        super().__init__(agent_id, f"NOISE_{agent_id}")
        self.exchange_id = exchange_id
        self.rng = random.Random(seed)
        self.wake_interval = wake_interval
        self.position = 0
        self.cash = 0.0

    def wakeup(self, now):
        assert self.kernel is not None
        exchange = self.kernel._agents[self.exchange_id]
        mid = exchange.last_trade

        side = "BUY" if self.rng.random() < 0.5 else "SELL"
        qty = self.rng.randint(1, 5)

        if self.rng.random() < 0.15:
            order = {"order_type": "MARKET", "side": side, "qty": qty}
        else:
            offset = self.rng.uniform(0.0, 3.0)
            if side == "BUY":
                price = round_to_tick(mid - offset)
            else:
                price = round_to_tick(mid + offset)
            order = {"order_type": "LIMIT", "side": side, "qty": qty, "price": price}

        self.kernel.send(self.agent_id, self.exchange_id, "NEW_ORDER", order)
        jitter = self.rng.randint(0, 3)
        self.kernel.wakeup(self.agent_id, now + self.wake_interval + jitter)

    def receive(self, msg):
        if msg.kind == "EXECUTION":
            qty = int(msg.data["qty"])
            price = float(msg.data["price"])
            if msg.data["side"] == "BUY":
                self.position += qty
                self.cash -= qty * price
            else:
                self.position -= qty
                self.cash += qty * price


# ─── Informed Trader ─────────────────────────────────────────────────────────

class InformedTrader(Agent):
    """
    Trades based on private information about the fundamental value.
    Observes the Oracle's value with noise and trades when the market
    price diverges significantly from the fundamental.

    From ABIDES-MARL: informed traders submit orders based on
    "alpha signals" that influence observed price updates.
    """

    def __init__(self, agent_id, exchange_id, oracle: Oracle, seed,
                 wake_interval=8, noise_std=1.0, threshold=0.5):
        super().__init__(agent_id, f"INFORMED_{agent_id}")
        self.exchange_id = exchange_id
        self.oracle = oracle
        self.rng = random.Random(seed)
        self.wake_interval = wake_interval
        self.noise_std = noise_std
        self.threshold = threshold
        self.position = 0
        self.cash = 0.0

    def wakeup(self, now):
        assert self.kernel is not None
        fundamental = self.oracle.get_value(now) + self.rng.gauss(0, self.noise_std)
        exchange = self.kernel._agents[self.exchange_id]
        market_price = exchange.last_trade
        diff = fundamental - market_price

        if abs(diff) > self.threshold:
            side = "BUY" if diff > 0 else "SELL"
            qty = max(1, min(10, int(abs(diff) * 2)))

            if side == "BUY":
                price = round_to_tick(market_price + abs(diff) * self.rng.uniform(0.3, 0.7))
            else:
                price = round_to_tick(market_price - abs(diff) * self.rng.uniform(0.3, 0.7))

            order = {"order_type": "LIMIT", "side": side, "qty": qty, "price": price}
            self.kernel.send(self.agent_id, self.exchange_id, "NEW_ORDER", order)

        jitter = self.rng.randint(0, 3)
        self.kernel.wakeup(self.agent_id, now + self.wake_interval + jitter)

    def receive(self, msg):
        if msg.kind == "EXECUTION":
            qty = int(msg.data["qty"])
            price = float(msg.data["price"])
            if msg.data["side"] == "BUY":
                self.position += qty
                self.cash -= qty * price
            else:
                self.position -= qty
                self.cash += qty * price


# ─── Market Maker ────────────────────────────────────────────────────────────

class MarketMakerAgent(Agent):
    """
    Posts symmetric bid/ask quotes around the mid-price with
    inventory-skewed adjustment. Cancels and reposts every wakeup.

    From ABIDES-MARL: market makers compete to quote prices and
    provide liquidity, balancing profit with inventory control.
    """

    def __init__(self, agent_id, exchange_id, seed, wake_interval=3,
                 spread=1.0, order_qty=5, max_inventory=50):
        super().__init__(agent_id, f"MM_{agent_id}")
        self.exchange_id = exchange_id
        self.rng = random.Random(seed)
        self.wake_interval = wake_interval
        self.spread = spread
        self.order_qty = order_qty
        self.max_inventory = max_inventory
        self.position = 0
        self.cash = 0.0
        self.active_order_ids: List[int] = []

    def wakeup(self, now):
        assert self.kernel is not None

        # Cancel all previous orders before reposting
        if self.active_order_ids:
            self.kernel.send(
                self.agent_id, self.exchange_id, "CANCEL_ORDER",
                {"cancel_all": True}
            )
            self.active_order_ids.clear()

        exchange = self.kernel._agents[self.exchange_id]
        mid = exchange.last_trade

        # Inventory skew: shift quotes to reduce exposure
        inventory_skew = -self.position * 0.02
        adjusted_mid = mid + inventory_skew
        half = self.spread / 2.0

        bid_price = round_to_tick(adjusted_mid - half)
        ask_price = round_to_tick(adjusted_mid + half)

        if self.position < self.max_inventory:
            self.kernel.send(
                self.agent_id, self.exchange_id, "NEW_ORDER",
                {"order_type": "LIMIT", "side": "BUY",
                 "qty": self.order_qty, "price": bid_price}
            )

        if self.position > -self.max_inventory:
            self.kernel.send(
                self.agent_id, self.exchange_id, "NEW_ORDER",
                {"order_type": "LIMIT", "side": "SELL",
                 "qty": self.order_qty, "price": ask_price}
            )

        jitter = self.rng.randint(0, 1)
        self.kernel.wakeup(self.agent_id, now + self.wake_interval + jitter)

    def receive(self, msg):
        if msg.kind == "EXECUTION":
            qty = int(msg.data["qty"])
            price = float(msg.data["price"])
            if msg.data["side"] == "BUY":
                self.position += qty
                self.cash -= qty * price
            else:
                self.position -= qty
                self.cash += qty * price
        elif msg.kind == "ORDER_ACCEPTED":
            self.active_order_ids.append(msg.data["order_id"])


# ─── Liquidity Trader ────────────────────────────────────────────────────────

class LiquidityTrader(Agent):
    """
    Has an execution goal: acquire (or sell) Q units by deadline T.
    Uses a TWAP-like strategy with increasing urgency near deadline.

    From ABIDES-MARL: the liquidity trader's optimization problem
    is embedded within the strategic trading environment.
    Observation: [t, last_price, remaining_qty]
    """

    def __init__(self, agent_id, exchange_id, seed, target_qty=100,
                 deadline=8000, wake_interval=20, side="BUY"):
        super().__init__(agent_id, f"LIQ_{agent_id}")
        self.exchange_id = exchange_id
        self.rng = random.Random(seed)
        self.target_qty = target_qty
        self.remaining_qty = target_qty
        self.deadline = deadline
        self.wake_interval = wake_interval
        self.side = side
        self.position = 0
        self.cash = 0.0

    def wakeup(self, now):
        assert self.kernel is not None
        if self.remaining_qty <= 0 or now >= self.deadline:
            return

        remaining_time = max(1, self.deadline - now)
        remaining_steps = max(1, remaining_time // self.wake_interval)
        qty = max(1, min(self.remaining_qty, self.remaining_qty // remaining_steps))

        urgency = 1.0 - (remaining_time / self.deadline)
        exchange = self.kernel._agents[self.exchange_id]
        mid = exchange.last_trade

        if self.rng.random() < urgency * 0.6:
            order = {"order_type": "MARKET", "side": self.side, "qty": qty}
        else:
            offset = self.rng.uniform(0.0, 0.5)
            if self.side == "BUY":
                price = round_to_tick(mid - offset)
            else:
                price = round_to_tick(mid + offset)
            order = {"order_type": "LIMIT", "side": self.side,
                     "qty": qty, "price": price}

        self.kernel.send(self.agent_id, self.exchange_id, "NEW_ORDER", order)
        jitter = self.rng.randint(0, 5)
        self.kernel.wakeup(self.agent_id, now + self.wake_interval + jitter)

    def receive(self, msg):
        if msg.kind == "EXECUTION":
            qty = int(msg.data["qty"])
            price = float(msg.data["price"])
            if msg.data["side"] == "BUY":
                self.position += qty
                self.cash -= qty * price
            else:
                self.position -= qty
                self.cash += qty * price
            self.remaining_qty -= qty


# Backward compatibility
RandomTrader = NoiseTrader


# ─── Visualization / TUI ────────────────────────────────────────────────────

def get_aggregated_book(orders, descending=True):
    levels = defaultdict(int)
    for o in orders:
        levels[o.price] += o.qty
    return sorted(levels.items(), key=lambda x: x[0], reverse=descending)


def _safe_addstr(stdscr, y, x, text, attr=0):
    """Write to screen ignoring out-of-bounds errors."""
    try:
        h, w = stdscr.getmaxyx()
        if 0 <= y < h and 0 <= x < w:
            stdscr.addstr(y, x, text[:w - x - 1], attr)
    except curses.error:
        pass


def draw_tui(stdscr, kernel, exchange, oracle, agents):
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)    # Bids / Buy
    curses.init_pair(2, curses.COLOR_RED, -1)      # Asks / Sell
    curses.init_pair(3, curses.COLOR_CYAN, -1)     # Headers
    curses.init_pair(4, curses.COLOR_YELLOW, -1)   # Info
    curses.init_pair(5, curses.COLOR_WHITE, -1)    # Default
    curses.init_pair(6, curses.COLOR_MAGENTA, -1)  # Oracle
    curses.curs_set(0)
    stdscr.nodelay(True)

    while kernel.running:
        for _ in range(5):
            if not kernel.step():
                break

        try:
            if stdscr.getch() == ord('q'):
                break
        except Exception:
            pass

        stdscr.erase()
        height, width = stdscr.getmaxyx()

        # ── Header ──
        fund = oracle.get_value(kernel.time)
        delta = exchange.last_trade - fund
        header = (f" ABIDES POC v0.1.0 │ t={kernel.time:05d} │ "
                  f"Last={exchange.last_trade:.2f} │ "
                  f"Fund={fund:.2f} │ Δ={delta:+.2f} ")
        _safe_addstr(stdscr, 0, 0, header, curses.color_pair(3) | curses.A_BOLD)
        _safe_addstr(stdscr, 1, 0, "═" * (width - 1))

        book_y = 2
        # ── Order Book ──
        _safe_addstr(stdscr, book_y, 2,
                     f"{'BID QTY':<10} {'BID PX':<10} │ {'ASK PX':>10} {'ASK QTY':>10}",
                     curses.color_pair(3))

        bids = get_aggregated_book(exchange.bids, descending=True)
        asks = get_aggregated_book(exchange.asks, descending=False)
        max_depth = max(3, height - book_y - 22)

        for i in range(min(max_depth, max(len(bids), len(asks)))):
            y = book_y + 1 + i
            if y >= height - 1:
                break
            if i < len(bids):
                px, qty = bids[i]
                _safe_addstr(stdscr, y, 2, f"{qty:<10} {px:<10.2f}", curses.color_pair(1))
            _safe_addstr(stdscr, y, 24, "│", curses.color_pair(5))
            if i < len(asks):
                px, qty = asks[i]
                _safe_addstr(stdscr, y, 26, f"{px:>10.2f} {qty:>10}", curses.color_pair(2))

        # ── Tape ──
        tape_x = width // 2
        _safe_addstr(stdscr, book_y, tape_x, "RECENT TRADES (TAPE)", curses.color_pair(3))
        _safe_addstr(stdscr, book_y + 1, tape_x,
                     f"{'TIME':<8} {'PRICE':<10} {'QTY':<8} {'SIDE'}", curses.color_pair(4))

        for i, trade in enumerate(reversed(exchange.history[-max_depth:])):
            y = book_y + 2 + i
            if y >= height - 18:
                break
            color = curses.color_pair(1) if trade.aggressor_side == "BUY" else curses.color_pair(2)
            _safe_addstr(stdscr, y, tape_x,
                         f"{trade.ts:<8} {trade.price:<10.2f} {trade.qty:<8} {trade.aggressor_side}",
                         color)

        # ── Agent Stats ──
        stats_y = height - 17
        _safe_addstr(stdscr, stats_y - 1, 0, "─" * (width - 1))
        
        # Header
        _safe_addstr(stdscr, stats_y - 1, 2, " AGENTS ", curses.color_pair(6))
        header_str = f" {'TYPE':<10} {'CNT':<5} {'POS':<8} {'CASH':<12} {'MtM':<12} {'EXTRA'}"
        _safe_addstr(stdscr, stats_y, 0, header_str, curses.color_pair(3))

        types = defaultdict(list)
        for a in agents:
            types[a.name.split("_")[0]].append(a)

        row = 1
        for tname, group in types.items():
            total_pos = sum(a.position for a in group)
            total_cash = sum(a.cash for a in group)
            total_mtm = sum(a.cash + a.position * exchange.last_trade for a in group)
            n = len(group)
            
            line = f" {tname:<10} {n:<5d} {total_pos:<8d} {total_cash:<12.1f} {total_mtm:<12.1f}"
            
            if tname == "LIQ":
                rem = sum(a.remaining_qty for a in group)
                line += f" rem={rem}"
                
            if stats_y + row < height - 11:
                _safe_addstr(stdscr, stats_y + row, 0, line, curses.color_pair(4))
            row += 1

        # ── Logs ──
        log_y = height - 10
        _safe_addstr(stdscr, log_y - 1, 0, "─" * (width - 1))
        _safe_addstr(stdscr, log_y - 1, 2, " SYSTEM LOGS ", curses.color_pair(3))

        for i, log in enumerate(list(kernel.logs)[-9:]):
            _safe_addstr(stdscr, log_y + i, 1, log, curses.color_pair(5))

        stdscr.refresh()
        time.sleep(0.05)


# ─── Demo ────────────────────────────────────────────────────────────────────

def run_demo(seed=42, end_time=10000):
    kernel = Kernel(seed=seed)
    oracle = Oracle(r_bar=100.0, kappa=0.05, sigma=0.5, seed=seed + 1000)
    exchange = ExchangeAgent(agent_id=0, start_price=100.0)
    kernel.register(exchange)

    agent_id = 1
    all_agents = []

    # 2 Market Makers (fast, tight spread)
    for i in range(2):
        mm = MarketMakerAgent(
            agent_id=agent_id, exchange_id=0, seed=seed + agent_id,
            wake_interval=3, spread=0.80 + i * 0.20, order_qty=5
        )
        kernel.register(mm)
        all_agents.append(mm)
        agent_id += 1

    # 3 Informed Traders (observe fundamental)
    for i in range(3):
        it = InformedTrader(
            agent_id=agent_id, exchange_id=0, oracle=oracle,
            seed=seed + agent_id, wake_interval=8, noise_std=0.5 + i * 0.3
        )
        kernel.register(it)
        all_agents.append(it)
        agent_id += 1

    # 1 Liquidity Trader (BUY)
    lt = LiquidityTrader(
        agent_id=agent_id, exchange_id=0, seed=seed + agent_id,
        target_qty=100, deadline=8000, wake_interval=15, side="BUY"
    )
    kernel.register(lt)
    all_agents.append(lt)
    agent_id += 1

    # 1 Liquidity Trader (SELL)
    lt2 = LiquidityTrader(
        agent_id=agent_id, exchange_id=0, seed=seed + agent_id,
        target_qty=80, deadline=8000, wake_interval=18, side="SELL"
    )
    kernel.register(lt2)
    all_agents.append(lt2)
    agent_id += 1

    # 12 Noise Traders (random / ZI)
    for i in range(12):
        nt = NoiseTrader(
            agent_id=agent_id, exchange_id=0,
            seed=seed + agent_id, wake_interval=5
        )
        kernel.register(nt)
        all_agents.append(nt)
        agent_id += 1

    # Set latencies
    n = agent_id
    for src in range(n):
        for dst in range(n):
            if src != dst:
                kernel.set_latency(src, dst, kernel.rng.randint(1, 10))
            else:
                kernel.set_latency(src, dst, 0)

    # Wake up all agents
    for agent in all_agents:
        kernel.wakeup(agent.agent_id, at_time=1)

    # Run with TUI
    try:
        curses.wrapper(draw_tui, kernel, exchange, oracle, all_agents)
    except KeyboardInterrupt:
        pass

    # Final summary
    print("\nSimulation stopped.")
    print(f"Final Time: {kernel.time}")
    print(f"Last Price: {exchange.last_trade:.2f}")
    print(f"Oracle Value: {oracle.value:.2f}")
    print(f"\n── Agent Summary ──")
    for agent in all_agents:
        mtm = agent.cash + agent.position * exchange.last_trade
        extra = ""
        if isinstance(agent, LiquidityTrader):
            extra = f"  remaining={agent.remaining_qty}"
        print(f"  {agent.name:.<20s} pos={agent.position:>5d}  "
              f"cash={agent.cash:>10.2f}  MtM={mtm:>10.2f}{extra}")


if __name__ == "__main__":
    run_demo()
