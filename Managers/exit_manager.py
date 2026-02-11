"""
Exit Manager Module

This module provides functionality for managing various exit strategies in the backtesting engine.
Each exit type is implemented as a separate strategy class following the Strategy pattern.

Classes:
    ExitStrategy: Abstract base class for all exit strategies
    StopLossExit: Stop loss exit strategy (Points, Percentage, Weekday-specific)
    TargetProfitExit: Target profit exit strategy
    TrailingStopLossExit: Trailing stop loss exit strategy
    ConditionalExit: Conditional exit based on spot movement or other conditions
    IndicatorExit: Indicator-based exit (e.g., VWAP, moving averages)
    TimeBasedExit: Time-based exit (e.g., square off time)
    ExitManager: Main manager class that coordinates all exit strategies
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, time
import polars as pl


class ExitStrategy(ABC):
    """Abstract base class for exit strategies."""
    
    @abstractmethod
    def check_exit_condition(
        self,
        position: Dict[str, Any],
        current_timestamp: datetime,
        current_ltp: float,
        spot_df: pl.DataFrame,
        **kwargs
    ) -> Tuple[bool, str]:
        """
        Check if exit condition is met for this strategy.
        
        Args:
            position: Dictionary containing position details (entry price, quantity, etc.)
            current_timestamp: Current timestamp being processed
            current_ltp: Current last traded price
            spot_df: Spot price dataframe
            **kwargs: Additional strategy-specific parameters
            
        Returns:
            Tuple of (should_exit: bool, exit_reason: str)
        """
        pass


class StopLossExit(ExitStrategy):
    """Stop loss exit strategy supporting Points, Percentage, and Weekday-specific SL."""
    
    def check_exit_condition(
        self,
        position: Dict[str, Any],
        current_timestamp: datetime,
        spot_df: pl.DataFrame,
        **kwargs
    ) -> Tuple[bool, str]:
        """
        Check stop loss condition.
        
        Supports three types:
        1. Points: Fixed point-based stop loss
        2. Percentage: Percentage-based stop loss
        3. Weekday-specific: Different SL for each day of the week
        
        Args:
            position: Position details with 'entry_price', 'position_type', 'leg_dict'
            current_timestamp: Current timestamp
            current_ltp: Current LTP
            spot_df: Spot dataframe (not used)
            **kwargs: Additional parameters
            
        Returns:
            Tuple of (should_exit, exit_reason)
        """
        leg_dict = position.leg_dict
        
        if not leg_dict.get("stoploss_toggle", False):
            return False, ""
        
        entry_price = position.entry_price
        position_type = position.position_type
        stoploss_type = leg_dict.get("stoploss_type", "Points")
        stoploss_value = leg_dict.get("stoploss_value", 0)
        
        if entry_price == 0 or stoploss_value == 0:
            return False, ""
        
        ohlc = position.OHLCV_data

        # Determine current LTP based on compare type
        if position.stop_loss_compare_type == "":
            sl_comparing_value = ohlc['Low'] if position_type.upper() == "BUY" else ohlc['High']
        else:
            sl_comparing_value = ohlc[position.stop_loss_compare_type]

        if position_type.upper() == "BUY":
            if sl_comparing_value <= position.stop_loss:
                return True, f"SL Triggered Exit for leg {leg_dict.get('unique_leg_id', '')} at {position.stop_loss} with a comapraring value of {sl_comparing_value}"
        else:  # SELL
            if sl_comparing_value >= position.stop_loss:
                return True, f"SL Triggered Exit for leg {leg_dict.get('unique_leg_id', '')} at {position.stop_loss} with a comapraring value of {sl_comparing_value}"
        
        
        # # Calculate P&L
        # if position_type.upper() == "BUY":
        #     pnl = round(sl_comparing_value - entry_price, 2)
        # else:  # SELL
        #     pnl = round(entry_price - sl_comparing_value, 2)
        
        # # Check stop loss based on type
        # if stoploss_type == "Points":
        #     # Points-based stop loss
        #     if pnl <= -stoploss_value:
        #         return True, f"SL Triggered for leg {leg_dict.get('unique_leg_id', '')} at {position.stop_loss} with a comapraring value of {sl_comparing_value}"
        
        # elif stoploss_type == "Percentage":
        #     # Percentage-based stop loss
        #     percentage_loss = (pnl / entry_price) * 100
        #     if percentage_loss <= (-stoploss_value * 100):
        #         return True, f"SL Triggered for leg {leg_dict.get('unique_leg_id', '')} at {position.stop_loss} with a comapraring value of {sl_comparing_value}"
        
        # else:
        #     # Weekday-specific stop loss
        #     # stoploss_value is already loaded based on weekday during leg parsing
        #     percentage_loss = (pnl / entry_price) * 100
        #     if percentage_loss <= (-stoploss_value * 100):
        #         weekday = current_timestamp.strftime('%A')
        #         return True, f"SL Triggered for leg {leg_dict.get('unique_leg_id', '')} at {position.stop_loss} with a comapraring value of {sl_comparing_value}"
        
        return False, ""


class TargetProfitExit(ExitStrategy):
    """Target profit exit strategy."""
    
    def check_exit_condition(
        self,
        position: Dict[str, Any],
        current_timestamp: datetime,
        spot_df: pl.DataFrame,
        **kwargs
    ) -> Tuple[bool, str]:
        """
        Check target profit condition.
        
        Args:
            position: Position details with 'entry_price', 'position_type', 'leg_dict'
            current_timestamp: Current timestamp
            current_ltp: Current LTP
            spot_df: Spot dataframe (not used)
            **kwargs: Additional parameters
            
        Returns:
            Tuple of (should_exit, exit_reason)
        """
        leg_dict = position.leg_dict
        
        if not leg_dict.get("target_toggle", False):
            return False, ""
        
        entry_price = position.entry_price
        position_type = position.position_type
        target_value = leg_dict.get("target_value", 0)  # Percentage (already divided by 100)
        
        if entry_price == 0 or target_value == 0:
            return False, ""
        
        ohlc = position.OHLCV_data

        # Determine current LTP based on compare type
        if position.target_compare_type == "":
            target_comparing_value = ohlc['High'] if position_type.upper() == "BUY" else ohlc['Low']
        else:
            target_comparing_value = ohlc[position.target_compare_type]
        
        # Calculate P&L percentage
        if position_type.upper() == "BUY":
            # Check if target is hit
            if target_comparing_value >= position.target_price:
                return True, f"Target Triggered Exit for leg {leg_dict.get('unique_leg_id', '')} at {position.target_price} with a comapraring value of {target_comparing_value}"
        
        else:  # SELL
            if target_comparing_value <= position.target_price:
                return True, f"Target Triggered Exit for leg {leg_dict.get('unique_leg_id', '')} at {position.target_price} with a comapraring value of {target_comparing_value}"
                

        return False, ""


class TrailingStopLossExit(ExitStrategy):
    """Trailing stop loss exit strategy."""
    
    def __init__(self):
        """Initialize trailing SL with tracking variables."""
        self.trail_activated_positions = {}  # {position_id: {'highest_profit': float, 'trail_sl': float}}
    
    def check_exit_condition(
        self,
        position: Dict[str, Any],
        current_timestamp: datetime,
        current_ltp: float,
        spot_df: pl.DataFrame,
        **kwargs
    ) -> Tuple[bool, str]:
        """
        Check trailing stop loss condition.
        
        Trailing SL works as follows:
        1. When profit reaches trail_value1, activate trailing
        2. Trail the stop loss by trail_value2 from the highest profit achieved
        
        Args:
            position: Position details
            current_timestamp: Current timestamp
            current_ltp: Current LTP
            spot_df: Spot dataframe (not used)
            **kwargs: Additional parameters
            
        Returns:
            Tuple of (should_exit, exit_reason)
        """
        leg_dict = position.get('leg_dict', {})
        
        if not leg_dict.get("trail_sl_toggle", False):
            return False, ""
        
        position_id = position.get('position_id', '')
        entry_price = position.get('entry_price', 0)
        position_type = position.get('position_type', 'BUY')
        
        trail_value1 = leg_dict.get("trail_value1", 0)  # Activation threshold (points)
        trail_value2 = leg_dict.get("trail_value2", 0)  # Trail amount (points)
        
        if entry_price == 0 or trail_value1 == 0 or trail_value2 == 0:
            return False, ""
        
        # Calculate current P&L
        if position_type.upper() == "BUY":
            current_pnl = current_ltp - entry_price
        else:  # SELL
            current_pnl = entry_price - current_ltp
        
        # Initialize position tracking if not exists
        if position_id not in self.trail_activated_positions:
            self.trail_activated_positions[position_id] = {
                'highest_profit': current_pnl,
                'trail_sl': None,
                'activated': False
            }
        
        position_trail_data = self.trail_activated_positions[position_id]
        
        # Update highest profit
        if current_pnl > position_trail_data['highest_profit']:
            position_trail_data['highest_profit'] = current_pnl
        
        # Check if trailing should be activated
        if not position_trail_data['activated'] and current_pnl >= trail_value1:
            position_trail_data['activated'] = True
            position_trail_data['trail_sl'] = current_pnl - trail_value2
        
        # If trailing is activated, update trailing SL
        if position_trail_data['activated']:
            new_trail_sl = position_trail_data['highest_profit'] - trail_value2
            if position_trail_data['trail_sl'] is None or new_trail_sl > position_trail_data['trail_sl']:
                position_trail_data['trail_sl'] = new_trail_sl
            
            # Check if trailing SL is hit
            if current_pnl <= position_trail_data['trail_sl']:
                return True, f"Trailing_SL_{trail_value2}"
        
        return False, ""
    
    def remove_position_tracking(self, position_id: str):
        """Remove position from trailing tracking when exited."""
        if position_id in self.trail_activated_positions:
            del self.trail_activated_positions[position_id]


class ConditionalExit(ExitStrategy):
    """Conditional exit based on spot movement or other conditions."""
    
    def check_exit_condition(
        self,
        position: Dict[str, Any],
        current_timestamp: datetime,
        current_ltp: float,
        spot_df: pl.DataFrame,
        **kwargs
    ) -> Tuple[bool, str]:
        """
        Check conditional exit.
        
        Can include conditions like:
        - Spot moving beyond certain level
        - Specific time-based conditions
        - Custom logic based on strategy
        
        Args:
            position: Position details
            current_timestamp: Current timestamp
            current_ltp: Current LTP
            spot_df: Spot dataframe
            **kwargs: Must contain 'entry_spot', 'condition_params'
            
        Returns:
            Tuple of (should_exit, exit_reason)
        """
        condition_params = kwargs.get('condition_params', {})
        if not condition_params:
            return False, ""
        
        # Example: Exit if spot moves beyond threshold
        spot_threshold = condition_params.get('spot_threshold')
        if spot_threshold:
            entry_spot = kwargs.get('entry_spot', 0)
            current_spot_row = spot_df.filter(pl.col("Timestamp") == current_timestamp)
            
            if not current_spot_row.is_empty():
                current_spot = current_spot_row["Close"][0]
                spot_movement = abs(current_spot - entry_spot)
                
                if spot_movement >= spot_threshold:
                    return True, f"Conditional_Spot_Movement_{spot_threshold}"
        
        return False, ""


class IndicatorExit(ExitStrategy):
    """Indicator-based exit strategy."""
    
    def check_exit_condition(
        self,
        position: Dict[str, Any],
        current_timestamp: datetime,
        current_ltp: float,
        spot_df: pl.DataFrame,
        **kwargs
    ) -> Tuple[bool, str]:
        """
        Check indicator-based exit.
        
        Supports exits based on:
        - VWAP crossover
        - Moving average crossover
        - RSI levels
        - Custom indicators
        
        Args:
            position: Position details
            current_timestamp: Current timestamp
            current_ltp: Current LTP
            spot_df: Spot dataframe
            **kwargs: Must contain 'indicator_params'
            
        Returns:
            Tuple of (should_exit, exit_reason)
        """
        indicator_params = kwargs.get('indicator_params', {})
        if not indicator_params:
            return False, ""
        
        indicator_type = indicator_params.get('type', '').upper()
        
        if indicator_type == 'VWAP':
            return self._check_vwap_exit(position, current_timestamp, spot_df)
        
        # Add more indicator types as needed
        
        return False, ""
    
    def _check_vwap_exit(
        self,
        position: Dict[str, Any],
        current_timestamp: datetime,
        spot_df: pl.DataFrame
    ) -> Tuple[bool, str]:
        """Check VWAP-based exit."""
        # Get data until current timestamp
        df_until_now = spot_df.filter(pl.col("Timestamp") <= current_timestamp)
        if df_until_now.is_empty():
            return False, ""
        
        # Calculate VWAP
        vwap = df_until_now["Close"].mean()
        
        # Get current spot
        current_spot_row = spot_df.filter(pl.col("Timestamp") == current_timestamp)
        if current_spot_row.is_empty():
            return False, ""
        
        current_spot = current_spot_row["Close"][0]
        
        # Check crossover based on position type
        option_type = position.get('leg_dict', {}).get('option_type', '').upper()
        
        if option_type == 'CE':
            # Exit CE if spot crosses below VWAP
            if current_spot < vwap:
                return True, "VWAP_Exit_CE"
        elif option_type == 'PE':
            # Exit PE if spot crosses above VWAP
            if current_spot > vwap:
                return True, "VWAP_Exit_PE"
        
        return False, ""


class TimeBasedExit(ExitStrategy):
    """Time-based exit strategy."""
    
    def check_exit_condition(
        self,
        position: Dict[str, Any],
        current_timestamp: datetime,
        current_ltp: float,
        spot_df: pl.DataFrame,
        **kwargs
    ) -> Tuple[bool, str]:
        """
        Check time-based exit.
        
        Args:
            position: Position details
            current_timestamp: Current timestamp
            current_ltp: Current LTP
            spot_df: Spot dataframe (not used)
            **kwargs: Must contain 'exit_time' (datetime.time object)
            
        Returns:
            Tuple of (should_exit, exit_reason)
        """
        exit_time = kwargs.get('exit_time')
        if exit_time is None:
            return False, ""
        
        if current_timestamp.time() >= exit_time:
            return True, f"Time_Exit_{exit_time.strftime('%H:%M')}"
        
        return False, ""


class ExitManager:
    """
    Main Exit Manager that coordinates all exit strategies.
    
    This class is composed by DayProcessor and handles all exit logic.
    
    Attributes:
        strategies: Dictionary of exit strategy instances
        priority_order: List defining exit check priority
    """
    
    def __init__(self):
        """Initialize ExitManager with all available strategies."""
        self.strategies: Dict[str, ExitStrategy] = {
            "STOPLOSS": StopLossExit(),
            "TARGET": TargetProfitExit(),
            "TRAILING": TrailingStopLossExit(),
            "CONDITIONAL": ConditionalExit(),
            "INDICATOR": IndicatorExit(),
            "TIME": TimeBasedExit()
        }
        
        # Priority order for exit checks (checked in this order)
        self.priority_order = [
            "STOPLOSS",      # Check SL first
            "TARGET",        # Then target
            "TRAILING",      # Then trailing SL
            "TIME",          # Then time-based exit
            "CONDITIONAL",   # Then conditional exits
            "INDICATOR"      # Finally indicator-based exits
        ]
    
    def check_exit(
        self,
        position: Dict[str, Any],
        current_timestamp: datetime,
        current_ltp: float,
        spot_df: pl.DataFrame,
        **kwargs
    ) -> Tuple[bool, str]:
        """
        Check all exit conditions for a position.
        
        Checks exit conditions in priority order and returns on first match.
        
        Args:
            position: Position dictionary containing all position details
            current_timestamp: Current timestamp being processed
            current_ltp: Current last traded price
            spot_df: Spot price dataframe
            **kwargs: Additional parameters (exit_time, condition_params, indicator_params, etc.)
            
        Returns:
            Tuple of (should_exit: bool, exit_reason: str)
        """
        # Check each exit strategy in priority order
        for strategy_name in self.priority_order:
            strategy = self.strategies[strategy_name]
            
            should_exit, exit_reason = strategy.check_exit_condition(
                position, current_timestamp, current_ltp, spot_df, **kwargs
            )
            
            if should_exit:
                return True, exit_reason
        
        return False, ""
    
    def check_specific_exit(
        self,
        exit_type: str,
        position: Dict[str, Any],
        current_timestamp: datetime,
        spot_df: pl.DataFrame,
        **kwargs
    ) -> Tuple[bool, str]:
        """
        Check a specific exit strategy only.
        
        Args:
            exit_type: Type of exit to check (STOPLOSS, TARGET, etc.)
            position: Position details
            current_timestamp: Current timestamp
            current_ltp: Current LTP
            spot_df: Spot dataframe
            **kwargs: Additional parameters
            
        Returns:
            Tuple of (should_exit, exit_reason)
        """
        exit_type_upper = exit_type.upper()
        
        if exit_type_upper not in self.strategies:
            return False, ""
        
        strategy = self.strategies[exit_type_upper]

        return strategy.check_exit_condition(
            position, current_timestamp, spot_df, **kwargs
        )
    
    def remove_position_from_trailing(self, position_id: str):
        """
        Remove position from trailing stop loss tracking.
        
        Should be called when position is exited.
        
        Args:
            position_id: ID of the position to remove
        """
        trailing_strategy = self.strategies.get("TRAILING")
        if trailing_strategy and hasattr(trailing_strategy, 'remove_position_tracking'):
            trailing_strategy.remove_position_tracking(position_id)
    
    def reset_all_strategies(self):
        """Reset all strategies that have state."""
        for strategy in self.strategies.values():
            if hasattr(strategy, 'reset'):
                strategy.reset()    