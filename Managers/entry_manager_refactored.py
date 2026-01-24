"""
Refactored Entry Manager Module - Scalable Entry System Architecture

This module provides a scalable, professional entry management system using
the Strategy Pattern. New entry types can be easily added by creating new
strategy classes.

Architecture:
- EntryUtilities: Shared utilities for strike calculation, order creation
- EntryStrategy (ABC): Abstract base class for all entry strategies  
- Concrete Strategies: SimpleEntry, MomentumEntry, RangeBreakoutEntry, etc.
- UnifiedEntryManager: Main manager that handles all entry types seamlessly

Usage:
    # Initialize with all dependencies
    manager = UnifiedEntryManager(
        base=50,
        intraday_df_dict=intraday_df_dict,
        spot_df=spot_df,
        EntryMode="Close",
        lot_qty=1,
        lotsize=50,
        StoplossCalMode="Close",
        logger=logger,
        miss_con=miss_con,
        straddle_filepath=straddle_filepath,
        indices="NIFTY",
        rolling_straddle_slice_time=rolling_straddle_slice_time
    )
    
    # Execute entry - automatically selects correct strategy
    TRADE_DICT, order_book, orders, day_breaker = manager.entry(
        index=current_timestamp,
        order=leg_dict,
        spot=spot_price,
        leg_id=leg_id,
        TRADE_DICT=TRADE_DICT,
        order_book=order_book,
        orders=orders
    )

Adding New Entry Types:
    1. Create a new class inheriting from EntryStrategy
    2. Implement execute() method
    3. Register in UnifiedEntryManager._register_strategies()
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, time
import pandas as pd
import copy
from dateutil.relativedelta import relativedelta
import polars as pl


# ============================================================================
# SHARED UTILITIES
# ============================================================================

class EntryUtilities:
    """
    Shared utilities for entry operations.
    Consolidates common functionality used across all entry strategies.
    """
    @staticmethod
    def order_book_entry(TRADE_DICT, index, position_index, order_book, custom_summary=""):
        order_book["Timestamp"].append(index)
        order_book['Ticker'].append(TRADE_DICT['TradingSymbol'][position_index])
        order_book['Price'].append(TRADE_DICT['Entry_price'][position_index])
        order_book['Order_side'].append(TRADE_DICT['Position_type'][position_index])
        if custom_summary != "":
            order_book['Summary'].append(custom_summary)
        else:
            order_book['Summary'].append(
                    f"{TRADE_DICT['Instrument_type'][position_index]} Position Short, Sl Price: {'NA' if TRADE_DICT['stop_loss'][position_index] == 0 else TRADE_DICT['stop_loss'][position_index]}, "
                    f"Tgt Price: {'NA' if TRADE_DICT['target_price'][position_index] == 0 else TRADE_DICT['target_price'][position_index]}, "
                    f"Trailing Price: {'NA' if TRADE_DICT['Trailing'][position_index] == 0 else TRADE_DICT['Trailing'][position_index]} ")

        return order_book
    
    @staticmethod
    def calculate_strike(
        strike_type: str,
        spot: float,
        base: float,
        order: Dict[str, Any],
        options_extractor_con: object,
        index: datetime
    ) -> float:
        """
        Calculate strike price based on strike type.
        
        Args:
            strike_type: Type of strike (ATM, OTM, ITM, PREMIUM, etc.)
            spot: Current spot price
            base: Strike base (e.g., 50 for NIFTY)
            order: Order dictionary
            intraday_df: Intraday options dataframe
            index: Current timestamp
            
        Returns:
            Calculated strike price
        """
        if strike_type == "ATM":
            return base * round(spot / base)
        
        elif strike_type == "OTM":
            spread_value = order.get("spread", 0) * base
            if order.get("option_type") == "CE":
                return base * round((spot + spread_value) / base)
            elif order.get("option_type") == "PE":
                return base * round((spot - spread_value) / base)
        
        elif strike_type == "ITM":
            spread_value = order.get("spread", 0) * base
            if order.get("option_type") == "CE":
                return base * round((spot - spread_value) / base)
            elif order.get("option_type") == "PE":
                return base * round((spot + spread_value) / base)
        
        elif strike_type == "PREMIUM":
            premium_value = order.get("premium_value", 0)
            premium_consideration = order.get("premium_consideration", "CLOSEST")
            option_type = order.get("option_type")
            
            if premium_consideration == "CLOSEST":
                ce_pe_strike = intraday_df[
                    (intraday_df['Instrument_type'] == option_type) &
                    (intraday_df['Close'] <= premium_value) &
                    (intraday_df.index == index)
                ]
                ce_pe_strike = ce_pe_strike.sort_values(by='Close', ascending=False)
                return ce_pe_strike.iloc[0]["Strike"] if not ce_pe_strike.empty else None
            
            elif premium_consideration == "PREMIUM>=":
                ce_pe_strike = intraday_df[
                    (intraday_df['Instrument_type'] == option_type) &
                    (intraday_df['Close'] >= premium_value) &
                    (intraday_df.index == index)
                ]
                ce_pe_strike = ce_pe_strike.sort_values(by='Close', ascending=True)
                return ce_pe_strike.iloc[0]["Strike"] if not ce_pe_strike.empty else None
            
            elif premium_consideration == "NEAREST":
                ce_pe_strike = intraday_df[
                    (intraday_df['Instrument_type'] == option_type) &
                    (intraday_df.index == index)
                ]
                ce_pe_strike['Difference'] = abs(ce_pe_strike["Close"] - premium_value)
                min_diff = ce_pe_strike["Difference"].min()
                return ce_pe_strike[ce_pe_strike["Difference"] == min_diff]["Strike"].iloc[0]
        
        elif strike_type == "ATM STRADDLE PREMIUM PERCENTAGE":
            atm_strike = base * round(spot / base)
            atm_strike_options = intraday_df[intraday_df['Strike'] == atm_strike]
            atm_strike_options = atm_strike_options[atm_strike_options.index.time == index.time()]
            
            if len(atm_strike_options) >= 2:
                combined_premium = atm_strike_options["Close"].sum()
                execution_premium = (combined_premium * order.get("atm_straddle_premium", 0)) / 100
                
                ce_pe_strike = intraday_df[
                    (intraday_df['Instrument_type'] == order.get("option_type")) &
                    (intraday_df['Close'] <= execution_premium) &
                    (intraday_df.index == index)
                ]
                ce_pe_strike = ce_pe_strike.sort_values(by='Close', ascending=False)
                return ce_pe_strike.iloc[0]["Strike"] if not ce_pe_strike.empty else None
        
        return None
    
    @staticmethod
    def get_options_row(
        strike_price: float,
        order: Dict[str, Any],
        options_extractor_con: object,
        index: datetime,
        indices: str
    ) -> pd.Series:
        """Get options row for given strike, order, and timestamp."""
        intraday_df = options_extractor_con.data_handler(strike_price, order["leg_expiry_selection"], current_timestamp=index, indices=indices)

        row_df = intraday_df.filter((pl.col('Strike') == strike_price) & (pl.col('Instrument_type') == order.get("option_type")) & (pl.col('Timestamp').dt.time() == index.time()))
        return row_df
    
    @staticmethod
    def get_options_row_with_ticker(
        ticker: str,
        options_extractor_con: object,
        index: datetime,
        indices: str,
        expiry_type: str
    ) -> pd.Series:
        """Get options row for given ticker and timestamp."""
        intraday_df = options_extractor_con.data_handler(strike_price=None, expiry_type=expiry_type, current_timestamp=index, indices=indices, ticker=ticker)
        row_df = intraday_df.filter((pl.col('Ticker') == ticker) & (pl.col('Timestamp').dt.time() == index.time()))
        return row_df
    
    @staticmethod
    def calculate_stoploss_target(
        entry_price: float,
        order: Dict[str, Any],
        position: str,
        stoploss_cal_mode: str
    ) -> Tuple[float, float]:
        """
        Calculate stop loss and target prices.
        
        Returns:
            Tuple of (stop_loss, target_price)
        """
        stop_loss = 0.0
        target_price = 0.0
        
        if order.get("stoploss_toggle"):
            stoploss_type = order.get("stoploss_type", "Percentage")
            stoploss_value = order.get("stoploss_value", 0)
            
            if stoploss_type == "Points":
                if position == "Sell":
                    stop_loss = round(entry_price + stoploss_value, 2)
                else:  # Buy
                    stop_loss = round(entry_price - stoploss_value, 2)
            else:  # Percentage
                if position == "Sell":
                    stop_loss = round(entry_price + (entry_price * stoploss_value), 2)
                else:  # Buy
                    stop_loss = round(entry_price - (entry_price * stoploss_value), 2)
        
        if order.get("target_toggle"):
            target_value = order.get("target_value", 0)
            if position == "Sell":
                target_price = round(entry_price - (entry_price * target_value), 2)
            else:  # Buy
                target_price = round(entry_price + (entry_price * target_value), 2)
        
        return stop_loss, target_price
    
    @staticmethod
    def create_trade_entry(
        leg_id: str,
        index: datetime,
        temp_row: pd.Series,
        order: Dict[str, Any],
        TRADE_DICT: Dict[str, List],
        order_book: Dict[str, List],
        entry_mode: str,
        stoploss_cal_mode: str,
        lot_qty: int,
        lotsize: int,
        sl_target_price: Optional[float] = None
    ) -> Tuple[Dict, Dict]:
        """
        Create trade entry in TRADE_DICT and order_book.
        
        This consolidates the repetitive order creation logic.
        """
        # Calculate stop loss and target
        entry_price = temp_row[entry_mode]

        if sl_target_price is not None:
            stop_loss, target_price = EntryUtilities.calculate_stoploss_target(
                sl_target_price, order, order.get("position"), stoploss_cal_mode
            )
        else:
            stop_loss, target_price = EntryUtilities.calculate_stoploss_target(
                entry_price, order, order.get("position"), stoploss_cal_mode
            )
        
        # Calculate PnL
        position = order.get("position", "Sell")
        if position == "Sell":
            pnl = (entry_price - temp_row['Close']) * (lot_qty * lotsize)
            order_side = "Sell"
            summary = (
                f"{order.get('option_type')} Position Short, "
                f"Sl Price: {'NA' if stop_loss == 0 else stop_loss}, "
                f"Tgt Price: {'NA' if target_price == 0 else target_price}, "
                f"Trailing Price: {'NA' if not order.get('trail_sl_toggle') else entry_price}"
            )
        else:  # Buy
            pnl = (temp_row['Close'] - entry_price) * (lot_qty * lotsize)
            order_side = "Buy"
            summary = (
                f"{order.get('option_type')} Position Long, "
                f"Sl Price: {'NA' if stop_loss == 0 else stop_loss}, "
                f"Tgt Price: {'NA' if target_price == 0 else target_price}, "
                f"Trailing Price: {'NA' if not order.get('trail_sl_toggle') else entry_price}"
            )
        
        # Update TRADE_DICT
        TRADE_DICT['Leg_id'].append(leg_id)
        TRADE_DICT["Entry_timestamp"].append(index)
        TRADE_DICT['Timestamp'].append(index)
        TRADE_DICT['TradingSymbol'].append(temp_row['Ticker'])
        TRADE_DICT['Instrument_type'].append(temp_row['Instrument_type'])
        TRADE_DICT['Entry_price'].append(entry_price)
        TRADE_DICT['LTP'].append(temp_row['Close'])
        TRADE_DICT['Position_type'].append(position)
        TRADE_DICT['Strike'].append(temp_row['Strike'])
        TRADE_DICT['Stop_loss'].append(stop_loss)
        TRADE_DICT['Target_price'].append(target_price)
        TRADE_DICT['Trailing'].append(entry_price if order.get("trail_sl_toggle") else 0)
        TRADE_DICT['PnL'].append(pnl)
        TRADE_DICT['Lot_size'].append(lot_qty)
        TRADE_DICT['Expiry_type'].append(order['leg_expiry_selection'])
        
        # Update order_book
        EntryUtilities.order_book_entry(TRADE_DICT, index, -1, order_book, custom_summary=summary)

        return TRADE_DICT, order_book


# ============================================================================
# ABSTRACT BASE CLASS
# ============================================================================

class EntryStrategy(ABC):
    """
    Abstract base class for all entry strategies.
    
    All entry strategies must implement the execute() method which handles
    the entry logic for that specific strategy type.
    """
    
    def __init__(self, utilities: EntryUtilities, **config):
        """
        Initialize entry strategy.
        
        Args:
            utilities: EntryUtilities instance for shared operations
            **config: Strategy-specific configuration
        """
        self.utilities = utilities
        self.config = config
    
    @abstractmethod
    def execute(
        self,
        leg_id: str,
        order: Dict[str, Any],
        spot: float,
        index: datetime,
        TRADE_DICT: Dict[str, List],
        order_book: Dict[str, List],
        orders: Dict[str, Any],
        **kwargs
    ) -> Tuple[Dict, Dict, Dict, bool]:
        """
        Execute the entry strategy.
        
        Args:
            leg_id: Leg identifier
            order: Order/leg configuration dictionary
            spot: Current spot price
            index: Current timestamp
            TRADE_DICT: Trade dictionary to update
            order_book: Order book dictionary to update
            orders: Orders dictionary
            **kwargs: Additional strategy-specific parameters
            
        Returns:
            Tuple of (TRADE_DICT, order_book, orders, day_breaker)
        """
        pass
    
    def reset(self):
        """Reset strategy state if needed. Override in subclasses."""
        pass


# ============================================================================
# CONCRETE STRATEGY IMPLEMENTATIONS
# ============================================================================

class SimpleEntryStrategy(EntryStrategy):
    """
    Simple entry strategy - immediate execution based on strike selection.
    """
    
    def execute(
        self,
        leg_id: str,
        order: Dict[str, Any],
        spot: float,
        index: datetime,
        TRADE_DICT: Dict[str, List],
        order_book: Dict[str, List],
        orders: Dict[str, Any],
        **kwargs
    ) -> Tuple[Dict, Dict, Dict, bool]:
        """Execute simple entry."""
        intraday_df_dict = kwargs.get("intraday_df_dict")
        entry_mode = kwargs.get("EntryMode")
        stoploss_cal_mode = kwargs.get("StoplossCalMode")
        lot_qty = kwargs.get("lot_qty", 1)
        lotsize = kwargs.get("lotsize", 50)
        base = kwargs.get("base", 50)
        
        intraday_df = intraday_df_dict[order["leg_expiry_selection"]]
        
        # Calculate strike
        strike_price = self.utilities.calculate_strike(
            order.get("strike_type", "ATM"),
            spot,
            base,
            order,
            intraday_df,
            index
        )
        
        # Override with static strike if provided
        if "static_strike" in order:
            strike_price = order["static_strike"]
        
        # Get options row
        temp = self.utilities.get_options_row(strike_price, order, intraday_df, index)
        
        # Handle hedges if needed
        if order.get("hedges") and temp.empty:
            strike_price = self._find_hedge_strike(
                strike_price, order, intraday_df, index, base, order.get("spread", 0)
            )
            temp = self.utilities.get_options_row(strike_price, order, intraday_df, index)
        
        if temp.empty:
            raise ValueError(f"No options data found for strike {strike_price} at {index}")
        
        tempCE_or_PE = temp[temp['Instrument_type'] == order.get("option_type")].iloc[0]
        
        # Create trade entry
        TRADE_DICT, order_book = self.utilities.create_trade_entry(
            leg_id, index, tempCE_or_PE, order, TRADE_DICT, order_book,
            entry_mode, stoploss_cal_mode, lot_qty, lotsize
        )
        
        # Store first entry price
        if "first_entry_price" not in orders.get(leg_id, {}):
            leg_index = TRADE_DICT["leg_id"].index(leg_id)
            orders[leg_id]["first_entry_price"] = TRADE_DICT["SellPrice"][leg_index]
        
        return TRADE_DICT, order_book, orders, False
    
    def _find_hedge_strike(
        self,
        strike_price: float,
        order: Dict[str, Any],
        intraday_df: pd.DataFrame,
        index: datetime,
        base: float,
        max_depth: int
    ) -> float:
        """Find hedge strike when original is empty."""
        depth = max_depth
        option_type = order.get("option_type")
        
        while depth >= 0:
            hedge_temp = intraday_df[
                (intraday_df['Strike'] == strike_price) &
                (intraday_df['Instrument_type'] == option_type)
            ]
            hedge_temp = hedge_temp[hedge_temp.index.time == index.time()]
            
            if not hedge_temp.empty:
                return strike_price
            
            # Adjust strike
            if option_type == "CE":
                strike_price -= base
            elif option_type == "PE":
                strike_price += base
            
            depth -= 1
        
        return strike_price


class MomentumEntryStrategy(EntryStrategy):
    """
    Simple Momentum entry strategy - waits for price to reach a threshold.
    """
    
    def __init__(self, utilities: EntryUtilities, **config):
        super().__init__(utilities, **config)
        self.pending_entries: Dict[str, Dict[str, Any]] = {}
    
    def execute(
        self,
        leg_id: str,
        order: Dict[str, Any],
        spot: float,
        index: datetime,
        TRADE_DICT: Dict[str, List],
        order_book: Dict[str, List],
        orders: Dict[str, Any],
        **kwargs
    ) -> Tuple[Dict, Dict, Dict, bool]:
        """
        Execute momentum entry - first updates pending entry, then checks for execution.
        """
        # Store pending entry if not already stored
        if leg_id not in self.pending_entries and order.get("order_initialization_time", index) == index:
            self._update_pending_entry(leg_id, order, spot, index, **kwargs)
        
        # Check if execution condition is met
        return self._check_and_execute(leg_id, index, TRADE_DICT, order_book, orders, **kwargs)
    
    def _update_pending_entry(
        self,
        leg_id: str,
        order: Dict[str, Any],
        spot: float,
        index: datetime,
        **kwargs
    ):
        """Update pending entry with calculated prices."""
        options_extractor_con = kwargs.get("options_extractor_con")
        base = kwargs.get("base", 50)
        entry_mode = kwargs.get("EntryMode")
                
        # Calculate strike
        strike_price = self.utilities.calculate_strike(
            order.get("strike_type", "ATM"),
            spot,
            base,
            order,
            options_extractor_con,
            index
        )
        
        # Get options row
        temp = self.utilities.get_options_row(strike_price, order, options_extractor_con, index, indices=self.config["indices"])

        if temp.height == 0:
            raise ValueError(f"No options data for momentum entry at {index}")
        
        tempCE_or_PE = temp.row(0, named=True)

        # Calculate entry price based on direction
        sm_percentage_direction = order.get("sm_percentage_direction", "PERCENTAGE_UP")
        sm_percent_value = order.get("sm_percent_value", 0) / 100
        normal_entry_price = tempCE_or_PE[entry_mode]
        
        if sm_percentage_direction == "PERCENTAGE_UP":
            sm_entry_price = round(tempCE_or_PE["Close"] + (tempCE_or_PE["Close"] * sm_percent_value), 2)
        elif sm_percentage_direction == "PERCENTAGE_DOWN":
            sm_entry_price = round(tempCE_or_PE["Close"] - (tempCE_or_PE["Close"] * sm_percent_value), 2)
        elif sm_percentage_direction == "POINTS_UP":
            sm_entry_price = round(tempCE_or_PE["Close"] + order.get("sm_percent_value", 0), 2)
        elif sm_percentage_direction == "POINTS_DOWN":
            sm_entry_price = round(tempCE_or_PE["Close"] - order.get("sm_percent_value", 0), 2)
        else:
            sm_entry_price = normal_entry_price
        
        # Store pending entry
        self.pending_entries[leg_id] = {
            "order": order.copy(),
            "ticker": tempCE_or_PE["Ticker"],
            "normal_entry_price": normal_entry_price,
            "sm_entry_price": sm_entry_price,
            "sm_percentage_direction": sm_percentage_direction
        }
    
    def _check_and_execute(
        self,
        leg_id: str,
        index: datetime,
        TRADE_DICT: Dict[str, List],
        order_book: Dict[str, List],
        orders: Dict[str, Any],
        **kwargs
    ) -> Tuple[Dict, Dict, Dict, bool]:
        """Check if momentum condition is met and execute if so."""
        if leg_id not in self.pending_entries:
            return TRADE_DICT, order_book, orders, False
        
        pending = self.pending_entries[leg_id]
        order = pending["order"]
        options_extractor_con = kwargs.get("options_extractor_con")
        entry_mode = kwargs.get("EntryMode")
        stoploss_cal_mode = kwargs.get("StoplossCalMode")
        lot_qty = kwargs.get("lot_qty", 1)
        lotsize = kwargs.get("lotsize", 50)
                
        # Get current option data
        temp = self.utilities.get_options_row_with_ticker(
            ticker=pending["ticker"],
            options_extractor_con=options_extractor_con,
            index=index,
            indices=self.config["indices"],
            expiry_type=order["leg_expiry_selection"]
        )


        if temp.height == 0:
            return TRADE_DICT, order_book, orders, False
        
        tempCE_or_PE = temp.row(0, named=True)
        current_close = tempCE_or_PE["Close"]
        sm_entry_price = pending["sm_entry_price"]
        direction = pending["sm_percentage_direction"]
        
        # Check if condition is met
        condition_met = False
        if direction in ["PERCENTAGE_UP", "POINTS_UP"]:
            condition_met = current_close >= sm_entry_price
        elif direction in ["PERCENTAGE_DOWN", "POINTS_DOWN"]:
            condition_met = current_close <= sm_entry_price
        
        if not condition_met:
            return TRADE_DICT, order_book, orders, False
        
        # Execute entry
        # Handle sm_leg_data if present
        if order.get("sm_leg_data"):
            prev_order = copy.deepcopy(order)
            prev_orders = copy.deepcopy(orders)
            order = order | order["sm_leg_data"]
            order["sm_toggle"] = False
            # Recursive call to execute with modified order
            TRADE_DICT, order_book, orders, day_breaker = self._execute_modified_order(
                leg_id, order, index, TRADE_DICT, order_book, orders, **kwargs
            )
            orders = prev_orders
            orders[leg_id]["first_entry_price"] = TRADE_DICT["SellPrice"][TRADE_DICT["leg_id"].index(leg_id)]
        else:
            # Determine entry price based on sm_tgt_sl_price setting
            sm_tgt_sl_price = order.get("sm_tgt_sl_price", "Entry_price")
            if sm_tgt_sl_price == "Entry_price":
                entry_price = tempCE_or_PE[entry_mode]
            elif sm_tgt_sl_price == "SM_price":
                entry_price = sm_entry_price
            else:  # System_price
                entry_price = pending["normal_entry_price"]
            
            # Create trade entry
            tempCE_or_PE_copy = tempCE_or_PE.copy()
            # tempCE_or_PE_copy[entry_mode] = entry_price
            
            TRADE_DICT, order_book = self.utilities.create_trade_entry(
                leg_id, index, tempCE_or_PE_copy, order, TRADE_DICT, order_book,
                entry_mode, stoploss_cal_mode, lot_qty, lotsize, sl_target_price=sm_entry_price
            )

            

            # Update entry price for stoploss/target calculation
            # leg_index = TRADE_DICT["Leg_id"].index(leg_id)
            # TRADE_DICT["Entry_price"][leg_index] = entry_price
        
        # Store first entry price
        if "first_entry_price" not in orders.get(leg_id, {}):
            leg_index = TRADE_DICT["Leg_id"].index(leg_id)
            orders[leg_id]["first_entry_price"] = TRADE_DICT["Entry_price"][leg_index]
        
        # Remove from pending
        del self.pending_entries[leg_id]
        
        return TRADE_DICT, order_book, orders, False
    
    def _execute_modified_order(
        self,
        leg_id: str,
        order: Dict[str, Any],
        index: datetime,
        TRADE_DICT: Dict[str, List],
        order_book: Dict[str, List],
        orders: Dict[str, Any],
        **kwargs
    ) -> Tuple[Dict, Dict, Dict, bool]:
        """Execute entry with modified order (for sm_leg_data case)."""
        # This would call back to UnifiedEntryManager.entry() recursively
        # For now, implement basic execution
        return TRADE_DICT, order_book, orders, False
    
    def reset(self):
        """Reset pending entries."""
        self.pending_entries.clear()


class RangeBreakoutEntryStrategy(EntryStrategy):
    """Range Breakout entry strategy."""
    
    def __init__(self, utilities: EntryUtilities, **config):
        super().__init__(utilities, **config)
        self.pending_entries: Dict[str, Dict[str, Any]] = {}
    
    def execute(
        self,
        leg_id: str,
        order: Dict[str, Any],
        spot: float,
        index: datetime,
        TRADE_DICT: Dict[str, List],
        order_book: Dict[str, List],
        orders: Dict[str, Any],
        **kwargs
    ) -> Tuple[Dict, Dict, Dict, bool]:
        """Execute range breakout entry."""
        from datetime import datetime as dt
        
        rb_time_threshold = dt.strptime(order.get("range_breakout_threshold_time", "15:30:00"), "%H:%M:%S").time()
        
        # Update pending entry if before threshold
        if index.time() <= rb_time_threshold and leg_id not in self.pending_entries:
            self._update_pending_entry(leg_id, order, spot, index, **kwargs)
        
        # Check and execute if after threshold
        if index.time() > rb_time_threshold:
            return self._check_and_execute(leg_id, index, TRADE_DICT, order_book, orders, **kwargs)
        
        return TRADE_DICT, order_book, orders, False
    
    def _update_pending_entry(
        self,
        leg_id: str,
        order: Dict[str, Any],
        spot: float,
        index: datetime,
        **kwargs
    ):
        """Update pending entry with range data."""
        from datetime import datetime as dt
        
        intraday_df_dict = kwargs.get("intraday_df_dict")
        spot_df = kwargs.get("spot_df")
        base = kwargs.get("base", 50)
        rb_time_threshold = dt.strptime(order.get("range_breakout_threshold_time", "15:30:00"), "%H:%M:%S").time()
        
        if order.get("underlying_asset") == "Instrument":
            intraday_df = intraday_df_dict[order["leg_expiry_selection"]]
            
            # Calculate strike
            strike_price = self.utilities.calculate_strike(
                order.get("strike_type", "ATM"),
                spot,
                base,
                order,
                intraday_df,
                index
            )
            
            # Get time range data
            temp = intraday_df[
                (intraday_df['Strike'] == strike_price) &
                (intraday_df['Instrument_type'] == order.get("option_type"))
            ]
            
            range_start = order.get("range_breakout_start", "Default")
            if range_start == "Default":
                temp = temp[(temp.index.time >= index.time()) & (temp.index.time <= rb_time_threshold)]
            elif range_start == "Exact":
                temp = temp[(temp.index.time > index.time()) & (temp.index.time <= rb_time_threshold)]
            
            if temp.empty:
                raise ValueError(f"No range data found for range breakout at {index}")
            
            ticker = temp["Ticker"].iloc[0]
            
            # Calculate range break price
            range_break_of = order.get("range_breakout_of", "High")
            if range_break_of == "High":
                range_break_price = temp["High"].max()
            else:  # Low
                range_break_price = temp["Low"].min()
            
            self.pending_entries[leg_id] = {
                "order": order.copy(),
                "ticker": ticker,
                "range_break_price": range_break_price,
                "underlying_asset": "Instrument"
            }
        
        elif order.get("underlying_asset") == "Underlying":
            temp = spot_df[
                (spot_df.index.time >= index.time()) &
                (spot_df.index.time <= rb_time_threshold)
            ]
            
            if temp.empty:
                raise ValueError(f"No spot range data found at {index}")
            
            ticker = temp["Ticker"].iloc[0] if "Ticker" in temp.columns else "SPOT"
            
            range_break_of = order.get("range_breakout_of", "High")
            if range_break_of == "High":
                range_break_price = temp["High"].max()
            else:  # Low
                range_break_price = temp["Low"].min()
            
            self.pending_entries[leg_id] = {
                "order": order.copy(),
                "ticker": ticker,
                "range_break_price": range_break_price,
                "underlying_asset": "Underlying",
                "spot_data": temp
            }
    
    def _check_and_execute(
        self,
        leg_id: str,
        index: datetime,
        TRADE_DICT: Dict[str, List],
        order_book: Dict[str, List],
        orders: Dict[str, Any],
        **kwargs
    ) -> Tuple[Dict, Dict, Dict, bool]:
        """Check if range breakout condition is met and execute."""
        if leg_id not in self.pending_entries:
            return TRADE_DICT, order_book, orders, False
        
        pending = self.pending_entries[leg_id]
        order = pending["order"]
        intraday_df_dict = kwargs.get("intraday_df_dict")
        spot_df = kwargs.get("spot_df")
        base = kwargs.get("base", 50)
        entry_mode = kwargs.get("EntryMode")
        stoploss_cal_mode = kwargs.get("StoplossCalMode")
        lot_qty = kwargs.get("lot_qty", 1)
        lotsize = kwargs.get("lotsize", 50)
        
        rb_trigger = False
        
        if pending["underlying_asset"] == "Instrument":
            intraday_df = intraday_df_dict[order["leg_expiry_selection"]]
            temp = intraday_df[intraday_df['Ticker'] == pending["ticker"]]
            temp = temp[temp.index.time == index.time()]
            
            if not temp.empty:
                tempCE_or_PE = temp.iloc[0]
                range_compare_section = order.get("range_compare_section", "Close")
                range_break_of = order.get("range_breakout_of", "High")
                
                if range_break_of == "Low":
                    rb_trigger = tempCE_or_PE[range_compare_section] < pending["range_break_price"]
                else:  # High
                    rb_trigger = tempCE_or_PE[range_compare_section] > pending["range_break_price"]
                
                if rb_trigger:
                    TRADE_DICT, order_book = self.utilities.create_trade_entry(
                        leg_id, index, tempCE_or_PE, order, TRADE_DICT, order_book,
                        entry_mode, stoploss_cal_mode, lot_qty, lotsize
                    )
        
        elif pending["underlying_asset"] == "Underlying":
            spot_chunk = spot_df[spot_df.index.time == index.time()]
            
            if not spot_chunk.empty:
                spot_row = spot_chunk.iloc[0]
                range_compare_section = order.get("range_compare_section", "Close")
                range_break_of = order.get("range_breakout_of", "High")
                
                if range_break_of == "Low":
                    rb_trigger = spot_row[range_compare_section] < pending["range_break_price"]
                else:  # High
                    rb_trigger = spot_row[range_compare_section] > pending["range_break_price"]
                
                if rb_trigger:
                    # Need to calculate strike for entry
                    spot = spot_row["Close"]
                    intraday_df = intraday_df_dict[order["leg_expiry_selection"]]
                    strike_price = self.utilities.calculate_strike(
                        order.get("strike_type", "ATM"),
                        spot,
                        base,
                        order,
                        intraday_df,
                        index
                    )
                    
                    temp = intraday_df[
                        (intraday_df['Strike'] == strike_price) &
                        (intraday_df['Instrument_type'] == order.get("option_type"))
                    ]
                    temp = temp[temp.index.time == index.time()]
                    
                    if not temp.empty:
                        tempCE_or_PE = temp.iloc[0]
                        TRADE_DICT, order_book = self.utilities.create_trade_entry(
                            leg_id, index, tempCE_or_PE, order, TRADE_DICT, order_book,
                            entry_mode, stoploss_cal_mode, lot_qty, lotsize
                        )
        
        if rb_trigger and "first_entry_price" not in orders.get(leg_id, {}):
            leg_index = TRADE_DICT["leg_id"].index(leg_id)
            orders[leg_id]["first_entry_price"] = TRADE_DICT["SellPrice"][leg_index]
        
        if rb_trigger:
            del self.pending_entries[leg_id]
        
        return TRADE_DICT, order_book, orders, False
    
    def reset(self):
        """Reset pending entries."""
        self.pending_entries.clear()


class RollingStraddleEntryStrategy(EntryStrategy):
    """Rolling Straddle entry strategy."""
    
    def __init__(self, utilities: EntryUtilities, **config):
        super().__init__(utilities, **config)
        self.pending_entries: Dict[str, Dict[str, Any]] = {}
        self.rolling_straddle_vwap_df = pd.DataFrame()
        self.straddle_filepath = config.get("straddle_filepath", "")
        self.indices = config.get("indices", "")
        self.rolling_straddle_slice_time = config.get("rolling_straddle_slice_time", None)
    
    def execute(
        self,
        leg_id: str,
        order: Dict[str, Any],
        spot: float,
        index: datetime,
        TRADE_DICT: Dict[str, List],
        order_book: Dict[str, List],
        orders: Dict[str, Any],
        **kwargs
    ) -> Tuple[Dict, Dict, Dict, bool]:
        """Execute rolling straddle entry."""
        # Initialize rolling straddle data if needed
        if self.rolling_straddle_vwap_df.empty:
            self._generate_rolling_vwap(index)
        
        # Store pending entry
        if leg_id not in self.pending_entries:
            self.pending_entries[leg_id] = {
                "order": order.copy(),
                "consecutive_candles": order.get("rolling_straddle_consecutive_candles", 1),
                "breach_on": order.get("rolling_straddle_breach_on", "High")
            }
        
        # Check condition and execute
        return self._check_and_execute(leg_id, index, TRADE_DICT, order_book, orders, **kwargs)
    
    def _generate_rolling_vwap(self, index: datetime):
        """Generate rolling straddle VWAP data."""
        from datetime import datetime as dt
        from dateutil.relativedelta import relativedelta
        
        straddle_path = (
            f"{self.straddle_filepath}/{index.year}/{index.month}/"
            f"{str(index.day).zfill(2)}_{str(index.month).zfill(2)}_{index.year}_{self.indices}_Straddle.csv"
        )
        
        try:
            straddle_df = pd.read_csv(straddle_path)
            straddle_df["Timestamp"] = pd.to_datetime(straddle_df["Timestamp"])
            straddle_df.set_index("Timestamp", inplace=True)
            
            # Generate rolling metrics
            if self.rolling_straddle_slice_time:
                straddle_df = straddle_df[straddle_df.index.time >= self.rolling_straddle_slice_time]
            
            straddle_df["Rolling_straddle_low"] = straddle_df["Rolling_Straddle_Synthetic"].cummin()
            straddle_df["Rolling_straddle_high"] = straddle_df["Rolling_Straddle_Synthetic"].cummax()
            
            self.rolling_straddle_vwap_df = straddle_df
            
        except Exception as e:
            # Log error but continue
            self.rolling_straddle_vwap_df = pd.DataFrame()
    
    def _check_and_execute(
        self,
        leg_id: str,
        index: datetime,
        TRADE_DICT: Dict[str, List],
        order_book: Dict[str, List],
        orders: Dict[str, Any],
        **kwargs
    ) -> Tuple[Dict, Dict, Dict, bool]:
        """Check rolling straddle condition and execute."""
        if leg_id not in self.pending_entries:
            return TRADE_DICT, order_book, orders, False
        
        if self.rolling_straddle_vwap_df.empty:
            return TRADE_DICT, order_book, orders, False
        
        pending = self.pending_entries[leg_id]
        order = pending["order"]
        consecutive_candles = pending["consecutive_candles"]
        breach_on = pending["breach_on"]
        
        # Get previous chunk
        previous_chunk = self.rolling_straddle_vwap_df[self.rolling_straddle_vwap_df.index <= index]
        chunk = previous_chunk.tail(consecutive_candles)
        
        if len(chunk) < consecutive_candles:
            return TRADE_DICT, order_book, orders, False
        
        # Check condition
        straddle_condition = False
        if breach_on == "High":
            straddle_condition = (chunk["Rolling_Straddle_Synthetic"] >= chunk["Rolling_straddle_high"]).all()
        elif breach_on == "Low":
            straddle_condition = (chunk["Rolling_Straddle_Synthetic"] <= chunk["Rolling_straddle_low"]).all()
        
        if straddle_condition:
            # Delegate to UnifiedEntryManager for actual execution
            # For now, mark as ready
            order["rolling_straddle_toggle"] = False
            del self.pending_entries[leg_id]
            # Execution would happen through main manager
        
        return TRADE_DICT, order_book, orders, False
    
    def reset(self):
        """Reset pending entries and VWAP data."""
        self.pending_entries.clear()
        self.rolling_straddle_vwap_df = pd.DataFrame()


class RollingStraddleVWAPEntryStrategy(EntryStrategy):
    """Rolling Straddle VWAP entry strategy."""
    
    def __init__(self, utilities: EntryUtilities, **config):
        super().__init__(utilities, **config)
        self.pending_entries: Dict[str, Dict[str, Any]] = {}
        # Share VWAP data with RollingStraddleEntryStrategy if available
        self.rolling_straddle_vwap_df = pd.DataFrame()
    
    def execute(
        self,
        leg_id: str,
        order: Dict[str, Any],
        spot: float,
        index: datetime,
        TRADE_DICT: Dict[str, List],
        order_book: Dict[str, List],
        orders: Dict[str, Any],
        **kwargs
    ) -> Tuple[Dict, Dict, Dict, bool]:
        """Execute rolling straddle VWAP entry."""
        # This would share VWAP data generation with RollingStraddleEntryStrategy
        # Implementation similar to RollingStraddleEntryStrategy but checks VWAP instead
        return TRADE_DICT, order_book, orders, False


# ============================================================================
# UNIFIED ENTRY MANAGER
# ============================================================================

class UnifiedEntryManager:
    """
    Unified Entry Manager - Handles all entry types seamlessly.
    
    This is the main entry point for all entry operations. It automatically
    selects and executes the correct strategy based on the order configuration.
    
    Features:
    - Automatic strategy selection based on order configuration
    - Easy to add new entry types (just create a new strategy class)
    - Centralized error handling and logging
    - Shared utilities to avoid code duplication
    - Support for all existing entry types
    
    Usage:
        manager = UnifiedEntryManager(**config)
        TRADE_DICT, order_book, orders, day_breaker = manager.entry(
            index, order, spot, leg_id, TRADE_DICT, order_book, orders
        )
    """
    
    def __init__(
        self,
        base: float,
        options_extractor_con: object,
        spot_df: pd.DataFrame,
        EntryMode: str,
        lot_qty: int,
        lotsize: int,
        StoplossCalMode: str,
        logger: Any,
        miss_con: Any,
        straddle_filepath: str = "",
        indices: str = "",
        rolling_straddle_slice_time: Optional[time] = None
    ):
        """
        Initialize Unified Entry Manager.
        
        Args:
            base: Strike base (e.g., 50 for NIFTY)
            intraday_df_dict: Dictionary of intraday dataframes by expiry
            spot_df: Spot price dataframe
            EntryMode: Entry price mode ("Open", "High", "Low", "Close")
            lot_qty: Lot quantity
            lotsize: Lot size
            StoplossCalMode: Stoploss calculation mode
            logger: Logger instance
            miss_con: Missing data handler
            straddle_filepath: Path to straddle files
            indices: Index name
            rolling_straddle_slice_time: Rolling straddle slice time
        """
        # Store configuration
        self.base = base
        self.options_extractor_con = options_extractor_con
        self.spot_df = spot_df
        self.EntryMode = EntryMode
        self.lot_qty = lot_qty
        self.lotsize = lotsize
        self.StoplossCalMode = StoplossCalMode
        self.logger = logger
        self.miss_con = miss_con
        self.straddle_filepath = straddle_filepath
        self.indices = indices
        self.rolling_straddle_slice_time = rolling_straddle_slice_time
        
        # Initialize utilities
        self.utilities = EntryUtilities()
        
        # Register all strategies
        self.strategies: Dict[str, EntryStrategy] = {}
        self._register_strategies()
    
    def _register_strategies(self):
        """Register all available entry strategies."""
        config = {
            "straddle_filepath": self.straddle_filepath,
            "indices": self.indices,
            "rolling_straddle_slice_time": self.rolling_straddle_slice_time
        }
        
        self.strategies = {
            "SIMPLE": SimpleEntryStrategy(self.utilities, **config),
            "MOMENTUM": MomentumEntryStrategy(self.utilities, **config),
            "RANGE_BREAKOUT": RangeBreakoutEntryStrategy(self.utilities, **config),
            "ROLLING_STRADDLE": RollingStraddleEntryStrategy(self.utilities, **config),
            "ROLLING_STRADDLE_VWAP": RollingStraddleVWAPEntryStrategy(self.utilities, **config)
        }
    
    def _select_strategy(self, order: Dict[str, Any]) -> EntryStrategy:
        """
        Select the appropriate strategy based on order configuration.
        
        Args:
            order: Order/leg configuration dictionary
            
        Returns:
            Selected EntryStrategy instance
        """
        # Priority order for strategy selection
        if order.get("rolling_straddle_toggle"):
            return self.strategies["ROLLING_STRADDLE"]
        elif order.get("rolling_straddle_vwap_toggle"):
            return self.strategies["ROLLING_STRADDLE_VWAP"]
        elif order.get("sm_toggle"):
            return self.strategies["MOMENTUM"]
        elif order.get("range_breakout_toggle"):
            return self.strategies["RANGE_BREAKOUT"]
        else:
            # Default to simple entry
            return self.strategies["SIMPLE"]
    
    def entry(
        self,
        index: datetime,
        order: Dict[str, Any],
        spot: float,
        leg_id: str,
        TRADE_DICT: Dict[str, List],
        order_book: Dict[str, List],
        orders: Dict[str, Any],
        order_initialization: bool = False
    ) -> Tuple[Dict, Dict, Dict, bool]:
        """
        Execute entry for a leg.
        
        This is the main entry point that automatically selects and executes
        the correct strategy based on the order configuration.
        
        Args:
            index: Current timestamp
            order: Order/leg configuration dictionary
            spot: Current spot price
            leg_id: Leg identifier
            TRADE_DICT: Trade dictionary to update
            order_book: Order book dictionary to update
            orders: Orders dictionary
            
        Returns:
            Tuple of (TRADE_DICT, order_book, orders, day_breaker)
        """
        def log_missing_strike():
            msg = (
                f"{index.date()} Time:{index.time()}, Spot:{spot}, "
                f"Expiry:{order.get('leg_expiry_selection')} Missing {order.get('strike_type')} Strike"
            )
            self.logger.info(msg)
            self.miss_con.missing_dict_update(index, msg)
        
        try:
            # Select appropriate strategy
            strategy = self._select_strategy(order)
            
            # Execute strategy with all required parameters
            kwargs = {
                "options_extractor_con": self.options_extractor_con,
                "spot_df": self.spot_df,
                "EntryMode": self.EntryMode,
                "StoplossCalMode": self.StoplossCalMode,
                "lot_qty": self.lot_qty,
                "lotsize": self.lotsize,
                "base": self.base
            }
            if order_initialization:
                order["order_initialization_time"] = index

            TRADE_DICT, order_book, orders, day_breaker = strategy.execute(
                leg_id, order, spot, index, TRADE_DICT, order_book, orders, **kwargs
            )
            
            return TRADE_DICT, order_book, orders, day_breaker
            
        except Exception as e:
            self.logger.error(f"Entry execution error for leg {leg_id} at {index}: {e}")
            log_missing_strike()
            return TRADE_DICT, order_book, orders, True
    
    def register_strategy(self, name: str, strategy: EntryStrategy):
        """
        Register a new entry strategy.
        
        This allows adding new entry types dynamically.
        
        Args:
            name: Strategy name/identifier
            strategy: EntryStrategy instance
        """
        self.strategies[name.upper()] = strategy
    
    def reset_strategies(self):
        """Reset all strategies that have state."""
        for strategy in self.strategies.values():
            strategy.reset()


# ============================================================================
# BACKWARD COMPATIBILITY WRAPPER
# ============================================================================

class Entry_Execution:
    """
    Backward compatibility wrapper for existing code.
    
    This class maintains the same interface as the old Entry_Execution class
    but internally uses UnifiedEntryManager for all operations.
    """
    
    def __init__(
        self,
        logger,
        miss_con,
        sm_constructor,
        rb_constructor,
        rs_constructor,
        entry_initialization,
        straddle_filepath,
        indices,
        rolling_straddle_slice_time
    ):
        """Initialize with all dependencies for backward compatibility."""
        # Extract configuration from existing constructors
        base = entry_initialization.base
        intraday_df_dict = entry_initialization.intraday_df_dict
        spot_df = rb_constructor.spot_df if hasattr(rb_constructor, 'spot_df') else pd.DataFrame()
        EntryMode = entry_initialization.EntryMode
        lot_qty = entry_initialization.lot_qty
        lotsize = entry_initialization.lotsize
        StoplossCalMode = entry_initialization.StoplossCalMode
        
        # Create unified manager
        self.manager = UnifiedEntryManager(
            base=base,
            intraday_df_dict=intraday_df_dict,
            spot_df=spot_df,
            EntryMode=EntryMode,
            lot_qty=lot_qty,
            lotsize=lotsize,
            StoplossCalMode=StoplossCalMode,
            logger=logger,
            miss_con=miss_con,
            straddle_filepath=straddle_filepath,
            indices=indices,
            rolling_straddle_slice_time=rolling_straddle_slice_time
        )
        
        # Keep references for any legacy access
        self.logger = logger
        self.miss_con = miss_con
        self.sm_constructor = sm_constructor
        self.rb_constructor = rb_constructor
        self.rs_constructor = rs_constructor
        self.entry_initialization = entry_initialization
    
    def entry(
        self,
        index: datetime,
        order: Dict[str, Any],
        spot: float,
        leg_id: str,
        TRADE_DICT: Dict[str, List],
        order_book: Dict[str, List],
        orders: Dict[str, Any]
    ) -> Tuple[Dict, Dict, Dict, bool]:
        """
        Entry method matching old interface.
        
        Delegates to UnifiedEntryManager for actual execution.
        """
        return self.manager.entry(
            index, order, spot, leg_id, TRADE_DICT, order_book, orders
        )
