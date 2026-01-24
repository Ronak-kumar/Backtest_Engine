"""
Reentry Manager Module

This module provides functionality for managing re-entry strategies after exit.
Re-entries can occur after stop loss hits or target hits, with various conditions.

Classes:
    ReentryStrategy: Abstract base class for re-entry strategies
    SimpleReentry: Simple re-entry (immediate or after delay)
    MomentumReentry: Re-entry based on momentum reversal
    TimeDelayReentry: Re-entry after time delay
    ConditionalReentry: Conditional re-entry based on market conditions
    ReentryManager: Main manager class that coordinates all re-entry strategies
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, time, timedelta
import polars as pl


class ReentryStrategy(ABC):
    """Abstract base class for re-entry strategies."""
    
    @abstractmethod
    def check_reentry_condition(
        self,
        leg_dict: Dict[str, Any],
        exit_info: Dict[str, Any],
        current_timestamp: datetime,
        spot_df: pl.DataFrame,
        **kwargs
    ) -> bool:
        """
        Check if re-entry condition is met.
        
        Args:
            leg_dict: Leg configuration dictionary
            exit_info: Information about the exit that occurred
            current_timestamp: Current timestamp
            spot_df: Spot price dataframe
            **kwargs: Additional strategy-specific parameters
            
        Returns:
            True if re-entry condition is met, False otherwise
        """
        pass


class SimpleReentry(ReentryStrategy):
    """Simple re-entry strategy (immediate re-entry)."""
    
    def check_reentry_condition(
        self,
        leg_dict: Dict[str, Any],
        exit_info: Dict[str, Any],
        current_timestamp: datetime,
        spot_df: pl.DataFrame,
        **kwargs
    ) -> bool:
        """
        Check simple re-entry condition (immediate re-entry).
        
        Args:
            leg_dict: Leg configuration
            exit_info: Exit information
            current_timestamp: Current timestamp
            spot_df: Spot dataframe (not used)
            **kwargs: Additional parameters
            
        Returns:
            True if should re-enter immediately
        """
        exit_type = exit_info.get('exit_type', '')
        
        # Check if re-entry is enabled for this exit type
        if exit_type == 'SL':
            return leg_dict.get("rentry_sl_toggle", False)
        elif exit_type == 'TARGET':
            return leg_dict.get("rentry_tgt_toggle", False)
        
        return False


class MomentumReentry(ReentryStrategy):
    """Re-entry based on momentum reversal."""
    
    def check_reentry_condition(
        self,
        leg_dict: Dict[str, Any],
        exit_info: Dict[str, Any],
        current_timestamp: datetime,
        spot_df: pl.DataFrame,
        **kwargs
    ) -> bool:
        """
        Check momentum-based re-entry condition.
        
        Re-entry occurs when:
        1. Re-entry is enabled for the exit type
        2. Re-entry type is "RE MOMENTUM"
        3. Spot has moved in favorable direction by specified percentage
        
        Args:
            leg_dict: Leg configuration with momentum re-entry parameters
            exit_info: Exit information including exit price and spot
            current_timestamp: Current timestamp
            spot_df: Spot price dataframe
            **kwargs: Must contain entry-related parameters
            
        Returns:
            True if momentum re-entry condition is met
        """
        exit_type = exit_info.get('exit_type', '')
        
        # Check if re-entry is enabled and type is momentum
        if exit_type == 'SL':
            if not leg_dict.get("rentry_sl_toggle", False):
                return False
            if leg_dict.get("rentry_type_sl", "") != "RE MOMENTUM":
                return False
        elif exit_type == 'TARGET':
            if not leg_dict.get("rentry_tgt_toggle", False):
                return False
            if leg_dict.get("rentry_type_tgt", "") != "RE MOMENTUM":
                return False
        else:
            return False
        
        # Get momentum parameters
        sm_percentage_direction = leg_dict.get("sm_percentage_direction", "").upper()
        sm_percent_value = leg_dict.get("sm_percent_value", 0)
        exit_spot = exit_info.get('exit_spot', 0)
        
        if exit_spot == 0 or sm_percent_value == 0:
            return False
        
        # Get current spot
        current_spot_row = spot_df.filter(pl.col("Timestamp") == current_timestamp)
        if current_spot_row.is_empty():
            return False
        
        current_spot = current_spot_row["Close"][0]
        
        # Calculate percentage movement from exit
        percent_movement = ((current_spot - exit_spot) / exit_spot) * 100
        
        # Check if movement meets re-entry criteria
        if sm_percentage_direction == "ABOVE":
            return percent_movement >= sm_percent_value
        elif sm_percentage_direction == "BELOW":
            return percent_movement <= -sm_percent_value
        
        return False


class TimeDelayReentry(ReentryStrategy):
    """Re-entry after a time delay."""
    
    def __init__(self):
        """Initialize with tracking of exit times."""
        self.exit_times: Dict[str, datetime] = {}  # {leg_id: exit_timestamp}
    
    def check_reentry_condition(
        self,
        leg_dict: Dict[str, Any],
        exit_info: Dict[str, Any],
        current_timestamp: datetime,
        spot_df: pl.DataFrame,
        **kwargs
    ) -> bool:
        """
        Check time-delayed re-entry condition.
        
        Args:
            leg_dict: Leg configuration
            exit_info: Exit information
            current_timestamp: Current timestamp
            spot_df: Spot dataframe (not used)
            **kwargs: Must contain 'reentry_time_threshold' (time object)
            
        Returns:
            True if time delay has passed
        """
        leg_id = leg_dict.get("leg_id", "")
        exit_type = exit_info.get('exit_type', '')
        exit_timestamp = exit_info.get('exit_timestamp')
        
        # Check if re-entry is enabled
        if exit_type == 'SL' and not leg_dict.get("rentry_sl_toggle", False):
            return False
        if exit_type == 'TARGET' and not leg_dict.get("rentry_tgt_toggle", False):
            return False
        
        # Get re-entry time threshold
        reentry_time_threshold = kwargs.get('reentry_time_threshold')
        if reentry_time_threshold is None:
            return False
        
        # Store exit time if not already stored
        if leg_id not in self.exit_times:
            self.exit_times[leg_id] = exit_timestamp
        
        # Check if current time is past the threshold
        return current_timestamp.time() >= reentry_time_threshold
    
    def clear_exit_time(self, leg_id: str):
        """Clear stored exit time for a leg."""
        if leg_id in self.exit_times:
            del self.exit_times[leg_id]


class ConditionalReentry(ReentryStrategy):
    """Conditional re-entry based on market conditions."""
    
    def check_reentry_condition(
        self,
        leg_dict: Dict[str, Any],
        exit_info: Dict[str, Any],
        current_timestamp: datetime,
        spot_df: pl.DataFrame,
        **kwargs
    ) -> bool:
        """
        Check conditional re-entry.
        
        Can include conditions like:
        - Spot returning to certain level
        - Premium conditions
        - Specific market conditions
        
        Args:
            leg_dict: Leg configuration
            exit_info: Exit information
            current_timestamp: Current timestamp
            spot_df: Spot dataframe
            **kwargs: Additional condition parameters
            
        Returns:
            True if conditional re-entry is met
        """
        exit_type = exit_info.get('exit_type', '')
        
        # Check if re-entry is enabled
        if exit_type == 'SL' and not leg_dict.get("rentry_sl_toggle", False):
            return False
        if exit_type == 'TARGET' and not leg_dict.get("rentry_tgt_toggle", False):
            return False
        
        # Example: Re-enter if spot returns within certain range
        condition_params = kwargs.get('reentry_condition_params', {})
        
        if condition_params.get('type') == 'SPOT_RETURN':
            entry_spot = exit_info.get('entry_spot', 0)
            spot_threshold = condition_params.get('spot_threshold', 0)
            
            if entry_spot == 0:
                return False
            
            current_spot_row = spot_df.filter(pl.col("Timestamp") == current_timestamp)
            if current_spot_row.is_empty():
                return False
            
            current_spot = current_spot_row["Close"][0]
            
            # Re-enter if spot is within threshold of entry spot
            if abs(current_spot - entry_spot) <= spot_threshold:
                return True
        
        return False


class ReentryTracker:
    """
    Tracks re-entry counts for each leg to enforce limits.
    
    Attributes:
        reentry_counts: Dictionary tracking re-entry counts {leg_id: {'sl': count, 'tgt': count}}
    """
    
    def __init__(self):
        """Initialize re-entry tracker."""
        self.reentry_counts: Dict[str, Dict[str, int]] = {}
    
    def can_reenter(
        self,
        leg_id: str,
        exit_type: str,
        leg_dict: Dict[str, Any]
    ) -> bool:
        """
        Check if re-entry is allowed based on count limits.
        
        Args:
            leg_id: Leg identifier
            exit_type: Exit type ('SL' or 'TARGET')
            leg_dict: Leg configuration with re-entry limits
            
        Returns:
            True if re-entry is allowed, False if limit reached
        """
        # Initialize if not exists
        if leg_id not in self.reentry_counts:
            self.reentry_counts[leg_id] = {'sl': 0, 'tgt': 0}
        
        # Get current count and limit
        if exit_type == 'SL':
            current_count = self.reentry_counts[leg_id]['sl']
            limit = leg_dict.get("total_sl_rentry", float('inf'))
        elif exit_type == 'TARGET':
            current_count = self.reentry_counts[leg_id]['tgt']
            limit = leg_dict.get("total_tgt_rentry", float('inf'))
        else:
            return False
        
        return current_count < limit
    
    def increment_reentry(self, leg_id: str, exit_type: str):
        """
        Increment re-entry count for a leg.
        
        Args:
            leg_id: Leg identifier
            exit_type: Exit type ('SL' or 'TARGET')
        """
        if leg_id not in self.reentry_counts:
            self.reentry_counts[leg_id] = {'sl': 0, 'tgt': 0}
        
        if exit_type == 'SL':
            self.reentry_counts[leg_id]['sl'] += 1
        elif exit_type == 'TARGET':
            self.reentry_counts[leg_id]['tgt'] += 1
    
    def get_reentry_count(self, leg_id: str, exit_type: str) -> int:
        """
        Get current re-entry count.
        
        Args:
            leg_id: Leg identifier
            exit_type: Exit type
            
        Returns:
            Current re-entry count
        """
        if leg_id not in self.reentry_counts:
            return 0
        
        if exit_type == 'SL':
            return self.reentry_counts[leg_id]['sl']
        elif exit_type == 'TARGET':
            return self.reentry_counts[leg_id]['tgt']
        
        return 0
    
    def reset(self):
        """Reset all re-entry counts."""
        self.reentry_counts.clear()


class ReentryManager:
    """
    Main Reentry Manager that coordinates all re-entry strategies.
    
    This class is composed by DayProcessor and handles all re-entry logic.
    
    Attributes:
        strategies: Dictionary of re-entry strategy instances
        tracker: Re-entry tracker for enforcing limits
        pending_reentries: Queue of pending re-entries
    """
    
    def __init__(self):
        """Initialize ReentryManager with all available strategies."""
        self.strategies: Dict[str, ReentryStrategy] = {
            "SIMPLE": SimpleReentry(),
            "MOMENTUM": MomentumReentry(),
            "TIME_DELAY": TimeDelayReentry(),
            "CONDITIONAL": ConditionalReentry()
        }
        self.tracker = ReentryTracker()
        self.pending_reentries: list = []  # List of pending re-entry requests
    
    def register_exit(
        self,
        leg_dict: Dict[str, Any],
        exit_info: Dict[str, Any]
    ):
        """
        Register an exit and check if re-entry should be scheduled.
        
        Args:
            leg_dict: Leg configuration
            exit_info: Exit information (exit_type, exit_timestamp, exit_price, etc.)
        """
        exit_type = exit_info.get('exit_type', '')
        leg_id = leg_dict.get("leg_id", "")
        
        # Check if re-entry is enabled for this exit type
        if exit_type == 'SL':
            reentry_enabled = leg_dict.get("rentry_sl_toggle", False)
            reentry_type = leg_dict.get("rentry_type_sl", "")
        elif exit_type == 'TARGET':
            reentry_enabled = leg_dict.get("rentry_tgt_toggle", False)
            reentry_type = leg_dict.get("rentry_type_tgt", "")
        else:
            return
        
        if not reentry_enabled:
            return
        
        # Check if re-entry limit is reached
        if not self.tracker.can_reenter(leg_id, exit_type, leg_dict):
            return
        
        # Add to pending re-entries
        pending_reentry = {
            'leg_dict': leg_dict,
            'exit_info': exit_info,
            'reentry_type': reentry_type,
            'registered_at': exit_info.get('exit_timestamp')
        }
        self.pending_reentries.append(pending_reentry)
    
    def check_reentries(
        self,
        current_timestamp: datetime,
        spot_df: pl.DataFrame,
        **kwargs
    ) -> list:
        """
        Check all pending re-entries and return those that should execute.
        
        Args:
            current_timestamp: Current timestamp
            spot_df: Spot price dataframe
            **kwargs: Additional parameters for strategies
            
        Returns:
            List of leg_dicts that should re-enter
        """
        reentries_to_execute = []
        remaining_pending = []
        
        for pending in self.pending_reentries:
            leg_dict = pending['leg_dict']
            exit_info = pending['exit_info']
            reentry_type = pending['reentry_type']
            
            # Map reentry type to strategy
            strategy_key = self._map_reentry_type(reentry_type)
            
            if strategy_key not in self.strategies:
                # Invalid strategy, skip this re-entry
                continue
            
            strategy = self.strategies[strategy_key]
            
            # Check if re-entry condition is met
            should_reenter = strategy.check_reentry_condition(
                leg_dict, exit_info, current_timestamp, spot_df, **kwargs
            )
            
            if should_reenter:
                # Increment re-entry count
                exit_type = exit_info.get('exit_type', '')
                leg_id = leg_dict.get("leg_id", "")
                self.tracker.increment_reentry(leg_id, exit_type)
                
                reentries_to_execute.append(leg_dict)
            else:
                # Keep in pending
                remaining_pending.append(pending)
        
        # Update pending list
        self.pending_reentries = remaining_pending
        
        return reentries_to_execute
    
    def _map_reentry_type(self, reentry_type: str) -> str:
        """
        Map re-entry type string to strategy key.
        
        Args:
            reentry_type: Re-entry type from leg configuration
            
        Returns:
            Strategy key
        """
        reentry_type_upper = reentry_type.upper()
        
        mapping = {
            "SIMPLE": "SIMPLE",
            "IMMEDIATE": "SIMPLE",
            "RE MOMENTUM": "MOMENTUM",
            "MOMENTUM": "MOMENTUM",
            "TIME_DELAY": "TIME_DELAY",
            "DELAY": "TIME_DELAY",
            "CONDITIONAL": "CONDITIONAL"
        }
        
        return mapping.get(reentry_type_upper, "SIMPLE")
    
    def clear_pending_reentries_for_leg(self, leg_id: str):
        """
        Clear all pending re-entries for a specific leg.
        
        Args:
            leg_id: Leg identifier
        """
        self.pending_reentries = [
            pending for pending in self.pending_reentries
            if pending['leg_dict'].get('leg_id', '') != leg_id
        ]
    
    def get_reentry_counts(self, leg_id: str) -> Dict[str, int]:
        """
        Get re-entry counts for a leg.
        
        Args:
            leg_id: Leg identifier
            
        Returns:
            Dictionary with 'sl' and 'tgt' counts
        """
        if leg_id not in self.tracker.reentry_counts:
            return {'sl': 0, 'tgt': 0}
        return self.tracker.reentry_counts[leg_id].copy()
    
    def reset(self):
        """Reset reentry manager (for new day)."""
        self.pending_reentries.clear()
        self.tracker.reset()
        
        # Reset strategies with state
        for strategy in self.strategies.values():
            if hasattr(strategy, 'reset'):
                strategy.reset()