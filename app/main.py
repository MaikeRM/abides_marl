import os
import contextlib

if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.runner import SimulationRunner
import dearpygui.dearpygui as dpg


class SimulationApp:
    def __init__(self):
        self.runner = SimulationRunner()
        self.simulation_running = False
        self.agent_options_loaded = False
        
        self.history = []
        self.trade_history = []
        self.window_size = 100
        self.max_window_size = 1000

        # Colors for log rows etc.
        self._light_blue = [100, 150, 255, 255]
        self._red = [255, 100, 100, 255]
        self._green = [100, 255, 100, 255]
        
        self.agent_pnl_history = {}
        self.agent_type_colors = {
            "MarketMakerAgent": [50, 200, 255, 255],
            "ValueAgent": [100, 255, 100, 255],
            "ZeroIntelligenceAgent": [255, 200, 50, 255],
            "LiquidityTrader": [255, 100, 100, 255],
            "ExchangeAgent": [200, 200, 200, 255]
        }
        
    def setup_dpg(self):
        dpg.create_context()
        dpg.create_viewport(title='ABIDES Simulation Dashboard - DearPyGui', width=1280, height=800)
        dpg.setup_dearpygui()

        with dpg.theme(tag="bid_bar_theme"):
            with dpg.theme_component(dpg.mvProgressBar):
                dpg.add_theme_color(dpg.mvThemeCol_PlotHistogram, (40, 150, 40, 150))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (0, 0, 0, 0))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))

        with dpg.theme(tag="ask_bar_theme"):
            with dpg.theme_component(dpg.mvProgressBar):
                dpg.add_theme_color(dpg.mvThemeCol_PlotHistogram, (150, 40, 40, 150))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (0, 0, 0, 0))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))

        with dpg.theme(tag="vol_bar_theme"):
            with dpg.theme_component(dpg.mvProgressBar):
                dpg.add_theme_color(dpg.mvThemeCol_PlotHistogram, (40, 100, 200, 150))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (0, 0, 0, 0))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))

        with dpg.window(label="Main View", tag="main_window"):
            with dpg.group(horizontal=True):
                dpg.add_button(label="Reset (R)", callback=self.reset_simulation, width=120)
                dpg.add_button(label="Start/Stop (S)", callback=self.toggle_simulation, width=120)
                dpg.add_button(label="Step (Space)", callback=self.step_simulation, width=120)
                
            dpg.add_separator()
            
            with dpg.tab_bar(tag="main_tab_bar"):
                # Dashboard Tab
                with dpg.tab(label="Dashboard"):
                    with dpg.group(horizontal=True):
                        # Left Column: Order Book
                        with dpg.child_window(width=500, border=True):
                            dpg.add_text("Order Book (Bids | Asks)", color=self._light_blue)
                            with dpg.table(tag="order_book_table", header_row=True, resizable=True, 
                                           policy=dpg.mvTable_SizingStretchProp, scrollY=True, freeze_rows=1,
                                           borders_outerH=True, borders_innerV=True, borders_innerH=True, borders_outerV=True):
                                dpg.add_table_column(label="Buy")
                                dpg.add_table_column(label="Bids")
                                dpg.add_table_column(label="Price")
                                dpg.add_table_column(label="Asks")
                                dpg.add_table_column(label="Sell")
                                dpg.add_table_column(label="Volume")
                                dpg.add_table_column(label="Imbalance")

                        # Right Column: Stats & Trades
                        with dpg.child_window(border=False):
                            with dpg.child_window(height=120, border=True):
                                dpg.add_text("Market Statistics", color=self._light_blue)
                                dpg.add_text("Waiting for simulation data...", tag="market_stats_text")

                            with dpg.child_window(border=True):
                                dpg.add_text("Recent Trades", color=self._light_blue)
                                with dpg.table(tag="trades_table", header_row=True, resizable=True, 
                                               policy=dpg.mvTable_SizingStretchProp, 
                                               borders_outerH=True, borders_innerV=True, borders_innerH=True, borders_outerV=True):
                                    dpg.add_table_column(label="Time")
                                    dpg.add_table_column(label="Price")
                                    dpg.add_table_column(label="Qty")
                                    dpg.add_table_column(label="Side")

                # Logs Tab
                with dpg.tab(label="Logs"):
                    with dpg.table(tag="events_log_table", header_row=True, resizable=True, 
                                   policy=dpg.mvTable_SizingStretchProp, scrollY=True, 
                                   borders_outerH=True, borders_innerV=True, borders_innerH=True, borders_outerV=True):
                        cols = ["Timestamp", "Sim Time", "Phase", "Kind", "Seq", "Delivery", 
                                "Source", "Destination", "Order Type", "Side", "Qty", "Price", "Order ID", "Cancel All", "Text"]
                        for c in cols:
                            dpg.add_table_column(label=c)
                        
                # LOB Heatmap Tab
                with dpg.tab(label="LOB Heatmap"):
                    with dpg.group(horizontal=True):
                        dpg.add_text("X-Axis Window Size:")
                        dpg.add_radio_button(
                            items=["100", "500", "1000"], 
                            default_value="100", 
                            horizontal=True, 
                            callback=self.update_window_size
                        )

                    with dpg.plot(label="Price & LOB History", height=-1, width=-1, tag="heatmap_plot"):
                        dpg.add_plot_legend()
                        dpg.add_plot_axis(dpg.mvXAxis, label="Time", tag="xaxis")
                        dpg.add_plot_axis(dpg.mvYAxis, label="Price", tag="yaxis")

                # Agent Tracker Tab
                with dpg.tab(label="Agent Tracker"):
                    with dpg.group(horizontal=True):
                        # 1. Dashboard Table
                        with dpg.child_window(width=450, height=250, border=True):
                            dpg.add_text("Agent Ecosystem Overview", color=self._light_blue)
                            with dpg.table(tag="agent_overview_table", header_row=True, resizable=True, 
                                           policy=dpg.mvTable_SizingStretchProp, borders_innerH=True):
                                dpg.add_table_column(label="Type")
                                dpg.add_table_column(label="Count")
                                dpg.add_table_column(label="Vol")
                                dpg.add_table_column(label="Pos")
                                dpg.add_table_column(label="Total PnL")

                        # 2. Scatter Plot
                        with dpg.child_window(height=250, border=True):
                            dpg.add_text("Scatter: Volume vs Total PnL", color=self._light_blue)
                            with dpg.plot(label="", height=-1, width=-1, tag="agent_scatter_plot"):
                                dpg.add_plot_legend()
                                dpg.add_plot_axis(dpg.mvXAxis, label="Volume", tag="scatter_xaxis")
                                dpg.add_plot_axis(dpg.mvYAxis, label="Total PnL", tag="scatter_yaxis")

                    # 3. Time Series Plot Row
                    with dpg.child_window(height=250, border=True):
                        dpg.add_text("Time Series: Total PnL by Agent Type", color=self._light_blue)
                        with dpg.plot(label="", height=-1, width=-1, tag="agent_ts_plot"):
                            dpg.add_plot_legend()
                            dpg.add_plot_axis(dpg.mvXAxis, label="Time", tag="ts_xaxis")
                            dpg.add_plot_axis(dpg.mvYAxis, label="Total PnL", tag="ts_yaxis")

                    dpg.add_separator()
                    
                    # 4. Drill-Down
                    dpg.add_text("Drill-down: Select Individual Agent:", color=self._light_blue)
                    dpg.add_combo([], tag="agent_select_combo", callback=self.update_agent_tracker_ui)
                    dpg.add_separator()
                    
                    with dpg.child_window(height=80, border=True):
                        dpg.add_text("Select an agent to see stats.", tag="agent_stats_text")
                        
                    with dpg.group(horizontal=True):
                        with dpg.child_window(width=450, border=True):
                            dpg.add_text("Active Orders", color=self._light_blue)
                            with dpg.table(tag="agent_orders_table", header_row=True, resizable=True, 
                                           policy=dpg.mvTable_SizingStretchProp, borders_outerH=True, borders_innerV=True, borders_innerH=True, borders_outerV=True):
                                dpg.add_table_column(label="Order ID")
                                dpg.add_table_column(label="Side")
                                dpg.add_table_column(label="Qty")
                                dpg.add_table_column(label="Price")
                                dpg.add_table_column(label="Time")
                        
                        with dpg.child_window(border=True):
                            dpg.add_text("Trade History", color=self._light_blue)
                            with dpg.table(tag="agent_trades_table", header_row=True, resizable=True, 
                                           policy=dpg.mvTable_SizingStretchProp, borders_outerH=True, borders_innerV=True, borders_innerH=True, borders_outerV=True):
                                dpg.add_table_column(label="Time")
                                dpg.add_table_column(label="Side")
                                dpg.add_table_column(label="Qty")
                                dpg.add_table_column(label="Price")

        dpg.set_primary_window("main_window", True)

        with dpg.handler_registry():
            dpg.add_key_press_handler(key=dpg.mvKey_R, callback=self.reset_simulation)
            dpg.add_key_press_handler(key=dpg.mvKey_S, callback=self.toggle_simulation)
            dpg.add_key_press_handler(key=dpg.mvKey_Spacebar, callback=self.step_simulation)

    def reset_simulation(self):
        with open(os.devnull, "w") as f, contextlib.redirect_stdout(f):
            self.runner.reset()
        
        self.history = []
        self.trade_history = []
        self.agent_pnl_history = {}
        self.update_ui()

    def toggle_simulation(self):
        self.simulation_running = not self.simulation_running

    def step_simulation(self):
        if not self.runner.step():
            self.runner.stop()
            self.simulation_running = False
        self.update_ui()

    def update_window_size(self, sender, app_data, user_data):
        self.window_size = int(app_data)
        self.update_plot()

    def update_agent_tracker_ui(self):
        self._sync_agent()

    def process_tick(self):
        if self.simulation_running:
            for _ in range(20):
                if not self.runner.step():
                    self.simulation_running = False
                    self.runner.stop()
                    break
            self.update_ui()

    def update_ui(self):
        state = self.runner.get_state()
        if not state:
            return

        time_val = state.get("time", 0)
        last_price = state.get("last_price", 0.0)
        fund_val = state.get("fundamental_value", 0.0)

        # 1. Update Stats
        stats_str = f"Simulation Time: {time_val}\n"
        stats_str += f"Last Traded Price: {last_price:.2f}\n"
        stats_str += f"Fundamental Value: {fund_val:.2f}"
        dpg.set_value("market_stats_text", stats_str)

        # 2. Update Order Book
        ob_bids = state.get("bids", [])
        ob_asks = state.get("asks", [])
        
        dpg.delete_item("order_book_table", children_only=True, slot=1)
        
        N = 40
        top_asks = ob_asks[:N]
        top_asks_rev = list(reversed(top_asks))  # Highest to lowest for DOM display
        top_bids = ob_bids[:N]                   # Already highest to lowest
        
        all_levels = top_asks + top_bids
        max_qty = max([lvl["qty"] for lvl in all_levels] + [1])
        
        for ask in top_asks_rev:
            price_str = f"{ask['price']:.2f}"
            qty_str = str(ask["qty"])
            frac = ask["qty"] / max_qty
            
            with dpg.table_row(parent="order_book_table"):
                dpg.add_text("")  # Buy
                dpg.add_text("")  # Bids
                dpg.add_text(price_str, color=self._red)  # Price
                p_ask = dpg.add_progress_bar(default_value=frac, overlay=qty_str, width=-1)
                dpg.bind_item_theme(p_ask, "ask_bar_theme")
                dpg.add_text("")  # Sell
                
                # Simulated Volume
                vol_frac = min(1.0, frac * 1.5)
                p_vol = dpg.add_progress_bar(default_value=vol_frac, overlay=str(int(ask["qty"] * 1.5)), width=-1)
                dpg.bind_item_theme(p_vol, "vol_bar_theme")
                dpg.add_text(f"{50 + frac*20:.2f}", color=[255,100,100])  # Imbalance

        for bid in top_bids:
            price_str = f"{bid['price']:.2f}"
            qty_str = str(bid["qty"])
            frac = bid["qty"] / max_qty
            
            with dpg.table_row(parent="order_book_table"):
                dpg.add_text("")  # Buy
                p_bid = dpg.add_progress_bar(default_value=frac, overlay=qty_str, width=-1)
                dpg.bind_item_theme(p_bid, "bid_bar_theme")
                dpg.add_text(price_str, color=self._green)  # Price
                dpg.add_text("")  # Asks
                dpg.add_text("")  # Sell
                
                # Simulated Volume
                vol_frac = min(1.0, frac * 1.5)
                p_vol = dpg.add_progress_bar(default_value=vol_frac, overlay=str(int(bid["qty"] * 1.5)), width=-1)
                dpg.bind_item_theme(p_vol, "vol_bar_theme")
                dpg.add_text(f"{50 + frac*20:.2f}", color=[100,255,100])  # Imbalance

        # 3. Update Trades
        trades_state = state.get("history", [])
        dpg.delete_item("trades_table", children_only=True, slot=1)
        for t in reversed(trades_state): # Show latest on top
            with dpg.table_row(parent="trades_table"):
                dpg.add_text(str(t["time"]))
                dpg.add_text(f"{t['price']:.2f}")
                dpg.add_text(str(t["qty"]))
                side_str = str(t["side"]).upper()
                dpg.add_text(t["side"], color=self._green if side_str in ["BID", "BUY"] else self._red)

        # 4. Agent Tracker Dashboard & Combo
        agents_data = state.get("agents", {})
        if not self.agent_options_loaded and agents_data:
            options = [f"{aid} - {adata.get('type', 'Unknown')}" for aid, adata in agents_data.items()]
            dpg.configure_item("agent_select_combo", items=options)
            self.agent_options_loaded = True
            
        self._sync_agent(state, last_price)

        if agents_data:
            eco_stats = {} 
            type_scatter_x = {}
            type_scatter_y = {}
            import random
            
            for aid, adata in agents_data.items():
                atype = adata.get("type", "Unknown")
                
                # Calculate True PnL
                unrealized = 0.0
                if adata["position"] > 0:
                    unrealized = adata["position"] * (last_price - adata.get("vwap", 0.0))
                elif adata["position"] < 0:
                    unrealized = abs(adata["position"]) * (adata.get("vwap", 0.0) - last_price)
                total_pnl = adata.get("realized_pnl", 0.0) + unrealized
                
                # Calculate Volume
                vol = sum([t.get("qty", 0) for t in adata.get("trade_history", [])])
                
                if atype not in eco_stats:
                     eco_stats[atype] = {"count": 0, "vol": 0, "pos": 0, "pnl": 0.0}
                     type_scatter_x[atype] = []
                     type_scatter_y[atype] = []
                     if atype not in self.agent_type_colors:
                         self.agent_type_colors[atype] = [random.randint(100,255), random.randint(100,255), random.randint(100,255), 255]
                         
                eco_stats[atype]["count"] += 1
                eco_stats[atype]["vol"] += vol
                eco_stats[atype]["pos"] += adata["position"]
                eco_stats[atype]["pnl"] += total_pnl
                
                type_scatter_x[atype].append(float(vol))
                type_scatter_y[atype].append(float(total_pnl))
                
            # Update Overview Table
            dpg.delete_item("agent_overview_table", children_only=True, slot=1)
            for atype, stats in eco_stats.items():
                with dpg.table_row(parent="agent_overview_table"):
                    val = self.agent_type_colors.get(atype, self._light_blue)
                    dpg.add_text(atype, color=val)
                    dpg.add_text(str(stats["count"]))
                    dpg.add_text(str(stats["vol"]))
                    dpg.add_text(str(stats["pos"]))
                    pnl_color = self._green if stats["pnl"] >= 0 else self._red
                    dpg.add_text(f"{stats['pnl']:.2f}", color=pnl_color)
            
            # Update Scatter Plot
            dpg.delete_item("scatter_yaxis", children_only=True)
            for atype in type_scatter_x:
                if not type_scatter_x[atype]: continue
                with dpg.theme() as t_scatter:
                    with dpg.theme_component(dpg.mvScatterSeries):
                        dpg.add_theme_color(dpg.mvPlotCol_Line, self.agent_type_colors.get(atype, self._light_blue), category=dpg.mvThemeCat_Plots)
                        dpg.add_theme_style(dpg.mvPlotStyleVar_Marker, dpg.mvPlotMarker_Circle, category=dpg.mvThemeCat_Plots)
                        dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, 6, category=dpg.mvThemeCat_Plots)
                s = dpg.add_scatter_series(type_scatter_x[atype], type_scatter_y[atype], parent="scatter_yaxis", label=atype)
                dpg.bind_item_theme(s, t_scatter)
            dpg.fit_axis_data("scatter_xaxis")
            dpg.fit_axis_data("scatter_yaxis")

            # Update Time Series History array
            cutoff_time = time_val - self.max_window_size
            for atype, stats in eco_stats.items():
                if atype not in self.agent_pnl_history:
                    self.agent_pnl_history[atype] = []
                self.agent_pnl_history[atype].append({"time": time_val, "pnl": stats["pnl"]})
                self.agent_pnl_history[atype] = [h for h in self.agent_pnl_history[atype] if h["time"] >= cutoff_time]

        # 5. Update Events Log
        events = state.get("events", [])
        dpg.delete_item("events_log_table", children_only=True, slot=1)
        for event in reversed(events[-100:]): # Only display last 100 for performance
            if event.get("kind") in {"LOG", "WAKEUP"} or event.get("phase") == "LOG":
                continue
            data = event.get("data", {})
            with dpg.table_row(parent="events_log_table"):
                dpg.add_text(event.get("timestamp", ""))
                dpg.add_text(str(event.get("sim_time", "")))
                dpg.add_text(event.get("phase", ""))
                dpg.add_text(event.get("kind", ""))
                dpg.add_text(str(event.get("seq", "")))
                dpg.add_text(str(event.get("delivery", "")))
                dpg.add_text(event.get("src_name", str(event.get("src", ""))))
                dpg.add_text(event.get("dst_name", str(event.get("dst", ""))))
                dpg.add_text(str(data.get("order_type", "")))
                dpg.add_text(str(data.get("side", "")))
                dpg.add_text(str(data.get("qty", "")))
                dpg.add_text(str(data.get("price", "")))
                dpg.add_text(str(data.get("order_id", "")))
                dpg.add_text(str(data.get("cancel_all", "")))
                dpg.add_text(str(data.get("text", "")))
                
        # 6. Heatmap update
        self.history.append({
            "time": time_val,
            "price": last_price,
            "bids": ob_bids,
            "asks": ob_asks
        })
        cutoff_time = time_val - self.max_window_size
        self.history = [snap for snap in self.history if snap["time"] >= cutoff_time]
        
        if trades_state:
            for tr in trades_state:
                if tr not in self.trade_history:
                    self.trade_history.append(tr)
        self.trade_history = [t for t in self.trade_history if t["time"] >= cutoff_time]

        self.update_plot()

    def _sync_agent(self, state=None, last_price=None):
        if not state:
            state = self.runner.get_state()
            last_price = state.get("last_price", 0.0) if state else 0.0
            
        if not state: return
            
        agents_data = state.get("agents", {})
        selected_agent = dpg.get_value("agent_select_combo")
        
        if selected_agent:
            aid_str = selected_agent.split(" ")[0]
            if aid_str.isdigit():
                aid = int(aid_str)
                if aid in agents_data:
                    adata = agents_data[aid]
                    unrealized = 0.0
                if adata["position"] > 0:
                    unrealized = adata["position"] * (last_price - adata["vwap"])
                elif adata["position"] < 0:
                    unrealized = abs(adata["position"]) * (adata["vwap"] - last_price)
                    
                total_pnl = adata["realized_pnl"] + unrealized
                
                agent_stats = f"Agent ID: {aid}\nPosition: {adata['position']} | VWAP: {adata['vwap']:.2f}\n"
                agent_stats += f"Cash: {adata['cash']:.2f} | Realized PnL: {adata['realized_pnl']:.2f}\n"
                agent_stats += f"Unrealized PnL: {unrealized:.2f} | Total PnL: {total_pnl:.2f}"
                dpg.set_value("agent_stats_text", agent_stats)

                # Agent Active Orders
                dpg.delete_item("agent_orders_table", children_only=True, slot=1)
                for oid, ord_data in adata["active_orders"].items():
                    with dpg.table_row(parent="agent_orders_table"):
                        dpg.add_text(str(oid))
                        side_str = str(ord_data["side"]).upper()
                        dpg.add_text(ord_data["side"], color=self._green if side_str in ["BID", "BUY"] else self._red)
                        dpg.add_text(str(ord_data["qty"]))
                        dpg.add_text(f"{ord_data['price']:.2f}")
                        dpg.add_text(str(ord_data["time"]))
                        
                # Agent Trades
                dpg.delete_item("agent_trades_table", children_only=True, slot=1)
                for trd in reversed(adata["trade_history"][-50:]):
                    with dpg.table_row(parent="agent_trades_table"):
                        dpg.add_text(str(trd["time"]))
                        side_str = str(trd["side"]).upper()
                        dpg.add_text(trd["side"], color=self._green if side_str in ["BID", "BUY"] else self._red)
                        dpg.add_text(str(trd["qty"]))
                        dpg.add_text(f"{trd['price']:.2f}")
        else:
            dpg.set_value("agent_stats_text", "Select an agent to see stats.")
            dpg.delete_item("agent_orders_table", children_only=True, slot=1)
            dpg.delete_item("agent_trades_table", children_only=True, slot=1)


    def update_plot(self):
        dpg.delete_item("yaxis", children_only=True)
        
        x_time = []
        y_price = []
        
        bid_best, bid_mid, bid_deep = [], [], []
        ask_best, ask_mid, ask_deep = [], [], []
        
        x_trades_buy, y_trades_buy = [], []
        x_trades_sell, y_trades_sell = [], []

        for snap in self.history:
            t = snap["time"]
            x_time.append(t)
            
            if snap["price"]:
                y_price.append(snap["price"])
            else:
                y_price.append(y_price[-1] if y_price else 0)
                
            bids = snap["bids"]
            if bids:
                bid_best.append(bids[0]["price"])
                bid_mid.append(bids[min(4, len(bids)-1)]["price"])
                bid_deep.append(bids[min(9, len(bids)-1)]["price"])
            else:
                fill_bid = bid_best[-1] if bid_best else (y_price[-1] if y_price else 0)
                bid_best.append(fill_bid)
                bid_mid.append(fill_bid)
                bid_deep.append(fill_bid)

            asks = snap["asks"]
            if asks:
                ask_best.append(asks[0]["price"])
                ask_mid.append(asks[min(4, len(asks)-1)]["price"])
                ask_deep.append(asks[min(9, len(asks)-1)]["price"])
            else:
                fill_ask = ask_best[-1] if ask_best else (y_price[-1] if y_price else 0)
                ask_best.append(fill_ask)
                ask_mid.append(fill_ask)
                ask_deep.append(fill_ask)

        for tr in self.trade_history:
            side_str = str(tr["side"]).upper()
            if side_str in ["BID", "BUY"]:
                x_trades_buy.append(tr["time"])
                y_trades_buy.append(tr["price"])
            else:
                x_trades_sell.append(tr["time"])
                y_trades_sell.append(tr["price"])

        # 1. SHADE SERIES (Liquidity Cloud)
        if len(x_time) > 1:
            # BIDS Depth Level 2 (Mid to Deep)
            with dpg.theme() as t_bid_shade2:
                with dpg.theme_component(dpg.mvShadeSeries):
                    dpg.add_theme_color(dpg.mvPlotCol_Fill, (40, 100, 200, 40), category=dpg.mvThemeCat_Plots)
                    dpg.add_theme_color(dpg.mvPlotCol_Line, (0, 0, 0, 0), category=dpg.mvThemeCat_Plots)
            s = dpg.add_shade_series(x_time, bid_mid, y2=bid_deep, parent="yaxis", label="Bid L2")
            dpg.bind_item_theme(s, t_bid_shade2)

            # BIDS Depth Level 1 (Best to Mid)
            with dpg.theme() as t_bid_shade1:
                with dpg.theme_component(dpg.mvShadeSeries):
                    dpg.add_theme_color(dpg.mvPlotCol_Fill, (50, 150, 255, 80), category=dpg.mvThemeCat_Plots)
                    dpg.add_theme_color(dpg.mvPlotCol_Line, (0, 0, 0, 0), category=dpg.mvThemeCat_Plots)
            s = dpg.add_shade_series(x_time, bid_best, y2=bid_mid, parent="yaxis", label="Bid L1")
            dpg.bind_item_theme(s, t_bid_shade1)

            # ASKS Depth Level 2 (Mid to Deep)
            with dpg.theme() as t_ask_shade2:
                with dpg.theme_component(dpg.mvShadeSeries):
                    dpg.add_theme_color(dpg.mvPlotCol_Fill, (200, 40, 40, 40), category=dpg.mvThemeCat_Plots)
                    dpg.add_theme_color(dpg.mvPlotCol_Line, (0, 0, 0, 0), category=dpg.mvThemeCat_Plots)
            s = dpg.add_shade_series(x_time, ask_mid, y2=ask_deep, parent="yaxis", label="Ask L2")
            dpg.bind_item_theme(s, t_ask_shade2)

            # ASKS Depth Level 1 (Best to Mid)
            with dpg.theme() as t_ask_shade1:
                with dpg.theme_component(dpg.mvShadeSeries):
                    dpg.add_theme_color(dpg.mvPlotCol_Fill, (255, 100, 100, 80), category=dpg.mvThemeCat_Plots)
                    dpg.add_theme_color(dpg.mvPlotCol_Line, (0, 0, 0, 0), category=dpg.mvThemeCat_Plots)
            s = dpg.add_shade_series(x_time, ask_best, y2=ask_mid, parent="yaxis", label="Ask L1")
            dpg.bind_item_theme(s, t_ask_shade1)

            # BEST BID LINE
            with dpg.theme() as t_best_bid:
                with dpg.theme_component(dpg.mvLineSeries):
                    dpg.add_theme_color(dpg.mvPlotCol_Line, (50, 200, 255, 200), category=dpg.mvThemeCat_Plots)
                    dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, 2, category=dpg.mvThemeCat_Plots)
            s = dpg.add_line_series(x_time, bid_best, parent="yaxis", label="Best Bid")
            dpg.bind_item_theme(s, t_best_bid)

            # BEST ASK LINE
            with dpg.theme() as t_best_ask:
                with dpg.theme_component(dpg.mvLineSeries):
                    dpg.add_theme_color(dpg.mvPlotCol_Line, (255, 100, 100, 200), category=dpg.mvThemeCat_Plots)
                    dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, 2, category=dpg.mvThemeCat_Plots)
            s = dpg.add_line_series(x_time, ask_best, parent="yaxis", label="Best Ask")
            dpg.bind_item_theme(s, t_best_ask)

        # 2. TRADES
        if x_trades_buy:
            with dpg.theme() as t_tbuy:
                with dpg.theme_component(dpg.mvScatterSeries):
                    dpg.add_theme_color(dpg.mvPlotCol_Line, (0, 255, 0, 255), category=dpg.mvThemeCat_Plots)
                    dpg.add_theme_style(dpg.mvPlotStyleVar_Marker, dpg.mvPlotMarker_Diamond, category=dpg.mvThemeCat_Plots)
                    dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, 6, category=dpg.mvThemeCat_Plots)
            s = dpg.add_scatter_series(x_trades_buy, y_trades_buy, parent="yaxis", label="Trades Buy")
            dpg.bind_item_theme(s, t_tbuy)

        if x_trades_sell:
            with dpg.theme() as t_tsell:
                with dpg.theme_component(dpg.mvScatterSeries):
                    dpg.add_theme_color(dpg.mvPlotCol_Line, (255, 0, 0, 255), category=dpg.mvThemeCat_Plots)
                    dpg.add_theme_style(dpg.mvPlotStyleVar_Marker, dpg.mvPlotMarker_Diamond, category=dpg.mvThemeCat_Plots)
                    dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, 6, category=dpg.mvThemeCat_Plots)
            s = dpg.add_scatter_series(x_trades_sell, y_trades_sell, parent="yaxis", label="Trades Sell")
            dpg.bind_item_theme(s, t_tsell)

        # 3. PRICE LINE
        if x_time and any(y_price):
            with dpg.theme() as t_price:
                with dpg.theme_component(dpg.mvLineSeries):
                    dpg.add_theme_color(dpg.mvPlotCol_Line, (255, 255, 255, 255), category=dpg.mvThemeCat_Plots)
                    dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, 2, category=dpg.mvThemeCat_Plots)
            s = dpg.add_line_series(x_time, y_price, parent="yaxis", label="Price")
            dpg.bind_item_theme(s, t_price)

        # Update Agent Time Series Plot
        dpg.delete_item("ts_yaxis", children_only=True)
        for atype, history_list in self.agent_pnl_history.items():
            ts_x = [h["time"] for h in history_list]
            ts_y = [h["pnl"] for h in history_list]
            if ts_x:
                with dpg.theme() as t_ts:
                    with dpg.theme_component(dpg.mvLineSeries):
                        dpg.add_theme_color(dpg.mvPlotCol_Line, self.agent_type_colors.get(atype, self._light_blue), category=dpg.mvThemeCat_Plots)
                        dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, 2, category=dpg.mvThemeCat_Plots)
                s = dpg.add_line_series(ts_x, ts_y, parent="ts_yaxis", label=atype)
                dpg.bind_item_theme(s, t_ts)

        if self.history:
            current_time = self.history[-1]["time"]
            t_min = max(0, current_time - self.window_size)
            t_max = current_time if current_time > self.window_size else self.window_size
            dpg.set_axis_limits("xaxis", t_min, t_max)
            dpg.fit_axis_data("yaxis")
            dpg.set_axis_limits("ts_xaxis", t_min, t_max)
            dpg.fit_axis_data("ts_yaxis")

    def run(self):
        self.setup_dpg()
        self.reset_simulation()
        
        dpg.show_viewport()
        
        while dpg.is_dearpygui_running():
            self.process_tick()
            dpg.render_dearpygui_frame()
            
        dpg.destroy_context()

def main():
    app = SimulationApp()
    app.run()

if __name__ == "__main__":
    main()
