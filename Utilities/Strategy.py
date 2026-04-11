"""
Strategy Base Classes and Registry

This module defines the base Strategy class and StrategyRegistry for conditional execution strategies
that can hook into the trading day lifecycle.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
import polars as pl

from Conditional_Execution.RSI_Execution import RSIExecution


class StrategyContext:
    """
    Context object passed to strategy methods containing current state.
    """
    def __init__(
        self,
        current_time: datetime,
        spot_price: float,
        vix_value: float,
        executed_orders: List[Dict[str, Any]],
        closed_positions: List[Dict[str, Any]],
        triggered_positions: List[Dict[str, Any]],
        main_orders: Dict[str, Any],
        pending_orders: Dict[str, Any],
        active_positions: Dict[str, Any],
        day_processor: Any  # Reference to DayProcessor for full access
    ):
        self.current_time = current_time
        self.spot_price = spot_price
        self.vix_value = vix_value
        self.executed_orders = executed_orders
        self.closed_positions = closed_positions
        self.triggered_positions = triggered_positions
        self.main_orders = main_orders
        self.pending_orders = pending_orders
        self.active_positions = active_positions
        self.day_processor = day_processor


class BaseStrategy(ABC):
    """
    Abstract base class for all conditional execution strategies.

    Strategies can hook into the trading day lifecycle and perform conditional execution
    between engine phases. They have ownership over orders they submit.
    """

    def __init__(self, strategy_id: str, config: Dict[str, Any], day_processor: Any):
        """
        Initialize strategy.

        Args:
            strategy_id: Unique identifier for this strategy instance
            config: Strategy-specific configuration
            day_processor: Reference to DayProcessor for accessing managers and data
        """
        self.strategy_id = strategy_id
        self.config = config
        self.day_processor = day_processor

    @abstractmethod
    def on_day_start(self, context: StrategyContext) -> None:
        """
        Called at the start of the trading day, before the bar loop.

        Args:
            context: Current trading context
        """
        pass

    @abstractmethod
    def on_bar(self, context: StrategyContext) -> None:
        """
        Called for each bar/timestamp in the trading day.

        This is where conditional execution logic should be implemented.
        Strategies can submit orders, modify positions, etc.

        Args:
            context: Current trading context
        """
        pass

    @abstractmethod
    def on_day_end(self, context: StrategyContext) -> None:
        """
        Called at the end of the trading day, after the bar loop.

        Args:
            context: Current trading context
        """
        pass

    def submit_order(
        self,
        leg_id: str,
        leg_config: Dict[str, Any],
        timestamp: datetime,
        spot_price: float,
        execution_type: str = ""
    ) -> bool:
        """
        Submit an order with strategy ownership.

        Args:
            leg_id: Leg identifier
            leg_config: Leg configuration
            timestamp: Current timestamp
            spot_price: Current spot price
            execution_type: Execution type

        Returns:
            True if order submitted successfully
        """
        # Add strategy ownership to leg_config
        leg_config = leg_config.copy()
        leg_config['strategy_owner'] = self.strategy_id

        order_id = self.day_processor.entry_manager.submit_order(
            leg_id=leg_id,
            leg_config=leg_config,
            timestamp=timestamp,
            spot_price=spot_price,
            execution_type=execution_type
        )
        return order_id is not None

    def get_owned_orders(self, context: StrategyContext) -> Dict[str, Any]:
        """
        Get orders owned by this strategy.

        Args:
            context: Current context

        Returns:
            Dict of order_id -> order_spec for orders owned by this strategy
        """
        owned_orders = {}
        for order_id, order_spec in context.pending_orders.items():
            if order_spec.get('strategy_owner') == self.strategy_id:
                owned_orders[order_id] = order_spec
        return owned_orders

    def can_modify_order(self, order_spec: Dict[str, Any]) -> bool:
        """
        Check if this strategy can modify the given order.

        Args:
            order_spec: Order specification

        Returns:
            True if this strategy owns the order
        """
        return order_spec.get('strategy_owner') == self.strategy_id


class RSIExecutionStrategy(BaseStrategy):
    """
    RSI-based conditional execution strategy.
    
    Monitors RSI levels and executes orders when RSI crosses oversold/overbought thresholds.
    """

    def __init__(self, strategy_id: str, config: Dict[str, Any], day_processor: Any):
        super().__init__(strategy_id, config, day_processor)
        self.rsi_executor = RSIExecution()

    def on_day_start(self, context: StrategyContext) -> None:
        """Reset RSI executor at day start."""
        self.rsi_executor.reset()

    def on_bar(self, context: StrategyContext) -> None:
        """Check RSI conditions on each bar."""
        # Get RSI value from spot_df (pandas)
        spot_df = context.day_processor.indicator_generator.spot_df
        rsi_value = spot_df[spot_df['Timestamp'] == context.current_time]['RSI_14'].iloc[0] if not spot_df.empty else None

        if rsi_value is None:
            return

        # Check if execution condition is met
        if self.rsi_executor.executor(spot_df, context.current_time):
            # RSI condition met - could submit orders here or trigger other actions
            # For now, just log
            print(f"RSI condition met at {context.current_time}: RSI={rsi_value}")

    def on_day_end(self, context: StrategyContext) -> None:
        """No action needed at day end."""
        pass


class StrategyRegistry:
    """
    Registry for managing active strategies during a trading day.
    """

    def __init__(self, day_processor: Any):
        """
        Initialize registry.

        Args:
            day_processor: Reference to DayProcessor
        """
        self.day_processor = day_processor
        self.active_strategies: Dict[str, BaseStrategy] = {}
        self.strategy_classes: Dict[str, type] = {}

    def register_strategy_class(self, strategy_type: str, strategy_class: type) -> None:
        """
        Register a strategy class by type.

        Args:
            strategy_type: String identifier for strategy type
            strategy_class: Strategy class (must inherit from BaseStrategy)
        """
        self.strategy_classes[strategy_type] = strategy_class

    def initialize_strategies(self, selected_strategies: List[Dict[str, Any]]) -> None:
        """
        Initialize strategies based on user selection.

        Args:
            selected_strategies: List of dicts with 'type' and 'config' keys
        """
        for strategy_config in selected_strategies:
            strategy_type = strategy_config['type']
            config = strategy_config.get('config', {})
            strategy_id = f"{strategy_type}_{len(self.active_strategies)}"

            if strategy_type in self.strategy_classes:
                strategy_instance = self.strategy_classes[strategy_type](
                    strategy_id=strategy_id,
                    config=config,
                    day_processor=self.day_processor
                )
                self.active_strategies[strategy_id] = strategy_instance
            else:
                raise ValueError(f"Unknown strategy type: {strategy_type}")

    def call_on_day_start(self, context: StrategyContext) -> None:
        """Call on_day_start for all active strategies."""
        for strategy in self.active_strategies.values():
            try:
                strategy.on_day_start(context)
            except Exception as e:
                # Log error but continue with other strategies
                print(f"Error in {strategy.strategy_id}.on_day_start: {e}")

    def call_on_bar(self, context: StrategyContext) -> None:
        """Call on_bar for all active strategies."""
        for strategy in self.active_strategies.values():
            try:
                strategy.on_bar(context)
            except Exception as e:
                # Log error but continue with other strategies
                print(f"Error in {strategy.strategy_id}.on_bar: {e}")

    def call_on_day_end(self, context: StrategyContext) -> None:
        """Call on_day_end for all active strategies."""
        for strategy in self.active_strategies.values():
            try:
                strategy.on_day_end(context)
            except Exception as e:
                # Log error but continue with other strategies
                print(f"Error in {strategy.strategy_id}.on_day_end: {e}")

    def get_strategy(self, strategy_id: str) -> BaseStrategy:
        """Get a strategy instance by ID."""
        return self.active_strategies.get(strategy_id)