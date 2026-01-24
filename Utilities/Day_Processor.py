# from datetime import datetime as dt
# from pathlib import Path
# import sys

# MAIN_DIR = Path(__file__).resolve().parent.parent
# sys.path.append(str(MAIN_DIR))

# from Core import EngineCoreVariables
# from Utilities.Helper_functions import OrderSequenceMapper


# class DayProcessor(EngineCoreVariables):
#     def __init__(self, current_date_str: str, entry_para_dict: dict, orders: dict, lazy_leg_dict: dict):

#         super.__init__()

#         # Day start time & end time
#         self.entry_time = dt.strptime(f"{current_date_str}  {entry_para_dict['strategy_entry_time']}", "%Y-%m-%d %H:%M:%S")
#         self.exit_time = dt.strptime(f"{current_date_str}  {entry_para_dict['strategy_exit_time']}", "%Y-%m-%d %H:%M:%S")

#     def day_initilization(self):
#         order_sequence_mapper_con = OrderSequenceMapper()
#         self.orders, self.lazy_leg_dict = order_sequence_mapper_con.legid_mapping(orders, lazy_leg_dict)




"""
Day Processor Module (Updated with Manager Composition)

This module coordinates the intraday processing flow using composition of specialized managers.
Each manager handles a specific aspect of trading execution.

Classes:
    DayProcessor: Main coordinator that composes all managers and orchestrates the trading flow
"""

from datetime import datetime as dt
from typing import Dict, Any, List, Optional
import polars as pl
import pandas as pd

# Import refactored entry manager for better scalability
from Managers.entry_manager_refactored import UnifiedEntryManager
from Managers.exit_manager import ExitManager
from Managers.pnl_manager import PNLManager
from Managers.reentry_manager import ReentryManager
from Utilities.Order_Sequencer import OrderSequenceMapper


