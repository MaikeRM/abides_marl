import math
import random
from typing import List, Dict, Optional
from app.agents.base import HeuristicAgent
from app.core.constants import round_to_tick


def sigmoid(x: float, beta: float) -> float:
    try:
        return 1.0 / (1.0 + math.exp(-beta * x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


DEFAULT_LEVELS_QUOTE_DICT = {
    1: [1, 0, 0, 0, 0],
    2: [0.5, 0.5, 0, 0, 0],
    3: [0.34, 0.33, 0.33, 0, 0],
    4: [0.25, 0.25, 0.25, 0.25, 0],
    5: [0.20, 0.20, 0.20, 0.20, 0.20]
}


class BaseMarketMakerAgent(HeuristicAgent):
    """
    Classe base para agrupar comportamentos em comum de market makers, como Lidar com Respostas
    (Order Accepted, Executions, Cancelled).
    """

    def __init__(self, agent_id, name):
        super().__init__(agent_id, name)
        self.pending_orders: List[int] = []

    def receive(self, msg):
        # Dispatch message
        if msg.kind == "MKT_DATA" and self.state == "AWAITING_DATA":
            self.state = "ACTIVE"
            self._update_mkt_cache(msg)
            self.handle_mkt_data(msg)
        elif msg.kind == "EXECUTION":
            self.handle_execution(msg)
        elif msg.kind == "ORDER_ACCEPTED":
            self.handle_order_accepted(msg)
            self.pending_orders.append(msg.data["order_id"])
        elif msg.kind == "ORDER_CANCELLED":
            self.handle_order_cancelled(msg)
            order_id = msg.data.get("order_id")
            if order_id in self.pending_orders:
                self.pending_orders.remove(order_id)

    def get_observation(self) -> list:
        """LOB state + inventory features for market-making RL agents.

        Features (8):
          [best_bid, best_ask, spread, mid_price, position, realized_pnl, vwap, last_trade]
        Missing bid/ask are replaced with last_trade to avoid None propagation.
        """
        last = self._last_mkt["last_trade"] or 0.0
        best_bid = self._last_mkt["best_bid"] if self._last_mkt["best_bid"] is not None else last
        best_ask = self._last_mkt["best_ask"] if self._last_mkt["best_ask"] is not None else last
        spread = best_ask - best_bid
        mid = (best_bid + best_ask) / 2.0
        return [best_bid, best_ask, spread, mid, float(self.position), self.realized_pnl, self.vwap, last]

    def reset(self) -> None:
        super().reset()
        self.pending_orders = []

    def handle_mkt_data(self, msg):
        pass


class MarketMakerAgent(BaseMarketMakerAgent):
    """
    Baseado no `MarketMakerAgent` canônico do ABIDES.
    Coloca ordens em X níveis de forma aleatória baseado num dict padrão de quote levels, limitando em spread.
    
    Nota: Substituímos internamente a lógica base de SpreadBased para se adequar a `runner.py` original 
    (que passava spread e order_qty).
    """

    def __init__(
        self,
        agent_id,
        exchange_id,
        seed,
        wake_interval=3,
        spread=1.0,
        order_qty=5,
        min_size=1,
        subscribe_num_levels=5,
        **kwargs
    ):
        super().__init__(agent_id, f"MM_{agent_id}")
        self.exchange_id = exchange_id
        self.rng = random.Random(seed)
        self.lambda_a = 1.0 / wake_interval
        
        self.spread = spread
        self.min_size = min_size
        self.max_size = order_qty * 2 # max variation
        self.subscribe_num_levels = subscribe_num_levels
        self.levels_quote_dict = DEFAULT_LEVELS_QUOTE_DICT

    def wakeup(self, now):
        assert self.kernel is not None
        if self.state == "AWAITING_DATA":
            return
        self.state = "AWAITING_DATA"
        self.kernel.send(self.agent_id, self.exchange_id, "QUERY_MKT_DATA", {})

    def handle_mkt_data(self, msg):
        now = self.kernel.time

        for order_id in self.pending_orders:
            self.kernel.send(self.agent_id, self.exchange_id, "CANCEL_ORDER", {"order_id": order_id})
        self.pending_orders.clear()

        best_bid = msg.data.get("best_bid")
        best_ask = msg.data.get("best_ask")
        last_trade = msg.data.get("last_trade", 100.0)

        mid = last_trade
        if best_bid is not None and best_ask is not None:
            mid = (best_bid + best_ask) / 2.0
        
        max_levels = len(self.levels_quote_dict.keys())
        num_levels = self.rng.randint(1, max_levels)
        size_split = self.levels_quote_dict.get(num_levels, [1])

        size = round(self.rng.randint(self.min_size, self.max_size) / 2)
        if size < 1:
            size = 1

        for i in range(num_levels):
            vol = round(size_split[i] * size)
            if vol <= 0:
                continue
            
            # Usando tick sizing arbitrário de 0.01 pra criar espaços em preços de floats em dólares
            bid_price = round_to_tick(mid - (self.spread / 2) - (i * 0.05))
            if best_bid is not None:
                bid_price = round_to_tick(best_bid - (i * 0.05))

            ask_price = round_to_tick(mid + (self.spread / 2) + (i * 0.05))
            if best_ask is not None:
                ask_price = round_to_tick(best_ask + (i * 0.05))

            self.kernel.send(
                self.agent_id,
                self.exchange_id,
                "NEW_ORDER",
                {"order_type": "LIMIT", "side": "BUY", "qty": vol, "price": bid_price},
            )
            self.kernel.send(
                self.agent_id,
                self.exchange_id,
                "NEW_ORDER",
                {"order_type": "LIMIT", "side": "SELL", "qty": vol, "price": ask_price},
            )

        delta_time = self.rng.expovariate(self.lambda_a)
        self.kernel.wakeup(self.agent_id, now + max(1, int(delta_time)))


class SpreadBasedMarketMakerAgent(BaseMarketMakerAgent):
    """
    Implementa a estratégia de ladder de Chakraborty-Kearns.
    Baseado no SpreadBasedMarketMakerAgent canônico do ABIDES.
    """

    def __init__(
        self,
        agent_id,
        exchange_id,
        seed,
        wake_interval=3,
        order_size=5,
        window_size=0.10, # Em dolares como 'cents'
        num_ticks=10, 
        tick_increment=0.01, # Tick de variação intra-ladder
        **kwargs
    ):
        super().__init__(agent_id, f"SBMM_{agent_id}")
        self.exchange_id = exchange_id
        self.rng = random.Random(seed)
        self.lambda_a = 1.0 / wake_interval
        self.order_size = order_size
        self.window_size = window_size
        self.num_ticks = num_ticks
        self.tick_increment = tick_increment

    def wakeup(self, now):
        assert self.kernel is not None
        if self.state == "AWAITING_DATA":
            return
        self.state = "AWAITING_DATA"
        self.kernel.send(self.agent_id, self.exchange_id, "QUERY_MKT_DATA", {})

    def handle_mkt_data(self, msg):
        now = self.kernel.time

        for order_id in self.pending_orders:
            self.kernel.send(self.agent_id, self.exchange_id, "CANCEL_ORDER", {"order_id": order_id})
        self.pending_orders.clear()

        best_bid = msg.data.get("best_bid")
        best_ask = msg.data.get("best_ask")
        last_trade = msg.data.get("last_trade", 100.0)

        mid = last_trade
        if best_bid is not None and best_ask is not None:
            mid = (best_bid + best_ask) / 2.0

        # Anchor 'bottom' clássico: bid no mid - 1, ask no mid + window_size
        highest_bid = round_to_tick(mid - self.tick_increment)
        lowest_ask = round_to_tick(mid + self.window_size)
        
        lowest_bid = round_to_tick(highest_bid - (self.num_ticks * self.tick_increment))
        highest_ask = round_to_tick(lowest_ask + (self.num_ticks * self.tick_increment))

        # Place bids
        current_bid = highest_bid
        while current_bid >= lowest_bid:
            self.kernel.send(
                self.agent_id,
                self.exchange_id,
                "NEW_ORDER",
                {"order_type": "LIMIT", "side": "BUY", "qty": self.order_size, "price": current_bid},
            )
            current_bid -= self.tick_increment
            current_bid = round_to_tick(current_bid)

        # Place asks
        current_ask = lowest_ask
        while current_ask <= highest_ask:
            self.kernel.send(
                self.agent_id,
                self.exchange_id,
                "NEW_ORDER",
                {"order_type": "LIMIT", "side": "SELL", "qty": self.order_size, "price": current_ask},
            )
            current_ask += self.tick_increment
            current_ask = round_to_tick(current_ask)

        delta_time = self.rng.expovariate(self.lambda_a)
        self.kernel.wakeup(self.agent_id, now + max(1, int(delta_time)))


class AdaptiveMarketMakerAgent(BaseMarketMakerAgent):
    """
    Modificação da estratégia de Chakraborty-Kearns, em que o 
    tamanho das ordens é balanceado utilizando skew beta baseado
    no inventário, atuando apenas no volume (ordens assimétricas)
    mas mantendo o spread intacto, assim como o ABIDES canônico.
    """

    def __init__(
        self,
        agent_id,
        exchange_id,
        seed,
        wake_interval=3,
        min_order_size=10,
        window_size=0.10,
        num_ticks=10,
        tick_increment=0.01,
        skew_beta=0.05,
        **kwargs
    ):
        super().__init__(agent_id, f"AMM_{agent_id}")
        self.exchange_id = exchange_id
        self.rng = random.Random(seed)
        self.lambda_a = 1.0 / wake_interval
        
        self.min_order_size = min_order_size
        self.window_size = window_size
        self.num_ticks = num_ticks
        self.tick_increment = tick_increment
        self.skew_beta = skew_beta
        
        self.buy_order_size = self.min_order_size
        self.sell_order_size = self.min_order_size

    def reset(self) -> None:
        super().reset()
        self.buy_order_size = self.min_order_size
        self.sell_order_size = self.min_order_size

    def wakeup(self, now):
        assert self.kernel is not None
        if self.state == "AWAITING_DATA":
            return
        self.state = "AWAITING_DATA"
        self.kernel.send(self.agent_id, self.exchange_id, "QUERY_MKT_DATA", {})

    def handle_mkt_data(self, msg):
        now = self.kernel.time

        for order_id in self.pending_orders:
            self.kernel.send(self.agent_id, self.exchange_id, "CANCEL_ORDER", {"order_id": order_id})
        self.pending_orders.clear()

        best_bid = msg.data.get("best_bid")
        best_ask = msg.data.get("best_ask")
        last_trade = msg.data.get("last_trade", 100.0)

        mid = last_trade
        if best_bid is not None and best_ask is not None:
            mid = (best_bid + best_ask) / 2.0

        qty = self.min_order_size * 2
        if self.skew_beta == 0:
            self.buy_order_size = self.min_order_size
            self.sell_order_size = self.min_order_size
        else:
            proportion_sell = sigmoid(self.position, self.skew_beta)
            sell_size = math.ceil(proportion_sell * qty)
            buy_size = math.floor((1 - proportion_sell) * qty)
            
            self.buy_order_size = buy_size if buy_size >= self.min_order_size else self.min_order_size
            self.sell_order_size = sell_size if sell_size >= self.min_order_size else self.min_order_size

        # Anchor 'middle' - Comum em MMs Adaptativos
        highest_bid = round_to_tick(mid - (0.5 * self.window_size))
        lowest_ask = round_to_tick(mid + (0.5 * self.window_size))
        
        lowest_bid = round_to_tick(highest_bid - (self.num_ticks * self.tick_increment))
        highest_ask = round_to_tick(lowest_ask + (self.num_ticks * self.tick_increment))

        # Place bids
        current_bid = highest_bid
        while current_bid >= lowest_bid:
            self.kernel.send(
                self.agent_id,
                self.exchange_id,
                "NEW_ORDER",
                {"order_type": "LIMIT", "side": "BUY", "qty": self.buy_order_size, "price": current_bid},
            )
            current_bid -= self.tick_increment
            current_bid = round_to_tick(current_bid)

        # Place asks
        current_ask = lowest_ask
        while current_ask <= highest_ask:
            self.kernel.send(
                self.agent_id,
                self.exchange_id,
                "NEW_ORDER",
                {"order_type": "LIMIT", "side": "SELL", "qty": self.sell_order_size, "price": current_ask},
            )
            current_ask += self.tick_increment
            current_ask = round_to_tick(current_ask)

        delta_time = self.rng.expovariate(self.lambda_a)
        self.kernel.wakeup(self.agent_id, now + max(1, int(delta_time)))


class POVMarketMakerAgent(BaseMarketMakerAgent):
    """
    MarketMaker baseado no SpreadBased (Chakraborty-Kearns) 
    que normalmente dimensiona suas ordens de acordo com o 
    Volume Transacionado (POV - Percentage of Volume).
    """

    def __init__(
        self,
        agent_id,
        exchange_id,
        seed,
        wake_interval=3,
        pov=0.05,
        min_order_size=20,
        window_size=0.10,
        num_ticks=10,
        tick_increment=0.01,
        **kwargs
    ):
        super().__init__(agent_id, f"POV_{agent_id}")
        self.exchange_id = exchange_id
        self.rng = random.Random(seed)
        self.lambda_a = 1.0 / wake_interval
        
        self.pov = pov
        self.min_order_size = min_order_size
        self.window_size = window_size
        self.num_ticks = num_ticks
        self.tick_increment = tick_increment
        self.order_size = self.min_order_size

    def wakeup(self, now):
        assert self.kernel is not None
        if self.state == "AWAITING_DATA":
            return
        self.state = "AWAITING_DATA"
        self.kernel.send(self.agent_id, self.exchange_id, "QUERY_MKT_DATA", {})

    def handle_mkt_data(self, msg):
        now = self.kernel.time

        for order_id in self.pending_orders:
            self.kernel.send(self.agent_id, self.exchange_id, "CANCEL_ORDER", {"order_id": order_id})
        self.pending_orders.clear()

        best_bid = msg.data.get("best_bid")
        best_ask = msg.data.get("best_ask")
        last_trade = msg.data.get("last_trade", 100.0)

        mid = last_trade
        if best_bid is not None and best_ask is not None:
            mid = (best_bid + best_ask) / 2.0

        self.order_size = self.min_order_size

        highest_bid = round_to_tick(mid - self.tick_increment)
        lowest_ask = round_to_tick(mid + self.window_size)
        
        lowest_bid = round_to_tick(highest_bid - (self.num_ticks * self.tick_increment))
        highest_ask = round_to_tick(lowest_ask + (self.num_ticks * self.tick_increment))

        current_bid = highest_bid
        while current_bid >= lowest_bid:
            self.kernel.send(
                self.agent_id,
                self.exchange_id,
                "NEW_ORDER",
                {"order_type": "LIMIT", "side": "BUY", "qty": self.order_size, "price": current_bid},
            )
            current_bid -= self.tick_increment
            current_bid = round_to_tick(current_bid)

        current_ask = lowest_ask
        while current_ask <= highest_ask:
            self.kernel.send(
                self.agent_id,
                self.exchange_id,
                "NEW_ORDER",
                {"order_type": "LIMIT", "side": "SELL", "qty": self.order_size, "price": current_ask},
            )
            current_ask += self.tick_increment
            current_ask = round_to_tick(current_ask)

        delta_time = self.rng.expovariate(self.lambda_a)
        self.kernel.wakeup(self.agent_id, now + max(1, int(delta_time)))
