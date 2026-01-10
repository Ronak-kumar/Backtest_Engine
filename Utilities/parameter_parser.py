import ast
from datetime import datetime as dt
import os
from pathlib import Path

import pandas as pd

def load_parameters_from_csv(csv_path):
    """
    Load parameters from CSV file and return as dictionary
    
    Args:
        csv_path: Path to CSV file containing parameters
        
    Returns:
        dict: Dictionary of parameters
    """
    # Read CSV file
    if isinstance(csv_path, str):
        csv_path = Path(csv_path)
    
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    # Read CSV - assumes format with index column and values
    # Adjust read_csv parameters based on your CSV structure
    try:
        # Try reading with index column (common format)
        df = pd.read_csv(csv_path, index_col=0, header=None)
    except:
        # Fallback: read without index
        df = pd.read_csv(csv_path)
    
    # Convert to dictionary
    # If CSV has structure: parameter_name | value
    if len(df.columns) == 1:
        param_dict = df.iloc[:, 0].to_dict()
    else:
        # If CSV has multiple columns, specify which one has values
        param_dict = df.to_dict('index')
    
    return param_dict

def _load_engine_main_entry_parameters(entry_para_dict):
    """
    Parse all entry parameters from dict
    Returns processed values matching the original logic
    """
    def get(key, default=None, typ=str):
        val = entry_para_dict.get(key, default)
        if val is None or (isinstance(val, str) and val.strip() == ""):
            return default
        try:
            return typ(val)
        except Exception:
            return default

    result = {}

    # ========== Dates ==========
    try:
        result['start_date'] = dt.strptime(entry_para_dict["start_date"], "%b-%y").strftime("%m/%Y")
        result['end_date'] = dt.strptime(entry_para_dict["end_date"], "%b-%y").strftime("%m/%Y")
    except:
        from dateutil import parser
        result['start_date'] = parser.parse(entry_para_dict["start_date"]).strftime("%d/%m/%Y")
        result['end_date'] = parser.parse(entry_para_dict["end_date"]).strftime("%d/%m/%Y")

    # ========== Entry/Exit Time ==========
    result['strategy_entry_time'] = entry_para_dict.get("strategy_entry_time")
    result['strategy_exit_time'] = entry_para_dict.get("strategy_exit_time")

    # ========== Index and Position ==========
    result['indices'] = entry_para_dict.get("indices")
    result['lots'] = int(entry_para_dict.get("lots", 1))
    result['strategy_name'] = entry_para_dict.get("strategy_name")

    # ========== Metrics ==========
    result['metric_generator_function'] = str(entry_para_dict.get("metric_generator_function", "")).upper() == "TRUE"

    # ========== Candle Type / Pricing ==========
    result['EntryMode'] = entry_para_dict.get("EntryMode")
    result['StoplossCalMode'] = entry_para_dict.get("StoplossCalMode")
    result['stoploss_compare_type'] = entry_para_dict.get("stoploss_compare_type")
    result['vix_candle_mode'] = entry_para_dict.get("vix_candle_mode")
    result['stoploss_hit'] = entry_para_dict.get("stoplosss_hit")
    result['spot_selection_mode'] = entry_para_dict.get("spot_selection_mode")

    # ========== Expiry and Before Trade ==========
    select_Day = str(entry_para_dict.get("select_expiry_toggle", "")).upper() == "TRUE"
    select_days_name_toggle = str(entry_para_dict.get("selected_days_toggle", "")).upper() == "TRUE"
    result['select_Day'] = select_Day
    result['select_days_name_toggle'] = select_days_name_toggle

    if select_Day:
        try:
            expiry_taketrade = ast.literal_eval(entry_para_dict["expiry_taketrade"])
        except:
            expiry_taketrade = []
        
        expiry_taketrade_list = []
        mapping = {
            "Expiry": 0,
            "1 Day Before Expiry": -1,
            "2 Days Before Expiry": -2,
            "3 Days Before Expiry": -3,
            "4 Days Before Expiry": -4,
        }
        for label, value in mapping.items():
            if label in expiry_taketrade:
                expiry_taketrade_list.append(value)
        result['expiry_taketrade_list'] = expiry_taketrade_list

    if select_days_name_toggle:
        try:
            result['selected_days_list'] = ast.literal_eval(entry_para_dict["selected_days"])
        except:
            result['selected_days_list'] = []

    # ========== Margin Type ==========
    result['fully_utilized_margin'] = int(entry_para_dict.get("fully_utilized_margin", 0))
    result['margin_type'] = entry_para_dict.get("margin_type")

    # ========== MTM Target ==========
    result['mtm_target_toggle'] = str(entry_para_dict.get("main_mtm_target_toggle", "")).upper() == "TRUE"
    result['mtm_target_type'] = entry_para_dict.get("main_mtm_target_type")
    result['main_mtm_trg'] = float(entry_para_dict.get("main_mtm_trg", 0.0) or 0.0)

    # ========== MTM Stoploss ==========
    result['mtm_stoploss_toggle'] = str(entry_para_dict.get("main_mtm_stoploss_toggle", "")).upper() == "TRUE"
    result['mtm_stoploss_type'] = entry_para_dict.get("main_mtm_stoploss_type")
    result['main_mtm_stoploss'] = float(entry_para_dict.get("main_mtm_stoploss", 0.0) or 0.0)

    # ========== Overall Take Profit ==========
    result['overall_take_profit_toggle'] = str(entry_para_dict.get("overall_trail_sl_toggle", "")).upper() == "TRUE"
    result['overall_tp_profit_value'] = float(entry_para_dict.get("take_profit_value", 0.0) or 0.0)
    result['overall_tp_trail_value'] = float(entry_para_dict.get("tp_trail_value", 0.0) or 0.0)

    # ========== MTM Stoploss Time Switch ==========
    try:
        time_val = entry_para_dict.get("mtm_stoploss_time_switch")
        if time_val and time_val.strip():
            result['mtm_stopoloss_switch_time'] = dt.strptime(time_val, "%H:%M:%S").time()
        else:
            result['mtm_stopoloss_switch_time'] = ""
    except:
        result['mtm_stopoloss_switch_time'] = ""

    try:
        result['main_mtm_stoploss_after_time_switch'] = float(entry_para_dict.get("main_mtm_stoploss_value_after_time_switch", 0.0) or 0.0)
    except:
        result['main_mtm_stoploss_after_time_switch'] = ''

    # ========== Directory Paths (Environment specific) ==========
    current_dir = os.getcwd().replace("\\", "/")
    result['current_dir'] = current_dir
    result['dependancy_dir'] = f"{current_dir}/dependency"

    # ========== Brokerage ==========
    result['brokerage_type'] = entry_para_dict.get("brokerage_type")
    if result['brokerage_type'] == "Custom":
        result['brokerage_val'] = float(entry_para_dict.get("brokerage_val", 0.0) or 0.0)
    else:
        result['brokerage_val'] = None  # or default value

    # ========== Slippage ==========
    result['slippage_type'] = entry_para_dict.get("slippage_type")
    if result['slippage_type'] == "Custom":
        result['slippage_percentage'] = float(entry_para_dict.get("slippage_percentage", 0.0) or 0.0)
    else:
        result['slippage_percentage'] = None  # or default value

    # ========== Square Off and Trail ==========
    result['square_off_type'] = entry_para_dict.get("square_off_type")
    result['trail_sl_to_breakeven'] = str(entry_para_dict.get("trail_sl_to_breakeven", "")).upper() == "TRUE"
    result['trail_leg_scope'] = entry_para_dict.get("trail_leg_scope")
    result['trail_sl_breakeven_stoploss_type'] = entry_para_dict.get("trail_sl_breakeven_stoploss_type")

    # ========== Other Toggles ==========
    result['plotting_charts'] = str(entry_para_dict.get("plotting_charts", "")).upper() == "TRUE"
    result['next_month_expiry_select'] = str(entry_para_dict.get("next_month_expiry_select", "")).upper() == "TRUE"

    # ========== Reentry Time ==========
    try:
        time_val = entry_para_dict.get("reentry_time_threshold")
        if time_val and time_val.strip():
            result['reentry_time_threshold'] = dt.strptime(time_val, "%H:%M:%S").time()
        else:
            result['reentry_time_threshold'] = ""
    except:
        result['reentry_time_threshold'] = ""

    # ========== Condition Checker ==========
    result['condition_checker_toggle'] = str(entry_para_dict.get("condition_checker_toggle", "")).upper() == "TRUE"
    result['condition_type'] = entry_para_dict.get("condition_type")
    result['rolling_straddle_percent_movement'] = float(entry_para_dict.get("rolling_straddle_percent_movement", 0.0) or 0.0)
    result['spot_percent_movement'] = float(entry_para_dict.get("spot_percent_movement", 0.0) or 0.0)
    
    # MISSING IN NEW CODE - Added here
    result['condition_threshold_time'] = entry_para_dict.get("condition_threshold_time")
    
    result['condition_modification_multiple'] = int(entry_para_dict.get("condition_modification_multiple", 0))

    # ========== RSM Parameters ==========
    result['rsm_straddle_movement'] = float(entry_para_dict.get("rolling_straddle_percent_rsm", 0.0) or 0.0)
    result['rsm_spot_movement'] = float(entry_para_dict.get("spot_movement", 0.0) or 0.0)
    result['rsm_divisor'] = float(entry_para_dict.get("divisor_helper", 0.0) or 0.0)

    # ========== Premium and Rolling ==========
    result['all_legs_premium_checking_multiple'] = float(entry_para_dict.get("all_legs_premium_checking_multiple", 0.0) or 0.0)
    result['rolling_atm_premium_value'] = float(entry_para_dict.get("rolling_atm_premium_value", 0.0) or 0.0)
    result['sl_val1'] = float(entry_para_dict.get("sl_val1", 0.0) or 0.0)
    result['sl_val2'] = float(entry_para_dict.get("sl_val2", 0.0) or 0.0)
    result['roll_on_point1'] = float(entry_para_dict.get("roll_on_point1", 0.0) or 0.0)
    result['roll_on_point2'] = float(entry_para_dict.get("roll_on_point2", 0.0) or 0.0)

    # ========== Adjustments ==========
    try:
        result['adjustments_ce'] = list(ast.literal_eval(entry_para_dict.get("adjustments_ce", "[]")))
    except:
        try:
            result['adjustments_ce'] = [float(entry_para_dict.get("adjustments_ce", 0.0))]
        except:
            result['adjustments_ce'] = []

    try:
        result['adjustments_pe'] = list(ast.literal_eval(entry_para_dict.get("adjustments_pe", "[]")))
    except:
        try:
            result['adjustments_pe'] = [float(entry_para_dict.get("adjustments_pe", 0.0))]
        except:
            result['adjustments_pe'] = []

    # ========== Conditional SL ==========
    result['conditional_sl_type_ce'] = entry_para_dict.get("conditional_sl_type_ce")
    result['conditional_sl_type_pe'] = entry_para_dict.get("conditional_sl_type_pe")
    result['sl_ce'] = float(entry_para_dict.get("sl_ce", 0.0) or 0.0)
    result['sl_pe'] = float(entry_para_dict.get("sl_pe", 0.0) or 0.0)
    result['ce_decay_points'] = float(entry_para_dict.get("ce_decay_points", 0.0) or 0.0)
    result['pe_decay_points'] = float(entry_para_dict.get("pe_decay_points", 0.0) or 0.0)

    # ========== Position Management ==========
    result['one_time_adjustment'] = str(entry_para_dict.get("one_time_adjustment", "")).upper() == "TRUE"
    result['all_position_square_off_at_sl'] = str(entry_para_dict.get("all_position_square_off_at_sl", "")).upper() == "TRUE"
    result['maintain_price_difference'] = str(entry_para_dict.get("maintain_price_difference_toggle", "")).upper() == "TRUE"

    # ========== Monitoring ==========
    result['monitoring_type'] = entry_para_dict.get("monitoring_type")
    result['monitoring_based_on'] = entry_para_dict.get("monitoring_based_on")
    result['type_of_monitoring_based_on'] = entry_para_dict.get("type_of_monitoring_based_on")
    result['direction_side'] = entry_para_dict.get("direction_side")
    result['breakout'] = entry_para_dict.get("breakout")
    result['breakout_value'] = float(entry_para_dict.get("breakout_value", 0.0) or 0.0)
    result['breakout_minutes'] = int(entry_para_dict.get("breakout_minutes", 0))
    result['breakout_minutes_type'] = entry_para_dict.get("breakout_minutes_type")

    # ========== Rolling Straddle Slice Time ==========
    try:
        time_val = entry_para_dict.get("rolling_straddle_slice_time")
        if time_val and time_val.strip():
            result['rolling_straddle_slice_time'] = dt.strptime(time_val, "%H:%M:%S").time()
        else:
            result['rolling_straddle_slice_time'] = ""
    except:
        result['rolling_straddle_slice_time'] = ""

    # ========== Overall Momentum ==========
    result['overall_momentum'] = str(entry_para_dict.get("overall_momentum", "")).upper() == "TRUE"
    result['overall_momentum_type'] = entry_para_dict.get("overall_momentum_type")
    result['overall_momentum_sl'] = float(entry_para_dict.get("overall_momentum_sl", 0.0) or 0.0)
    
    try:
        result['momentum_legs_selection'] = list(ast.literal_eval(entry_para_dict.get("momentum_legs_selection", "[]")))
    except:
        result['momentum_legs_selection'] = []

    # ========== Premium Threshold ==========
    result['premium_threshold_value'] = float(entry_para_dict.get("premium_threshold_value", 0.0) or 0.0)

    # ========== Lazy Leg ATM Threshold ==========
    try:
        time_val = entry_para_dict.get("lazy_leg_atm_threshold")
        if time_val and time_val.strip():
            result['lazy_leg_atm_threshold'] = dt.strptime(time_val, "%H:%M:%S").time()
        else:
            result['lazy_leg_atm_threshold'] = ""
    except:
        result['lazy_leg_atm_threshold'] = ""

    # ========== V Day Simulation ==========
    try:
        result['v_day_simulation_legs'] = list(ast.literal_eval(entry_para_dict.get("v_day_simulation_legs", "[]")))
    except:
        result['v_day_simulation_legs'] = []

    return result