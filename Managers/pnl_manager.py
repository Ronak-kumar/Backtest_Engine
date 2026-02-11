"""
PNL Manager Module

This module provides functionality for tracking positions and calculating profit & loss
on a per-minute basis. It maintains position state and calculates realized/unrealized P&L.

Classes:
    Position: Dataclass representing a single position
    PNLManager: Main manager class for P&L tracking and calculation
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
import polars as pl
import pandas as pd


@dataclass
class Position:
    """
    Represents a single trading position.
    
    Attributes:
        position_id: Unique identifier for the position
        leg_id: Leg identifier
        unique_leg_id: Unique leg identifier (e.g., "leg_1.5" for lazy legs)
        trading_symbol: Trading symbol (e.g., "NIFTY24JAN20000CE")
        instrument_type: CE or PE
        strike: Strike price
        expiry: Expiry date
        entry_timestamp: Entry timestamp
        entry_price: Entry price
        quantity: Number of lots/contracts
        position_type: BUY or SELL
        current_ltp: Current last traded price
        unrealized_pnl: Current unrealized P&L
        stop_loss: Stop loss level
        target_price: Target price level
        trailing_sl: Trailing stop loss level (if activated)
        leg_dict: Original leg configuration dictionary
        is_active: Whether position is still open
        exit_timestamp: Exit timestamp (None if still open)
        exit_price: Exit price (None if still open)
        exit_reason: Reason for exit (None if still open)
        realized_pnl: Realized P&L after exit
        sd_level: Standard deviation level at entry
    """
    position_id: str
    leg_id: str
    unique_leg_id: str
    trading_symbol: str
    instrument_type: str
    strike: float
    expiry: str
    entry_timestamp: datetime
    entry_price: float
    quantity: int
    position_type: str  # BUY or SELL
    leg_dict: Dict[str, Any]
    
    # Dynamic fields
    current_ltp: float = 0.0
    unrealized_pnl: float = 0.0
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    trailing_sl: Optional[float] = None
    is_active: bool = True

    # Compare type fields
    stop_loss_compare_type: str = ""
    target_compare_type: str = ""
    
    # Exit fields
    exit_timestamp: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    realized_pnl: float = 0.0
    
    # Additional tracking
    sd_level: str = ""

    # OHLCV data can be added here if needed in future
    OHLCV_data: pl.DataFrame = pl.DataFrame()
    
    def calculate_pnl(self, ltp: float) -> float:
        """
        Calculate P&L for current LTP.
        
        Args:
            ltp: Current last traded price
            
        Returns:
            P&L amount (positive for profit, negative for loss)
        """
        if self.position_type.upper() == "BUY":
            return round((ltp - self.entry_price) * self.quantity, 2)
        else:  # SELL
            return round((self.entry_price - ltp) * self.quantity, 2)
    
    def update_ltp(self, ltp: float):
        """
        Update current LTP and unrealized P&L.
        
        Args:
            ltp: New last traded price
        """
        self.current_ltp = ltp
        if self.is_active:
            self.unrealized_pnl = self.calculate_pnl(ltp)
    
    def close_position(self, exit_timestamp: datetime, exit_price: float, exit_reason: str):
        """
        Close the position and calculate realized P&L.
        
        Args:
            exit_timestamp: Timestamp of exit
            exit_price: Exit price
            exit_reason: Reason for exit
        """
        self.is_active = False
        self.current_ltp = exit_price
        self.exit_timestamp = exit_timestamp
        self.exit_price = exit_price
        self.exit_reason = exit_reason
        self.realized_pnl = self.calculate_pnl(exit_price)
        self.unrealized_pnl = 0.0


class PNLManager:
    """
    PNL Manager for tracking positions and calculating profit & loss.
    
    This class maintains all active and closed positions, updates LTPs per minute,
    and calculates both realized and unrealized P&L.
    
    Attributes:
        active_positions: Dictionary of currently active positions {position_id: Position}
        closed_positions: List of closed positions
        pnl_history: List of per-minute P&L snapshots
        total_realized_pnl: Cumulative realized P&L
        total_unrealized_pnl: Current unrealized P&L
    """
    
    def __init__(self):
        """Initialize PNL Manager."""
        self.active_positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []
        self.pnl_history: List[Dict[str, Any]] = []
        self.total_realized_pnl: float = 0.0
        self.total_unrealized_pnl: float = 0.0
        self._position_counter: int = 0
        self.charges_params: Dict[str, float] = {}
        # Order book to track executed orders (entries/exits)
        # Each entry: {"Timestamp","Ticker","Order_side","Price","Summary"}
        self.order_book: List[Dict[str, Any]] = []
    
    def create_position(
        self,
        leg_id: str,
        unique_leg_id: str,
        trading_symbol: str,
        instrument_type: str,
        strike: float,
        expiry: str,
        entry_timestamp: datetime,
        entry_price: float,
        quantity: int,
        position_type: str,
        leg_dict: Dict[str, Any],
        sd_level: str = "",
        stop_loss_compare_type: str = "",
        target_compare_type: str = "",
        OHLCV_data: pl.DataFrame = pl.DataFrame(),
        sl_value: Optional[float] = None,
        target_price: Optional[float] = None
    ) -> Position:
        """
        Create a new position.
        
        Args:
            leg_id: Leg identifier
            unique_leg_id: Unique leg identifier
            trading_symbol: Trading symbol
            instrument_type: CE or PE
            strike: Strike price
            expiry: Expiry date string
            entry_timestamp: Entry timestamp
            entry_price: Entry price
            quantity: Number of lots/contracts
            position_type: BUY or SELL
            leg_dict: Leg configuration dictionary
            sd_level: Standard deviation level at entry
            
        Returns:
            Created Position object
        """
        self._position_counter += 1
        position_id = f"{unique_leg_id}_{self._position_counter}"
        
        # Calculate initial stop loss and target
        if sl_value is not None:
            stop_loss = round(sl_value, 2)
        else:
            stop_loss = round(self._calculate_stop_loss(entry_price, leg_dict, position_type), 2)
        if target_price is not None:
            target_price = round(target_price, 2)
        else:
            target_price = round(self._calculate_target_price(entry_price, leg_dict, position_type), 2)
        
        position = Position(
            position_id=position_id,
            leg_id=leg_id,
            unique_leg_id=unique_leg_id,
            trading_symbol=trading_symbol,
            instrument_type=instrument_type,
            strike=strike,
            expiry=expiry,
            entry_timestamp=entry_timestamp,
            entry_price=entry_price,
            quantity=quantity,
            position_type=position_type,
            leg_dict=leg_dict,
            current_ltp=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            sd_level=sd_level,
            stop_loss_compare_type=stop_loss_compare_type,
            target_compare_type=target_compare_type,
            OHLCV_data=OHLCV_data
        )
        
        self.active_positions[position_id] = position

        # Record execution in order book
        try:
            self.record_order(
                timestamp=entry_timestamp,
                ticker=trading_symbol,
                order_side=position_type,
                price=entry_price,
                summary=f"Executed entry of leg {leg_id}, of strike {strike} with sl {stop_loss}, target {target_price}"
            )
        except Exception:
            # Non-fatal: ensure position still created even if order book fails
            pass
        return position
    
    def _calculate_stop_loss(
        self,
        entry_price: float,
        leg_dict: Dict[str, Any],
        position_type: str
    ) -> Optional[float]:
        """
        Calculate stop loss level.
        
        Args:
            entry_price: Entry price
            leg_dict: Leg configuration
            position_type: BUY or SELL
            
        Returns:
            Stop loss price level or None
        """
        if not leg_dict.get("stoploss_toggle", False):
            return None
        
        stoploss_type = leg_dict.get("stoploss_type", "Points")
        stoploss_value = leg_dict.get("stoploss_value", 0)
        
        if stoploss_value == 0:
            return None
        
        if stoploss_type == "Points":
            # Points-based SL
            if position_type.upper() == "BUY":
                return entry_price - stoploss_value
            else:  # SELL
                return entry_price + stoploss_value
        
        else:
            # Percentage-based SL (including weekday-specific)
            # stoploss_value is already in decimal form (e.g., 0.10 for 10%)
            if position_type.upper() == "BUY":
                return entry_price * (1 - stoploss_value)
            else:  # SELL
                return entry_price * (1 + stoploss_value)
    
    def _calculate_target_price(
        self,
        entry_price: float,
        leg_dict: Dict[str, Any],
        position_type: str
    ) -> Optional[float]:
        """
        Calculate target price level.
        
        Args:
            entry_price: Entry price
            leg_dict: Leg configuration
            position_type: BUY or SELL
            
        Returns:
            Target price level or None
        """
        if not leg_dict.get("target_toggle", False):
            return None
        
        target_value = leg_dict.get("target_value", 0)  # Already in decimal form
        
        if target_value == 0:
            return None
        
        if position_type.upper() == "BUY":
            return entry_price * (1 + target_value)
        else:  # SELL
            return entry_price * (1 - target_value)
    
    def update_all_ltps(
        self,
        current_timestamp: datetime,
        TRADE_DICT: Dict[str, float],
        options_extractor_con: object
    ):
        """
        Update LTPs for all active positions.
        
        Args:
            current_timestamp: Current timestamp
            ltp_dict: Dictionary mapping trading_symbol to LTP
        """
        # index extraction for trade dict update 
        symbol_to_idx = {s: i for i, s in enumerate(TRADE_DICT["TradingSymbol"])}
        for position in self.active_positions.values():
            intraday_df = options_extractor_con.intraday_options_df[position.expiry]
            ohlcv_row = (
                intraday_df
                .filter(
                    (pl.col("Ticker") == position.trading_symbol) &
                    (pl.col("Timestamp") <= current_timestamp)
                ).tail(1)

            )
            ohlcv_row = ohlcv_row.row(0, named=True)
            ohlcv_row['Close'] = round(ohlcv_row['Close'],2)
            ohlcv_row['Open'] = round(ohlcv_row['Open'],2)
            ohlcv_row['High'] = round(ohlcv_row['High'],2)
            ohlcv_row['Low'] = round(ohlcv_row['Low'],2)
            position.OHLCV_data = ohlcv_row
            ltp = ohlcv_row['Close']   

            position.update_ltp(ltp)

            # Update TRADE_DICT LTP
            idx = symbol_to_idx.get(position.trading_symbol)
            if idx is not None:
                TRADE_DICT["Timestamp"][idx] = current_timestamp
                TRADE_DICT["LTP"][idx] = position.current_ltp
                TRADE_DICT["PnL"][idx] = position.unrealized_pnl

        
        # Recalculate total unrealized P&L
        self._update_total_unrealized_pnl()
 
        return TRADE_DICT
    
    def update_position_ltp(
        self,
        position_id: str,
        ltp: float
    ):
        """
        Update LTP for a specific position.
        
        Args:
            position_id: Position ID
            ltp: New LTP
        """
        if position_id in self.active_positions:
            self.active_positions[position_id].update_ltp(ltp)
            self._update_total_unrealized_pnl()
    
    def close_position(
        self,
        position_id: str,
        exit_timestamp: datetime,
        exit_price: float,
        exit_reason: str
    ) -> Optional[Position]:
        """
        Close a position and move it to closed positions.
        
        Args:
            position_id: Position ID to close
            exit_timestamp: Exit timestamp
            exit_price: Exit price
            exit_reason: Reason for exit
            
        Returns:
            Closed Position object or None if position not found
        """
        if position_id not in self.active_positions:
            return None
        
        position = self.active_positions[position_id]
        position.close_position(exit_timestamp, exit_price, exit_reason)
        
        # Move to closed positions
        self.closed_positions.append(position)
        del self.active_positions[position_id]
        
        # Update total realized P&L
        self.total_realized_pnl += position.realized_pnl
        
        # Update total unrealized P&L (since one position is removed)
        self._update_total_unrealized_pnl()
        
        # Record exit in order book
        try:
            self.record_order(
                timestamp=exit_timestamp,
                ticker=position.trading_symbol,
                order_side=("Buy" if position.position_type == "Sell" else "Sell"),
                price=exit_price,
                summary=position.exit_reason
            )
        except Exception:
            pass
        
        return position
    
    def get_position(self, position_id: str) -> Optional[Position]:
        """
        Get a position by ID.
        
        Args:
            position_id: Position ID
            
        Returns:
            Position object or None
        """
        return self.active_positions.get(position_id)
    
    def get_positions_by_leg(self, unique_leg_id: str) -> List[Position]:
        """
        Get all active positions for a specific leg.
        
        Args:
            unique_leg_id: Unique leg identifier
            
        Returns:
            List of Position objects
        """
        return [
            pos for pos in self.active_positions.values()
            if pos.unique_leg_id == unique_leg_id
        ]
    
    def get_total_pnl(self) -> Dict[str, float]:
        """
        Get total P&L breakdown.
        
        Returns:
            Dictionary with realized, unrealized, and total P&L
        """
        return {
            'realized_pnl': self.total_realized_pnl,
            'unrealized_pnl': self.total_unrealized_pnl,
            'total_pnl': self.total_realized_pnl + self.total_unrealized_pnl
        }
    
    def get_position_count(self) -> Dict[str, int]:
        """
        Get position counts.
        
        Returns:
            Dictionary with active and closed position counts
        """
        return {
            'active': len(self.active_positions),
            'closed': len(self.closed_positions),
            'total': len(self.active_positions) + len(self.closed_positions)
        }
    
    def _update_total_unrealized_pnl(self):
        """Update total unrealized P&L from all active positions."""
        self.total_unrealized_pnl = sum(
            pos.unrealized_pnl for pos in self.active_positions.values()
        )
    
    def _record_pnl_snapshot(self, timestamp: datetime, spot_price: float):
        """
        Record a P&L snapshot at current timestamp.
        
        Args:
            timestamp: Current timestamp
        """
        for position in self.active_positions.values():
            self.pnl_history.append({
                "Entry_Timestamp": position.entry_timestamp,
                "Timestamp": timestamp,
                "Spot": spot_price,
                "Trading_symbol": position.trading_symbol,
                "Status": "OPEN",
                "Entry_price": position.entry_price,
                "Qty": position.quantity,
                "LTP": position.current_ltp,
                "PnL": position.unrealized_pnl,
                "Stop_loss": position.stop_loss,
                "Target": position.target_price,
                "Expiry": position.expiry,
            })

        for position in self.closed_positions:
            self.pnl_history.append({
                "Entry_Timestamp": position.entry_timestamp,
                "Timestamp": timestamp,
                "Spot": spot_price,
                "Trading_symbol": position.trading_symbol,
                "Status": "CLOSED",
                "Entry_price": position.entry_price,
                "Qty": position.quantity,
                "LTP": position.exit_price,
                "PnL": position.realized_pnl,
                "Stop_loss": position.stop_loss,
                "Target": position.target_price,
                "Expiry": position.expiry,
            })
    
    def get_pnl_dataframe(self) -> pl.DataFrame:
        """
        Get P&L history as a Polars DataFrame.
        
        Returns:
            Polars DataFrame with P&L history
        """
        if not self.pnl_history:
            return pl.DataFrame()
        
        return pl.DataFrame(self.pnl_history)
    
    def get_positions_dataframe(self, include_closed: bool = True) -> pl.DataFrame:
        """
        Get positions as a Polars DataFrame.
        
        Args:
            include_closed: Whether to include closed positions
            
        Returns:
            Pandas DataFrame with position details
        """
        positions = list(self.active_positions.values())
        
        if include_closed:
            positions.extend(self.closed_positions)
        
        if not positions:
            return pl.DataFrame()
        
        data = []
        for pos in positions:
            data.append({
                'position_id': pos.position_id,
                'leg_id': pos.leg_id,
                'unique_leg_id': pos.unique_leg_id,
                'trading_symbol': pos.trading_symbol,
                'instrument_type': pos.instrument_type,
                'strike': pos.strike,
                'expiry': pos.expiry,
                'entry_timestamp': pos.entry_timestamp,
                'entry_price': pos.entry_price,
                'quantity': pos.quantity,
                'position_type': pos.position_type,
                'current_ltp': pos.current_ltp,
                'unrealized_pnl': pos.unrealized_pnl,
                'is_active': pos.is_active,
                'exit_timestamp': pos.exit_timestamp,
                'exit_price': pos.exit_price,
                'exit_reason': pos.exit_reason,
                'realized_pnl': pos.realized_pnl,
                'sd_level': pos.sd_level,
                'stop_loss': pos.stop_loss,
                'target_price': pos.target_price
            })
        
        return pl.DataFrame(data)
    
    def day_file_creator(self, date_str: str, strategy_save_dir) -> None:
        """Create day file for PNL history."""

        day_df, charges_df = self.tradelog_dataframe()
        filesave_dir = strategy_save_dir / date_str[:4] / date_str[5:-3]
        filesave_dir.mkdir(parents=True, exist_ok=True)


        day_df = day_df.with_columns(pl.lit("TRADE").alias("RowType"))
        charges_df = charges_df.with_columns(pl.lit("CHARGES").alias("RowType"))

        final_df = pl.concat([day_df, charges_df], how="diagonal")

        
        day_file_path = filesave_dir / f"{date_str}_tradelog.parquet"
        final_df.write_parquet(day_file_path)

        self.write_orderbook_frame(strategy_save_dir)

    def tradelog_dataframe(self) -> pl.DataFrame:
        df = pl.DataFrame(self.pnl_history)
        total_df = (
            df.group_by("Timestamp")
            .agg(pl.col("PnL").sum().alias("PnL"))
            .with_columns([
                pl.lit(None).alias("Entry_Timestamp"),
                pl.lit("Total").alias("Trading_symbol"),
                pl.lit("").alias("Status"),
                pl.lit(None).alias("Spot"),
                pl.lit(None).alias("Entry_price"),
                pl.lit(None).alias("Qty"),
                pl.lit(None).alias("LTP"),
                pl.lit(None).alias("Stop_loss"),
                pl.lit(None).alias("Target"),
                pl.lit(None).alias("Expiry"),
            ])
            .select(df.columns)   # 👈 enforce same column order
        )

        last_total_row = df.filter(
                                            pl.col("Timestamp") == pl.col("Timestamp").max()
                                        )

        calculated_charges_df = self._charges_dataframe(last_total_row)  # To ensure charges are calculated if needed

        final_df = (
            pl.concat([df, total_df])
            .with_columns(
                pl.when(pl.col("Trading_symbol") == "Total")
                    .then(1)
                    .otherwise(0)
                    .alias("_is_total")
            )
            .sort(["Timestamp", "_is_total"])
            .drop("_is_total")
        )
        return final_df, calculated_charges_df

    def _charges_dataframe(self, last_entry: pl.DataFrame) -> pl.DataFrame:
        """Generate charges DataFrame (stub for future implementation)."""
        # Placeholder for charges calculation logic
        charges_df = last_entry  # Replace with actual charges calculation
        charges_df = charges_df.with_columns([

        # --- Buy / Sell values ---
        (pl.col("Entry_price") * pl.col("Qty"))
            .round(2)
            .alias("Buy Value"),

        (pl.col("LTP") * pl.col("Qty"))
            .round(2)
            .alias("Sell Value"),

        ])

        charges_df = charges_df.with_columns([

        # --- Turnover ---
        (pl.col("Buy Value") + pl.col("Sell Value"))
            .alias("Turnover"),
        ])

        charges_df = charges_df.with_columns([
            (
                pl.lit(self.charges_params.get("brokerage", 7)) * 2
            ).alias("Brokerage")
        ])

        charges_df = charges_df.with_columns([

        # --- Exchange + SEBI ---
        (pl.col("Turnover") * self.charges_params.get("exchange_tc", 0.0035))
            .alias("Exchange TC"),

        (pl.col("Turnover") * self.charges_params.get("sebi_tc", 0.0001))
            .alias("SEBI TC"),
                    ])


        charges_df = charges_df.with_columns([

            # --- GST ---
            (
                (pl.col("Brokerage")
                + pl.col("Exchange TC")
                + pl.col("SEBI TC"))
                * self.charges_params.get("gst", 18/100)
            ).round(2).alias("GST"),

            # --- STT & Stamp Duty ---
            (pl.col("Sell Value") * self.charges_params.get("stt", 0.025))
                .alias("STT"),

            (pl.col("Buy Value") * self.charges_params.get("stamp_duty", 0.003))
                .alias("Stamp Duty"),
        ])

        charges_df = charges_df.with_columns([


            # --- Slippage (entry + exit) ---
            (
                ((pl.col("Entry_price") * self.charges_params.get("slippage_percentage", 0.01))
                + (pl.col("LTP") * self.charges_params.get("slippage_percentage", 0.01))) * pl.col("Qty")
                ).round(2
            ).alias("Slippage")])


        charges_df = charges_df.with_columns([

            # --- Total Charges ---
            (
                pl.col("Brokerage")
                + pl.col("Exchange TC")
                + pl.col("SEBI TC")
                + pl.col("GST")
                + pl.col("STT")
                + pl.col("Stamp Duty")
                + pl.col("Slippage")
            ).round(2).alias("Sum"),
                                            ])



        charges_df = charges_df.with_columns([

            # --- Avg per lot ---
            (pl.col("Sum") / pl.col("Qty"))
                .round(4)
                .alias("AvgLotSum")

        ])

        charges_df = charges_df.with_columns(
            pl.when(pl.row_index() == pl.count() - 1)
            .then((pl.col("PnL").sum() - pl.col("Sum").sum()))
            .otherwise(None)
            .alias("Final PnL").round(2)
        )

        return charges_df

    def reset(self):
        """Reset PNL Manager (for new day or strategy reset)."""
        self.active_positions.clear()
        self.closed_positions.clear()
        self.pnl_history.clear()
        self.total_realized_pnl = 0.0
        self.total_unrealized_pnl = 0.0
        self._position_counter = 0
        self.order_book.clear()

    def record_order(self, timestamp: datetime, ticker: str, order_side: str, price: float, summary: str) -> None:
        """
        Record an executed order into the order book.

        Args:
            timestamp: Execution timestamp
            ticker: Trading symbol
            order_side: 'BUY', 'SELL' or descriptive side
            price: Executed price
            summary: Short summary string
        """
        self.order_book.append({
            "Timestamp": timestamp,
            "Ticker": ticker,
            "Order_side": order_side,
            "Price": round(float(price), 2) if price is not None else None,
            "Summary": summary,
        })

    def get_order_book_frame(self):
        if not self.order_book:
            return pl.DataFrame()
        return pl.DataFrame(self.order_book)


    def write_orderbook_frame(self, strategy_save_dir) -> None:
        """
        Write the order book frame.
        """
        order_book_df = self.get_order_book_frame()

        file_path = strategy_save_dir / 'order_book.csv'

        # 1️⃣ Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 2️⃣ Check if file exists
        file_exists = file_path.exists()

        # 3️⃣ Write
        if not file_exists:
            # First write → include header
            order_book_df.write_csv(file_path)
        else:
            # Append → no header
            with open(file_path, "ab") as f:
                order_book_df.write_csv(f, include_header=False)
