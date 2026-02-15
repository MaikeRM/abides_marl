import os
import contextlib

# Allow running both as `python -m app.main` and `python app/main.py`.
if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Header,
    Footer,
    DataTable,
    Static,
    Label,
    TabbedContent,
    TabPane,
)
from textual_plotext import PlotextPlot

from app.core.runner import SimulationRunner


class PriceChart(PlotextPlot):
    def __init__(self):
        super().__init__()
        self.prices = []
        self.times = []

    def update_price(self, time, price):
        self.prices.append(price)
        self.times.append(time)
        if len(self.prices) > 100:
            self.prices.pop(0)
            self.times.pop(0)

        self.plt.clear_figure()
        self.plt.plot(self.times, self.prices, marker="dot", color="green")
        self.plt.title("Price History")
        self.plt.xlabel("Time")
        self.plt.ylabel("Price")
        self.refresh()


class SimulationApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }

    TabbedContent {
        height: 1fr;
    }

    TabPane {
        height: 1fr;
    }
    
    #top_row {
        height: 2fr;
        border-bottom: solid green;
    }
    
    #bottom_row {
        height: 3fr;
    }
    
    #left_col {
        width: 50%;
        border-right: solid blue;
    }
    
    #right_col {
        width: 50%;
    }

    PriceChart {
        height: 1fr;
    }

    DataTable {
        height: 1fr;
    }
    
    .box_title {
        text-align: center;
        background: $primary;
        color: white;
        text-style: bold;
    }
    
    #stats_panel {
        height: auto;
        padding: 1;
        border-bottom: solid gray;
    }
    
    #events_log {
        height: 100%;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "reset", "Reset Simulation"),
        ("s", "toggle_simulation", "Start/Stop"),
        ("space", "step_simulation", "Step"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()

        with TabbedContent():
            with TabPane("Dashboard"):
                # Top Row: Chart
                with Container(id="top_row"):
                    yield PriceChart()

                # Bottom Row: Order Book & Trades/Stats
                with Horizontal(id="bottom_row"):
                    with Vertical(id="left_col"):
                        yield Label("Order Book (Bids | Asks)", classes="box_title")
                        yield DataTable(id="order_book")

                    with Vertical(id="right_col"):
                        with Vertical(classes="stats_box"):
                            yield Label("Market Statistics", classes="box_title")
                            yield Static(id="stats_panel")

                        yield Label("Recent Trades", classes="box_title")
                        yield DataTable(id="trades")

            with TabPane("Logs"):
                yield DataTable(id="events_log")

        yield Footer()

    def on_mount(self) -> None:
        self.runner = SimulationRunner()
        self.simulation_running = False

        self.query_one(PriceChart).plt.title("Price History")

        # Setup Order Book Table
        ob = self.query_one("#order_book", DataTable)
        ob.add_columns("Bid Qty", "Bid Price", "Ask Price", "Ask Qty")
        ob.cursor_type = "row"
        ob.zebra_stripes = True

        # Setup Trades Table
        trades = self.query_one("#trades", DataTable)
        trades.add_columns("Time", "Price", "Qty", "Side")
        trades.cursor_type = "row"
        trades.zebra_stripes = True

        # Setup Events Log Table
        events = self.query_one("#events_log", DataTable)
        events.add_columns(
            "Timestamp",
            "Sim Time",
            "Phase",
            "Kind",
            "Seq",
            "Delivery",
            "Source",
            "Destination",
            "Order Type",
            "Side",
            "Qty",
            "Price",
            "Order ID",
            "Cancel All",
            "Text",
        )
        events.cursor_type = "row"
        events.zebra_stripes = True

        # Initialize Simulation
        self.reset_simulation()

        # Timer for updates
        self.timer = self.set_interval(0.1, self.tick, pause=True)
        self.update_ui()

    def reset_simulation(self):
        # Redirect standard output to suppress print calls during reset
        with open(os.devnull, "w") as f, contextlib.redirect_stdout(f):
            self.runner.reset()

        self.query_one(PriceChart).prices = []
        self.query_one(PriceChart).times = []
        self.query_one("#order_book", DataTable).clear()
        self.query_one("#trades", DataTable).clear()
        self.query_one("#events_log", DataTable).clear()
        self.update_ui()

    def action_reset(self):
        self.reset_simulation()

    def action_toggle_simulation(self):
        self.simulation_running = not self.simulation_running
        if self.simulation_running:
            self.timer.resume()
        else:
            self.timer.pause()

    def action_step_simulation(self):
        self.runner.step()
        self.update_ui()

    def tick(self):
        if self.simulation_running:
            # Run multiple steps per tick for speed (20 steps per 0.1s = 200 steps/sec)
            for _ in range(20):
                if not self.runner.step():
                    self.simulation_running = False
                    self.timer.pause()
                    break
            self.update_ui()

    def update_ui(self):
        state = self.runner.get_state()
        if not state:
            return

        # Update Stats
        time_val = state.get("time", 0)
        last_price = state.get("last_price", 0.0)
        fund_val = state.get("fundamental_value", 0.0)

        stats = f"Time: {time_val}\n"
        stats += f"Last Price: {last_price:.2f}\n"
        stats += f"Fundamental Value: {fund_val:.2f}"
        self.query_one("#stats_panel", Static).update(stats)

        # Update Chart
        self.query_one(PriceChart).update_price(time_val, last_price)

        # Update Order Book
        ob = self.query_one("#order_book", DataTable)
        ob.clear()

        bids = state.get("bids", [])
        asks = state.get("asks", [])

        max_len = max(len(bids), len(asks))
        for i in range(max_len):
            b_qty = str(bids[i]["qty"]) if i < len(bids) else ""
            b_price = f"{bids[i]['price']:.2f}" if i < len(bids) else ""

            a_price = f"{asks[i]['price']:.2f}" if i < len(asks) else ""
            a_qty = str(asks[i]["qty"]) if i < len(asks) else ""

            ob.add_row(b_qty, b_price, a_price, a_qty)

        # Update Trades
        trades = self.query_one("#trades", DataTable)
        trades.clear()
        for t in state.get("history", []):
            trades.add_row(
                str(t["time"]), f"{t['price']:.2f}", str(t["qty"]), t["side"]
            )

        # Update Events Log
        events = self.query_one("#events_log", DataTable)
        events.clear()
        for event in state.get("events", []):
            if (
                event.get("kind") == "LOG"
                or event.get("phase") == "LOG"
                or event.get("kind") == "WAKEUP"
            ):
                continue
            data = event.get("data", {})
            events.add_row(
                event.get("timestamp", ""),
                str(event.get("sim_time", "")),
                event.get("phase", ""),
                event.get("kind", ""),
                str(event.get("seq", "")),
                str(event.get("delivery", "")),
                event.get("src_name", str(event.get("src", ""))),
                event.get("dst_name", str(event.get("dst", ""))),
                str(data.get("order_type", "")),
                str(data.get("side", "")),
                str(data.get("qty", "")),
                str(data.get("price", "")),
                str(data.get("order_id", "")),
                str(data.get("cancel_all", "")),
                str(data.get("text", "")),
            )


def main():
    app = SimulationApp()
    app.run()


if __name__ == "__main__":
    main()
