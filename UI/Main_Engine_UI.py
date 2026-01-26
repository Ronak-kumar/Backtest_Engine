import streamlit as st
import json
import datetime
import pandas as pd
import subprocess
import time
import os
import uuid
import glob
import csv
import textwrap
from pathlib import Path

MAIN_DIR = Path(__file__).resolve().parent.parent

# st.set_option('deprecation.showfileUploaderEncoding', False)
st.set_page_config(page_title="Main Engine 2.0 Dashboard", page_icon="💹", layout="wide")
st.markdown("""
        <style>
                .block-container {
                    padding-top: 1rem;
                    padding-bottom: 5rem;
                    padding-left: 5rem;
                    padding-right: 5rem;
                }
        </style>
        """, unsafe_allow_html=True)

st.markdown("<style>.css-1vbkxwb p {word-break: normal;margin-bottom: 0rem;}</style>", unsafe_allow_html=True)

st.markdown(
    """
    <style>
    .title {
        text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Display the title
st.markdown("<h1 class='title'>MAIN ENGINE 2.0 DASHBOARD</h1>", unsafe_allow_html=True)

data = {}


def subprocess_trigger(script_name,argument):
    if os.name == 'nt':
        subprocess.call(["start", "/min","cmd","/k","python", f"{script_name}.py ",f"{argument}"], shell=True)
        
    elif os.name == 'posix':
        print(f"argument ={argument}")

        command = f"gnome-terminal -- bash -c 'python {script_name}.py {argument}; exec bash'"
        subprocess.run(command, shell=True)

def run_csv_files():
    parent_dir = os.path.dirname(os.path.dirname(os.getcwd()))
    csvFolder = f'{MAIN_DIR}/strategies/{strategy}'
    argv=[strategy,max_terminals]
    #subprocess.call(f'python main_engine_runner.py {strategy}', shell=True)
    subprocess_trigger(script_name=f"{MAIN_DIR}/Engine_Runners/Main_Engine_Runner", argument=argv)

    #em_strategy_name = f"{str(strategy)}_{float(main_mtm_stoploss_value)}_{reentry_value}"
    if layer3:
        entry_manager_dic = {"strategy_name": str(strategy),
                             "index": em_indices,
                             "entry_time": em_entry_time,
                             "exit_time": em_exit_time,
                             "margin_type": em_margin_type,
                             "layer3_toggle": True if layer3 else False,
                             "Timestamp" : timestamp,
                             "Combined_sl_value" : float(combined_sl_value),
                             "margin_mtm_target_toggle": True if "percentage" in em_select_main_mtm_target_type else False,
                             "target_margin_percent": float(em_select_main_mtm_trg),
                             "mtm_target_toggle": True if "value" in em_select_main_mtm_target_type else False,
                             "mtm_target": float(em_select_main_mtm_trg),

                             "calculated_target_points_toggle": True if "calculated_points" in em_select_main_mtm_target_type else False,
                             "target_calculated_points": float(em_select_main_mtm_trg),

                             "margin_mtm_stoploss_toggle": True if "percentage" in em_select_mtm_stoploss_type else False,
                             "stoploss_margin_percent": float(em_main_mtm_stoploss_value),

                             "calculated_stoploss_points_toggle": True if "calculated_points" in em_select_mtm_stoploss_type else False,
                             "stoploss_calculated_points": float(em_main_mtm_stoploss_value),

                             "mtm_stoploss_toggle": True if "value" in em_select_mtm_stoploss_type else False,
                             "main_mtm_stoploss": -float(em_main_mtm_stoploss_value),
                             "peak_toggle": True if peak_toggle else False,
                             "peak_threshold": peak_threshold,
                             "european_criteria": european_criteria,
                             "daylight_toggle": daylight_saving_toggle,
                             "daylight_buffer": daylight_delay_buffer,
                             "entry_manager_type": "automate"}


    else:
        entry_manager_dic = {"strategy_name": str(strategy),
                             "index": em_indices,
                             "entry_time": em_entry_time,
                             "exit_time": em_exit_time,
                             "margin_type": em_margin_type,
                             "layer3_toggle": True if layer3 else False,
                             "Timestamp" : timestamp,
                             "Combined_sl_value" : float(combined_sl_value),
                             "margin_mtm_target_toggle": em_select_main_mtm_target_type,
                             "target_margin_percent": float(em_select_main_mtm_trg),
                             "mtm_target_toggle": em_select_main_mtm_target_type,
                             "mtm_target": float(em_select_main_mtm_trg),

                             "calculated_target_points_toggle": em_select_main_mtm_target_type,
                             "target_calculated_points": float(em_select_main_mtm_trg),

                             "calculated_stoploss_points_toggle": em_select_mtm_stoploss_type,
                             "stoploss_calculated_points": float(em_main_mtm_stoploss_value),

                             "margin_mtm_stoploss_toggle": em_select_mtm_stoploss_type,
                             "stoploss_margin_percent": float(em_main_mtm_stoploss_value),
                             "mtm_stoploss_toggle": em_select_mtm_stoploss_type,
                             "main_mtm_stoploss": -float(em_main_mtm_stoploss_value),
                             "peak_toggle": True if peak_toggle else False,
                             "peak_threshold": peak_threshold,
                             "european_criteria": european_criteria,
                             "daylight_toggle": daylight_saving_toggle,
                             "daylight_buffer": daylight_delay_buffer,
                             "entry_manager_type": "automate"}

    if len(em_indices) != 0:
        json_data = json.dumps(entry_manager_dic)
        filename = f'{csvFolder}/entry_manager_metrics.json'
        with open(filename, "w") as setting_file:
            json.dump(json_data, setting_file, cls=DateEncoder)
            time.sleep(5)
        subprocess_trigger(script_name='entry_manager_runner',argument=csvFolder)
            #subprocess.call(["start", "cmd", "/k", "python", "entry_manager_runner.py", json_data], shell=True)


def save_data_to_dict(entry_time, exit_time, indice, filename):
    data['start_date'] = start_date.strftime("%m-%d-%Y")
    data['end_date'] = end_date.strftime("%m-%d-%Y")
    data['strategy_entry_time'] = entry_time
    data['strategy_exit_time'] = exit_time
    data['indices'] = indice
    data['lots'] = int(lots)
    data['strategy_name'] = str(strategy)

    data['metric_generator_function'] = "True"

    data['rolling_straddle_slice_time'] = rolling_straddle_slice_time


    data['EntryMode'] = selected_entry_mode
    data['StoplossCalMode'] = selected_stoploss_cal_mode
    data['stoploss_compare_type'] = selected_stoploss_compare_type
    data['vix_candle_mode'] = selected_vix_candle_mode
    data['stoplosss_hit'] = stoploss_hit
    data['spot_selection_mode'] = spot_selection_mode

    if selected_expiry_toggle == True:
        data['select_expiry_toggle'] = "True"
    else:
        data['select_expiry_toggle'] = "False"

    data["selected_days_toggle"] = selected_days_toggle

    data["monthly_expiry_toggle"] = monthly_expiry


    if selected_days_toggle:
        data["selected_days"] = selected_days


    data['expiry_taketrade'] = Expiry_taketrade



    data['fully_utilized_margin'] = 0
    data['margin_type'] = margin_type
    data['backtest_overrider'] = backtest_overrider
    if select_main_mtm_target_toggle == True:
        data['main_mtm_target_toggle'] = "True"
    else:
        data['main_mtm_target_toggle'] = "False"

    data['main_mtm_target_type'] = select_main_mtm_target_type
    data['main_mtm_trg'] = float(select_main_mtm_trg)

    if mtm_stoploss_toggle == True:
        data['main_mtm_stoploss_toggle'] = "True"
    else:
        data['main_mtm_stoploss_toggle'] = "False"

    data['main_mtm_stoploss_type'] = select_mtm_stoploss_type
    data['main_mtm_stoploss'] = main_mtm_stoploss_value
    data['mtm_stoploss_time_switch'] = mtm_stoploss_time_switch
    data['main_mtm_stoploss_value_after_time_switch'] = main_mtm_stoploss_value_after_time_switch


    data['reentry_time_threshold'] = reentry_time_threshhold

    data['square_off_type'] = square_off_type
    data['premium_threshold_value'] = premium_threshold_value
    data['trail_sl_to_breakeven'] = trail_sl_to_breakeven
    data['trail_leg_scope'] = trail_leg_scope
    data['trail_sl_breakeven_stoploss_type'] = trail_sl_breakeven_stoploss_type


    data["brokerage_type"] = brokerage_type
    if brokerage_type == "Custom":
        data["brokerage_val"] = brokrage_val

    data["slippage_type"] = slippage_type
    if slippage_type == "Custom":
        data["slippage_percentage"] = slippage_percentage


    data["next_month_expiry_select"] = next_month_expiry_select
    data["plotting_charts"] = plotting_charts


    data["condition_checker_toggle"] = condition_checker_toggle
    data["condition_type"] = condition_type
    data["rolling_straddle_percent_movement"] = rolling_straddle_percent_movement
    data["spot_percent_movement"] = spot_percent_movement
    data["condition_threshold_time"] = condition_threshold_time
    data["condition_modification_multiple"] = condition_modification_multiple
    data["rolling_straddle_percent_rsm"] = rolling_straddle_percent_rsm
    data["spot_movement"] = spot_movement
    data["divisor_helper"] = divisor_helper


    data["monitoring_type"] = monitoring_type
    data["monitoring_based_on"] = monitoring_based_on
    data["type_of_monitoring_based_on"] = type_of_monitoring_based_on
    data["direction_side"] = direction_side
    data["breakout"] = breakout
    data["breakout_value"] = breakout_value
    data["breakout_minutes"] = breakout_minutes
    data["breakout_minutes_type"] = breakout_minutes_type


    data["all_legs_premium_checking_multiple"] = all_legs_premium_checking_multiple
    data["rolling_atm_premium_value"] = rolling_atm_premium_value
    data["sl_val1"] = sl_val1
    data["sl_val2"] = sl_val2
    data["roll_on_point1"] = roll_on_point1
    data["roll_on_point2"] = roll_on_point2


    data["one_time_adjustment"] = one_time_adjustment
    data["all_position_square_off_at_sl"] = all_position_square_off_at_sl
    data["maintain_price_difference_toggle"] = maintain_price_difference_toggle
    data["adjustments_ce"] = adjustments_ce
    data["adjustments_pe"] = adjustments_pe
    data["conditional_sl_type_ce"] = conditional_sl_type_ce
    data["conditional_sl_type_pe"] = conditional_sl_type_pe
    data["sl_ce"] = sl_ce
    data["sl_pe"] = sl_pe
    data["pe_decay_points"] = pe_decay_points
    data["ce_decay_points"] = ce_decay_points


    data['delta_adx_adjustment_value'] = delta_adx_adjustment_value
    data['trail_sl_50'] = trail_sl_50
    data['trail_sl_type'] = trail_sl_type
    data['adx_take_profit_value'] = adx_take_profit_value
    data['adx_value'] = adx_value
    data['drop_comparison'] = drop_comparison
    data['adx_compare'] = adx_compare

    data['overall_momentum'] = overall_momentum
    data['overall_momentum_type'] = overall_momentum_type
    data['overall_momentum_sl'] = overall_momentum_sl
    data['momentum_legs_selection'] = momentum_legs_selection
    data['momentum1_legs'] = {'bearish' : bearish_legs, 'bullish' : bullish_legs}
    data['momentum1_interval'] = interval_

    data['v_day_simulation_legs'] = v_day_simulation_legs

    data['overall_trail_sl_toggle'] = overall_trail_sl_toggle
    data['take_profit_value'] = take_profit_value
    data['tp_trail_value'] = tp_trail_value

    data['eod_on_consecutive_sl_toggle'] = eod_on_consecutive_sl_toggle
    data['reexecute_main_orders_on_consecutive_hit'] = reexecute_main_orders_on_consecutive_hit
    data['consecutive_sl_counts'] = consecutive_sl_counts


    data['first_sma'] = first_sma
    data['second_sma'] = second_sma

    data['combined_sl'] = combined_sl
    data['combined_sl_percentage'] = combined_sl_percentage
    data['pair_dict'] = pair_dict



    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)

        for key, value in data.items():
            writer.writerow([key, value])


class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.date):
            return obj.strftime("%m-%d-%Y")
        return super().default(obj)


def download_settings(strategyfolderpath):
    download_filename = f'{strategyfolderpath}/strategy_metrics.json'  # Use the provided strategy name as the filename
    settings_to_download = {k: v for k, v in st.session_state.items()
                            if "button" not in k}
    print(settings_to_download)

    for key, value in settings_to_download.items():
        if isinstance(value, str):
            try:
                date_obj = datetime.datetime.strptime(value, "%m-%d-%Y").date()
                settings_to_download[key] = date_obj
            except ValueError:
                pass
    # save the dic in the strategy_metrices.json file
    with open(download_filename, "w") as settings_file:
        json.dump(settings_to_download, settings_file, cls=DateEncoder)
    print(f"setting save to json file {download_filename}")


def load_settings_from_file(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r") as settings_file:
            loaded_settings = json.load(settings_file)
        # 'Convert date strings to datetime.date objects'''
        for key, value in loaded_settings.items():
            if isinstance(value, str):
                try:
                    date_obj = datetime.datetime.strptime(value, "%m-%d-%Y").date()
                    loaded_settings[key] = date_obj
                except ValueError:
                    pass
        return loaded_settings
    else:
        return None


def apply_settings():
    parent_dir = os.path.dirname(os.path.dirname(os.getcwd()))
    csvFolder = f'{MAIN_DIR}/strategies/{strategy}'
    download_filename = f"{csvFolder}/strategy_metrics.json"  # Use the provided strategy name to get the JSON file
    uploaded_settings = load_settings_from_file(download_filename)

    if uploaded_settings:
        for k in uploaded_settings.keys():
            st.session_state[k] = uploaded_settings[k]
            if st.session_state['strategy_name'] is None:
                st.session_state['strategy_name'] = st.session_state['strategy_name']

        savestatus.success("Settings loaded successfully✅")
    else:
        savestatus.error(f"Settings file '{download_filename}' not found in the current directory.")


def save_settings_to_csv():
    parent_dir = os.path.dirname(os.path.dirname(os.getcwd()))
    csvFolder = f'{MAIN_DIR}/strategies/{strategy}'
    os.makedirs(csvFolder, exist_ok=True)
    download_settings(csvFolder)
    startdate = start_date.strftime("%m%y")
    enddate = end_date.strftime("%m%y")
    for entry, values in timings_dict.items():
        for indice in indices:
            entry_time = values["entry_time"]
            exit_time = values["exit_time"]
            entrystr = entry_time.split(":")
            entrystr = f'{entrystr[0]}{entrystr[1]}'
            exitstr = exit_time.split(":")
            exitstr = f'{exitstr[0]}{exitstr[1]}'
            filename = f"{csvFolder}/entry_parameter_{startdate}_{enddate}_{entrystr}_{exitstr}_{indice}.csv"
            save_data_to_dict(entry_time, exit_time, indice, filename)

    leg_folder = f'{csvFolder}/leg_data'
    os.makedirs(leg_folder, exist_ok=True)
    for leg_number, leg_para in legsdata.items():
        filename = f"{leg_folder}/leg_{leg_number}.csv"
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)

            for key, value in leg_para.items():
                writer.writerow([key, value])

    sub_legs_folder =  f'{csvFolder}/sub_leg_data'
    os.makedirs(sub_legs_folder, exist_ok=True)
    for leg_number, leg_para in sub_legs_data.items():
        filename = f"{sub_legs_folder}/leg_{leg_number}.csv"
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)

            for key, value in leg_para.items():
                writer.writerow([key, value])


    savestatus.success("Data saved to CSV File")

def make_toggle2_false():
    # When toggle 1 is False, set toggle 2 to False
    if st.session_state.buying_toggle:
        st.session_state.Trailing_toggle = False
        st.session_state.Freeze_toggle = False
        st.session_state.sl_reentry_at_cost = False
        st.session_state.sl_old_stoploss = False
        st.session_state.sl_entry_atcost = False


def make_certain_toggle_false():
    if st.session_state.selected_days_toggle:
        st.session_state.selected_expiry_toggle = False
    elif st.session_state.selected_expiry_toggle:
        st.session_state.selected_days_toggle = False




def generate_sub_row(row_id,sub_leg_toggle,sub_leg_number):


    data = {}
    premium_value = None
    call_OTM_value = None
    strike_options_box = None

    row_container = st.empty()
    row_columns = row_container.columns((1.5, 1.5, 0.3))

    st.markdown(f"""
            <div style='
                background-color: #e0e0e0;
                padding: 3px;
                margin-top: 3px;
                border-radius: 3px;
                border: 2px solid #007bff;
                box-shadow: 2px 2px 8px rgba(0,0,0,0.1);
            '>
            <h4 style='color:#007bff;'>Lazy Leg #0.{sub_leg_number}</h4>
        """, unsafe_allow_html=True)

    # row_columns[1].markdown(f"**#{row_number}.{sub_leg_number}**")

    #row_columns[2].button("🗑️", key=f"delete_button{row_id}{sub_leg_toggle}{sub_leg_number}", on_click=remove_row, args=[row_id])
    leg_col= st.columns([0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
    leg_col2= st.columns([0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
    #################### Default Parameters @@@@@@@@@@@@@@@@@@@
    leg_premium_consideration = call_OTM_value = atm_stradle_premium= strike_options_box = call_option_type_value = None

    call_position_value = hedges = synthetic_or_spot = premium_value = None
    Target_profit_text_value = call_option_type_value = target_profit_toggle = None

    Friday_stoploss = stop_loss_text_value = stop_loss_selected_option = stop_loss_toggle = None

    Thursday_stoploss = Wednesday_stoploss = Tuesday_stoploss = Monday_stoploss = None
    Trail_sl_toggle= total_sl_rentry = total_tgt_rentry = re_entry_on_sl_selected_option = sl_rentry_toggle = target_rentry_toggle = None
    trail_sl_text_value2 = trail_sl_text_value1 = trail_sl_selected_option = None

    range_breakout_threshold_time = range_breakout_of = underlying_asset = range_compare_section = None
    vix_operator = "less than"
    vix_value = 0



    ##### Combined First Side #########
    call_option_type_value = leg_col[0].selectbox("Option Type:", ["CE", "PE"], key=f"first_option_value_{row_id}{sub_leg_toggle}{sub_leg_number}",
                                                  index=0)


    leg_expiry_selection = leg_col[1].selectbox("Expiry Selection:", ["Weekly", "Next_Weekly", "Monthly"], index=0,
                                        key=f"leg_expiry_selection_{row_id}{sub_leg_toggle}{sub_leg_number}")


    call_position_value = leg_col[2].selectbox("Position:", ["Buy", "Sell"], key=f"position_{row_id}{sub_leg_toggle}{sub_leg_number}")

    synthetic_or_spot = leg_col[3].selectbox("Entry ON:", ["Spot", "Synthetic"], key=f"synthetic_or_spot_{row_id}{sub_leg_toggle}{sub_leg_number}")
    strike_options_box = leg_col[4].selectbox("Strike Type", ["ATM", "ITM", "OTM", "PREMIUM", "ATM Straddle Premium Percentage"],
                                              key=f"first_Select_strike_type_{row_id}{sub_leg_toggle}{sub_leg_number}")
    if strike_options_box == "ATM":
        pass
    elif strike_options_box == "ATM Straddle Premium Percentage":
        atm_stradle_premium = leg_col[5].number_input(f"{strike_options_box}:", 1,
                                                 key=f"first_{strike_options_box}_premium_val_{row_id}{sub_leg_toggle}{sub_leg_number}")
    elif strike_options_box in ["ITM", "OTM"]:
        call_OTM_value = leg_col[5].number_input(f"{strike_options_box}:", 1,
                                                 key=f"first_{strike_options_box}_range_{row_id}{sub_leg_toggle}{sub_leg_number}")
    else:
        leg_premium_consideration = leg_col[5].selectbox("Premium Consideration:",
                                                            ["CLOSEST", "NEAREST", "PREMIUM>="], index=0,help="The CLOSEST will select all the premium<= value given value",
                                                            key=f"first_premium_consideration_{row_id}{sub_leg_toggle}{sub_leg_number}")
        premium_value = leg_col[6].text_input("Premium:", key=f"first_premium_value_{row_id}{sub_leg_toggle}{sub_leg_number}")



    if call_position_value == "Buy":

        hedges = leg_col2[0].toggle(label="hedges", key=f"hedges_toggle_{row_id}{sub_leg_toggle}{sub_leg_number}")
    else:
        hedges = leg_col2[0].toggle(label="hedges", key=f"hedges_toggle_{row_id}{sub_leg_toggle}{sub_leg_number}", disabled=True)

    target_profit_toggle = leg_col2[1].toggle(label="Target Profit", key=f"leg_target_profit_toggle_{row_id}{sub_leg_toggle}{sub_leg_number}")
    Target_profit_text_value = leg_col2[2].text_input(" ",1 , key=f"call_target_profit_value_{row_id}{sub_leg_toggle}{sub_leg_number}",
                                               label_visibility="collapsed", disabled=not target_profit_toggle)
    stop_loss_toggle = leg_col2[3].toggle(label="Stop Loss", key=f"leg_stoploss_toggle_{row_id}{sub_leg_toggle}{sub_leg_number}")
    stop_loss_selected_option = leg_col2[4].selectbox(" ", ["Percentage", "Day Wise Percentage", "Points"], index=1,
                                                          key=f"leg_stoploss_type_{row_id}{sub_leg_toggle}{sub_leg_number}",
                                                          label_visibility="collapsed",
                                                          disabled=not stop_loss_toggle)

    if stop_loss_selected_option == "Percentage" or stop_loss_selected_option == "Points":
        stop_loss_text_value = leg_col2[5].text_input(" ", 1, key=f"call_stoploss_value_{row_id}{sub_leg_toggle}{sub_leg_number}", label_visibility="collapsed", disabled=not stop_loss_toggle)
    else:
        stoploss_col = st.columns(5)

        if stop_loss_toggle:

            Monday_stoploss = stoploss_col[0].text_input("Monday:", 1, key=f"monday_stoploss_{row_id}{sub_leg_toggle}{sub_leg_number}", disabled=not stop_loss_toggle)
            Tuesday_stoploss = stoploss_col[1].text_input("Tuesday:", 1, key=f"tuesday_stoploss_{row_id}{sub_leg_toggle}{sub_leg_number}", disabled=not stop_loss_toggle)
            Wednesday_stoploss = stoploss_col[2].text_input("Wednesday:", 1, key=f"wednesday_stoploss_{row_id}{sub_leg_toggle}{sub_leg_number}", disabled=not stop_loss_toggle)
            Thursday_stoploss = stoploss_col[3].text_input("Thursday:", 1, key=f"thursday_stoploss_{row_id}{sub_leg_toggle}{sub_leg_number}", disabled=not stop_loss_toggle)
            Friday_stoploss = stoploss_col[4].text_input("Friday:", 1, key=f"friday_stoploss_{row_id}{sub_leg_toggle}{sub_leg_number}", disabled=not stop_loss_toggle)

    vix_col = st.columns(4)
    vix_checker_toggle = vix_col[0].toggle(label="Vix Checker Toggle", key=f"vix_checker_toggle_{row_id}{sub_leg_toggle}{sub_leg_number}")
    if vix_checker_toggle:
        vix_operator = vix_col[1].selectbox("Vix Operator:",
                                            ["greater than", "less than"], index=1,
                                            key=f"vix_operator_{row_id}{sub_leg_toggle}{sub_leg_number}")
        vix_value = vix_col[2].text_input("Vix Value", 1, key=f"vix_value_{row_id}{sub_leg_toggle}{sub_leg_number}")


    sm_percentage_direction = "PERCENTAGE_UP"
    sm_percent_value = 1
    sm_tgt_sl_price = "System_price"
    sm_leg_data = {}

    sm_col = st.columns(4)
    sm_entry_strike_col = st.columns(4)

    sm_toggle = sm_col[0].toggle(label="Simple Momentum", key=f"sm_toggle_{row_id}{sub_leg_toggle}{sub_leg_number}", disabled=overall_momentum or momentum_enabled)


    rentry_col = st.columns(4)
    target_rentry_toggle = rentry_col[1].toggle(label="Rentry On Target", key=f"leg_rentry_tgt_toggle_{row_id}{sub_leg_toggle}{sub_leg_number}")

    sl_rentry_toggle = rentry_col[2].toggle(label="Rentry On Stoploss", key=f"leg_rentry_sl_toggle_{row_id}{sub_leg_toggle}{sub_leg_number}")
    if sm_toggle:
        re_entry_on_sl_selected_option = rentry_col[2].selectbox(" ", ["RE ASAP", "RE MOMENTUM", "RE COST"],
                                                        key=f"call_slreentry_type_{row_id}{sub_leg_toggle}{sub_leg_number}",
                                                        label_visibility="collapsed",
                                                        disabled = not sl_rentry_toggle)
        re_entry_on_tgt_selected_option = rentry_col[1].selectbox(" ", ["RE ASAP", "RE MOMENTUM", "RE COST"],
                                                                  key=f"call_tgtreentry_type_{row_id}{sub_leg_toggle}{sub_leg_number}",
                                                                  label_visibility="collapsed",
                                                                  disabled=not target_rentry_toggle)
    else:
        re_entry_on_sl_selected_option = rentry_col[2].selectbox(" ", ["RE ASAP", "RE COST"],
                                                                 key=f"call_slreentry_type_{row_id}{sub_leg_toggle}{sub_leg_number}",
                                                                 label_visibility="collapsed",
                                                                 disabled=not sl_rentry_toggle)
        re_entry_on_tgt_selected_option = rentry_col[1].selectbox(" ", ["RE ASAP", "RE COST"],
                                                                  key=f"call_tgtreentry_type_{row_id}{sub_leg_toggle}{sub_leg_number}",
                                                                  label_visibility="collapsed",
                                                                  disabled=not target_rentry_toggle)

    if sl_rentry_toggle:
        total_sl_rentry = rentry_col[3].text_input("Total SL Rentry", 1, key=f"total_sl_rentry_{row_id}{sub_leg_toggle}{sub_leg_number}")

    if target_rentry_toggle:
        total_tgt_rentry = rentry_col[0].text_input("Total Target Rentry", 1, key=f"total_tgt_rentry_{row_id}{sub_leg_toggle}{sub_leg_number}")


    if re_entry_on_tgt_selected_option == "RE MOMENTUM" or re_entry_on_sl_selected_option == "RE MOMENTUM" or sm_toggle:
        sm_percentage_direction = sm_col[1].selectbox("Direction", ["PERCENTAGE_UP", "PERCENTAGE_DOWN", "POINTS_UP", "POINTS_DOWN"],
                                                      key=f"sm_percentage_direction_{row_id}{sub_leg_toggle}{sub_leg_number}")
        sm_percent_value = sm_col[2].text_input("Direction Percentage/Points", 1, key=f"sm_percent_value_{row_id}{sub_leg_toggle}{sub_leg_number}")
        sm_tgt_sl_price = sm_col[3].selectbox("Simple Moment Target/Stoploss Price ",
                                              ["SM_price", "Entry_price"], index=0,
                                              key=f"sm_tgt_sl_price_{row_id}{sub_leg_toggle}{sub_leg_number}")

        sm_entry_strike_type_toggle = sm_entry_strike_col[0].toggle("Strike Selection for Simple Moment Execution",
                                                                      key=f"sm_entry_strike_type_toggle_{row_id}{sub_leg_toggle}{sub_leg_number}")

        if sm_entry_strike_type_toggle:
            # Strike type selection
            sm_leg_strike_type = sm_entry_strike_col[1].selectbox(
                f"New Leg Strike Type",
                ["ATM", "ITM", "OTM", "PREMIUM"],
                index=0,
                key=f"sm_leg_strike_type_{row_id}{sub_leg_toggle}{sub_leg_number}")

            # Build dictionary based on strike_type
            sm_leg_data = {"strike_type": sm_leg_strike_type}

            if sm_leg_strike_type == "PREMIUM":
                sm_leg_premium_consideration = sm_entry_strike_col[2].selectbox(
                    "Premium Consideration:",
                    ["CLOSEST", "NEAREST"],
                    index=0,
                    key=f"sm_leg_premium_consideration_{row_id}{sub_leg_toggle}{sub_leg_number}"
                )
                sm_leg_premium_value = sm_entry_strike_col[3].number_input(
                    "Premium:",
                    min_value=0,
                    key=f"sm_leg_premium_{row_id}{sub_leg_toggle}{sub_leg_number}"
                )
                sm_leg_data["premium_consideration"] = sm_leg_premium_consideration
                sm_leg_data["premium"] = sm_leg_premium_value

            elif sm_leg_strike_type in ["ITM", "OTM"]:
                sm_leg_spread_value = sm_entry_strike_col[2].number_input(
                    "Spread:",
                    min_value=1,
                    key=f"sm_leg_spread_{row_id}{sub_leg_toggle}{sub_leg_number}"
                )
                sm_leg_data["spread"] = sm_leg_spread_value


    trailing_col = st.columns([0.4, 1, 1, 1])

    Trail_sl_toggle = trailing_col[0].toggle(label="Trail SL", key=f"leg_trailsl_toggle_{row_id}{sub_leg_toggle}{sub_leg_number}")
    trail_sl_selected_option = trailing_col[1].selectbox(" ", ["Points", "Percentage"], key=f"call_trailsl_type_{row_id}{sub_leg_toggle}{sub_leg_number}",
                                             label_visibility="collapsed", disabled=not Trail_sl_toggle)

    trail_sl_text_value1 = trailing_col[2].number_input(" ", key=f"call_trailsl_value1_{row_id}{sub_leg_toggle}{sub_leg_number}", label_visibility="collapsed",
                                            disabled=not Trail_sl_toggle, step=10)
    trail_sl_text_value2 = trailing_col[3].number_input(" ", key=f"call_trailsl_value2_{row_id}{sub_leg_toggle}{sub_leg_number}", label_visibility="collapsed",
                                            disabled=not Trail_sl_toggle, step=10)


    filtered = set(legs_keys_session)

    lazy_leg_col = st.columns([1, 1])
    lazy_leg_next_leg_col0, lazy_leg_next_leg_col1, lazy_leg_tgt_col1, lazy_leg_tgt_col2 = st.columns([1, 1, 1, 1])
    _, _, lazy_leg_sl_col1, lazy_leg_sl_col2 = st.columns([1, 1, 1, 1])

    leg_hopping_count_next_leg = 0
    leg_hopping_count_tgt = 0
    leg_hopping_count_sl = 0

    with lazy_leg_col[0]:

        select_next_leg_to_be_executed = st.toggle(
            f"Selected Leg Execution After Leg Completion",
            key=f"select_next_leg_to_be_executed_{row_id}{sub_leg_toggle}{sub_leg_number}",
            disabled=all_legs_disable_condition or rsm_enabled, on_change=toggle_handler,
            args=(f"select_next_leg_to_be_executed_{row_id}{sub_leg_toggle}{sub_leg_number}", f"lazy_leg_execution_on_target_sl_{row_id}{sub_leg_toggle}{sub_leg_number}"))
        if select_next_leg_to_be_executed:
            next_lazy_leg_to_be_executed = lazy_leg_next_leg_col0.selectbox(
                "Next leg to Be Executed",
                options=filtered,
                index=0,
                key=f"next_lazy_leg_to_be_executed_{row_id}{sub_leg_toggle}{sub_leg_number}"
            )

            leg_hopping_count_next_leg = lazy_leg_next_leg_col1.text_input("Execution Counter For Next Leg", value=1000,
                                                                key=f"leg_hopping_count_next_leg_{row_id}{sub_leg_toggle}{sub_leg_number}")

    with lazy_leg_col[1]:
        lazy_leg_execution_on_target_sl = st.toggle(
            f"Selected Leg Execution on Target/SL",
            key=f"lazy_leg_execution_on_target_sl_{row_id}{sub_leg_toggle}{sub_leg_number}",
            disabled=all_legs_disable_condition or rsm_enabled, on_change=toggle_handler,
            args=(f"lazy_leg_execution_on_target_sl_{row_id}{sub_leg_toggle}{sub_leg_number}", f"select_next_leg_to_be_executed_{row_id}{sub_leg_toggle}{sub_leg_number}"))

        if lazy_leg_execution_on_target_sl:
            lazy_leg_tobe_executed_on_target = lazy_leg_sl_col1.selectbox(
                "Target Leg",
                options=filtered,
                index=0,
                key=f"lazy_leg_tobe_executed_on_target_{row_id}{sub_leg_toggle}{sub_leg_number}"
            )
            leg_hopping_count_tgt = lazy_leg_tgt_col2.text_input("Execution Counter For Target", value=1000,
                                                                key=f"leg_hopping_count_tgt_{row_id}{sub_leg_toggle}{sub_leg_number}")

            lazy_leg_tobe_executed_on_sl = lazy_leg_sl_col1.selectbox(
                "SL Leg",
                options=filtered,
                index=0,
                key=f"lazy_leg_tobe_executed_on_sl_{row_id}{sub_leg_toggle}{sub_leg_number}"
            )
            leg_hopping_count_sl = lazy_leg_sl_col2.text_input("Execution Counter For SL", value=1000,
                                                                key=f"leg_hopping_count_sl_{row_id}{sub_leg_toggle}{sub_leg_number}")

    data["option_type"] = call_option_type_value
    data["strike_type"] = strike_options_box
    data["Spread"] = call_OTM_value
    data["atm_straddle_premium"] = atm_stradle_premium
    data["premium_consideration"] = leg_premium_consideration
    data["premium_value"] = premium_value

    data["entry_on"] = synthetic_or_spot

    data["hedges"] = hedges
    data["leg_expiry_selection"] = leg_expiry_selection

    data["position"] = call_position_value

    data["target_profit_toggle"] = target_profit_toggle
    data["target_profit_value"] = Target_profit_text_value

    data["stop_loss_toggle"] = stop_loss_toggle
    data["stop_loss_type"] = stop_loss_selected_option

    data["stop_loss_value"] = stop_loss_text_value
    data["Monday_stoploss"] = Monday_stoploss
    data["Tuesday_stoploss"] = Tuesday_stoploss
    data["Wednesday_stoploss"] = Wednesday_stoploss
    data["Thursday_stoploss"] = Thursday_stoploss
    data["Friday_stoploss"] = Friday_stoploss

    data["sm_toggle"] = sm_toggle
    data["sm_percentage_direction"] = sm_percentage_direction
    data["sm_percent_value"] = sm_percent_value
    data["sm_tgt_sl_price"] = sm_tgt_sl_price
    data["sm_leg_data"] = sm_leg_data



    data["re_entry_on_tgt_toggle"] = target_rentry_toggle
    data["re_entry_on_tgt_type"] = re_entry_on_tgt_selected_option

    data["re_entry_on_sl_toggle"] = sl_rentry_toggle
    data["re_entry_on_sl_type"] = re_entry_on_sl_selected_option

    data["total_sl_rentry"] = total_sl_rentry
    data["total_tgt_rentry"] = total_tgt_rentry

    data["trail_sl_toggle"] = Trail_sl_toggle
    data["trail_sl_type"] = trail_sl_selected_option
    data["trail_sl_value1"] = trail_sl_text_value1
    data["trail_sl_value2"] = trail_sl_text_value2
    data['sub_leg_toggle'] = sub_leg_toggle
    data['sub_leg_number'] = sub_leg_number

    data["vix_checker_toggle"] = vix_checker_toggle
    data["vix_operator"] = vix_operator
    data["vix_value"] = vix_value
    data['leg_execution_on_target_sl'] = lazy_leg_execution_on_target_sl
    if lazy_leg_execution_on_target_sl:
        data['leg_tobe_executed_on_target'] = lazy_leg_tobe_executed_on_target
        data['leg_tobe_executed_on_sl'] = lazy_leg_tobe_executed_on_sl

    if select_next_leg_to_be_executed:
        data['next_lazy_leg_to_be_executed'] = next_lazy_leg_to_be_executed


    data['leg_hopping_count_next_leg'] = leg_hopping_count_next_leg
    data['leg_hopping_count_sl'] = leg_hopping_count_sl
    data['leg_hopping_count_tgt'] = leg_hopping_count_tgt



    # Check if any component is active before returning the data
    if any(data.values()):
        return data

    st.write("---")


def generate_row(row_id):

    data = {}
    premium_value = None
    call_OTM_value = None
    strike_options_box = None

    row_container = st.empty()
    row_columns = row_container.columns((1.5, 1.5, 0.3))

    st.markdown(f"""
            <div style='
                background-color: #e0e0e0;
                padding: 3px;
                margin-top: 3px;
                border-radius: 3px;
                border: 2px solid #007bff;
                box-shadow: 2px 2px 8px rgba(0,0,0,0.1);
            '>
            <h4 style='color:#007bff;'>Leg #{row_number}</h4>
        """, unsafe_allow_html=True)

    # row_columns[1].markdown(f"**#{row_number}**")

    row_columns[2].button("🗑️", key=f"delete_button{row_id}", on_click=remove_row, args=[row_id])
    leg_col= st.columns([0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
    leg_col2= st.columns([0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
    #################### Default Parameters @@@@@@@@@@@@@@@@@@@
    leg_premium_consideration = call_OTM_value = atm_stradle_premium= strike_options_box = call_option_type_value = None

    call_position_value = hedges = synthetic_or_spot = premium_value = None
    Target_profit_text_value = call_option_type_value = target_profit_toggle = None

    Friday_stoploss = stop_loss_text_value = stop_loss_selected_option = stop_loss_toggle = None

    Thursday_stoploss = Wednesday_stoploss = Tuesday_stoploss = Monday_stoploss = None
    Trail_sl_toggle= total_sl_rentry = total_tgt_rentry = re_entry_on_sl_selected_option = sl_rentry_toggle = target_rentry_toggle = None
    trail_sl_text_value2 = trail_sl_text_value1 = trail_sl_selected_option = None

    range_breakout_threshold_time = range_breakout_of = underlying_asset = range_compare_section = range_breakout_start = None
    vix_operator = "less than"
    vix_value = 0

    ##### Combined First Side #########
    call_option_type_value = leg_col[0].selectbox("Option Type:", ["CE", "PE"], key=f"first_option_value_{row_id}",
                                                  index=0)


    leg_expiry_selection = leg_col[1].selectbox("Expiry Selection:", ["Weekly", "Next_Weekly", "Monthly"], index=0,
                                                key=f"leg_expiry_selection_{row_id}")



    call_position_value = leg_col[2].selectbox("Position:", ["Buy", "Sell"], key=f"position_{row_id}")

    synthetic_or_spot = leg_col[3].selectbox("Entry ON:", ["Spot", "Synthetic"], key=f"synthetic_or_spot_{row_id}")
    strike_options_box = leg_col[4].selectbox("Strike Type", ["ATM", "ITM", "OTM", "PREMIUM", "ATM Straddle Premium Percentage"],
                                              key=f"first_Select_strike_type_{row_id}")
    if strike_options_box == "ATM":
        pass
    elif strike_options_box == "ATM Straddle Premium Percentage":
        atm_stradle_premium = leg_col[5].number_input(f"{strike_options_box}:", 1,
                                                      key=f"first_{strike_options_box}_premium_val_{row_id}")
    elif strike_options_box in ["ITM", "OTM"]:
        call_OTM_value = leg_col[5].number_input(f"{strike_options_box}:", 1,
                                                 key=f"first_{strike_options_box}_range_{row_id}")
    else:
        leg_premium_consideration = leg_col[5].selectbox("Premium Consideration:",
                                                            ["CLOSEST", "NEAREST","PREMIUM>="], index=0,help="The CLOSEST will select all the premium<= value given value",
                                                            key=f"first_premium_consideration_{row_id}")
        premium_value = leg_col[6].text_input("Premium:", key=f"first_premium_value_{row_id}")


    if call_position_value == "Buy":

        hedges = leg_col2[0].toggle(label="hedges", key=f"hedges_toggle_{row_id}", disabled = rsm_enabled or delta_adx_enabled)
    else:
        hedges = leg_col2[0].toggle(label="hedges", key=f"hedges_toggle_{row_id}", disabled=True)


    target_profit_toggle = leg_col2[1].toggle(label="Target Profit", key=f"leg_target_profit_toggle_{row_id}", disabled=all_legs_disable_condition or rsm_enabled or delta_adx_enabled)
    Target_profit_text_value = leg_col2[2].text_input(" ",1 , key=f"call_target_profit_value_{row_id}",
                                               label_visibility="collapsed", disabled=not target_profit_toggle)
    stop_loss_toggle = leg_col2[3].toggle(label="Stop Loss", key=f"leg_stoploss_toggle_{row_id}", disabled=all_legs_disable_condition or delta_adx_enabled)
    stop_loss_selected_option = leg_col2[4].selectbox(" ", ["Percentage", "Day Wise Percentage", "Points"], index=1,
                                                          key=f"leg_stoploss_type_{row_id}",
                                                          label_visibility="collapsed",
                                                          disabled=not stop_loss_toggle)

    if stop_loss_selected_option == "Percentage" or stop_loss_selected_option == "Points":
        stop_loss_text_value = leg_col2[5].text_input(" ", 1, key=f"call_stoploss_value_{row_id}", label_visibility="collapsed", disabled=not stop_loss_toggle)
    else:
        if stop_loss_toggle:

            stoploss_col = st.columns(5)
            Monday_stoploss = stoploss_col[0].text_input("Monday:", 1, key=f"monday_stoploss_{row_id}", disabled=not stop_loss_toggle)
            Tuesday_stoploss = stoploss_col[1].text_input("Tuesday:", 1, key=f"tuesday_stoploss_{row_id}", disabled=not stop_loss_toggle)
            Wednesday_stoploss = stoploss_col[2].text_input("Wednesday:", 1, key=f"wednesday_stoploss_{row_id}", disabled=not stop_loss_toggle)
            Thursday_stoploss = stoploss_col[3].text_input("Thursday:", 1, key=f"thursday_stoploss_{row_id}", disabled=not stop_loss_toggle)
            Friday_stoploss = stoploss_col[4].text_input("Friday:", 1, key=f"friday_stoploss_{row_id}", disabled=not stop_loss_toggle)

    vix_col = st.columns(4)
    vix_checker_toggle = vix_col[0].toggle(label="Vix Checker Toggle", key=f"vix_checker_toggle_{row_id}", disabled=all_legs_disable_condition  or rsm_enabled or delta_adx_enabled)
    if vix_checker_toggle:
        vix_operator = vix_col[1].selectbox("Vix Operator:",
                                                ["greater than", "less than"], index=1,
                                                key=f"vix_operator_{row_id}")
        vix_value = vix_col[2].text_input("Vix Value", 1, key=f"vix_value_{row_id}")

    st.write(f"The following two toggles are for rolling straddle check.(Select Only One)")

    rs_col = st.columns(3)
    rolling_straddle_breach_on = "High"
    rolling_straddle_consecutive_candles = 1

    rolling_straddle_toggle = rs_col[0].toggle(label="Rolling Straddle Entry",
                                               key=f"rolling_straddle_toggle_{row_id}",
                                               disabled=all_legs_disable_condition or rsm_enabled or non_correlation_enabled or delta_adx_enabled or momentum_enabled)

    if rolling_straddle_toggle:
        rolling_straddle_breach_on = rs_col[1].selectbox("Rolling Straddle Breach On:",
                                                         ["High", "Low"], index=0,
                                                         key=f"rolling_straddle_breach_on_{row_id}",
                                                         disabled=not rolling_straddle_toggle)

        rolling_straddle_consecutive_candles = rs_col[2].text_input("Rolling Straddle Consecutive Candles", 1,
                                                                    key=f"rolling_straddle_consecutive_candles_{row_id}",
                                                                    disabled=not rolling_straddle_toggle)

    rsv_col = st.columns(3)
    rolling_straddle_vwap_breach_on = "above_rolling_straddle_vwap"
    rolling_straddle_vwap_consecutive_candles = 1

    rolling_straddle_vwap_toggle = rsv_col[0].toggle(label="Rolling Straddle Vwap Entry",
                                                     key=f"rolling_straddle_vwap_toggle_{row_id}",
                                                     disabled=all_legs_disable_condition or rsm_enabled or non_correlation_enabled or delta_adx_enabled or momentum_enabled)

    if rolling_straddle_vwap_toggle:
        rolling_straddle_vwap_breach_on = rsv_col[1].selectbox("Rolling Straddle Vwap Breach On:",
                                                               ["above_rolling_straddle_vwap",
                                                                "below_rolling_straddle_vwap"], index=0,
                                                               key=f"rolling_straddle_vwap_breach_on_{row_id}",
                                                               disabled=not rolling_straddle_vwap_toggle)

        rolling_straddle_vwap_consecutive_candles = rsv_col[2].text_input("Rolling Straddle VWAP Consecutive Candles",
                                                                          1,
                                                                          key=f"rolling_straddle_vwap_consecutive_candles_{row_id}",
                                                                          disabled=not rolling_straddle_vwap_toggle)

    sm_percentage_direction = "PERCENTAGE_UP"
    sm_percent_value = 1
    sm_tgt_sl_price = "System_price"
    sm_leg_data = {}

    st.write(f"The following two toggles are type of entry you want to take.(Select Only One)")

    sm_col = st.columns(4)
    sm_entry_strike_col = st.columns(4)

    sm_toggle = sm_col[0].toggle(label="Simple Momentum", key=f"sm_toggle_{row_id}", disabled=all_legs_disable_condition or rsm_enabled or delta_adx_enabled or overall_momentum or momentum_enabled)


    rb_col = st.columns(6)
    range_breakout_toggle = rb_col[0].toggle(label="Range Breakout Entry",
                                             key=f"range_breakout_toggle_{row_id}", disabled=all_legs_disable_condition  or rsm_enabled or delta_adx_enabled or momentum_enabled)

    if range_breakout_toggle:
        range_breakout_start = rb_col[1].selectbox("Range Of:",
                                               ["Default", "Exact"], index=0,
                                               key=f"range_breakout_start_{row_id}")
        range_breakout_threshold_time = rb_col[2].text_input(f"Range Breakout Time:", placeholder="HH:MM:SS",
                                                             key=f"range_breakout_threshold_time_{row_id}")
        range_breakout_of = rb_col[3].selectbox("Range Breakout Of:",
                                                ["High", "Low"], index=0,
                                                key=f"range_breakout_of_{row_id}")
        underlying_asset = rb_col[4].selectbox("Range Of:",
                                               ["Instrument", "Underlying"], index=0,
                                               key=f"underlying_asset_{row_id}")

        range_compare_section = rb_col[5].selectbox("Range Compare Section:",
                                                    [range_breakout_of, "Close"], index=0,
                                                    key=f"range_compare_section_{row_id}")

    rentry_col = st.columns(4)
    target_rentry_toggle = rentry_col[1].toggle(label="Rentry On Target", key=f"leg_rentry_tgt_toggle_{row_id}", disabled=all_legs_disable_condition  or rsm_enabled or delta_adx_enabled)

    sl_rentry_toggle = rentry_col[2].toggle(label="Rentry On Stoploss", key=f"leg_rentry_sl_toggle_{row_id}", disabled=all_legs_disable_condition or rsm_enabled or delta_adx_enabled)
    if sm_toggle:
        re_entry_on_sl_selected_option = rentry_col[2].selectbox(" ", ["RE ASAP", "RE MOMENTUM", "RE COST"],
                                                        key=f"call_slreentry_type_{row_id}",
                                                        label_visibility="collapsed",
                                                        disabled = not sl_rentry_toggle)
        re_entry_on_tgt_selected_option = rentry_col[1].selectbox(" ", ["RE ASAP", "RE MOMENTUM", "RE COST"],
                                                                  key=f"call_tgtreentry_type_{row_id}",
                                                                  label_visibility="collapsed",
                                                                  disabled=not target_rentry_toggle)
    else:
        re_entry_on_sl_selected_option = rentry_col[2].selectbox(" ", ["RE ASAP", "RE COST"],
                                                                 key=f"call_slreentry_type_{row_id}",
                                                                 label_visibility="collapsed",
                                                                 disabled=not sl_rentry_toggle)
        re_entry_on_tgt_selected_option = rentry_col[1].selectbox(" ", ["RE ASAP", "RE COST"],
                                                                  key=f"call_tgtreentry_type_{row_id}",
                                                                  label_visibility="collapsed",
                                                                  disabled=not target_rentry_toggle)

    if sl_rentry_toggle:
        total_sl_rentry = rentry_col[3].text_input("Total SL Rentry", 1, key=f"total_sl_rentry_{row_id}")

    if target_rentry_toggle:
        total_tgt_rentry = rentry_col[0].text_input("Total Target Rentry", 1, key=f"total_tgt_rentry_{row_id}")


    if re_entry_on_tgt_selected_option == "RE MOMENTUM" or re_entry_on_sl_selected_option == "RE MOMENTUM" or sm_toggle:
        sm_percentage_direction = sm_col[1].selectbox("Direction", ["PERCENTAGE_UP", "PERCENTAGE_DOWN", "POINTS_UP", "POINTS_DOWN"],
                                                      key=f"sm_percentage_direction_{row_id}")
        sm_percent_value = sm_col[2].text_input("Direction Percentage/Points", 1, key=f"sm_percent_value_{row_id}")
        sm_tgt_sl_price = sm_col[3].selectbox("Simple Moment Target/Stoploss Price ",
                                              ["SM_price", "Entry_price"], index=0,
                                              key=f"sm_tgt_sl_price_{row_id}")

        sm_entry_strike_type_toggle = sm_entry_strike_col[0].toggle("Strike Selection for Simple Moment Execution",
                                                                      key=f"sm_entry_strike_type_toggle_{row_id}")

        if sm_entry_strike_type_toggle:
            # Strike type selection
            sm_leg_strike_type = sm_entry_strike_col[1].selectbox(
                f"New Leg Strike Type",
                ["ATM", "ITM", "OTM", "PREMIUM"],
                index=0,
                key=f"sm_leg_strike_type_{row_id}")

            # Build dictionary based on strike_type
            sm_leg_data = {"strike_type": sm_leg_strike_type}

            if sm_leg_strike_type == "PREMIUM":
                sm_leg_premium_consideration = sm_entry_strike_col[2].selectbox(
                    "Premium Consideration:",
                    ["CLOSEST", "NEAREST"],
                    index=0,
                    key=f"sm_leg_premium_consideration_{row_id}"
                )
                sm_leg_premium_value = sm_entry_strike_col[3].number_input(
                    "Premium:",
                    min_value=0,
                    key=f"sm_leg_premium_{row_id}"
                )
                sm_leg_data["premium_consideration"] = sm_leg_premium_consideration
                sm_leg_data["premium"] = sm_leg_premium_value

            elif sm_leg_strike_type in ["ITM", "OTM"]:
                sm_leg_spread_value = sm_entry_strike_col[2].number_input(
                    "Spread:",
                    min_value=1,
                    key=f"sm_leg_spread_{row_id}"
                )
                sm_leg_data["spread"] = sm_leg_spread_value

    trailing_col = st.columns([0.4, 1, 1, 1])

    Trail_sl_toggle = trailing_col[0].toggle(label="Trail SL", key=f"leg_trailsl_toggle_{row_id}", disabled=all_legs_disable_condition or rsm_enabled or delta_adx_enabled)
    trail_sl_selected_option = trailing_col[1].selectbox(" ", ["Points", "Percentage"], key=f"call_trailsl_type_{row_id}",
                                             label_visibility="collapsed", disabled=not Trail_sl_toggle)

    trail_sl_text_value1 = trailing_col[2].number_input(" ", key=f"call_trailsl_value1_{row_id}", label_visibility="collapsed",
                                            disabled=not Trail_sl_toggle, step=10)
    trail_sl_text_value2 = trailing_col[3].number_input(" ", key=f"call_trailsl_value2_{row_id}", label_visibility="collapsed",
                                            disabled=not Trail_sl_toggle, step=10)

    filtered = set(legs_keys_session)

    lazy_leg_col = st.columns([1, 1])

    lazy_leg_next_leg_col0, lazy_leg_next_leg_col1, lazy_leg_tgt_col1, lazy_leg_tgt_col2 = st.columns([1, 1, 1, 1])
    _, _, lazy_leg_sl_col1, lazy_leg_sl_col2 = st.columns([1, 1, 1, 1])

    leg_hopping_count_next_leg = 0
    leg_hopping_count_tgt = 0
    leg_hopping_count_sl = 0
    with lazy_leg_col[0]:

        select_next_leg_to_be_executed = st.toggle(
            f"Selected Leg Execution After Leg Completion",
            key=f"select_next_leg_to_be_executed_{row_id}",
            disabled=all_legs_disable_condition or rsm_enabled, on_change=toggle_handler,
            args=(f"select_next_leg_to_be_executed_{row_id}", f"lazy_leg_execution_on_target_sl_{row_id}"))
        if select_next_leg_to_be_executed:
            next_lazy_leg_to_be_executed = lazy_leg_next_leg_col0.selectbox(
                "Next leg to Be Executed",
                options=filtered,
                index=0,
                key=f"next_lazy_leg_to_be_executed_{row_id}"
            )

            leg_hopping_count_next_leg = lazy_leg_next_leg_col1.text_input("Execution Counter For Next Leg", value=1000,
                                                                key=f"leg_hopping_count_next_leg_{row_id}")

    with lazy_leg_col[1]:
        lazy_leg_execution_on_target_sl = st.toggle(
            f"Selected Leg Execution on Target/SL",
            key=f"lazy_leg_execution_on_target_sl_{row_id}",
            disabled=all_legs_disable_condition or rsm_enabled, on_change=toggle_handler,
            args=(f"lazy_leg_execution_on_target_sl_{row_id}", f"select_next_leg_to_be_executed_{row_id}"))

        if lazy_leg_execution_on_target_sl:

            lazy_leg_tobe_executed_on_target = lazy_leg_tgt_col1.selectbox(
                "Target Leg",
                options=filtered,
                index=0,
                key=f"lazy_leg_tobe_executed_on_target_{row_id}"
            )
            leg_hopping_count_tgt = lazy_leg_tgt_col2.text_input("Execution Counter For Target", value=1000,
                                                                key=f"leg_hopping_count_tgt_{row_id}")

            lazy_leg_tobe_executed_on_sl = lazy_leg_sl_col1.selectbox(
                "SL Leg",
                options=filtered,
                index=0,
                key=f"lazy_leg_tobe_executed_on_sl_{row_id}"
            )

            leg_hopping_count_sl = lazy_leg_sl_col2.text_input("Execution Counter For SL", value=1000,
                                                                key=f"leg_hopping_count_sl_{row_id}")

    data["option_type"] = call_option_type_value
    data["strike_type"] = strike_options_box
    data["Spread"] = call_OTM_value
    data["atm_straddle_premium"] = atm_stradle_premium
    data["premium_consideration"] = leg_premium_consideration
    data["premium_value"] = premium_value

    data["entry_on"] = synthetic_or_spot

    data["hedges"] = hedges
    data["leg_expiry_selection"] = leg_expiry_selection

    data["position"] = call_position_value



    data["target_profit_toggle"] = target_profit_toggle
    data["target_profit_value"] = Target_profit_text_value


    data["stop_loss_toggle"] = stop_loss_toggle
    data["stop_loss_type"] = stop_loss_selected_option

    data["stop_loss_value"] = stop_loss_text_value
    data["Monday_stoploss"] = Monday_stoploss
    data["Tuesday_stoploss"] = Tuesday_stoploss
    data["Wednesday_stoploss"] = Wednesday_stoploss
    data["Thursday_stoploss"] = Thursday_stoploss
    data["Friday_stoploss"] = Friday_stoploss

    data["sm_toggle"] = sm_toggle
    data["sm_percentage_direction"] = sm_percentage_direction
    data["sm_percent_value"] = sm_percent_value
    data["sm_tgt_sl_price"] = sm_tgt_sl_price
    data["sm_leg_data"] = sm_leg_data

    data["range_breakout_toggle"] = range_breakout_toggle
    data["range_breakout_start"] = range_breakout_start
    data["range_breakout_threshold_time"] = range_breakout_threshold_time
    data["range_breakout_of"] = range_breakout_of
    data["underlying_asset"] = underlying_asset
    data["range_compare_section"] = range_compare_section


    data["rolling_straddle_toggle"] = rolling_straddle_toggle
    data["rolling_straddle_breach_on"] = rolling_straddle_breach_on
    data["rolling_straddle_consecutive_candles"] = rolling_straddle_consecutive_candles

    data["rolling_straddle_vwap_toggle"] = rolling_straddle_vwap_toggle
    data["rolling_straddle_vwap_breach_on"] = rolling_straddle_vwap_breach_on
    data["rolling_straddle_vwap_consecutive_candles"] = rolling_straddle_vwap_consecutive_candles

    data["re_entry_on_tgt_toggle"] = target_rentry_toggle
    data["re_entry_on_tgt_type"] = re_entry_on_tgt_selected_option


    data["re_entry_on_sl_toggle"] = sl_rentry_toggle
    data["re_entry_on_sl_type"] = re_entry_on_sl_selected_option


    data["total_sl_rentry"] = total_sl_rentry
    data["total_tgt_rentry"] = total_tgt_rentry

    data["trail_sl_toggle"] = Trail_sl_toggle
    data["trail_sl_type"] = trail_sl_selected_option
    data["trail_sl_value1"] = trail_sl_text_value1
    data["trail_sl_value2"] = trail_sl_text_value2

    data["vix_checker_toggle"] = vix_checker_toggle
    data["vix_operator"] = vix_operator
    data["vix_value"] = vix_value

    data['select_next_leg_to_be_executed'] = select_next_leg_to_be_executed
    if select_next_leg_to_be_executed:
        data['next_lazy_leg_to_be_executed'] = next_lazy_leg_to_be_executed

    
    data['leg_execution_on_target_sl'] = lazy_leg_execution_on_target_sl
    if lazy_leg_execution_on_target_sl:
        data['leg_tobe_executed_on_target'] = lazy_leg_tobe_executed_on_target
        data['leg_tobe_executed_on_sl'] = lazy_leg_tobe_executed_on_sl

    data['leg_hopping_count_next_leg'] = leg_hopping_count_next_leg
    data['leg_hopping_count_sl'] = leg_hopping_count_sl
    data['leg_hopping_count_tgt'] = leg_hopping_count_tgt

    if momentum_enabled:
        data['momentum_interval'] = interval_


    # Check if any component is active before returning the data
    if any(data.values()):
        return data

    st.write("---")


if "rows" not in st.session_state:
    st.session_state["rows"] = []

legsdata= {}
sub_legs_data = {}

if "legs_keys_session" not in st.session_state:
    st.session_state["legs_keys_session"] = ["None"]
legs_keys_session = st.session_state["legs_keys_session"]
if "None" not in legs_keys_session:
    legs_keys_session.append("None")


def add_row():
    element_id = uuid.uuid4()
    st.session_state["rows"].append(str(element_id))


def remove_row(row_id):
    st.session_state["rows"].remove(str(row_id))


# Initialize separate session state for lazy legs
if "lazy_rows" not in st.session_state:
    st.session_state["lazy_rows"] = []

def add_lazy_row():
    element_id = uuid.uuid4()
    st.session_state["lazy_rows"].append(str(element_id))

def remove_lazy_row(row_id):
    st.session_state["lazy_rows"].remove(str(row_id))


def toggle_handler(toggle1_key, toggle2_key):
    # Initialize toggles if not present
    if toggle1_key not in st.session_state:
        st.session_state[toggle1_key] = False
    if toggle2_key not in st.session_state:
        st.session_state[toggle2_key] = False

    # Enforce mutual exclusivity
    if st.session_state[toggle1_key]:
        st.session_state[toggle2_key] = False

with st.container():
    st.markdown("""
    <style>
        .stButton>button {
            width: 100%;
        }
    </style>
""", unsafe_allow_html=True)
    strategy_name, start_date, end_date, indicescol, lotscol, margin_bt, backtest_overrider_bt = st.columns(7)
    strategy = strategy_name.text_input("strategy name", key="strategy_name")
    start_date = start_date.date_input("Start Date", key="start_date")
    end_date = end_date.date_input("End Date", key="end_date")
    indices = indicescol.multiselect("Select index:", ["banknifty", "nifty", "finnifty", "bankex", "sensex"], key="select_index")
    lots = lotscol.number_input("Lots:", 1, key="lots")
    margin_type = margin_bt.selectbox("Margin Type:", ["hedged", "normal", "20%Hedge"], index=0,
                                            key="margin_type")
    backtest_overrider = backtest_overrider_bt.toggle("Modify Existing Backtest", key="backtest_overrider")

    if "expander_state" not in st.session_state:
        st.session_state.expander_state = False

    col1, col2 = st.columns([1, 1])
    with col2:
        st.subheader("Conditional settings")

        condition_type = "Rolling_Straddle_Spot_Movement_Tracker"
        rolling_straddle_percent_movement = "0"
        spot_percent_movement = "0"
        condition_threshold_time = "09:59:59"
        condition_modification_multiple = 1
        condition_checker_toggle = st.toggle("Condition Checker Toggle", key="condition_checker_toggle", on_change=toggle_handler,
            args=(f"condition_checker_toggle", f"overall_momentum"))

        all_legs_premium_checking_multiple = 0
        rolling_atm_premium_value = 0
        sl_val1 = 0
        sl_val2 = 0
        roll_on_point1 = 0
        roll_on_point2 = 0
        condition_cola = st.columns(5)

        one_time_adjustment = False
        all_position_square_off_at_sl = False
        maintain_price_difference_toggle = False
        adjustments_ce = 0
        adjustments_pe = 0
        conditional_sl_type_ce = "Percentage"
        conditional_sl_type_pe = "Percentage"
        sl_pe = 0
        sl_ce = 0
        pe_decay_points = 0
        ce_decay_points = 0

        rolling_straddle_percent_rsm = "0"
        spot_movement = "0"
        divisor_helper = "0"

        monitoring_type = "Static"
        monitoring_based_on = "Low"
        type_of_monitoring_based_on = "Low Till Entry Time"
        direction_side = "Low"
        breakout = "Upside"
        breakout_minutes = 1
        breakout_value = 1
        breakout_minutes_type = "Universal"

        delta_adx_adjustment_value = 'Adjustment_1'
        trail_sl_50 = False
        adx_take_profit_value = 0
        trail_sl_type = 'Value'
        adx_value = 0
        drop_comparison = 'Close'
        adx_compare = 0

        overall_momentum = False
        overall_momentum_type = "Percentage"
        overall_momentum_sl = 0
        momentum_legs_selection = {}
        lazy_leg_atm_threshold = ""
        premium_threshold_value = 0
        bullish_legs = set()
        bearish_legs = set()
        interval_ = 5

        overall_trail_sl_toggle = False
        take_profit_value = 0
        tp_trail_value = 0

        first_sma = 0
        second_sma = 0

        eod_on_consecutive_sl_toggle = False
        reexecute_main_orders_on_consecutive_hit = False
        consecutive_sl_counts = 0

        combined_sl = False
        pair_dict = {}
        combined_sl_percentage = 0




        v_day_simulation_legs = {}

        if condition_checker_toggle:

            condition_type = condition_cola[0].selectbox("Condition Type:", ["Rolling_Straddle_Spot_Movement_Tracker", "Rolling_ATM_Premium_Straddle", "Weekly_Positional_With_Adjustments", "RSM_Threshold", "Non_Correlation", 'Delta_ADX', "V_Day", "Momentum1", "SMA", "Striker"],
                                                         index=0,
                                                         key="condition_type")
            if condition_type == "Rolling_Straddle_Spot_Movement_Tracker":
                rolling_straddle_percent_movement = condition_cola[1].text_input("Rolling Straddle Movement Percentage",
                                                                                 key="rolling_straddle_percent_movement")
                spot_percent_movement = condition_cola[2].text_input("Spot Movement Percentage",
                                                                     key="spot_percent_movement")
                condition_threshold_time = condition_cola[3].text_input("Condition Threshold Time", placeholder="HH:MM:SS",
                                                                        key="condition_threshold_time")
                condition_modification_multiple = condition_cola[4].text_input("Spot Movement Multiple (Exit condition)",
                                                                     key="condition_modification_multiple",
                                                                               help=textwrap.dedent("""\
                                                                                                   If the movement of spot is above or below the spot movement multiple,
                                                                                                    it will close all the running position and orders and execute all orders again:

                                                                                                       • Example: given spot multiple is 5 and index spread is 50 so the movement of upper bound and lower bound is 250
                                                                                                       • Vary indices to indices 50/100
                                                                                                                       """),)

            elif condition_type == "Rolling_ATM_Premium_Straddle":
                all_legs_premium_checking_multiple = condition_cola[1].text_input(
                    "Minimum Strike Price Multiple",
                    key="all_legs_premium_checking_multiple")

                rolling_atm_premium_value = condition_cola[2].text_input(
                    "Base Premium",
                    key="rolling_atm_premium_value")


                with condition_cola[3]:
                    with st.container(border=True):
                        st.caption("#### 🔼 Upper Section")

                        roll_on_point1 = st.text_input("Spot Difference",
                                        help =f"Roll Points all legs if all legs combined Premium > {rolling_atm_premium_value}",
                                        key="roll_on_point1"
                        )

                        sl_val1 = st.text_input("SL Percentage",
                                        help = f"SL Value if all legs combined Premium > {rolling_atm_premium_value}",
                                        key="sl_val1"
                        )
                with condition_cola[4]:

                    with st.container(border=True):
                        st.caption("#### 🔽 Lower Section")
                        roll_on_point2 = st.text_input("Spot Difference",
                                        help =f"Roll Points all legs if all legs combined Premium < {rolling_atm_premium_value}",
                                        key="roll_on_point2"
                        )

                        sl_val2 = st.text_input("SL Percentage",
                                        help =f"SL Value if all legs combined Premium < {rolling_atm_premium_value}",
                                        key="sl_val2"
                        )

                # sl_val1 = condition_cola[3].text_input(
                #     f"SL Value if all legs combined Premium if > {rolling_atm_premium_value}",
                #     key="sl_val1")
                #
                # sl_val2 = condition_cola[3].text_input(
                #     f"SL Value if all legs combined Premium if < {rolling_atm_premium_value}",
                #     key="sl_val2")
                #
                # roll_on_point1 = condition_cola[4].text_input(
                #     f"Roll Points all legs if all legs combined Premium > {rolling_atm_premium_value}",
                #     key="roll_on_point1")
                #
                # roll_on_point2 = condition_cola[4].text_input(
                #     f"Roll Points all legs if all legs combined Premium < {rolling_atm_premium_value}",
                #     key="roll_on_point2")

            elif condition_type == "Weekly_Positional_With_Adjustments":
                one_time_adjustment = condition_cola[0].toggle("One Time Adjustment", key="one_time_adjustment", help="Per day only one time adjustment will be triggered.")
                all_position_square_off_at_sl = condition_cola[0].toggle("All Position Square Off at SL Hit", key="all_position_square_off_at_sl", help="Square off all position when SL hit of any position")
                maintain_price_difference_toggle = condition_cola[0].toggle("Maintain Price Difference", key="maintain_price_difference_toggle")

                with condition_cola[1]:
                    with st.container(border=True):
                        st.caption("#### 🔼 CE Section")

                        adjustments_ce = st.text_input("Adjustment",
                                        # help =f"Example: adjustment1, adjustment2, adjustment2.....",
                                        key="adjustments_ce"
                        )

                        conditional_sl_type_ce = st.selectbox("SL Type:",
                                                                     ["Percentage",
                                                                      "Points"],
                                                                     index=0,
                                                                     key="conditional_sl_type_ce")

                        sl_ce = st.text_input(f"SL {conditional_sl_type_ce}",
                                        # help = f"SL Value if all legs combined Premium > {rolling_atm_premium_value}",
                                        key="sl_ce"
                        )

                        ce_decay_points = st.text_input(f"Decay Points", 0,
                                              # help = f"SL Value if all legs combined Premium > {rolling_atm_premium_value}",
                                              key="ce_decay_points"
                                              )

                        # Validation logic
                        if adjustments_ce and sl_ce:
                            try:
                                # Convert to float
                                adjustment_values = [float(val.strip()) for val in adjustments_ce.split(",") if
                                                     val.strip()]
                                sl_value = float(sl_ce)

                                # Compare and show warning if any adjustment is greater than SL
                                for val in adjustment_values:
                                    if sl_value <= val:
                                        st.warning(f"⚠️ SL ({sl_value}) is less than adjustment value: {val}")
                                        break  # Warn only once

                            except ValueError:
                                st.error("❌ Please enter only numeric values in 'Adjustment' and 'SL'.")
                with condition_cola[3]:

                    with st.container(border=True):
                        st.caption("#### 🔽 PE Section")
                        adjustments_pe = st.text_input("Adjustment",
                                                       # help =f"Example: adjustment1, adjustment2, adjustment2.....",
                                                       key="adjustments_pe"
                                                       )

                        conditional_sl_type_pe = st.selectbox("SL Type:",
                                                                             ["Percentage",
                                                                              "Points"],
                                                                             index=0,
                                                                             key="conditional_sl_type_pe")

                        sl_pe = st.text_input(f"SL {conditional_sl_type_pe}",
                                              # help = f"SL Value if all legs combined Premium > {rolling_atm_premium_value}",
                                              key="sl_pe"
                                              )

                        pe_decay_points = st.text_input(f"Decay Points", 0,
                                                        # help = f"SL Value if all legs combined Premium > {rolling_atm_premium_value}",
                                                        key="pe_decay_points"
                                                        )

                        # Validation logic
                        if adjustments_pe and sl_pe:
                            try:
                                # Convert to float
                                adjustment_values = [float(val.strip()) for val in adjustments_pe.split(",") if
                                                     val.strip()]
                                sl_value = float(sl_pe)

                                # Compare and show warning if any adjustment is greater than SL
                                for val in adjustment_values:
                                    if sl_value <= val:
                                        st.warning(f"⚠️ SL ({sl_value}) is less than adjustment value: {val}")
                                        break  # Warn only once

                            except ValueError:
                                st.error("❌ Please enter only numeric values in 'Adjustment' and 'SL'.")

            elif condition_type == "RSM_Threshold":
                rolling_straddle_percent_rsm = condition_cola[1].text_input("Rolling Straddle Movement Percentage",
                                                                                 key="rolling_straddle_percent_rsm", help = 'movement greater than')
                spot_movement = condition_cola[2].text_input("Spot Movement Percentage",
                                                                                 key="spot_movement", help='movement less than')
                divisor_helper = condition_cola[3].text_input("Divisor",
                                                                                 key="divisor_helper", help='For new threshold -> straddle_movement / Divisor')

            elif condition_type == "Non_Correlation":
                monitoring_type = condition_cola[1].selectbox("Monitoring:",
                                                             ["Static",
                                                              "Dynamic"],
                                                             index=0,
                                                             key="monitoring_type")

                monitoring_based_on = condition_cola[1].selectbox("Monitoring Based On:",
                                                              ["Low",
                                                               "High",
                                                               "Start"],
                                                              index=0,
                                                              key="monitoring_based_on")

                direction_side = condition_cola[2].selectbox("Direction Side:",
                                                                  ["Upside",
                                                                   "Downside"],
                                                                  index=0,
                                                                  key="direction_side")

                if monitoring_based_on != "Start":
                    type_of_monitoring_based_on = condition_cola[2].selectbox(f"Type Of {monitoring_based_on}:",
                                                                  [f"{monitoring_based_on} Till Entry Time",
                                                                   f"Rolling {monitoring_based_on}"],
                                                                  index=0,
                                                                  key="type_of_monitoring_based_on")

                breakout = condition_cola[3].selectbox("Breakout:",
                                                             ["Percentage",
                                                              "Value"],
                                                             index=0,
                                                             key="breakout")

                breakout_value = condition_cola[3].text_input("",1,
                                                       key="breakout_value")

                breakout_minutes = condition_cola[4].number_input("Breakouts Minutes:",
                                                                  min_value=1,
                                                       key="breakout_minutes")

                breakout_minutes_type = condition_cola[4].selectbox("Minutes Type:",
                                                       ["Exact",
                                                        "Universal"],
                                                       index=0,
                                                       key="breakout_minutes_type")

            elif condition_type == 'Delta_ADX':
                delta_adx_adjustment_value = condition_cola[0].selectbox('Select Adjustment', ['Adjustment_1', 'Auto_ADX'], key = 'delta_adx_adjustment_value', help = 'adjustment1 (ltp on one side < entry price of other side * 0.5)-> First occurance->exit higher premium leg, second occurance->exit lower premium leg, do this alternatively :: AutoADX-> ADX above value-> 3min a range->range breaks up -> put short, range breaks down-> short call, ADX below user value -> short both legs')
                adx_value = condition_cola[1].number_input('ADX Value', key = 'adx_value', min_value=0.0, step = 0.01)
                
                if delta_adx_adjustment_value != 'Auto_ADX':
                    adx_compare = condition_cola[1].selectbox('ADX Compare type', ['above', 'below'], key = 'adx_compare', help = 'entries will be taken if index close is above or below adx')
                    drop_comparison = condition_cola[2].selectbox('Drop Comparison', ['Close', 'Low'], key = 'drop_comparison', help = 'Entry price of one option type is compared to close/low of other option type')
                
                trail_sl_50 = condition_cola[3].toggle("Enable Trailing SL (50%) of profit", key = 'trail_sl_50')
                if trail_sl_50:
                    with condition_cola[4]:
                        trail_sl_type = st.radio('Mtm', ['Value', 'Percentage'], key = 'trail_sl_percentage')
                        
                        adx_take_profit_value = st.number_input('Enter Profit', step = 0.1, min_value=0.0, key = 'adx_take_profit_value')
                
                pass

            elif condition_type == 'Momentum1':
                # interval_ = condition_cola[1].number_input('Candle Interval', key = 'momentum_interval', min_value=5, step = 5, help='Condition is check at close of this candle interval')
                # print(interval_)
                main_legs = {leg for leg in legs_keys_session if "." not in leg and "None" not in leg}
                bullish_legs = condition_cola[1].multiselect(
                    'Bullish Legs',
                    options=list(main_legs - set(bearish_legs) if 'bearish_legs' in locals() else main_legs),
                    key='momentum_bullish_legs'
                )

                # Multiselect for bearish legs
                bearish_legs = condition_cola[2].multiselect(
                    'Bearish Legs', options=list(main_legs - set(bullish_legs)),
                    key='momentum_bearish_legs'
                )


            elif condition_type == "V_Day":
                v_day_main_legs = {leg for leg in legs_keys_session if "." not in leg and "None" not in leg}

                v_day_simulation_legs = st.multiselect("Select Simulation Legs:", v_day_main_legs, help="Legs selected in this setting will be used for simulation only other legs will be used for main execution",
                                                                        key="v_day_simulation_legs")
                if len(v_day_simulation_legs) > 2:
                    v_day_simulation_legs = v_day_simulation_legs[:2]
                    st.warning("You can select a maximum of 2 legs only.")


            elif condition_type == "SMA":
                first_sma = condition_cola[1].text_input("First SMA Value",
                                                                                 key="first_sma")
                second_sma = condition_cola[2].text_input("Second SMA Value",
                                                                     key="second_sma")

        all_legs_disable_condition = (condition_checker_toggle and (condition_type == "Rolling_ATM_Premium_Straddle" or condition_type == "Weekly_Positional_With_Adjustments"))
        rsm_enabled = (condition_checker_toggle and (condition_type == "RSM_Threshold"))
        delta_adx_enabled = (condition_checker_toggle and (condition_type == "Delta_ADX"))
        momentum_enabled = (condition_checker_toggle and (condition_type == "Momentum1"))
        non_correlation_enabled = (condition_checker_toggle and (condition_type == "Non_Correlation"))

        timings_dict = {}
        st.markdown('<style> h2#entry-settings { font-size: 21px; text-align: center;padding:0px; } </style>',
                    unsafe_allow_html=True)
        st.subheader("Entry settings")

        with st.container():
            stcol1, temp, stcol2 , stcol3 = st.columns([1, 0.5, 1, 1])
        number_of_entries = stcol1.number_input("Number of Entries:", min_value=1, key="numberofentries")

        reentry_time_threshhold_toggle = stcol2.toggle(label="Re-entry Time Threshold Toggle", key='reentry_time_threshhold_toggle', help="If you turn toggle on you can change threshold time by default it takes 15:25:59")
        reentry_time_threshhold = stcol2.text_input("Time", value="15:28:59",
                                                    key="reentry_time_threshhold",
                                                    label_visibility="collapsed",
                                                    disabled=not reentry_time_threshhold_toggle)

        next_month_expiry_select = stcol3.toggle(label="Select next month expiry if weekly and monthly expiry are same", key='next_month_expiry_select')


        with st.container():
            col2_1, col2_2, _, col3_3 = st.columns([0.5, 0.5, 1, 0.8])
            for i in range(number_of_entries):
                entry_time = col2_1.text_input(f"Entry Time {i + 1}:", placeholder="HH:MM:SS",
                                               key=f"entry_time_{i + 1}")
                exit_time = col2_2.text_input(f"Exit Time {i + 1}:", placeholder="HH:MM:SS", key=f"exit_time_{i + 1}")

                timings_dict[f"Entry {i + 1}"] = {"entry_time": entry_time, "exit_time": exit_time}

            rolling_straddle_slice_time = col3_3.text_input(f"Rolling Straddle Start Time", placeholder="HH:MM:SS", key="rolling_straddle_slice_time", help="Rolling straddle will be calculated by your given time, for default calculation leave the field empty")


    with col1:
        st.subheader("Legs settings")

        square_off_col = st.columns(4)

        square_off_type = square_off_col[0].radio(
                "Square Off",
                options=["Partial", "Complete"],
                horizontal=True,
                disabled = True
        )
        premium_threshold_toggle = square_off_col[0].toggle("Premium Threshold", key="premium_threshold_toggle")
        if premium_threshold_toggle:
            premium_threshold_value = square_off_col[0].text_input(f"Premium Threshold Value", 0,
                                                                       key="premium_threshold_value"
                                                                       )
            
        

        # Trail SL checkbox
        trail_sl_to_breakeven = square_off_col[1].toggle("Trail SL to Break-even price", key = "trail_sl_to_breakeven",
             help="""
             - **All Legs**: If any leg’s SL is hit, trail the SL of all other legs to their respective entry prices.
             - **SL Legs**: If any leg’s SL is hit, only trail the SL of other legs, whose SL is specified, to their respective entry prices.
             - **Note**: The position that changed to breakeven will be checked next minute for stoploss checking.
             """)

        # All Legs / SL Legs selection
        trail_leg_scope = square_off_col[1].radio(
                "Trails Sl",
                key="trail_leg_scope",
                options=["All Legs", "SL Legs"],
                horizontal=True,
                label_visibility="collapsed",
            disabled= not trail_sl_to_breakeven
        )
        combined_sl = square_off_col[1].toggle("Apply Combined SL", key="combined_sl", help="The legs should be even")
        if combined_sl:
            pair_count = int(len(set(legs_keys_session))/2)
            filtered = set(legs_keys_session)
            with square_off_col[1]:
                combined_sl_percentage = st.text_input(f"Combined SL Percentage",
                                                            key="combined_sl_percentage"
                                                            )
                combine_col1, combine_col2 = st.columns(2)

                for i in range(pair_count):
                    pair_key = f"Pair_{i+1}"
                    combined_pair1 = combine_col1.selectbox(
                        "Pair Leg 1",
                        options=filtered,
                        key=f"pair_leg1_{i + 1}"
                    )

                    combined_pair2 = combine_col2.selectbox(
                        "Pair Leg 2",
                        options=filtered,
                        key=f"pair_leg2_{i + 1}"
                    )
                    pair_dict[pair_key] = [combined_pair1, combined_pair2]



        overall_momentum = square_off_col[2].toggle("Overall Momentum", key = "overall_momentum",
             help="""
             - **All Legs**: If selected legs combined premium goes below user given percentage value all legs will be executed,
             """ , on_change=toggle_handler,
            args=(f"overall_momentum", f"condition_checker_toggle"))
        if overall_momentum:
            overall_momentum_type = square_off_col[2].selectbox("Overall Momentum Type:", ["Percentage", "Points"], index=0,
                                                      key="overall_momentum_type")

            overall_momentum_sl = square_off_col[2].text_input(f"Overall Momentum {overall_momentum_type}",
                                                            key="overall_momentum_sl"
                                                            )

        trail_sl_breakeven_stoploss_type = square_off_col[3].selectbox("Break-even stoploss trigger type", ["High/Low", "Close"], index=0, key="trail_sl_breakeven_stoploss_type",
            help=textwrap.dedent("""\
                    If same strike is selected for position closing:
                    
                        • High/Low: High is selected for Sell side position, and Low is selected for Buy side position.
                        • Close: Candle close is used irrespective of Buy/Sell side.
                                        """),
            disabled= not trail_sl_to_breakeven
        )

        shift_lazy_leg_to_atm = square_off_col[3].toggle(label="Shift Lazy Leg to ATM Toggle",
                                                         key='shift_lazy_leg_to_atm')
        if shift_lazy_leg_to_atm:
            lazy_leg_atm_threshold = square_off_col[3].text_input("Lazy leg ATM shift threshold:",
                                                                  placeholder="HH:MM:SS", key="lazy_leg_atm_threshold")

        overall_trail_sl_toggle = square_off_col[0].toggle("Enable Take profit", key = 'overall_trail_sl_toggle', help = "Sets trailing stop once overall PnL reaches a user-defined level; exits all positions if PnL falls below specified value", disabled=trail_sl_50)
        if overall_trail_sl_toggle:
            with square_off_col[0]:
                # trail_sl_type = st.radio('', ['Value', 'Percentage'], key = 'trail_sl_percentage', help = 'When pnl > defined value, enable trail')

                take_profit_value = st.number_input('Enter Profit Value', step=0.1, min_value=0.0,
                                                    key='take_profit_value', disabled=trail_sl_50)
                tp_trail_value = st.number_input('Enter Trail Value', key='tp_trail_value', min_value=0.0, step=0.0,
                                                 disabled=trail_sl_50)

        eod_on_consecutive_sl_toggle = square_off_col[0].toggle("EOD on consecutive sl", key = 'eod_on_consecutive_sl_toggle')
        if eod_on_consecutive_sl_toggle:
            with square_off_col[0]:
                consecutive_sl_counts = st.number_input('Consecutive SL Counts', step=1, min_value=1,
                                                    key='consecutive_sl_counts')

        reexecute_main_orders_on_consecutive_hit = square_off_col[0].toggle("Reexecute Main Orders On Consecutive Sl",
                                                                key='reexecute_main_orders_on_consecutive_hit')

        if overall_momentum:
            main_legs = {leg for leg in legs_keys_session if "." not in leg and "None" not in leg}

            momentum_legs_selection = square_off_col[2].multiselect("Select Legs:", main_legs,
                                             key="momentum_legs_selection")

    # Ensure independent expander states
    if "expander_state_main" not in st.session_state:
        st.session_state.expander_state_main = False
    if "expander_state_lazy" not in st.session_state:
        st.session_state.expander_state_lazy = False





    legs_col1, legs_col2 = st.columns(2)
    with legs_col1.expander("**Main Legs Builder**", expanded=st.session_state.expander_state_main):
        call_con = st.container()
        with call_con:
            st.button("Add Main Leg", on_click=add_row)
            row_number = 0

            for row in st.session_state["rows"]:
                if delta_adx_enabled and row_number > 2:
                    st.error("⚠️ Delta ADX strategy currently supports only **two legs**.")
                    break

                row_number += 1
                legs_keys_session.append(f'leg_{row_number}')
                row_data = generate_row(row)
                legsdata[f"{row_number}"] = row_data


    with legs_col2.expander("**Lazy Legs Builder**", expanded=st.session_state.expander_state_lazy):
        st.button("Add Lazy Leg", on_click=add_lazy_row)

        lazy_leg_number = 0
        for row in st.session_state["lazy_rows"]:
            lazy_leg_number += 1
            legs_keys_session.append(f'leg_0.{lazy_leg_number}')
            sub_leg_toggle = True  # Always active since this is an independent leg
            sub_leg_data = generate_sub_row(
                row_id=row,
                sub_leg_toggle=sub_leg_toggle,
                sub_leg_number=lazy_leg_number
            )
            sub_legs_data[f"0_{lazy_leg_number}"] = sub_leg_data


            # Delete button for each lazy leg
            st.button("🗑️ Remove Lazy Leg", key=f"delete_lazy_button_{row}",
                      on_click=remove_lazy_row, args=[row])
    stoplosscol, temp = st.columns(2)




    with stoplosscol:
        stoplosscol.subheader("Price Selection Of Candles")
        Expiry_taketrade = 0

        spot_mode, EntryMode, StoplossCalMode, stoploss_compare_type, vix_candle_mode, stoplosshit = st.columns(6)
        spot_selection_mode = spot_mode.selectbox("Spot Selection Mode:", ["Open", "High", "Low", "Close"], index=3,
                                                  key="spot_selection_mode")
        selected_entry_mode = EntryMode.selectbox("Entry Mode:", ["Open", "High", "Low", "Close"], index=3,
                                                  key="entry_mode")
        selected_stoploss_cal_mode = StoplossCalMode.selectbox("Stop Loss Calculation Mode:",
                                                               ["Open", "High", "Low", "Close"], index=3,
                                                               key="stoploss_cal_mode")
        selected_stoploss_compare_type = stoploss_compare_type.selectbox("Stop Loss Compare Type:",
                                                                         ["Open", "High", "Low", "Close"], index=1,
                                                                         key="stoploss_compare_type")
        selected_vix_candle_mode = vix_candle_mode.selectbox("VIX Candle Mode:", ["Open", "High", "Low", "Close"],
                                                             index=3, key="vix_candle_mode")
        stoploss_hit = stoplosshit.selectbox("StopLoss Hit:", ["stoploss", "Open", "High", "Low", "Close"], index=0,
                                             key="stoploss_hit")

        select_expiry_bt, selext_txt, seleted_day_bt = st.columns(3)

        selected_expiry_toggle = select_expiry_bt.toggle(label="Select_Expires", key='select_expiry_toggle')

        selext_txt.write("Keep either select expiry true or keep Select days true")

        monthly_expiry = st.toggle(label="Select Monthly Expiry", key='monthly_expiry_toggle')



        if selected_expiry_toggle:
            Expiry_taketrade = st.multiselect("Expiry Take Trade:", ["Expiry", "1 Day Before Expiry", "2 Days Before Expiry",
                                                                     "3 Days Before Expiry", "4 Days Before Expiry", "Monthly Expiry"], key="expiry_taketrade")
            selected_days_toggle = seleted_day_bt.toggle(label="Select_Days", key='select_day_toggle', disabled = True)
        else:
            selected_days_toggle = seleted_day_bt.toggle(label="Select_Days", key='select_day_toggle')




        if selected_days_toggle:
            selected_days = st.multiselect("Select Days:", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], key="selected_days")


    mtm_target, mtm_stoploss = st.columns(2)

    with mtm_target:
        st.subheader("MTM Target Settings")

        select_main_mtm_target_type = "percentage"
        select_main_mtm_trg = 0



        select_main_mtm_target_toggle = st.toggle(label="MTM Target", key="main_mtm_target_toggle")

        if select_main_mtm_target_toggle:
            mtm_target_type, main_mtm_trg, mtm_reentry_tgt = st.columns([1, 1, 1])

            select_main_mtm_target_type = mtm_target_type.radio("MTM Target Type:", ["value", "percentage"], index=1,
                                                                key="mtm_target_type")
            select_main_mtm_trg = main_mtm_trg.text_input("Main MTM Target:", key="main_mtm_trg")


        st.subheader("Taxes and Costs Settings")
        br_select, brokerage = st.columns([0.5, 0.5])

        brokerage_type = br_select.selectbox("Brokerage Type:",
                                             ["Default", "Custom"], index=0, key="brokerage_type")
        if brokerage_type == "Custom":
            brokrage_val = brokerage.text_input('Brokerage Value', 0, key="brokerage")

        sp_select, slippage = st.columns([0.5, 0.5])
        slippage_type = sp_select.selectbox("Slippage Type:",
                                             ["Default", "Custom"], index=0, key="slippage_type")
        if slippage_type == "Custom":
            slippage_percentage = slippage.text_input('Slippage Percentage', 0, key="slippage")



    with mtm_stoploss:
        
        st.subheader("MTM Stoploss settings ")

        select_mtm_stoploss_type = "percentage"
        main_mtm_stoploss_value = 0
        main_mtm_stoploss_value_after_time_switch = 0
        mtm_stoploss_time_switch = ""


        

        mtm_stoploss_toggle = st.toggle(
            label="MTM Stoploss",
            key="mtm_stoploss_toggle",

        )
        if mtm_stoploss_toggle:
            mtm_stoploss_type, main_mtm_stoploss_before_switch_bt, main_mtm_stoploss_time_switch_bt, main_mtm_stoploss_after_switch_bt = st.columns(4)
            select_mtm_stoploss_type = mtm_stoploss_type.radio("MTM Stoploss Type:", ["value", "percentage"], index=1,
                                                            key="mtm_stoploss_type")

            main_mtm_stoploss_value = main_mtm_stoploss_before_switch_bt.text_input(
                "Main MTM Stoploss Before Time Switch:", key="main_mtm_stoploss", value=0)
            mtm_stoploss_time_switch = main_mtm_stoploss_time_switch_bt.text_input("MTM Stoploss Switch Time :",
                                                                                placeholder="HH:MM:SS",
                                                                                key="mtm_stoploss_time_switch",
                                                                                help="Leave empty if don't want to switch mtm stoploss")
            main_mtm_stoploss_value_after_time_switch = main_mtm_stoploss_after_switch_bt.text_input(
                "Main MTM Stoploss After Time Switch:", key="main_mtm_stoploss_value_after_time_switch")
            

        





end_col = st.columns(4)
max_terminals = end_col[0].text_input(f"No of terminals to open", 1, placeholder="1",key=f"terminals")
plotting_charts = end_col[1].toggle(label="Plot SD, PNL, Spot Graphs",
                                     key='plotting_charts')

st.markdown("""
        <style>
                .block-container {
                    padding-top: 1rem;
                    padding-bottom: 5rem;
                    padding-left: 5rem;
                    padding-right: 5rem;
                }
        </style>
        """, unsafe_allow_html=True)

st.markdown("<style>.css-1vbkxwb p {word-break: normal;margin-bottom: 0rem;}</style>", unsafe_allow_html=True)

st.markdown(
    """
    <style>
    .title {
        text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Display the title
st.markdown("<h1 class='title'>Entry Manager</h1>", unsafe_allow_html=True)

with st.container():
    st.markdown("""
    <style>
        .stButton>button {
            width: 100%;
        }
    </style>
""", unsafe_allow_html=True)
    em_start_timecol, em_end_timecol, em_indicescol, em_margincol = st.columns(4)
    em_indices = em_indicescol.multiselect("Select index:", ["banknifty", "nifty", "finnifty", "bankex", "sensex"],
                                           key="em_select_index")

    em_entry_time = em_start_timecol.text_input(f"Entry Time :", placeholder="HH:MM:SS", key=f"em_entry_time")
    em_exit_time = em_end_timecol.text_input(f"Exit Time :", placeholder="HH:MM:SS", key=f"em_exit_time")
    em_margin_type = em_margincol.selectbox("Margin Type:", ["Hedged Margin", "Margin"], index=0,
                                            key="em_margin")

with st.container():
    st.subheader("Layer3 Configration")

    layer3toggle = st.columns(1)

    layer3 = layer3toggle[0].toggle(label="Activate Layer3", key='layer3_toggle')
    european_criteria = False
    em_select_mtm_stoploss_type = False
    em_main_mtm_stoploss_value = 0
    em_select_main_mtm_target_type = False
    em_select_main_mtm_trg = 0
    daylight_saving_toggle = False
    daylight_delay_buffer = 0
    peak_toggle = False
    peak_threshold = ""
    timestamp = ""
    combined_sl_value = 0
    if layer3 == True:
        tm_stamp, sl_com = st.columns(2)

        timestamp = tm_stamp.text_input(f"Timestamp :", placeholder="HH:MM:SS", key=f"timestamp__")
        combined_sl_value = sl_com.number_input("Combined Overall Stoploss", key='combined_sll')

        european_criteria = st.toggle(label="European Criteria", key="european_criteria")
        entrymanager_mtm_target, entrymanager_mtm_stoploss = st.columns(2)

        with entrymanager_mtm_target:
            st.subheader("MTM Target Settings")
            em_select_main_mtm_target_type = "False"
            em_select_main_mtm_trg = 0

            em_select_main_mtm_target_toggle = st.toggle(label="MTM Target", key="em_main_mtm_target_toggle")

            if em_select_main_mtm_target_toggle:
                em_mtm_target_type, em_main_mtm_trg = st.columns([1, 1])

                em_select_main_mtm_target_type = em_mtm_target_type.radio("MTM Target Type:", ["value", "percentage", "calculated_points"],
                                                                          index=1, key="em_mtm_target_type")
                em_select_main_mtm_trg = em_main_mtm_trg.text_input("Main MTM Target:", key="em_main_mtm_trg")

        with entrymanager_mtm_stoploss:
            st.subheader("MTM Stoploss settings ")

            em_select_mtm_stoploss_type = "False"
            em_main_mtm_stoploss_value = 0

            em_mtm_stoploss_toggle = st.toggle(label="MTM Stoploss", key="em_mtm_stoploss_toggle")
            if em_mtm_stoploss_toggle:
                em_mtm_stoploss_type, em_main_mtm_stoploss, mtm_reentry_sl = st.columns(3)
                em_select_mtm_stoploss_type = em_mtm_stoploss_type.radio("MTM Stoploss Type:", ["value", "percentage", "calculated_points"],
                                                                         index=1, key="em_mtm_stoploss_type")
                em_main_mtm_stoploss_value = em_main_mtm_stoploss.text_input("Main MTM Stoploss:",
                                                                             key="em_main_mtm_stoploss")
                if european_criteria:
                    daylight_col, daylight_delay_col = st.columns(2)
                    daylight_saving_toggle = daylight_col.toggle(label="Daylight Saving Toggle", key="daylight_toggle")
                    if daylight_saving_toggle:
                        daylight_delay_buffer = daylight_delay_col.number_input(f"Daylight Delay Buffer", 0,
                                                                                key=f"daylight_delay")

                if not daylight_saving_toggle:
                    peak, peak_time = st.columns(2)
                    peak_toggle = peak.toggle(label="Peak Toggle", key="em_peak_toggle")
                    if peak_toggle:
                        peak_threshold = peak_time.text_input(f"Peak Time Threshold:", value="09:15:59",
                                                              key=f"em_peak_threshold")
                    else:
                        peak_threshold = peak_time.text_input(f"Peak Time Threshold:", placeholder="HH:MM:SS",
                                                              key=f"em_peak_threshold")

savebtn, loadbtn, Runbtn, savestatus = st.columns(4)
savebtn = savebtn.button("Save ", on_click=save_settings_to_csv, key="save_button")
loadbtn = loadbtn.button("Load ", on_click=apply_settings, key="load_button")
Runbtn = Runbtn.button("Run", on_click=run_csv_files, key="Run_button")

