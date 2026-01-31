from pathlib import Path
import sys
MAIN_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(MAIN_DIR))

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
# from Managers.entry_manager import UnifiedEntryManager
from Managers.exit_manager import ExitManager
from Managers.pnl_manager import PNLManager
from Managers.reentry_manager import ReentryManager
from Utilities.Order_Sequencer import OrderSequenceMapper
from Managers.entry_manager.entry_manager import EntryManager
from Visualization.trade_plotter import ProfessionalTradeAnalystPlotter


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
        self.entry_manager = None
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
        
        # ADD: New entry manager initialization
        self.entry_manager = EntryManager(
            options_extractor=options_extractor_con,
            spot_df=None,  # Will be set in process_day()
            config={
                'base': self.entry_para_dict['base_symbol_spread'],
                'lotsize': self.entry_para_dict['symbol_lotsize'],
                'lot_qty': self.entry_para_dict['lots'],
                'EntryMode': self.entry_para_dict['EntryMode'],
                'StoplossCalMode': self.entry_para_dict['StoplossCalMode'],
                'indices': self.entry_para_dict['indices']
            },
            logger=None  # Pass logger if you have one
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


            # ============================================================
            # UPDATE POSITIONS (if any exist)
            # ============================================================
            if len(self.pnl_manager.active_positions) > 0 or len(self.pnl_manager.closed_positions) > 0:
                # Update P&L for open positions
                self.TRADE_DICT = self.pnl_manager.update_all_ltps(current_timestamp=timestamp,
                                                TRADE_DICT=self.TRADE_DICT,
                                                options_extractor_con=self.day_option_frame_con)
                
            # ============================================================
            # CHECKING POSITIONS CLOSING
            # ============================================================
            if len(self.pnl_manager.active_positions) > 0:
                # Check stop loss for all active positions
                standing_positions_list = list(self.pnl_manager.active_positions.values())
                for standing_position in standing_positions_list:
                    stop_loss_triggers, summary = self.exit_manager.check_specific_exit(exit_type="STOPLOSS", position=standing_position,
                                                current_timestamp=current_time, current_ltp=spot_price, spot_df=spot_df)
                    if stop_loss_triggers:
                        exit_price = standing_position.stop_loss
                        logger.info(f"Stop loss triggered exit for position {standing_position.leg_id} at {current_time}")
                        self.pnl_manager.close_position(position_id=standing_position.position_id, exit_timestamp=current_time,
                                                        exit_price=exit_price, exit_reason=summary)
                
                standing_positions_list = list(self.pnl_manager.active_positions.values())
                for standing_position in standing_positions_list:
                    target_triggers, summary = self.exit_manager.check_specific_exit(exit_type="TARGET", position=standing_position,
                            current_timestamp=current_time, current_ltp=spot_price, spot_df=spot_df)
                    if target_triggers:
                        exit_price = standing_position.target_price
                        logger.info(f"Target triggered exit for position {standing_position.leg_id} at {current_time}")
                        self.pnl_manager.close_position(position_id=standing_position.position_id, exit_timestamp=current_time,
                                                        exit_price=exit_price, exit_reason=summary)
                        
            
            # Re-entry logic for positions that were closed
            if len(self.pnl_manager.closed_positions) > 0:
                closed_positions_list = list(self.pnl_manager.closed_positions)
                for closed_position in closed_positions_list:
                    if closed_position.exit_timestamp != current_time:
                        continue  # Only check re-entry on the timestamp when position was closed
                    
                    record_entry = False
                    leg_id = closed_position.leg_id
                    order_to_execute = closed_position.leg_dict

                    stoploss_based_closing = "SL" in closed_position.exit_reason
                    target_based_closing = "Target" in closed_position.exit_reason

                    # Rentry for sl based closed position
                    if stoploss_based_closing and order_to_execute.get("rentry_sl_toggle", False):
                        if order_to_execute.get("total_sl_rentry", 0) != None and order_to_execute.get("total_sl_rentry", 0) > 0:
                            self.order_sequence_mapper_con.hopping_count_manager(leg_id, "total_sl_rentry")
                            order_to_execute['total_sl_rentry'] -= 1
                            reentry_execution_type = "IMMEDIATE"
                            record_entry = True

                    # Rentry for target based closed position
                    elif target_based_closing and order_to_execute.get("rentry_tgt_toggle", False):
                        if order_to_execute.get("total_tgt_rentry", 0) != None and order_to_execute.get("total_tgt_rentry", 0) > 0:
                            self.order_sequence_mapper_con.hopping_count_manager(leg_id, "total_tgt_rentry")
                            order_to_execute['total_tgt_rentry'] -= 1
                            reentry_execution_type = "IMMEDIATE"
                            record_entry = True


                    # lazy legs execution 
                    if not record_entry:
                        if stop_loss_triggers and order_to_execute.get("leg_hopping_count_sl", 0) > 0 and order_to_execute.get("leg_tobe_executed_on_sl", False):
                            order_to_execute, leg_id =  self.order_sequence_mapper_con.get_next_order(order_to_execute, leg_id, hopping_type="leg_hopping_count_sl", leg_to_fetch="leg_tobe_executed_on_sl")
                            record_entry = True
                            reentry_execution_type = ""


                        elif target_based_closing and order_to_execute.get("leg_hopping_count_tgt", 0) > 0 and order_to_execute.get("leg_tobe_executed_on_target", False):
                            order_to_execute, leg_id =  self.order_sequence_mapper_con.get_next_order(order_to_execute, leg_id, hopping_type="leg_hopping_count_tgt", leg_to_fetch="leg_tobe_executed_on_target")
                            record_entry = True
                            reentry_execution_type = ""

                            # order_to_execute["leg_hopping_count_tgt"] -= 1
                            # leg_id = order_to_execute.get("leg_tobe_executed_on_target", "").replace(".", "_")
                            # order_to_execute = self.order_sequence_mapper_con.get_order(leg_id)

                        elif (stoploss_based_closing or target_based_closing) and order_to_execute.get("leg_hopping_count_next_leg", 0) > 0 and order_to_execute.get("next_lazy_leg_to_be_executed", False):
                            order_to_execute, leg_id =  self.order_sequence_mapper_con.get_next_order(order_to_execute, leg_id, hopping_type="leg_hopping_count_next_leg", leg_to_fetch="next_lazy_leg_to_be_executed")
                            record_entry = True
                            reentry_execution_type = ""

                            # order_to_execute["leg_hopping_count_next_leg"] -= 1
                            # leg_id = order_to_execute.get("next_lazy_leg_to_be_executed", "").replace(".", "_")
                            # order_to_execute = self.order_sequence_mapper_con.get_order(leg_id)




                    if record_entry:
                        # registring oredrs in entry manager
                        try:
                            order_id = self.entry_manager.submit_order(
                                leg_id=leg_id,
                                leg_config=order_to_execute,
                                timestamp=current_time,
                                spot_price=spot_price,
                                execution_type=reentry_execution_type
                            )
                            
                            if order_id:
                                logger.info(f"Submitted order: {order_id} for {leg_id}")
                            else:
                                logger.warning(f"Failed to submit order for {leg_id}")
                                
                        except Exception as e:
                            logger.error(f"Error submitting order for {leg_id}: {e}")
                            self.day_breaker = True
                            break

                # Check for exit conditions
                # self.TRADE_DICT, self.CLOSE_DICT, self.day_breaker = self.exit_manager.check_exits(
                #     current_time=current_time,
                #     spot_price=spot_price,
                #     vix_value=vix_value,
                #     prev_day_close=prev_day_close,
                #     TRADE_DICT=self.TRADE_DICT,
                #     CLOSE_DICT=self.CLOSE_DICT,
                #     entry_para_dict=self.entry_para_dict,
                #     logger=logger
                # )
                
                if self.day_breaker:
                    logger.info("Day breaker activated. Exiting day loop.")
                    break


            # ============================================================
            # PHASE 1: ORDER SUBMISSION (at entry time)
            # ============================================================
            if current_time.time() >= self.entry_time.time() and not self.initial_entry:
                logger.info(f"Submitting orders at {current_time.time()}")
                
                # Submit all main leg orders
                for leg_id, order in self.order_sequence_mapper_con.main_orders.items():
                    try:
                        order_id = self.entry_manager.submit_order(
                            leg_id=leg_id,
                            leg_config=order,
                            timestamp=current_time,
                            spot_price=spot_price
                        )
                        
                        if order_id:
                            logger.info(f"Submitted order: {order_id} for {leg_id}")
                        else:
                            logger.warning(f"Failed to submit order for {leg_id}")
                            
                    except Exception as e:
                        logger.error(f"Error submitting order for {leg_id}: {e}")
                        self.day_breaker = True
                        break
                
                self.initial_entry = True
                
                # Log statistics
                stats = self.entry_manager.get_statistics()
                logger.info(f"Pending orders: {stats['pending_count']}")
                logger.info(f"By strategy: {stats['pending_by_strategy']}")
            
            # ============================================================
            # PHASE 2: EXECUTE PENDING ORDERS (every minute)
            # ============================================================
            if self.initial_entry and len(self.entry_manager.pending_orders) != 0:
                try:
                    TRADE_DICT, order_book, executed_ids = self.entry_manager.execute_pending_entries(
                        timestamp=current_time,
                        spot_price=spot_price,
                        TRADE_DICT=self.TRADE_DICT,
                        order_book=self.order_book
                    )
                    
                    # Update instance variables
                    self.TRADE_DICT = TRADE_DICT
                    self.order_book = order_book
                    
                    # If orders were executed, create positions
                    if executed_ids:
                        logger.info(f"Executed {len(executed_ids)} orders at {current_time.time()}")
                        
                        for order_id in executed_ids:
                            # Find the index of this execution in TRADE_DICT
                            # (newly executed orders are at the end)
                            position_idx = len(self.TRADE_DICT['Leg_id']) - len(executed_ids) + executed_ids.index(order_id)
                            
                            # Get leg_id and order
                            executed_leg_id = self.TRADE_DICT['Leg_id'][position_idx]
                            leg_order = self.order_sequence_mapper_con._get_order(executed_leg_id)
                            # leg_order = self.orders[executed_leg_id]
                            
                            # Create position in PNL Manager
                            self.pnl_manager.create_position(
                                leg_id=executed_leg_id,
                                unique_leg_id=leg_order['unique_leg_id'],
                                trading_symbol=self.TRADE_DICT['TradingSymbol'][position_idx],
                                instrument_type=self.TRADE_DICT['Instrument_type'][position_idx],
                                strike=self.TRADE_DICT['Strike'][position_idx],
                                expiry=self.TRADE_DICT['Expiry_type'][position_idx],
                                entry_timestamp=self.TRADE_DICT['Entry_timestamp'][position_idx],
                                entry_price=self.TRADE_DICT['Entry_price'][position_idx],
                                quantity=self.TRADE_DICT['Lot_size'][position_idx] * self.entry_manager.config['lotsize'],
                                position_type=self.TRADE_DICT['Position_type'][position_idx],
                                leg_dict=leg_order,
                                sl_value=self.TRADE_DICT['Stop_loss'][position_idx],
                                target_price=self.TRADE_DICT['Target_price'][position_idx]
                            )
                            
                            logger.info(f"Created position for {executed_leg_id}")
                            
                except Exception as e:
                    logger.error(f"Error executing pending entries: {e}")
                    self.day_breaker = True
                    break
            
            # ============================================================
            # RECORD SNAPSHOT
            # ============================================================
            if len(self.pnl_manager.active_positions) > 0 or len(self.pnl_manager.closed_positions) > 0:
                self.pnl_manager._record_pnl_snapshot(timestamp=timestamp, spot_price=spot_price)

            ### Exiting day early when there is nothing to execute ###
            if len(self.pnl_manager.active_positions) == 0 and self.initial_entry and len(self.entry_manager.pending_orders) == 0:
                self.day_breaker = True
            
            # ============================================================
            # EXIT TIME CHECK
            # ============================================================
            if current_time.time() >= self.exit_time.time() or self.day_breaker:
                logger.info("Strategy exit time reached. Exiting day loop.")




                # Closing all the standing position as engine running on intraday setup
                if len(self.pnl_manager.active_positions) > 0:  
                    # Check stop loss for all active positions
                    standing_positions_list = list(self.pnl_manager.active_positions.values())
                    for standing_position in standing_positions_list:
                        summary = f"{'Exit time'if current_time.time() >= self.exit_time.time() else 'Day breaker flag'} triggered for leg {standing_position.unique_leg_id} closing position at ltp of {standing_position.current_ltp}"
                        exit_price = standing_position.current_ltp
                        logger.info(f"Exit time of day breaker for position {standing_position.leg_id} at {current_time}")
                        self.pnl_manager.close_position(position_id=standing_position.position_id, exit_timestamp=current_time,
                                                        exit_price=exit_price, exit_reason=summary)

                ### Creatng per day plotting ###
                order_book_df = self.pnl_manager.get_order_book_frame()
                plotter = ProfessionalTradeAnalystPlotter(order_book_df.to_pandas(), spot_df.to_pandas(), self.entry_para_dict['strategy_name'])
                plotter_save_path = self.strategy_save_dir / "Spot_Plot" / f'{(self.entry_para_dict["indices"]+"_"+current_time.strftime("%Y_%m_%d"))}.html'
                plotter.plot_professional_analysis(plotter_save_path)

                day_df, _ = self.pnl_manager.tradelog_dataframe()
                results = quick_analyze(
                    trades=order_book_df.to_pandas(),
                    market_data=spot_df.to_pandas(),
                    output_dir=f'{self.strategy_save_dir}/analysis'
                                                )



                # Save day file
                self.pnl_manager.day_file_creator(
                    date_str=self.entry_time.strftime("%Y-%m-%d"),
                    strategy_save_dir=self.strategy_save_dir
                )
                break
