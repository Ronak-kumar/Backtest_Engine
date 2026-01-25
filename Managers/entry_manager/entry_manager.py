"""
Entry Manager - Main Orchestrator

This is the main entry point for all order submissions and executions.
It manages the pending orders queue and delegates to appropriate strategies.
"""

from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import polars as pl

from .base_strategy import OrderSpec, EntryStrategy
from .immediate_strategy import ImmediateEntryStrategy
from .momentum_strategy import MomentumEntryStrategy
from .range_breakout_strategy import RangeBreakoutStrategy


class EntryManager:
    """
    Main Entry Manager that orchestrates all entry operations.
    
    This class:
    1. Accepts order submission requests
    2. Routes orders to appropriate strategies
    3. Maintains pending orders queue
    4. Executes orders when conditions are met
    
    Attributes:
        pending_orders: Dict mapping order_id to OrderSpec
        strategy_registry: Dict mapping strategy_type to strategy instance
        executed_orders: List of executed order_ids (for tracking)
    """
    
    def __init__(
        self,
        options_extractor,
        spot_df: pl.DataFrame,
        config: Dict[str, Any],
        logger: Any = None
    ):
        """
        Initialize Entry Manager.
        
        Args:
            options_extractor: Object to fetch options data
            spot_df: Spot price dataframe
            config: Configuration dict with:
                - base: Strike base
                - lotsize: Lot size
                - lot_qty: Number of lots
                - EntryMode: Entry price mode
                - StoplossCalMode: SL calculation mode
                - indices: Index name
            logger: Optional logger instance
        """
        self.options_extractor = options_extractor
        self.spot_df = spot_df
        self.config = config
        self.logger = logger
        
        # Initialize pending orders queue
        self.pending_orders: Dict[str, OrderSpec] = {}
        
        # Track executed orders
        self.executed_orders: List[str] = []
        
        # Initialize strategy registry
        self.strategy_registry: Dict[str, EntryStrategy] = {}
        self._register_strategies()
        
        self._log("EntryManager initialized with strategies: " + 
                  ", ".join(self.strategy_registry.keys()))
    
    def _register_strategies(self):
        """
        Register all available entry strategies.
        
        To add a new strategy:
        1. Create a new class inheriting from EntryStrategy
        2. Add it to this registry
        """
        self.strategy_registry = {
            'IMMEDIATE': ImmediateEntryStrategy(
                self.options_extractor,
                self.spot_df,
                self.config,
                self.logger
            ),
            'MOMENTUM': MomentumEntryStrategy(
                self.options_extractor,
                self.spot_df,
                self.config,
                self.logger
            ),
            'RANGE_BREAKOUT': RangeBreakoutStrategy(
                self.options_extractor,
                self.spot_df,
                self.config,
                self.logger
            )
        }
    
    def _determine_strategy_type(self, leg_config: Dict[str, Any]) -> str:
        """
        Determine which strategy to use based on leg configuration.
        
        Args:
            leg_config: Leg configuration dictionary
            
        Returns:
            Strategy type string (IMMEDIATE, MOMENTUM, RANGE_BREAKOUT)
        """
        # Check for momentum strategy
        if leg_config.get('sm_toggle'):
            return 'MOMENTUM'
        
        # Check for range breakout strategy
        if leg_config.get('range_breakout_toggle'):
            return 'RANGE_BREAKOUT'
        
        # Default to immediate
        return 'IMMEDIATE'
    
    def submit_order(
        self,
        leg_id: str,
        leg_config: Dict[str, Any],
        timestamp: datetime,
        spot_price: float,
        execution_type: str = ""
    ) -> Optional[str]:
        """
        PHASE 1: Submit an order for later execution.
        
        This method:
        1. Determines which strategy to use
        2. Gets the strategy instance
        3. Calls strategy.generate_order_spec()
        4. Stores order in pending_orders
        5. Returns order_id
        
        Args:
            leg_id: Leg identifier (e.g., 'leg_1')
            leg_config: Complete leg configuration
            timestamp: Current timestamp
            spot_price: Current spot price
            
        Returns:
            order_id if successful, None if order could not be created
            
        Example:
            order_id = entry_manager.submit_order(
                leg_id='leg_1',
                leg_config=config,
                timestamp=datetime.now(),
                spot_price=20000.0
            )
        """
        try:
            # Determine strategy type
            if execution_type == "":
                strategy_type = self._determine_strategy_type(leg_config)
            else:
                strategy_type = execution_type

            
            # Get strategy instance
            if strategy_type not in self.strategy_registry:
                self._log(
                    f"Unknown strategy type: {strategy_type}",
                    'error'
                )
                return None
            
            strategy = self.strategy_registry[strategy_type]
            
            # Generate order spec
            self._log(
                f"Generating {strategy_type} order for {leg_id} at {timestamp}"
            )
            
            order_spec = strategy.generate_order_spec(
                leg_id=leg_id,
                leg_config=leg_config,
                timestamp=timestamp,
                spot_price=spot_price
            )
            
            if order_spec is None:
                self._log(
                    f"Failed to generate order spec for {leg_id}",
                    'warning'
                )
                return None
            
            # Store in pending orders
            self.pending_orders[order_spec.order_id] = order_spec
            
            self._log(
                f"Order submitted: {order_spec.order_id} "
                f"(Strategy: {strategy_type}, Leg: {leg_id})"
            )
            
            return order_spec.order_id
            
        except Exception as e:
            self._log(f"Error submitting order for {leg_id}: {e}", 'error')
            return None
    
    def execute_pending_entries(
        self,
        timestamp: datetime,
        spot_price: float,
        TRADE_DICT: Dict[str, list],
        order_book: Dict[str, list]
    ) -> Tuple[Dict[str, list], Dict[str, list], List[str]]:
        """
        PHASE 2: Check and execute all pending orders.
        
        This method:
        1. Loops through all pending orders
        2. For each order, checks if can_execute()
        3. If yes, calls strategy.execute()
        4. Updates TRADE_DICT and order_book
        5. Removes from pending_orders
        6. Returns list of executed order_ids
        
        Args:
            timestamp: Current timestamp
            spot_price: Current spot price
            TRADE_DICT: Trade dictionary to update
            order_book: Order book dictionary to update
            
        Returns:
            Tuple of (updated TRADE_DICT, updated order_book, executed_order_ids)
            
        Example:
            TRADE_DICT, order_book, executed = entry_manager.execute_pending_entries(
                timestamp=current_time,
                spot_price=20050.0,
                TRADE_DICT=TRADE_DICT,
                order_book=order_book
            )
            
            if executed:
                print(f"Executed: {executed}")
        """
        executed_order_ids = []
        
        # Create a copy of pending order ids to iterate
        # (we'll be modifying the dict during iteration)
        pending_ids = list(self.pending_orders.keys())
        
        for order_id in pending_ids:
            order_spec = self.pending_orders[order_id]
            
            try:
                # Get the strategy that created this order
                strategy_type = order_spec.strategy_type
                
                if strategy_type not in self.strategy_registry:
                    self._log(
                        f"Unknown strategy type for order {order_id}: {strategy_type}",
                        'error'
                    )
                    continue
                
                strategy = self.strategy_registry[strategy_type]
                
                # Check if can execute
                can_execute = strategy.can_execute(
                    order_spec=order_spec,
                    timestamp=timestamp,
                    spot_price=spot_price
                )
                
                if can_execute:
                    # Execute the order
                    self._log(
                        f"Executing order {order_id} for {order_spec.leg_id} "
                        f"at {timestamp}"
                    )
                    
                    TRADE_DICT, order_book = strategy.execute(
                        order_spec=order_spec,
                        timestamp=timestamp,
                        spot_price=spot_price,
                        TRADE_DICT=TRADE_DICT,
                        order_book=order_book
                    )
                    
                    # Remove from pending
                    del self.pending_orders[order_id]
                    
                    # Track execution
                    executed_order_ids.append(order_id)
                    self.executed_orders.append(order_id)
                    
                    self._log(
                        f"Order executed successfully: {order_id}"
                    )
                
            except Exception as e:
                self._log(
                    f"Error executing order {order_id}: {e}",
                    'error'
                )
                # Keep order in pending - don't remove on error
                continue
        
        if executed_order_ids:
            self._log(
                f"Executed {len(executed_order_ids)} orders at {timestamp}"
            )
        
        return TRADE_DICT, order_book, executed_order_ids
    
    def get_pending_orders(self) -> Dict[str, OrderSpec]:
        """
        Get all pending orders.
        
        Returns:
            Dictionary of pending orders
        """
        return self.pending_orders.copy()
    
    def get_pending_count(self) -> int:
        """
        Get count of pending orders.
        
        Returns:
            Number of pending orders
        """
        return len(self.pending_orders)
    
    def get_executed_count(self) -> int:
        """
        Get count of executed orders.
        
        Returns:
            Number of executed orders
        """
        return len(self.executed_orders)
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a pending order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if cancelled, False if not found
        """
        if order_id in self.pending_orders:
            order_spec = self.pending_orders[order_id]
            del self.pending_orders[order_id]
            
            self._log(
                f"Cancelled order {order_id} for {order_spec.leg_id}"
            )
            return True
        
        return False
    
    def cancel_all_pending(self):
        """Cancel all pending orders."""
        count = len(self.pending_orders)
        self.pending_orders.clear()
        
        self._log(f"Cancelled {count} pending orders")
    
    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of an order.
        
        Args:
            order_id: Order ID
            
        Returns:
            Dict with status info, or None if not found
        """
        # Check pending
        if order_id in self.pending_orders:
            order_spec = self.pending_orders[order_id]
            return {
                'status': 'PENDING',
                'order_id': order_id,
                'leg_id': order_spec.leg_id,
                'strategy_type': order_spec.strategy_type,
                'created_at': order_spec.timestamp_created
            }
        
        # Check executed
        if order_id in self.executed_orders:
            return {
                'status': 'EXECUTED',
                'order_id': order_id
            }
        
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get entry manager statistics.
        
        Returns:
            Dict with various statistics
        """
        # Count by strategy type
        strategy_counts = {}
        for order_spec in self.pending_orders.values():
            strategy_type = order_spec.strategy_type
            strategy_counts[strategy_type] = strategy_counts.get(strategy_type, 0) + 1
        
        return {
            'pending_count': len(self.pending_orders),
            'executed_count': len(self.executed_orders),
            'pending_by_strategy': strategy_counts,
            'total_submitted': len(self.pending_orders) + len(self.executed_orders)
        }
    
    def reset(self):
        """
        Reset the entry manager (for new day or testing).
        
        Clears all pending and executed orders.
        """
        self.pending_orders.clear()
        self.executed_orders.clear()
        
        self._log("EntryManager reset")
    
    def _log(self, message: str, level: str = 'info'):
        """
        Log a message if logger is available.
        
        Args:
            message: Message to log
            level: Log level (info, warning, error)
        """
        if self.logger:
            log_method = getattr(self.logger, level, self.logger.info)
            log_method(f"[EntryManager] {message}")