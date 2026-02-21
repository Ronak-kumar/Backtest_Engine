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

# Try importing pandas_ta, fallback to manual calculation if not available
try:
    import pandas_ta_classic as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False
    print("Warning: pandas_ta not available. Using manual indicator calculations.")

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
    
    def __init__(self, orders_df, spot_df, prev_day_df, strategy_name="Strategy"):
        """
        Args:
            orders_df: Order book DataFrame with columns: Timestamp, Order_side, Ticker, Price, Summary
            spot_df: Spot price DataFrame with columns: Timestamp, Open, High, Low, Close, Volume
            strategy_name: Name of the strategy for title
        """
        self.orders_df = orders_df.copy()
        self.spot_df = spot_df.copy()
        self.current_date = self.spot_df["Timestamp"].iloc[-1].date()
        # self.spot_df = pd.concat([prev_day_df, self.spot_df])
        self.strategy_name = strategy_name
        # Indicator visibility states (default: all visible)
        self.indicator_visibility = {
            'supertrend': False,
            'pivot_points': False,
            'rsi': True,
            'adx': True
        }
        self._prepare_data()
        self._calculate_indicators()
        
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
    
    def _calculate_indicators(self):
        """Calculate technical indicators: Supertrend, Pivot Points, RSI, ADX."""
        # Set index for pandas_ta if needed
        df = self.spot_df.copy()
        df.set_index("Timestamp", inplace=True)
        
        # Ensure we have required columns
        if not all(col in df.columns for col in ['Open', 'High', 'Low', 'Close']):
            raise ValueError("Missing required OHLC columns")
        
        # Calculate RSI (14 period - TradingView default)
        if PANDAS_TA_AVAILABLE:
            df.ta.rsi(length=14, append=True)
            self.spot_df['RSI'] = df['RSI_14'].values
        else:
            self.spot_df['RSI'] = self._calculate_rsi(df['Close'], period=14)
        
        # Calculate ADX (14 period - TradingView default)
        if PANDAS_TA_AVAILABLE:
            df.ta.adx(length=14, append=True)
            self.spot_df['ADX'] = df['ADX_14'].values
            self.spot_df['DI+'] = df['DMP_14'].values
            self.spot_df['DI-'] = df['DMN_14'].values
        else:
            adx_data = self._calculate_adx(df, period=14)
            self.spot_df['ADX'] = adx_data['ADX'].values
            self.spot_df['DI+'] = adx_data['DI+'].values
            self.spot_df['DI-'] = adx_data['DI-'].values
        
        # Calculate Supertrend (10 period, 3.0 multiplier - TradingView default)
        if PANDAS_TA_AVAILABLE:
            df.ta.supertrend(length=10, multiplier=3.0, append=True)
            self.spot_df['Supertrend'] = df['SUPERT_10_3.0'].values
            self.spot_df['Supertrend_Direction'] = df['SUPERTd_10_3.0'].values
        else:
            st_data = self._calculate_supertrend(df, period=10, multiplier=3.0)
            self.spot_df['Supertrend'] = st_data['Supertrend'].values
            self.spot_df['Supertrend_Direction'] = st_data['Direction'].values
        
        # Calculate Pivot Points (daily pivots)
        pivot_data = self._calculate_pivot_points(df)
        self.spot_df['PP'] = pivot_data['PP'].values
        self.spot_df['R1'] = pivot_data['R1'].values
        self.spot_df['R2'] = pivot_data['R2'].values
        self.spot_df['S1'] = pivot_data['S1'].values
        self.spot_df['S2'] = pivot_data['S2'].values
        
        # Reset index if needed
        if df.index.name == "Timestamp":
            df.reset_index(inplace=True)
    
    def _calculate_rsi(self, close, period=14):
        """Calculate RSI manually."""
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_adx(self, df, period=14):
        """Calculate ADX, DI+, DI- manually."""
        high = df['High']
        low = df['Low']
        close = df['Close']
        
        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calculate Directional Movement
        dm_plus = high - high.shift()
        dm_minus = low.shift() - low
        dm_plus = dm_plus.where((dm_plus > dm_minus) & (dm_plus > 0), 0)
        dm_minus = dm_minus.where((dm_minus > dm_plus) & (dm_minus > 0), 0)
        
        # Smooth TR and DM
        atr = tr.rolling(window=period).mean()
        di_plus = 100 * (dm_plus.rolling(window=period).mean() / atr)
        di_minus = 100 * (dm_minus.rolling(window=period).mean() / atr)
        
        # Calculate ADX
        dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus)
        adx = dx.rolling(window=period).mean()
        
        return pd.DataFrame({
            'ADX': adx,
            'DI+': di_plus,
            'DI-': di_minus
        })
    
    def _calculate_supertrend(self, df, period=10, multiplier=3.0):
        """Calculate Supertrend manually (TradingView method)."""
        high = df['High']
        low = df['Low']
        close = df['Close']
        
        # Calculate ATR
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        # Calculate basic bands
        hl_avg = (high + low) / 2
        upper_band = hl_avg + (multiplier * atr)
        lower_band = hl_avg - (multiplier * atr)
        
        # Initialize arrays
        supertrend = pd.Series(index=df.index, dtype=float)
        direction = pd.Series(index=df.index, dtype=float)
        
        for i in range(len(df)):
            if i == 0:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1
            else:
                # Update upper and lower bands
                if close.iloc[i] <= supertrend.iloc[i-1]:
                    supertrend.iloc[i] = upper_band.iloc[i]
                else:
                    supertrend.iloc[i] = lower_band.iloc[i]
                
                # Determine direction
                if close.iloc[i] > supertrend.iloc[i]:
                    direction.iloc[i] = 1
                elif close.iloc[i] < supertrend.iloc[i]:
                    direction.iloc[i] = -1
                else:
                    direction.iloc[i] = direction.iloc[i-1]
        
        return pd.DataFrame({
            'Supertrend': supertrend,
            'Direction': direction
        })
    
    def _calculate_pivot_points(self, df):
        """Calculate daily pivot points (PP, R1, R2, S1, S2)."""
        # Work with a copy to avoid modifying original
        df_work = df.copy()
        
        # If Timestamp is in columns, use it; otherwise use index
        if 'Timestamp' in df_work.columns:
            df_work['Date'] = pd.to_datetime(df_work['Timestamp']).dt.date
        elif isinstance(df_work.index, pd.DatetimeIndex):
            df_work['Date'] = df_work.index.date
        else:
            # Try to convert index to datetime
            try:
                df_work['Date'] = pd.to_datetime(df_work.index).date
            except:
                # Last resort: create date column from index position
                df_work['Date'] = df_work.index
        
        # Group by date to get daily High, Low, Close
        daily_data = df_work.groupby('Date').agg({
            'High': 'max',
            'Low': 'min',
            'Close': 'last'
        })
        
        # Calculate pivots (Standard Pivot Point formula)
        daily_data['PP'] = (daily_data['High'] + daily_data['Low'] + daily_data['Close']) / 3
        daily_data['R1'] = 2 * daily_data['PP'] - daily_data['Low']
        daily_data['R2'] = daily_data['PP'] + (daily_data['High'] - daily_data['Low'])
        daily_data['S1'] = 2 * daily_data['PP'] - daily_data['High']
        daily_data['S2'] = daily_data['PP'] - (daily_data['High'] - daily_data['Low'])
        
        # Map back to original dataframe by merging on Date
        result = df_work.merge(daily_data[['PP', 'R1', 'R2', 'S1', 'S2']], 
                        left_on='Date', right_index=True, how='left')
        
        # Fill NaN values with forward fill (same pivot for the day)
        for col in ['PP', 'R1', 'R2', 'S1', 'S2']:
            result[col] = result[col].ffill().bfill()
        
        return pd.DataFrame({
            'PP': result['PP'].values,
            'R1': result['R1'].values,
            'R2': result['R2'].values,
            'S1': result['S1'].values,
            'S2': result['S2'].values
        })
    
    def plot_professional_analysis(self, save_path=None, show=True):
        """
        Create professional multi-layer visualization with technical indicators.
        
        Returns:
            plotly Figure object
        """
        # Create subplots: Main chart + RSI + ADX + Performance metrics
        fig = make_subplots(
            rows=5, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            row_heights=[0.40, 0.15, 0.15, 0, 0.30],
            subplot_titles=(
                "<b>Price Action & Order Execution</b>", 
                "<b>RSI (14)</b>",
                "<b>ADX (14)</b>",
                "",
                "<b>Trade Performance (Cumulative P&L)</b>"
            ),
            specs=[
                [{"secondary_y": True}],
                [{"secondary_y": False}],
                [{"secondary_y": False}],
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
        # TECHNICAL INDICATORS ON MAIN CHART
        # ============================================================
        
        # Supertrend (TradingView style: green when bullish, red when bearish)
        if self.indicator_visibility['supertrend'] and 'Supertrend' in self.spot_df.columns:
            st_up = self.spot_df[self.spot_df['Supertrend_Direction'] == 1]
            st_down = self.spot_df[self.spot_df['Supertrend_Direction'] == -1]
            
            if len(st_up) > 0:
                fig.add_trace(
                    go.Scatter(
                        x=st_up["Timestamp"],
                        y=st_up["Supertrend"],
                        mode="lines",
                        name="Supertrend (Bullish)",
                        line=dict(color="#00D4AA", width=2),
                        hovertemplate="<b>Supertrend</b><br>Time: %{x}<br>Price: %{y:.2f}<extra></extra>",
                        showlegend=True,
                        legendgroup="supertrend"
                    ),
                    row=1, col=1
                )
            
            if len(st_down) > 0:
                fig.add_trace(
                    go.Scatter(
                        x=st_down["Timestamp"],
                        y=st_down["Supertrend"],
                        mode="lines",
                        name="Supertrend (Bearish)",
                        line=dict(color="#F23645", width=2),
                        hovertemplate="<b>Supertrend</b><br>Time: %{x}<br>Price: %{y:.2f}<extra></extra>",
                        showlegend=True,
                        legendgroup="supertrend"
                    ),
                    row=1, col=1
                )
        
        # Pivot Points (TradingView style: PP in white, R1/R2 in red, S1/S2 in green)
        if self.indicator_visibility['pivot_points']:
            if 'PP' in self.spot_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=self.spot_df["Timestamp"],
                        y=self.spot_df["PP"],
                        mode="lines",
                        name="Pivot Point (PP)",
                        line=dict(color="#FFFFFF", width=1.5, dash="dash"),
                        hovertemplate="<b>PP</b><br>Time: %{x}<br>Price: %{y:.2f}<extra></extra>",
                        showlegend=True,
                        legendgroup="pivots",
                        visible=True if self.indicator_visibility['pivot_points'] else 'legendonly'
                    ),
                    row=1, col=1
                )
            
            if 'R1' in self.spot_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=self.spot_df["Timestamp"],
                        y=self.spot_df["R1"],
                        mode="lines",
                        name="Resistance 1 (R1)",
                        line=dict(color="#FF6B6B", width=1, dash="dot"),
                        hovertemplate="<b>R1</b><br>Time: %{x}<br>Price: %{y:.2f}<extra></extra>",
                        showlegend=True,
                        legendgroup="pivots",
                        visible=True if self.indicator_visibility['pivot_points'] else 'legendonly'
                    ),
                    row=1, col=1
                )
            
            if 'R2' in self.spot_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=self.spot_df["Timestamp"],
                        y=self.spot_df["R2"],
                        mode="lines",
                        name="Resistance 2 (R2)",
                        line=dict(color="#FF5252", width=1, dash="dot"),
                        hovertemplate="<b>R2</b><br>Time: %{x}<br>Price: %{y:.2f}<extra></extra>",
                        showlegend=True,
                        legendgroup="pivots",
                        visible=True if self.indicator_visibility['pivot_points'] else 'legendonly'
                    ),
                    row=1, col=1
                )
            
            if 'S1' in self.spot_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=self.spot_df["Timestamp"],
                        y=self.spot_df["S1"],
                        mode="lines",
                        name="Support 1 (S1)",
                        line=dict(color="#4CAF50", width=1, dash="dot"),
                        hovertemplate="<b>S1</b><br>Time: %{x}<br>Price: %{y:.2f}<extra></extra>",
                        showlegend=True,
                        legendgroup="pivots",
                        visible=True if self.indicator_visibility['pivot_points'] else 'legendonly'
                    ),
                    row=1, col=1
                )
            
            if 'S2' in self.spot_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=self.spot_df["Timestamp"],
                        y=self.spot_df["S2"],
                        mode="lines",
                        name="Support 2 (S2)",
                        line=dict(color="#66BB6A", width=1, dash="dot"),
                        hovertemplate="<b>S2</b><br>Time: %{x}<br>Price: %{y:.2f}<extra></extra>",
                        showlegend=True,
                        legendgroup="pivots",
                        visible=True if self.indicator_visibility['pivot_points'] else 'legendonly'
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
        # LAYER 7: RSI INDICATOR (TradingView style)
        # ============================================================
        if 'RSI' in self.spot_df.columns:
            rsi_visible = True if self.indicator_visibility['rsi'] else 'legendonly'
            fig.add_trace(
                go.Scatter(
                    x=self.spot_df["Timestamp"],
                    y=self.spot_df["RSI"],
                    mode="lines",
                    name="RSI (14)",
                    line=dict(color="#FFA726", width=2),
                    hovertemplate="<b>RSI</b><br>Time: %{x}<br>RSI: %{y:.2f}<extra></extra>",
                    showlegend=True,
                    visible=rsi_visible
                ),
                row=2, col=1
            )
            
            # Add RSI levels (30, 50, 70) - TradingView style
            fig.add_hline(y=70, line_dash="dash", line_color="#FF5252", line_width=1, 
                         annotation_text="Overbought (70)", row=2, col=1)
            fig.add_hline(y=50, line_dash="dot", line_color="#9E9E9E", line_width=0.5, row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="#4CAF50", line_width=1,
                         annotation_text="Oversold (30)", row=2, col=1)
            
            # Fill overbought/oversold zones
            fig.add_hrect(y0=70, y1=100, fillcolor="rgba(255, 82, 82, 0.1)", 
                         layer="below", line_width=0, row=2, col=1)
            fig.add_hrect(y0=0, y1=30, fillcolor="rgba(76, 175, 80, 0.1)", 
                         layer="below", line_width=0, row=2, col=1)
        
        # ============================================================
        # LAYER 8: ADX INDICATOR (TradingView style)
        # ============================================================
        if 'ADX' in self.spot_df.columns:
            adx_visible = True if self.indicator_visibility['adx'] else 'legendonly'
            
            # ADX line
            fig.add_trace(
                go.Scatter(
                    x=self.spot_df["Timestamp"],
                    y=self.spot_df["ADX"],
                    mode="lines",
                    name="ADX (14)",
                    line=dict(color="#9C27B0", width=2),
                    hovertemplate="<b>ADX</b><br>Time: %{x}<br>ADX: %{y:.2f}<extra></extra>",
                    showlegend=True,
                    visible=adx_visible
                ),
                row=3, col=1
            )
            
            # DI+ line
            if 'DI+' in self.spot_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=self.spot_df["Timestamp"],
                        y=self.spot_df["DI+"],
                        mode="lines",
                        name="DI+",
                        line=dict(color="#4CAF50", width=1.5),
                        hovertemplate="<b>DI+</b><br>Time: %{x}<br>DI+: %{y:.2f}<extra></extra>",
                        showlegend=True,
                        visible=adx_visible
                    ),
                    row=3, col=1
                )
            
            # DI- line
            if 'DI-' in self.spot_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=self.spot_df["Timestamp"],
                        y=self.spot_df["DI-"],
                        mode="lines",
                        name="DI-",
                        line=dict(color="#F44336", width=1.5),
                        hovertemplate="<b>DI-</b><br>Time: %{x}<br>DI-: %{y:.2f}<extra></extra>",
                        showlegend=True,
                        visible=adx_visible
                    ),
                    row=3, col=1
                )
            
            # Add ADX level (25) - TradingView style
            fig.add_hline(y=25, line_dash="dash", line_color="#FFA726", line_width=1,
                         annotation_text="Strong Trend (25)", row=3, col=1)
        
        # ============================================================
        # LAYER 9: PERFORMANCE METRICS (Cumulative P&L)
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
                row=5, col=1
            )
            
            # Add zero line
            fig.add_hline(
                y=0,
                line_dash="dash",
                line_color="gray",
                row=5, col=1
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
        
        # Build updatemenus for indicator toggles
        # Track which traces belong to which indicators
        all_visible = [True] * len(fig.data)
        supertrend_indices = []
        pivot_indices = []
        rsi_indices = []
        adx_indices = []
        
        for i, trace in enumerate(fig.data):
            name = trace.name if hasattr(trace, 'name') else ""
            if "Supertrend" in name:
                supertrend_indices.append(i)
            elif any(x in name for x in ["PP", "R1", "R2", "S1", "S2", "Pivot", "Resistance", "Support"]):
                pivot_indices.append(i)
            elif "RSI" in name:
                rsi_indices.append(i)
            elif any(x in name for x in ["ADX", "DI+", "DI-"]):
                adx_indices.append(i)
        
        # Create toggle buttons - TradingView style
        # Simple approach: buttons to show/hide indicator groups
        buttons = [
            dict(
                label="All Indicators",
                method="update",
                args=[{"visible": all_visible}]
            )
        ]
        
        # Helper to create visibility with specific indices hidden
        def hide_indices(indices):
            vis = [True] * len(fig.data)
            for idx in indices:
                if idx < len(vis):
                    vis[idx] = False
            return vis
        
        if supertrend_indices:
            buttons.append(dict(
                label="Toggle Supertrend",
                method="update",
                args=[{"visible": hide_indices(supertrend_indices)}]
            ))
        
        if pivot_indices:
            buttons.append(dict(
                label="Toggle Pivots",
                method="update",
                args=[{"visible": hide_indices(pivot_indices)}]
            ))
        
        if rsi_indices:
            buttons.append(dict(
                label="Toggle RSI",
                method="update",
                args=[{"visible": hide_indices(rsi_indices)}]
            ))
        
        if adx_indices:
            buttons.append(dict(
                label="Toggle ADX",
                method="update",
                args=[{"visible": hide_indices(adx_indices)}]
            ))
        
        updatemenus = [
            dict(
                type="buttons",
                direction="right",
                active=0,
                x=0.01,
                xanchor="left",
                y=1.02,
                yanchor="top",
                buttons=buttons,
                bgcolor="rgba(0,0,0,0.8)",
                bordercolor="rgba(255,255,255,0.3)",
                borderwidth=1,
                font=dict(size=11, color="white")
            ),
        ]
        
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
            title_font_size=20,
            updatemenus=updatemenus
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
        fig.update_yaxes(
            title_text="<b>RSI</b>",
            title_font=dict(size=13, color="white"),
            tickfont=dict(size=11),
            range=[0, 100],
            row=2, col=1
        )
        fig.update_yaxes(
            title_text="<b>ADX</b>",
            title_font=dict(size=13, color="white"),
            tickfont=dict(size=11),
            range=[0, 100],
            row=3, col=1
        )
        fig.update_yaxes(
            title_text="<b>Cumulative P&L</b>",
            title_font=dict(size=13, color="white"),
            tickfont=dict(size=11),
            row=5, col=1
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