class DayProcessor:
    """
    Day Processor coordinates all intraday trading operations using composition.
    
    This class composes four main managers:
    - EntryManager: Handles all entry strategies
    - ExitManager: Handles all exit strategies  
    - PNLManager: Tracks positions and calculates P&L
    - ReentryManager: Handles re-entry strategies
    
    Attributes:
        entry_time: Strategy entry time
        exit_time: Strategy exit time
        entry_manager: EntryManager instance
        exit_manager: ExitManager instance
        pnl_manager: PNLManager instance
        reentry_manager: ReentryManager instance
        TRADE_DICT: Dictionary for tracking trade data
        order_book: Dictionary for order book entries
        CLOSE_DICT: Dictionary for closed positions
        day_breaker: Flag to break the day loop
        entry_spot: Spot price at entry time
        sd: Standard deviation level
        initial_entry: Flag for initial entry completion
        overall_tp_activated: Flag for overall take profit activation
    """

    def __init__(self, current_date_str: str, entry_para_dict: dict, options_extractor_con: object):
        """
        Initialize DayProcessor with managers and trading parameters.
        
        Args:
            current_date_str: Current date in 'YYYY-MM-DD' format
            entry_para_dict: Dictionary containing all strategy parameters
        """
        # Day start time & end time
        self.entry_time = dt.strptime(
            f"{current_date_str}  {entry_para_dict['strategy_entry_time']}", 
            "%Y-%m-%d %H:%M:%S"
        )
        self.exit_time = dt.strptime(
            f"{current_date_str}  {entry_para_dict['strategy_exit_time']}", 
            "%Y-%m-%d %H:%M:%S"
        )
        
        # Store entry parameters
        self.entry_para_dict = entry_para_dict
        
        # Initialize managers
        # Note: entry_manager will be initialized in process_day() when intraday_df_dict is available
        self.entry_manager: Optional[UnifiedEntryManager] = None
        self.exit_manager = ExitManager()
        self.pnl_manager = PNLManager()
        self.reentry_manager = ReentryManager()
        
        # Trade dictionary 
        self.TRADE_DICT = {
            "Leg_id": [],
            'Entry_timestamp': [],
            'Timestamp': [],
            'TradingSymbol': [],
            'Instrument_type': [],
            'Entry_price': [],
            'LTP': [],
            'Lot_size': [],
            'PnL': [],
            'Expiry_type': [],
            'Stop_loss': [],
            'Target_price': [],
            'Strike': [],
            'Position_type': [],
            'Trailing': []
        }
        
        # Order book dictionary 
        self.order_book = {
            'Timestamp': [],
            'Ticker': [],
            'Order_side': [],
            'Price': [],
            'Summary': []
        }
        
        # Closed position dictionary 
        self.CLOSE_DICT = {
            'Entry_timestamp': [],
            'Timestamp': [],
            'TradingSymbol': [],
            'Instrument_type': [],
            "SD": [],
            'Entry_price': [],
            'LTP': [],
            'Lot_size': [],
            'PnL': []
        }
        
        # Day state flags
        self.day_breaker = False
        self.entry_spot = None
        
        # Engine flags
        self.initial_entry = False
        self.overall_tp_activated = False



        self.orders = {}
        self.lazy_leg_dict = {}
        self.option_types = []
        self.expiry_types = []

        self.day_option_frame_con = options_extractor_con


    def options_frame_initilizer(self):
        intraday_options_df = {}
        for expiry_type in self.expiry_types:
            intraday_options_df[expiry_type] = pl.DataFrame()
        self.day_option_frame_con.intraday_options_df = intraday_options_df


    def _initialize_entry_manager(
        self,
        options_extractor_con: object,
        spot_df: pd.DataFrame,
        logger: Any,
        miss_con: Any,
        straddle_filepath: str = "",
        rolling_straddle_slice_time: Optional[dt.time] = None
    ):
        """
        Initialize the unified entry manager with all required parameters.
        
        This should be called before process_day() or within process_day()
        when all data is available.
        
        Args:
            intraday_df_dict: Dictionary of intraday dataframes by expiry
            spot_df: Spot price dataframe
            logger: Logger instance
            miss_con: Missing data handler
            straddle_filepath: Path to straddle files
            rolling_straddle_slice_time: Rolling straddle slice time
        """
        if self.entry_manager is not None:
            # Already initialized, reset if needed
            self.entry_manager.reset_strategies()
            return
        
        # Extract configuration from entry_para_dict
        # These keys match the parameter parser output and config structure
        base = self.entry_para_dict.get('base_symbol_spread', 50)
        EntryMode = self.entry_para_dict.get('EntryMode', 'Close')  # From parameter_parser
        lot_qty = self.entry_para_dict.get('lot_qty', 1)  # Default to 1 if not specified
        lotsize = self.entry_para_dict.get('symbol_lotsize', 50)  # Set from config in Main_Engine
        StoplossCalMode = self.entry_para_dict.get('StoplossCalMode', 'Close')  # From parameter_parser
        indices = self.entry_para_dict.get('indices', 'NIFTY')
        
        # Initialize unified entry manager
        self.entry_manager = UnifiedEntryManager(
            base=base,
            options_extractor_con=options_extractor_con,
            spot_df=spot_df.to_pandas() if isinstance(spot_df, pl.DataFrame) else spot_df,
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
    
    def process_day(
        self,
        spot_df: pl.DataFrame,
        vix_df: pl.DataFrame,
        prev_day_close: float,
        charges_params_dict: Dict[str, Any],
        logger: Any,
        synthetic_df: pd.DataFrame,
        intraday_df_dict: Optional[Dict[str, pd.DataFrame]] = None,
        miss_con: Optional[Any] = None,
        straddle_filepath: str = "",
        rolling_straddle_slice_time: Optional[dt.time] = None
    ):
        """
        Main method to process the trading day.
        
        This method orchestrates the entire trading day by coordinating
        the entry, exit, P&L tracking, and re-entry strategies through
        their respective managers.
        
        Args:
            spot_df: Spot price dataframe (polars DataFrame)
            vix_df: VIX dataframe (polars DataFrame)
            prev_day_close: Previous day closing price
            charges_params_dict: Charges configuration dictionary
            logger: Logger instance
            synthetic_df: Synthetic dataframe
            intraday_df_dict: Dictionary of intraday dataframes by expiry (required for entry)
            miss_con: Missing data handler (required for entry)
            straddle_filepath: Path to straddle files (optional)
            rolling_straddle_slice_time: Rolling straddle slice time (optional)
        """
        # Initialize entry manager if not already initialized
        if self.entry_manager is None:
            #if intraday_df_dict is None or miss_con is None:
            #    raise ValueError(
            #        "intraday_df_dict and miss_con are required for entry manager initialization. "
            #        "Please provide them in process_day() call."
            #    )
            
            self._initialize_entry_manager(
                options_extractor_con=self.day_option_frame_con,
                spot_df=spot_df,
                logger=logger,
                miss_con=miss_con,
                straddle_filepath=straddle_filepath,
                rolling_straddle_slice_time=rolling_straddle_slice_time
            )

            self.order_sequence_mapper_con = OrderSequenceMapper()
            self.orders, self.lazy_leg_dict = self.order_sequence_mapper_con.legid_mapping(self.orders, self.lazy_leg_dict)
            self.pnl_manager.charges_params = charges_params_dict


        
        print("Processing Day...")
        # Iterate through each timestamp in the spot dataframe
        for timestamp in spot_df['Timestamp']:
            current_time = timestamp
            spot_price = spot_df.filter(pl.col('Timestamp') == timestamp).select('Close').item()

            try:
                vix_value = vix_df.filter(pl.col('Timestamp') == timestamp).select('Close').item()
            except:
                logger.warning(f"VIX data missing for timestamp {timestamp}. Using previous value.")
                try:
                    vix_value = vix_df.filter(pl.col('Timestamp') < timestamp).select('Close').tail(1).item()
                    logger.warning(f"VIX data missing for timestamp {timestamp}, And previous to that as well.")
                except:
                    vix_value = 0

            # print(f"Current Time: {current_time}, Spot Price: {spot_price}, VIX: {vix_value}")

            # Time Debugger
            if current_time.date() == dt.strptime('28/01/2025', "%d/%m/%Y").date():
                debug = ""
                if current_time.time() == dt.strptime('14:10:00', "%H:%M:%S").time():
                    debug = ""


            if len(self.pnl_manager.active_positions) > 0 or len(self.pnl_manager.closed_positions) > 0:
                # Update P&L for open positions
                self.TRADE_DICT = self.pnl_manager.update_all_ltps(current_timestamp=timestamp,
                                                TRADE_DICT=self.TRADE_DICT,
                                                options_extractor_con=self.day_option_frame_con)
                
            if len(self.pnl_manager.active_positions) > 0:
                # Check stop loss for all active positions
                standing_positions_list = list(self.pnl_manager.active_positions.values())
                for standing_position in standing_positions_list:
                    stop_loss_triggers, summary = self.exit_manager.check_specific_exit(exit_type="STOPLOSS", position=standing_position,
                                                current_timestamp=current_time, current_ltp=spot_price, spot_df=spot_df)
                    if stop_loss_triggers:
                        exit_price = standing_position.stop_loss
                        logger.info(f"Stop loss triggered for position {standing_position.leg_id} at {current_time}")
                        self.pnl_manager.close_position(position_id=standing_position.position_id, exit_timestamp=current_time,
                                                        exit_price=exit_price, exit_reason=summary)
                
                standing_positions_list = list(self.pnl_manager.active_positions.values())
                for standing_position in standing_positions_list:
                    target_triggers, summary = self.exit_manager.check_specific_exit(exit_type="TARGET", position=standing_position,
                            current_timestamp=current_time, current_ltp=spot_price, spot_df=spot_df)
                    if target_triggers:
                        exit_price = standing_position.target_price
                        logger.info(f"Target triggered for position {standing_position.leg_id} at {current_time}")
                        self.pnl_manager.close_position(position_id=standing_position.position_id, exit_timestamp=current_time,
                                                        exit_price=exit_price, exit_reason=summary)
                        
            
            # Re-entry logic for positions that were closed
            # if len(self.pnl_manager.closed_positions) > 0:
            #     closed_positions_list = list(self.pnl_manager.closed_positions)
            #     for closed_position in closed_positions_list:
            #         if closed_position.exit_timestamp != current_time:
            #             continue  # Only check re-entry on the timestamp when position was closed
                    
            #         current_order = self.order_sequence_mapper_con.get_order(closed_position.unique_leg_id)
            #         reentry_triggered, summary = self.reentry_manager.check_reentry_conditions(
            #             position=closed_position,
            #             current_timestamp=current_time,
            #             current_ltp=spot_price,
            #             spot_df=spot_df,
            #             entry_para_dict=self.entry_para_dict
            #         )
            #         if reentry_triggered:
            #             logger.info(f"Re-entry triggered for position {closed_position.leg_id} at {current_time}")
            #             # Create new order dict based on closed position details
            #             new_order = closed_position.leg_dict.copy()
            #             new_order['order_initialization_time'] = current_time
                        
            #             # Execute re-entry using entry manager
            #             self.TRADE_DICT, self.order_book, self.orders, day_breaker = self.entry_manager.entry(
            #                 index=current_time,
            #                 order=new_order,
            #                 spot=spot_price,
            #                 leg_id=closed_position.leg_id,
            #                 TRADE_DICT=self.TRADE_DICT,
            #                 order_book=self.order_book,
            #                 orders={closed_position.leg_id: new_order}
            #             )
                        
            #             if day_breaker:
            #                 self.day_breaker = True
            #                 break

            #     # Check for exit conditions
            #     # self.TRADE_DICT, self.CLOSE_DICT, self.day_breaker = self.exit_manager.check_exits(
            #     #     current_time=current_time,
            #     #     spot_price=spot_price,
            #     #     vix_value=vix_value,
            #     #     prev_day_close=prev_day_close,
            #     #     TRADE_DICT=self.TRADE_DICT,
            #     #     CLOSE_DICT=self.CLOSE_DICT,
            #     #     entry_para_dict=self.entry_para_dict,
            #     #     logger=logger
            #     # )
                
            #     if self.day_breaker:
            #         logger.info("Day breaker activated. Exiting day loop.")
            #         break


            if current_time.time() >= self.entry_time.time() and not self.initial_entry:
                # Handle initial entry logic using unified entry manager
                if self.entry_manager is None:
                    logger.error("Entry manager not initialized. Please provide intraday_df_dict and miss_con in process_day()")
                    break
                
                # Execute entry for all legs
                for leg_id, order in self.orders.items():
                    try:
                        order["order_initialization_time"] = current_time
                        self.TRADE_DICT, self.order_book, self.orders, day_breaker = self.entry_manager.entry(
                            index=current_time,
                            order=order,
                            spot=spot_price,
                            leg_id=leg_id,
                            TRADE_DICT=self.TRADE_DICT,
                            order_book=self.order_book,
                            orders=self.orders,
                        )
                        if day_breaker:
                            self.day_breaker = True
                            break
                    except Exception as e:
                        logger.error(f"Entry execution failed for leg {leg_id} at {current_time}: {e}")
                        self.day_breaker = True
                        break

                self.initial_entry = True
                            
            # Execute pending entries for conditional strategies (momentum, range breakout, rolling straddle)
            # These strategies check conditions on every timestamp
            if self.entry_manager is not None and self.initial_entry:
                # Re-check all pending entries (momentum, range breakout, rolling straddle)
                # The unified manager handles this internally - strategies check conditions each call
                for leg_id, order in self.orders.items():
                    # Skip already executed legs
                    if leg_id in self.TRADE_DICT.get("leg_id", []):
                        continue
                    
                    # Only re-check if it's a conditional entry type
                    if (order.get("sm_toggle") or 
                        order.get("range_breakout_toggle") or 
                        order.get("rolling_straddle_toggle") or 
                        order.get("rolling_straddle_vwap_toggle")):
                        try:
                            self.TRADE_DICT, self.order_book, self.orders, day_breaker = self.entry_manager.entry(
                                index=current_time,
                                order=order,
                                spot=spot_price,
                                leg_id=leg_id,
                                TRADE_DICT=self.TRADE_DICT,
                                order_book=self.order_book,
                                orders=self.orders
                            )
                            
                            if day_breaker:
                                self.day_breaker = True
                                break
                        except Exception as e:
                            logger.warning(f"Conditional entry check failed for leg {leg_id} at {current_time}: {e}")
                            # Don't break on conditional entry failures - these are expected until condition is met
                        
                        if len(self.TRADE_DICT["Leg_id"] + self.CLOSE_DICT["Entry_price"]) > self.pnl_manager._position_counter:
                            self.pnl_manager.create_position(leg_id=leg_id,
                                                            unique_leg_id=order['unique_leg_id'],
                                                            trading_symbol=self.TRADE_DICT['TradingSymbol'][-1],
                                                            instrument_type=self.TRADE_DICT['Instrument_type'][-1],
                                                            strike=self.TRADE_DICT['Strike'][-1],
                                                            expiry=self.TRADE_DICT['Expiry_type'][-1],
                                                            entry_timestamp=self.TRADE_DICT['Entry_timestamp'][-1],
                                                            entry_price=self.TRADE_DICT['Entry_price'][-1],
                                                            quantity=self.TRADE_DICT['Lot_size'][-1]* self.entry_manager.lotsize,
                                                            position_type=self.TRADE_DICT['Position_type'][-1],
                                                            leg_dict=order,
                                                            sl_value=self.TRADE_DICT['Stop_loss'][-1],
                                                            target_price=self.TRADE_DICT['Target_price'][-1],
                                                            )
                            self.TRADE_DICT = self.pnl_manager.update_all_ltps(current_timestamp=timestamp,
                                                            TRADE_DICT=self.TRADE_DICT,
                                                            options_extractor_con=self.day_option_frame_con)

            # if (len(self.pnl_manager.active_positions) + len(self.pnl_manager.closed_positions)) > 0:
            #     print(self.pnl_manager.pnl_history[-1])

            # Record snapshot
            if len(self.pnl_manager.active_positions) > 0 or len(self.pnl_manager.closed_positions) > 0:
                self.pnl_manager._record_pnl_snapshot(timestamp=timestamp, spot_price=spot_price)
                

            if current_time.time() >= self.exit_time.time(): #or len(self.pnl_manager.active_positions) == 0 or self.day_breaker:
                logger.info("Strategy exit time reached. Exiting day loop.")
                self.pnl_manager.day_file_creator(date_str=self.entry_time.strftime("%Y-%m-%d"), strategy_save_dir=self.strategy_save_dir)
                break