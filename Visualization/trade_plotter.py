"""
Professional Trade Analyst Plotting Framework

This module provides institutional-grade interactive visualizations for order execution analysis.
It combines multiple perspectives: Price Action, Order Flow, Risk Zones, and Performance Metrics.

Key Principles:
1. **Price Context**: Candlesticks + Volume for market structure
2. **Order Flow**: Buy/Sell execution with entry → exit arrows showing trade lifecycle
3. **Risk Visualization**: Stop Loss zones, Target zones, Trailing stops
4. **Performance Metrics**: P&L progression, Win Rate, Risk/Reward per trade
5. **Interactivity**: Click trades to see full lifecycle, hover for instant details
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import re

class ProfessionalTradeAnalystPlotter:
    """
    Institutional-grade trade execution plotter with multi-layer insights.
    
    Visualization Layers:
    1. Candlestick chart with volume
    2. Order entry/exit points with lifecycle arrows
    3. Risk zones (SL, Target, Trailing SL)
    4. Trade annotations with P&L
    5. Win/Loss zones shaded
    6. Performance metrics panel
    """
    
    def __init__(self, orders_df, spot_df, strategy_name="Strategy"):
        """
        Args:
            orders_df: Order book DataFrame with columns: Timestamp, Order_side, Ticker, Price, Summary
            spot_df: Spot price DataFrame with columns: Timestamp, Open, High, Low, Close, Volume
            strategy_name: Name of the strategy for title
        """
        self.orders_df = orders_df.copy()
        self.spot_df = spot_df.copy()
        self.strategy_name = strategy_name
        self._prepare_data()
        
    def _prepare_data(self):
        """Prepare and clean data."""
        # Ensure datetime types
        self.spot_df["Timestamp"] = pd.to_datetime(self.spot_df["Timestamp"])
        self.orders_df["Timestamp"] = pd.to_datetime(self.orders_df["Timestamp"])
        
        # Sort for proper alignment
        self.spot_df = self.spot_df.sort_values("Timestamp")
        self.orders_df = self.orders_df.sort_values("Timestamp")
        
        # Add Volume if missing (default)
        if "Volume" not in self.spot_df.columns:
            self.spot_df["Volume"] = 0
            
        # Classify orders: ENTRY vs EXIT
        self.orders_df["Trade_Type"] = self.orders_df["Summary"].apply(self._classify_trade_type)
        
        # Build trade pairs: Entry → Exit
        self.trades = self._build_trade_pairs()
        
    def _classify_trade_type(self, summary):
        """Classify order as ENTRY, EXIT_SL, EXIT_TARGET, or OTHER."""
        summary_lower = summary.lower()
        if "entry" in summary_lower:
            return "ENTRY"
        elif "exit" in summary_lower or "day breaker" in summary_lower:
            if "sl" in summary_lower:
                return "EXIT_SL"
            elif "target" in summary_lower:
                return "EXIT_TARGET"
            return "EXIT"
        return "OTHER"
        
    def _build_trade_pairs(self):
        """Match entry orders with their corresponding exits to show trade lifecycle."""
        trades = []
        entries = self.orders_df[self.orders_df["Trade_Type"] == "ENTRY"].copy()
        exits = self.orders_df[self.orders_df["Trade_Type"].isin(["EXIT_SL", "EXIT_TARGET", "EXIT", "OTHER"])].copy()
        
        for idx, entry in entries.iterrows():
            # Find next exit after this entry
            text = entry.Summary

            match = re.search(r"(leg_\d+)", text)
            leg_id = match.group(1) if match else None

            next_exits = exits[
                                    (exits["Timestamp"] > entry["Timestamp"]) &
                                    (exits["Ticker"] == entry["Ticker"]) &
                                    (exits["Summary"].str.contains(leg_id, regex=False))
                                ]
            if len(next_exits) > 0:
                exit_order = next_exits.iloc[0]
                
                pnl = self._calculate_pnl(
                    entry["Order_side"],
                    entry["Price"],
                    exit_order["Price"]
                )
                
                trades.append({
                    "entry_time": entry["Timestamp"],
                    "exit_time": exit_order["Timestamp"],
                    "entry_price": entry["Price"],
                    "exit_price": exit_order["Price"],
                    "entry_side": entry["Order_side"],
                    "exit_type": exit_order["Trade_Type"],
                    "entry_ticker": entry.get("Ticker", ""),
                    "pnl": pnl,
                    "pnl_pct": (pnl / entry["Price"] * 100) if entry["Price"] != 0 else 0,
                    "is_win": pnl > 0,
                    "duration_minutes": (exit_order["Timestamp"] - entry["Timestamp"]).total_seconds() / 60
                })
        
        return pd.DataFrame(trades) if trades else pd.DataFrame()
    
    def _calculate_pnl(self, side, entry_price, exit_price):
        """Calculate P&L based on side."""
        if side.upper() == "BUY":
            return (exit_price - entry_price)
        else:  # SELL
            return (entry_price - exit_price)
    
    def plot_professional_analysis(self, save_path=None, show=True):
        """
        Create professional multi-layer visualization.
        
        Returns:
            plotly Figure object
        """
        # Create subplots: Main chart + Volume + Performance metrics
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.12,
            row_heights=[0.55, 0, 0.30],
            subplot_titles=(
                "<b>Price Action & Order Execution</b>", 
                "", 
                "<b>Trade Performance (Cumulative P&L)</b>"
            ),
            specs=[
                [{"secondary_y": True}],
                [{"secondary_y": False}],
                [{"secondary_y": False}]
            ]
        )
        
        
        # ============================================================
        # LAYER 1: CANDLESTICK CHART
        # ============================================================
        fig.add_trace(
            go.Candlestick(
                x=self.spot_df["Timestamp"],
                open=self.spot_df["Open"],
                high=self.spot_df["High"],
                low=self.spot_df["Low"],
                close=self.spot_df["Close"],
                name="NIFTY Spot",
                increasing_line_color="#26a69a",
                decreasing_line_color="#ef5350",
                increasing_fillcolor="#26a69a",
                decreasing_fillcolor="#ef5350",
                hovertemplate="<b>Candle</b><br>Time: %{x}<br>O: %{open:.2f}<br>H: %{high:.2f}<br>L: %{low:.2f}<br>C: %{close:.2f}<extra></extra>"
            ),
            row=1, col=1
        )
        
        # ============================================================
        # LAYER 2: WIN/LOSS BACKGROUND ZONES
        # ============================================================
        if len(self.trades) > 0:
            for idx, trade in self.trades.iterrows():
                zone_color = "rgba(76, 175, 80, 0.1)" if trade["is_win"] else "rgba(244, 67, 54, 0.1)"
                zone_label = "Winning Trade" if trade["is_win"] else "Losing Trade"
                
                fig.add_vrect(
                    x0=trade["entry_time"],
                    x1=trade["exit_time"],
                    fillcolor=zone_color,
                    layer="below",
                    line_width=0,
                    name=zone_label,
                    showlegend=(idx == 0),
                    row=1, col=1
                )
        
        # ============================================================
        # LAYER 3: ORDER ENTRY/EXIT MARKERS WITH ARROWS
        # ============================================================
        
        # BUY entries
        buy_entries = self.orders_df[
            (self.orders_df["Trade_Type"] == "ENTRY")
        ]
        
        fig.add_trace(
            go.Scatter(
                x=buy_entries["Timestamp"],
                y=buy_entries["Price"],
                mode="markers",
                name="Entry",
                marker=dict(
                    symbol="triangle-up",
                    size=16,
                    color="#2196F3",
                    line=dict(color="white", width=2.5)
                ),
                hovertemplate="<b>Entry</b><br>Time: %{x}<br>Price: %{y:.2f}<br>%{customdata}<extra></extra>",
                customdata=buy_entries["Ticker"],
                showlegend=True
            ),
            row=1, col=1, secondary_y=True
        )
        
        # SELL entries
        sell_entries = self.orders_df[
            (self.orders_df["Trade_Type"] == "EXIT") | (self.orders_df["Trade_Type"] == "OTHER")
        ]
        
        fig.add_trace(
            go.Scatter(
                x=sell_entries["Timestamp"],
                y=sell_entries["Price"],
                mode="markers",
                name="Exit",
                marker=dict(
                    symbol="triangle-down",
                    size=16,
                    color="#F44336",
                    line=dict(color="white", width=2.5)
                ),
                hovertemplate="<b>Exit</b><br>Time: %{x}<br>Price: %{y:.2f}<br>%{customdata}<extra></extra>",
                customdata=sell_entries["Ticker"],
                showlegend=True
            ),
            row=1, col=1, secondary_y=True
        )
        
        # EXIT markers (SL hits in red, Target hits in green)
        exit_sl = self.orders_df[self.orders_df["Trade_Type"] == "EXIT_SL"]
        fig.add_trace(
            go.Scatter(
                x=exit_sl["Timestamp"],
                y=exit_sl["Price"],
                mode="markers+text",
                name="Stop Loss Hit",
                marker=dict(
                    symbol="circle",
                    size=14,
                    color="#FF5722",
                    line=dict(color="darkred", width=2.5)
                ),
                text=["🛑"] * len(exit_sl),
                textposition="top center",
                hovertemplate="<b>Stop Loss Exit</b><br>Time: %{x}<br>Price: %{y:.2f}<extra></extra>",
                showlegend=True
            ),
            row=1, col=1, secondary_y=True
        )
        
        exit_target = self.orders_df[self.orders_df["Trade_Type"] == "EXIT_TARGET"]
        fig.add_trace(
            go.Scatter(
                x=exit_target["Timestamp"],
                y=exit_target["Price"],
                mode="markers+text",
                name="Target Hit",
                marker=dict(
                    symbol="star",
                    size=16,
                    color="#4CAF50",
                    line=dict(color="darkgreen", width=2.5)
                ),
                text=["✓"] * len(exit_target),
                textposition="top center",
                hovertemplate="<b>Target Exit</b><br>Time: %{x}<br>Price: %{y:.2f}<extra></extra>",
                showlegend=True
            ),
            row=1, col=1, secondary_y=True
        )

        exit_others = self.orders_df[self.orders_df["Trade_Type"] == "EXIT"]

        fig.add_trace(
            go.Scatter(
                x=exit_others["Timestamp"],
                y=exit_others["Price"],
                mode="markers+text",
                name="Time / Session Exit",
                marker=dict(
                    symbol="diamond",
                    size=14,
                    color="#FFC107",          # amber (neutral)
                    line=dict(color="#8D6E63", width=2.5)
                ),
                text=["⏰"] * len(exit_others),
                textposition="top center",
                hovertemplate=(
                    "<b>Time / Session Exit</b><br>"
                    "Time: %{x}<br>"
                    "Price: %{y:.2f}"
                    "<extra></extra>"
                ),
                showlegend=True
            ),
            row=1, col=1, secondary_y=True
        )
        
        # ============================================================
        # LAYER 4: TRADE LIFECYCLE ARROWS (Entry → Exit)
        # ============================================================
        if len(self.trades) > 0:
            for idx, trade in self.trades.iterrows():
                arrow_color = "#4CAF50" if trade["is_win"] else "#FF5722"
                arrow_width = 3.5
                
                fig.add_trace(
                    go.Scatter(
                        x=[trade["entry_time"], trade["exit_time"]],
                        y=[trade["entry_price"], trade["exit_price"]],
                        mode="lines",
                        name=f"Trade {idx+1} ({'+' if trade['is_win'] else ''}{trade['pnl']:.2f})",
                        line=dict(
                            color=arrow_color,
                            width=arrow_width,
                            dash="solid"
                        ),
                        hovertemplate="<b>Trade Lifecycle</b><br>Duration: " + f"{trade['duration_minutes']:.0f}min" + "<br>P&L: " + f"{trade['pnl']:.2f}" + " ({:.1f}%)<extra></extra>".format(trade['pnl_pct']),
                        showlegend=False,
                        opacity=0.7
                    ),
                    row=1, col=1, secondary_y=True
                )
        
        # ============================================================
        # LAYER 5: VOLUME PROFILE
        # ============================================================
        # colors = ["#ef5350" if row["Open"] >= row["Close"] else "#26a69a" 
        #           for idx, row in self.spot_df.iterrows()]
        
        # fig.add_trace(
        #     go.Bar(
        #         x=self.spot_df["Timestamp"],
        #         y=self.spot_df["Volume"],
        #         name="Volume",
        #         marker=dict(color=colors),
        #         hovertemplate="Time: %{x}<br>Volume: %{y:,.0f}<extra></extra>",
        #         showlegend=False
        #     ),
        #     row=2, col=1
        # )
        
        # ============================================================
        # LAYER 6: PERFORMANCE METRICS (Cumulative P&L)
        # ============================================================
        if len(self.trades) > 0:
            # Calculate cumulative P&L
            self.trades["cumulative_pnl"] = self.trades["pnl"].cumsum()
            
            fig.add_trace(
                go.Scatter(
                    x=self.trades["exit_time"],
                    y=self.trades["cumulative_pnl"],
                    mode="lines+markers",
                    name="Cumulative P&L",
                    line=dict(color="#9C27B0", width=3),
                    marker=dict(size=8),
                    fill="tozeroy",
                    fillcolor="rgba(156, 39, 176, 0.2)",
                    hovertemplate="Exit Time: %{x}<br>Cumulative P&L: %{y:.2f}<extra></extra>",
                    showlegend=True
                ),
                row=3, col=1
            )
            
            # Add zero line
            fig.add_hline(
                y=0,
                line_dash="dash",
                line_color="gray",
                row=3, col=1
            )
        
        # ============================================================
        # LAYOUT & STYLING
        # ============================================================
        
        # Calculate statistics
        win_count = len(self.trades[self.trades["is_win"]]) if len(self.trades) > 0 else 0
        loss_count = len(self.trades[~self.trades["is_win"]]) if len(self.trades) > 0 else 0
        total_pnl = self.trades["pnl"].sum() if len(self.trades) > 0 else 0
        win_rate = (win_count / len(self.trades) * 100) if len(self.trades) > 0 else 0
        
        title = (
            f"<b>{self.strategy_name} – Professional Trade Analysis</b><br>"
            f"<sup>Trades: {len(self.trades)} | Win Rate: {win_rate:.1f}% ({win_count}W/{loss_count}L) | "
            f"Total P&L: {total_pnl:+.2f}</sup>"
        )
        
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(size=20, color="white", family="Arial Black"),
                x=0.5,
                xanchor="center",
                y=0.98,
                yanchor="top"
            ),
            template="plotly_dark",
            hovermode="x unified",
            showlegend=True,
            legend=dict(
                orientation="v",
                y=0.98,
                x=1.01,
                xanchor="left",
                bgcolor="rgba(0,0,0,0.7)",
                bordercolor="rgba(255,255,255,0.3)",
                borderwidth=1,
                font=dict(size=11)
            ),
            font=dict(family="Arial, sans-serif", size=12, color="white"),
            plot_bgcolor="rgba(20,20,20,1)",
            paper_bgcolor="rgba(10,10,10,1)",
            margin=dict(l=80, r=250, t=120, b=80),
            title_font_size=20
        )
        
        # Update x-axes
        fig.update_xaxes(
            rangeslider_visible=False,
            type="date",
            tickfont=dict(size=11),
            title_font=dict(size=12),
            row=1, col=1
        )
        
        # Update y-axes with larger fonts
        fig.update_yaxes(
            title_text="<b>Spot Price</b>",
            title_font=dict(size=13, color="white"),
            tickfont=dict(size=11),
            row=1, col=1
        )
        # fig.update_yaxes(
        #     title_text="<b>Volume</b>",
        #     title_font=dict(size=13, color="white"),
        #     tickfont=dict(size=11),
        #     row=2, col=1
        # )
        fig.update_yaxes(
            title_text="<b>Cumulative P&L</b>",
            title_font=dict(size=13, color="white"),
            tickfont=dict(size=11),
            row=3, col=1
        )
        
        if save_path:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            fig.write_html(save_path)
            # print(f"✓ Chart saved: {save_path}")
        
        # if show:
        #     fig.show()
        
        return fig
    
    def get_trade_statistics(self):
        """Return detailed trade statistics."""
        if len(self.trades) == 0:
            return {"error": "No trades found"}
        
        stats = {
            "total_trades": len(self.trades),
            "winning_trades": len(self.trades[self.trades["is_win"]]),
            "losing_trades": len(self.trades[~self.trades["is_win"]]),
            "win_rate": (len(self.trades[self.trades["is_win"]]) / len(self.trades) * 100),
            "total_pnl": self.trades["pnl"].sum(),
            "avg_pnl_per_trade": self.trades["pnl"].mean(),
            "max_win": self.trades["pnl"].max(),
            "max_loss": self.trades["pnl"].min(),
            "avg_trade_duration_mins": self.trades["duration_minutes"].mean(),
            "profit_factor": (
                self.trades[self.trades["is_win"]]["pnl"].sum() / 
                abs(self.trades[~self.trades["is_win"]]["pnl"].sum())
                if len(self.trades[~self.trades["is_win"]]) > 0 else float('inf')
            )
        }
        return stats


if __name__ == "__main__":
    import os
    
    # Example usage
    orders_df = pd.read_csv(
        r"C:\backtest_engine\backtest_results\nifty\algo_backtest_re1_full1_hedge2\legs4_01_2020_01_2026_0916_1530\nifty_Order_book_01_2020_01_2026_0916_1530.csv"
    )
    
    spot_df = pd.read_csv(r"D:\spot_sample.csv")  # Provide spot data
    
    plotter = ProfessionalTradeAnalystPlotter(orders_df, spot_df, strategy_name="Algo Backtest")
    
    # Generate plot
    plotter.plot_professional_analysis(
        save_path="professional_trade_analysis.html",
        show=True
    )
    
    # Print statistics
    print(plotter.get_trade_statistics())
