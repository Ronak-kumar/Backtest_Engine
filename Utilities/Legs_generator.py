"""
Legs Generator Module

This module provides functionality to parse and load trading leg configurations
from CSV files for options trading strategies.

Classes:
    LegsHandler: Handles parsing of main legs and lazy (sub) legs from CSV files
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import ast
from datetime import datetime


class LegsHandler:
    """
    Handler for loading and parsing trading leg configurations from CSV files.
    
    This class manages the parsing of main legs and lazy (sub) legs from CSV files,
    converting them into structured dictionaries for use in trading strategies.
    
    Attributes:
        orders: Dictionary of main leg configurations
        lazy_leg_dict: Dictionary of lazy (sub) leg configurations
        option_types: List of option types found in legs
        expiry_types: List of expiry types found in legs
        synthetic_checking: Boolean flag indicating if synthetic legs are present
    """
    
    def __init__(self):
        """Initialize LegsHandler with empty containers."""
        self.orders: Dict[str, Dict[str, Any]] = {}
        self.lazy_leg_dict: Dict[str, Dict[str, Any]] = {}
        self.option_types: List[str] = []
        self.expiry_types: List[str] = []
        self.synthetic_checking: bool = False
        self._is_loaded: bool = False
        self._has_weekday_stoploss: bool = False  # Track if any leg has weekday-specific stoploss
        self._last_loaded_date: Optional[datetime] = None  # Track last date used for loading
        self.total_multiple = None
        self.total_orders = None

    
    def _check_weekday_stoploss_required(self) -> bool:
        """
        Check if any loaded leg requires weekday-specific stoploss calculations.
        
        Returns:
            True if any leg has stoploss_type that is not "Points" or "Percentage"
        """
        # Check main legs
        for leg_dict in self.orders.values():
            if leg_dict.get("stoploss_toggle"):
                stoploss_type = leg_dict.get("stoploss_type", "")
                if stoploss_type not in ["Points", "Percentage"]:
                    return True
        
        # Check lazy legs
        for leg_dict in self.lazy_leg_dict.values():
            if leg_dict.get("stoploss_toggle"):
                stoploss_type = leg_dict.get("stoploss_type", "")
                if stoploss_type not in ["Points", "Percentage"]:
                    return True
        
        return False
    
    def legs_generator(self, param_csv_file_dir: str, current_date: Optional[datetime] = None, force_reload: bool = False) -> Tuple[Dict, Dict, List[str], List[str], bool]:
        """
        Generate legs from CSV files in the specified directory.
        
        This method intelligently loads legs based on whether weekday-specific 
        stoploss calculations are needed:
        - If legs have weekday-specific stoploss (not "Points" or "Percentage"), 
          it will reload when the date changes
        - If legs only have "Points" or "Percentage" stoploss, it caches the 
          results and reuses them for all dates (much more efficient)
        
        Args:
            param_csv_file_dir: Base directory containing leg_data and sub_leg_data folders
            current_date: Optional datetime object for date-specific calculations (e.g., weekday stoploss)
            force_reload: If True, force reload even if already loaded (overrides smart reload logic)
            
        Returns:
            Tuple containing:
                - orders: Dictionary of main leg configurations
                - lazy_leg_dict: Dictionary of lazy leg configurations
                - option_types: List of option types
                - expiry_types: List of expiry types
                - synthetic_checking: Boolean indicating synthetic legs presence
        """
        # Determine if reload is needed
        needs_reload = False
        
        if force_reload:
            # Force reload explicitly requested
            needs_reload = True
        elif not self._is_loaded:
            # First time loading - always load
            needs_reload = True
        elif self._has_weekday_stoploss:
            # Weekday stoploss detected - check if date changed
            if current_date is not None and current_date != self._last_loaded_date:
                # Date changed, need to reload for weekday-specific calculations
                needs_reload = True
            # If date hasn't changed, no need to reload
        
        # If already loaded and no reload needed, return cached data
        if self._is_loaded and not needs_reload:
            return self.orders, self.lazy_leg_dict, self.option_types, self.expiry_types, self.synthetic_checking
        
        # Reload legs
        param_dir = Path(param_csv_file_dir)
        main_legs_dir = param_dir / "leg_data"
        lazy_legs_dir = param_dir / "sub_leg_data"
        
        # Clear previous data before reload
        if needs_reload:
            self.reset()
        
        self._main_legs_generator(main_legs_dir, current_date)
        self._lazy_legs_generator(lazy_legs_dir, current_date)
        
        # After loading, check if any leg has weekday-specific stoploss
        self._has_weekday_stoploss = self._check_weekday_stoploss_required()
        self._last_loaded_date = current_date
        self._is_loaded = True

        ##### Elements Generation for Margin Calculation #######
        self.total_multiple = max(self.option_types.count("CE"), self.option_types.count("PE"))
        self.total_orders = len(self.orders) 

        
        return self.orders, self.lazy_leg_dict, self.option_types, self.expiry_types, self.synthetic_checking
    
    def reset(self) -> None:
        """Reset the handler to allow reloading of legs."""
        self.orders.clear()
        self.lazy_leg_dict.clear()
        self.option_types.clear()
        self.expiry_types.clear()
        self.synthetic_checking = False
        self._is_loaded = False
        self._has_weekday_stoploss = False
        self._last_loaded_date = None
        self.total_multiple = None
        self.total_orders = None
    
    def _parse_leg_file(self, leg_file_path: Path, leg_id: str, current_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Parse a single leg CSV file into a dictionary.
        
        Args:
            leg_file_path: Path to the leg CSV file
            leg_id: Identifier for this leg
            current_date: Optional datetime for date-specific calculations
            
        Returns:
            Dictionary containing parsed leg configuration
            
        Raises:
            FileNotFoundError: If leg file doesn't exist
            KeyError: If required fields are missing from CSV
            ValueError: If data types cannot be converted
        """
        if not leg_file_path.exists():
            raise FileNotFoundError(f"Leg file not found: {leg_file_path}")
        
        try:
            leg_data = pd.read_csv(leg_file_path, header=None, index_col=0)
        except Exception as e:
            raise ValueError(f"Error reading leg file {leg_file_path}: {e}")
        
        leg_dict: Dict[str, Any] = {"leg_id": leg_id}
        
        # Helper function to safely get and convert values
        def get_value(key: str, default: Any = None, converter: Optional[callable] = None):
            try:
                if key in leg_data.index:
                    value = leg_data.loc[key].item()
                    if pd.notna(value):
                        return converter(value) if converter else value
                return default
            except (KeyError, ValueError, AttributeError) as e:
                if default is not None:
                    return default
                raise KeyError(f"Required field '{key}' missing or invalid in {leg_file_path}: {e}")
        
        # Parse strike type and related fields
        leg_dict["strike_type"] = get_value("strike_type", converter=str.upper)
        strike_type = leg_dict["strike_type"]
        
        if strike_type in ["ITM", "OTM"]:
            leg_dict["spread"] = get_value("Spread", converter=int)
        elif strike_type == "ATM STRADDLE PREMIUM PERCENTAGE":
            leg_dict["atm_straddle_premium"] = get_value("atm_straddle_premium", converter=int)
        elif strike_type == "PREMIUM":
            leg_dict["premium_consideration"] = get_value("premium_consideration", converter=str.upper)
            leg_dict["premium_value"] = get_value("premium_value", converter=float)
        
        # Parse basic leg properties
        leg_dict["option_type"] = get_value("option_type", converter=str.upper)
        leg_dict["entry_on"] = get_value("entry_on")
        leg_dict["hedges"] = get_value("hedges", default=False, converter=lambda x: str(x).upper() == "TRUE")
        leg_dict["position"] = get_value("position")
        
        # Parse target profit settings
        leg_dict["target_toggle"] = get_value("target_profit_toggle", default=False, converter=lambda x: str(x).upper() == "TRUE")
        if leg_dict["target_toggle"]:
            leg_dict["target_value"] = get_value("target_profit_value", converter=lambda x: float(x) / 100)
        
        # Parse stop loss settings
        leg_dict["stoploss_toggle"] = get_value("stop_loss_toggle", default=False, converter=lambda x: str(x).upper() == "TRUE")
        if leg_dict["stoploss_toggle"]:
            leg_dict["stoploss_type"] = get_value("stop_loss_type")
            stoploss_type = leg_dict["stoploss_type"]
            
            if stoploss_type == "Points":
                leg_dict["stoploss_value"] = get_value("stop_loss_value", converter=float)
            elif stoploss_type == "Percentage":
                leg_dict["stoploss_value"] = get_value("stop_loss_value", converter=lambda x: float(x) / 100)
            else:
                # Day-specific stoploss (e.g., "Monday_stoploss")
                if current_date is not None:
                    weekday_key = f"{current_date.strftime('%A')}_stoploss"
                    leg_dict["stoploss_value"] = get_value(weekday_key, converter=lambda x: float(x) / 100)
                else:
                    leg_dict["stoploss_value"] = get_value("stop_loss_value", converter=lambda x: float(x) / 100)
        
        # Parse re-entry settings
        leg_dict["rentry_tgt_toggle"] = get_value("re_entry_on_tgt_toggle", default=False, converter=lambda x: str(x).upper() == "TRUE")
        leg_dict["rentry_type_tgt"] = get_value("re_entry_on_tgt_type", default="")
        leg_dict["rentry_sl_toggle"] = get_value("re_entry_on_sl_toggle", default=False, converter=lambda x: str(x).upper() == "TRUE")
        leg_dict["rentry_type_sl"] = get_value("re_entry_on_sl_type", default="")
        
        if leg_dict["rentry_sl_toggle"]:
            leg_dict["total_sl_rentry"] = get_value("total_sl_rentry", converter=float)
        if leg_dict["rentry_tgt_toggle"]:
            leg_dict["total_tgt_rentry"] = get_value("total_tgt_rentry", converter=float)
        
        # Parse trailing stop loss settings
        leg_dict["trail_sl_toggle"] = get_value("trail_sl_toggle", default=False, converter=lambda x: str(x).upper() == "TRUE")
        if leg_dict["trail_sl_toggle"]:
            leg_dict["trailing_type"] = get_value("trail_sl_type")
            leg_dict["trail_value1"] = get_value("trail_sl_value1", converter=int)
            leg_dict["trail_value2"] = get_value("trail_sl_value2", converter=int)
        
        # Parse VIX checker settings
        leg_dict["vix_checker_toggle"] = get_value("vix_checker_toggle", default=False, converter=lambda x: str(x).upper() == "TRUE")
        leg_dict["vix_operator"] = get_value("vix_operator", default="")
        leg_dict["vix_value"] = get_value("vix_value", converter=float)
        
        # Parse expiry selection
        leg_dict["leg_expiry_selection"] = get_value("leg_expiry_selection")
        expiry_selection = leg_dict["leg_expiry_selection"]
        if expiry_selection and expiry_selection not in self.expiry_types:
            self.expiry_types.append(expiry_selection)
        
        # Parse synthetic momentum settings
        leg_dict["sm_toggle"] = get_value("sm_toggle", default=False, converter=lambda x: str(x).upper() == "TRUE")
        rentry_tgt_type = get_value("re_entry_on_tgt_type", default="")
        rentry_sl_type = get_value("re_entry_on_sl_type", default="")
        
        if leg_dict["sm_toggle"] or rentry_tgt_type == "RE MOMENTUM" or rentry_sl_type == "RE MOMENTUM":
            leg_dict["sm_percentage_direction"] = get_value("sm_percentage_direction", default="")
            leg_dict["sm_tgt_sl_price"] = get_value("sm_tgt_sl_price", default="")
            leg_dict["sm_percent_value"] = get_value("sm_percent_value", converter=float)
        
        # Check for synthetic entry
        entry_on = leg_dict["entry_on"]
        if entry_on == "Synthetic":
            self.synthetic_checking = True
        
        # Parse range breakout settings
        leg_dict["range_breakout_toggle"] = get_value("range_breakout_toggle", default=False, converter=lambda x: str(x).upper() == "TRUE")
        if leg_dict["range_breakout_toggle"]:
            leg_dict["range_breakout_start"] = get_value("range_breakout_start")
            leg_dict["range_breakout_threshold_time"] = get_value("range_breakout_threshold_time")
            leg_dict["range_breakout_of"] = get_value("range_breakout_of")
            leg_dict["underlying_asset"] = get_value("underlying_asset")
            leg_dict["range_compare_section"] = get_value("range_compare_section")
        
        # Parse rolling straddle settings
        leg_dict["rolling_straddle_toggle"] = get_value("rolling_straddle_toggle", default=False, converter=lambda x: str(x).upper() == "TRUE")
        if leg_dict["rolling_straddle_toggle"]:
            leg_dict["rolling_straddle_breach_on"] = get_value("rolling_straddle_breach_on")
            leg_dict["rolling_straddle_consecutive_candles"] = get_value("rolling_straddle_consecutive_candles", converter=int)
            leg_dict["rolling_straddle_vwap_toggle"] = get_value("rolling_straddle_vwap_toggle", default=False, converter=lambda x: str(x).upper() == "TRUE")
            if leg_dict["rolling_straddle_vwap_toggle"]:
                leg_dict["rolling_straddle_vwap_breach_on"] = get_value("rolling_straddle_vwap_breach_on")
                leg_dict["rolling_straddle_vwap_consecutive_candles"] = get_value("rolling_straddle_vwap_consecutive_candles", converter=int)
        
        # Parse optional fields
        leg_dict["start_over_from"] = get_value("start_over_from", default=None)
        leg_dict["leg_tobe_executed_on_target"] = get_value("leg_tobe_executed_on_target", default=None)
        leg_dict["leg_tobe_executed_on_sl"] = get_value("leg_tobe_executed_on_sl", default=None)
        leg_dict["next_lazy_leg_to_be_executed"] = get_value("next_lazy_leg_to_be_executed", default=None)
        
        # Parse leg hopping counts
        leg_dict["leg_hopping_count_sl"] = get_value("leg_hopping_count_sl", default=0, converter=int)
        leg_dict["leg_hopping_count_tgt"] = get_value("leg_hopping_count_tgt", default=0, converter=int)
        leg_dict["leg_hopping_count_next_leg"] = get_value("leg_hopping_count_next_leg", default=0, converter=int)

        # Unique leg identifier
        leg_dict["unique_leg_id"] = leg_file_path.stem
        
        # Parse SM leg data (stored as string representation of list)
        sm_leg_data_str = get_value("sm_leg_data", default="[]")
        try:
            leg_dict["sm_leg_data"] = ast.literal_eval(sm_leg_data_str) if isinstance(sm_leg_data_str, str) else sm_leg_data_str
        except (ValueError, SyntaxError) as e:
            print(f"Warning: Could not parse sm_leg_data for leg {leg_id}: {e}. Using empty list.")
            leg_dict["sm_leg_data"] = []
        
        return leg_dict
    
    def _extract_leg_id_from_path(self, file_path: Path) -> str:
        """
        Extract leg ID from file path.
        
        Args:
            file_path: Path to leg file
            
        Returns:
            Extracted leg ID string
        """
        # Extract leg number from filename (e.g., "leg_1.csv" -> "1")
        stem = file_path.stem  # Get filename without extension
        parts = stem.split('_')
        if len(parts) > 1:
            leg_id = parts[-1].split()[0]  # Take last part after underscore, split by space and take first
        else:
            leg_id = stem.split()[0]  # Fallback: just take first part if no underscore
        return leg_id
    
    def _main_legs_generator(self, main_legs_dir: Path, current_date: Optional[datetime] = None) -> None:
        """
        Generate main legs from CSV files in the specified directory.
        
        Args:
            main_legs_dir: Directory containing main leg CSV files
            current_date: Optional datetime for date-specific calculations
        """
        if not main_legs_dir.exists():
            print(f"Warning: Main legs directory does not exist: {main_legs_dir}")
            return
        
        # Find all CSV files in the directory
        leg_files = sorted(main_legs_dir.glob("*.csv"))
        
        if not leg_files:
            print(f"Warning: No CSV files found in main legs directory: {main_legs_dir}")
            return
        
        for leg_file in leg_files:
            try:
                leg_id = self._extract_leg_id_from_path(leg_file)
                leg_dict = self._parse_leg_file(leg_file, leg_id, current_date)
                
                # Store in orders dictionary with key "leg_{leg_id}"
                self.orders[f"leg_{leg_id}"] = leg_dict
                
                # Track option types
                option_type = leg_dict.get("option_type")
                self.option_types.append(option_type)
                    
            except Exception as e:
                print(f"Error processing main leg file {leg_file}: {e}")
                continue
    
    def _lazy_legs_generator(self, lazy_legs_dir: Path, current_date: Optional[datetime] = None) -> None:
        """
        Generate lazy (sub) legs from CSV files in the specified directory.
        
        Args:
            lazy_legs_dir: Directory containing lazy leg CSV files
            current_date: Optional datetime for date-specific calculations
        """
        if not lazy_legs_dir.exists():
            print(f"Warning: Lazy legs directory does not exist: {lazy_legs_dir}")
            return
        
        # Find all CSV files in the directory
        lazy_leg_files = sorted(lazy_legs_dir.glob("*.csv"))
        
        if not lazy_leg_files:
            print(f"Warning: No CSV files found in lazy legs directory: {lazy_legs_dir}")
            return
        
        for lazy_leg_file in lazy_leg_files:
            try:
                # Extract leg number from path (e.g., "path/to/leg_1.5.csv" -> "leg_1.5")
                leg_number = lazy_leg_file.stem  # Filename without extension
                
                # Extract leg ID (e.g., "leg_1.5" -> "1.5")
                leg_id = self._extract_leg_id_from_path(lazy_leg_file)
                
                sub_leg_dict = self._parse_leg_file(lazy_leg_file, leg_id, current_date)
                
                # Store using the full leg number as key (e.g., "leg_1.5")
                self.lazy_leg_dict[leg_number] = sub_leg_dict
                
                # Track option types
                option_type = sub_leg_dict.get("option_type")
                if option_type and option_type not in self.option_types:
                    self.option_types.append(option_type)
                    
            except Exception as e:
                print(f"Error processing lazy leg file {lazy_leg_file}: {e}")
                continue
    
    def get_orders(self) -> Dict[str, Dict[str, Any]]:
        """Get the main orders dictionary."""
        return self.orders.copy()
    
    def get_lazy_legs(self) -> Dict[str, Dict[str, Any]]:
        """Get the lazy legs dictionary."""
        return self.lazy_leg_dict.copy()
    
    def get_option_types(self) -> List[str]:
        """Get the list of option types."""
        return self.option_types.copy()
    
    def get_expiry_types(self) -> List[str]:
        """Get the list of expiry types."""
        return self.expiry_types.copy()
    
    def has_synthetic_legs(self) -> bool:
        """Check if any synthetic legs are present."""
        return self.synthetic_checking
