"""
Base Strategy Module - Core Components for Entry Management

This module provides:
1. OrderSpec dataclass - Container for pending order data
2. EntryStrategy base class - Abstract interface for all strategies
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import polars as pl


@dataclass
class OrderSpec:
    """
    Specification for a pending order.
    
    This is the data package that gets stored in pending_orders queue.
    It contains all information needed to execute the order later.
    
    Attributes:
        order_id: Unique identifier for this order
        leg_id: Leg identifier (e.g., 'leg_1', 'leg_2')
        leg_config: Complete leg configuration dictionary
        timestamp_created: When this order was created
        strategy_type: Type of strategy (IMMEDIATE, MOMENTUM, RANGE_BREAKOUT, etc.)
        strategy_data: Strategy-specific data needed for execution
    """
    order_id: str
    leg_id: str
    leg_config: Dict[str, Any]
    timestamp_created: datetime
    strategy_type: str
    strategy_data: Dict[str, Any] = field(default_factory=dict)
    
    def __repr__(self) -> str:
        return (
            f"OrderSpec(id={self.order_id}, leg={self.leg_id}, "
            f"strategy={self.strategy_type}, created={self.timestamp_created})"
        )


class EntryStrategy(ABC):
    """
    Abstract base class for all entry strategies.
    
    Each strategy must implement three methods:
    1. generate_order_spec() - Create order specification (PHASE 1)
    2. can_execute() - Check if order can execute (PHASE 2)
    3. execute() - Execute the order (PHASE 2)
    
    This ensures all strategies work uniformly with EntryManager.
    """
    
    def __init__(
        self,
        options_extractor,
        spot_df: pl.DataFrame,
        config: Dict[str, Any],
        logger: Any = None
    ):
        """
        Initialize strategy with dependencies.
        
        Args:
            options_extractor: Object to fetch options data
            spot_df: Spot price dataframe
            config: Configuration dict with:
                - base: Strike base (e.g., 50 for NIFTY)
                - lotsize: Lot size for the index
                - lot_qty: Number of lots
                - EntryMode: Price mode for entry (Open/High/Low/Close)
                - StoplossCalMode: Price mode for SL calculation
                - indices: Index name (NIFTY, BANKNIFTY, etc.)
            logger: Optional logger instance
        """
        self.options_extractor = options_extractor
        self.spot_df = spot_df
        self.config = config
        self.logger = logger
        
        # Extract commonly used config values
        self.base = config.get('base', 50)
        self.lotsize = config.get('lotsize', 50)
        self.lot_qty = config.get('lot_qty', 1)
        self.entry_mode = config.get('EntryMode', 'Close')
        self.stoploss_cal_mode = config.get('StoplossCalMode', 'Close')
        self.indices = config.get('indices', 'NIFTY')
    
    @abstractmethod
    def generate_order_spec(
        self,
        leg_id: str,
        leg_config: Dict[str, Any],
        timestamp: datetime,
        spot_price: float
    ) -> Optional[OrderSpec]:
        """
        PHASE 1: Generate order specification with all data needed for execution.
        
        This method should:
        1. Calculate strike price based on leg_config
        2. Fetch required option data
        3. Calculate any thresholds or conditions
        4. Store all data in strategy_data dict
        5. Return OrderSpec
        
        Args:
            leg_id: Leg identifier
            leg_config: Leg configuration dictionary
            timestamp: Current timestamp
            spot_price: Current spot price
            
        Returns:
            OrderSpec with strategy_data populated, or None if cannot create
            
        Example strategy_data for Momentum:
            {
                'ticker': 'NIFTY24JAN20000CE',
                'strike': 20000.0,
                'instrument_type': 'CE',
                'normal_entry_price': 100.00,
                'momentum_threshold_price': 105.00,
                'direction': 'PERCENTAGE_UP',
                'initial_close': 100.00
            }
        """
        pass
    
    @abstractmethod
    def can_execute(
        self,
        order_spec: OrderSpec,
        timestamp: datetime,
        spot_price: float
    ) -> bool:
        """
        PHASE 2: Check if order can be executed at current timestamp.
        
        This method should:
        1. Use data from order_spec.strategy_data
        2. Check current market conditions
        3. Determine if execution criteria are met
        4. Return True/False
        
        Args:
            order_spec: The order specification to check
            timestamp: Current timestamp
            spot_price: Current spot price
            
        Returns:
            True if order can execute, False otherwise
            
        Example for Momentum:
            - Get current option price
            - Compare to threshold
            - Return True if threshold crossed
        """
        pass
    
    @abstractmethod
    def execute(
        self,
        order_spec: OrderSpec,
        timestamp: datetime,
        spot_price: float,
        TRADE_DICT: Dict[str, list],
        order_book: Dict[str, list]
    ) -> Tuple[Dict[str, list], Dict[str, list]]:
        """
        PHASE 2: Execute the order and update TRADE_DICT, order_book.
        
        This method should:
        1. Use data from order_spec.strategy_data
        2. Calculate final entry price
        3. Calculate stop loss and target
        4. Update TRADE_DICT with position details
        5. Update order_book with execution record
        6. Return updated dicts
        
        Args:
            order_spec: The order specification to execute
            timestamp: Current timestamp
            spot_price: Current spot price
            TRADE_DICT: Trade dictionary to update
            order_book: Order book dictionary to update
            
        Returns:
            Tuple of (updated TRADE_DICT, updated order_book)
        """
        pass
    
    # Helper methods (common across strategies)
    
    def _calculate_strike(
        self,
        leg_config: Dict[str, Any],
        spot_price: float
    ) -> float:
        """
        Calculate strike price based on strike_type.
        
        Args:
            leg_config: Leg configuration
            spot_price: Current spot price
            
        Returns:
            Calculated strike price
        """
        strike_type = leg_config.get('strike_type', 'ATM')
        
        if strike_type == 'ATM':
            return self.base * round(spot_price / self.base)
        
        elif strike_type == 'OTM':
            spread_value = leg_config.get('spread', 0) * self.base
            if leg_config.get('option_type') == 'CE':
                return self.base * round((spot_price + spread_value) / self.base)
            else:  # PE
                return self.base * round((spot_price - spread_value) / self.base)
        
        elif strike_type == 'ITM':
            spread_value = leg_config.get('spread', 0) * self.base
            if leg_config.get('option_type') == 'CE':
                return self.base * round((spot_price - spread_value) / self.base)
            else:  # PE
                return self.base * round((spot_price + spread_value) / self.base)
        
        else:
            # Default to ATM
            return self.base * round(spot_price / self.base)
    
    def _calculate_sl_target(
        self,
        entry_price: float,
        leg_config: Dict[str, Any],
        position_type: str
    ) -> Tuple[float, float]:
        """
        Calculate stop loss and target prices.
        
        Args:
            entry_price: Entry price for position
            leg_config: Leg configuration
            position_type: 'Buy' or 'Sell'
            
        Returns:
            Tuple of (stop_loss, target_price)
        """
        stop_loss = 0.0
        target_price = 0.0
        
        # Calculate stop loss
        if leg_config.get('stoploss_toggle'):
            stoploss_type = leg_config.get('stoploss_type', 'Percentage')
            stoploss_value = leg_config.get('stoploss_value', 0)
            
            if stoploss_type == 'Points':
                if position_type == 'Sell':
                    stop_loss = round(entry_price + stoploss_value, 2)
                else:  # Buy
                    stop_loss = round(entry_price - stoploss_value, 2)
            else:  # Percentage
                if position_type == 'Sell':
                    stop_loss = round(entry_price + (entry_price * stoploss_value), 2)
                else:  # Buy
                    stop_loss = round(entry_price - (entry_price * stoploss_value), 2)
        
        # Calculate target
        if leg_config.get('target_toggle'):
            target_value = leg_config.get('target_value', 0)
            if position_type == 'Sell':
                target_price = round(entry_price - (entry_price * target_value), 2)
            else:  # Buy
                target_price = round(entry_price + (entry_price * target_value), 2)
        
        return stop_loss, target_price
    
    def _log(self, message: str, level: str = 'info'):
        """
        Log a message if logger is available.
        
        Args:
            message: Message to log
            level: Log level (info, warning, error)
        """
        if self.logger:
            log_method = getattr(self.logger, level, self.logger.info)
            log_method(f"[{self.__class__.__name__}] {message}")
    
    def _get_option_row(
        self,
        strike: float,
        leg_config: Dict[str, Any],
        timestamp: datetime
    ) -> Optional[pl.DataFrame]:
        """
        Get option data for specific strike and timestamp.
        
        Args:
            strike: Strike price
            leg_config: Leg configuration
            timestamp: Timestamp to fetch data for
            
        Returns:
            Polars DataFrame with option data, or None if not found
        """
        try:
            df = self.options_extractor.data_handler(
                strike_price=strike,
                expiry_type=leg_config['leg_expiry_selection'],
                current_timestamp=timestamp,
                indices=self.indices
            )
            
            # Filter for specific instrument type
            filtered = df.filter(
                (pl.col('Strike') == strike) &
                (pl.col('Instrument_type') == leg_config['option_type']) &
                (pl.col('Timestamp').dt.time() == timestamp.time())
            )
            
            return filtered if filtered.height > 0 else None
            
        except Exception as e:
            self._log(f"Error fetching option data: {e}", 'error')
            return None
    
    def _get_option_by_ticker(
        self,
        ticker: str,
        leg_config: Dict[str, Any],
        timestamp: datetime
    ) -> Optional[pl.DataFrame]:
        """
        Get option data by ticker symbol.
        
        Args:
            ticker: Ticker symbol
            leg_config: Leg configuration
            timestamp: Timestamp to fetch data for
            
        Returns:
            Polars DataFrame with option data, or None if not found
        """
        try:
            df = self.options_extractor.data_handler(
                strike_price=None,
                expiry_type=leg_config['leg_expiry_selection'],
                current_timestamp=timestamp,
                indices=self.indices,
                ticker=ticker
            )
            
            filtered = df.filter(
                (pl.col('Ticker') == ticker) &
                (pl.col('Timestamp').dt.time() == timestamp.time())
            )
            
            return filtered if filtered.height > 0 else None
            
        except Exception as e:
            self._log(f"Error fetching option by ticker: {e}", 'error')
            return None