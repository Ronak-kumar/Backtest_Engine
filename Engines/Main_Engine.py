from pathlib import Path
import sys
from dateutil.relativedelta import relativedelta
import polars as pl
from datetime import datetime as dt
import pandas as pd


MAIN_DIR = Path(__file__).resolve().parent.parent
TRADING_DAYS_QUERY_NUM = 3
FULL_DATA_QUERY_NUM = 1
sys.path.append(str(MAIN_DIR))

from Utilities.parameter_parser import _load_engine_main_entry_parameters
from Utilities.parameter_parser import load_parameters_from_csv
from Utilities.Yaml_Loader import LoadYamlfile
from Utilities.Logger import Logger
from Utilities.missing_date_handler import MissingDates
from Utilities.clickhouse_connector import ClickHouse
from Utilities.query_template_loader import QueryTemplateLoader
from Utilities.Helper_functions import LotSize
from Utilities.Legs_generator import LegsHandler
from Utilities.drawdown_calculation import drawdown_cal
from Utilities.heat_map import heat_map
from Utilities.Day_Processor import DayProcessor
from Managers.options_data_manager import DayOptionFrame
from Database_manager.data_extractor import MonthlyParquetBuilder
from Managers.EOD_file_manager import EODFileManager
import time

start_time = time.time()
### Parameters Loading Section ###
# param_csv_file = sys.argv[1]
param_csv_file = r"D:\Development\Coding_Projects\market_project\old_backtest_engine\strategies\algo_backtest_re1_full1_without_hedge2_2025\entry_parameter_0125_0126_0916_1530_nifty.csv".replace("\\", "/")
param_csv_file_dir = ("/").join(param_csv_file.split("/")[:-1])
entry_para_dict = _load_engine_main_entry_parameters(load_parameters_from_csv(param_csv_file))

directional_processing = False
consecutive_sl_counts = 2

### Logger Configration ###
log_class = Logger(log_path=MAIN_DIR/'logs')
logger = log_class.setup_logger(name='Debug', log_file=f"{entry_para_dict['strategy_name']}_{entry_para_dict['indices']}.log")

### YAML Loading ###
config = LoadYamlfile(file_path=MAIN_DIR / 'settings' / 'config.yaml')

###### Index Parameters #######
entry_para_dict['base_symbol_spread'] = config.get('symbol_spread_mapping', entry_para_dict['indices'].lower())
entry_para_dict['symbol_lotsize'] = config.get('symbol_lotsize_mapping', entry_para_dict['indices'].lower())

### Setting Result Save Path ###
result_save_dir = MAIN_DIR / "results" /  entry_para_dict['indices'].lower()
result_save_dir.mkdir(parents=True, exist_ok=True)

####### Getting Holiday and Event files ######
holidays_path = MAIN_DIR / 'csv' / config.get('csv_files_configration', 'holidays_csv_filename')
events_path = MAIN_DIR / 'csv' / config.get('csv_files_configration','event_csv_filename')

###### Chargers static value #######
charges_params_dict = config.get('charges_configration')
charges_params_dict['gst_percentage'] = charges_params_dict["gst_percentage"]/100
charges_params_dict['slippage_percentage'] = charges_params_dict["slippage_percentage"]/100


####### Getting Holiday and Event files ######
holidays_df = pl.read_csv(holidays_path)
holidays_df = holidays_df = holidays_df.with_columns(pl.col("DATE").str.to_date("%d-%b-%y", strict=False).alias("DATE"))
events_df = pl.read_csv(events_path, columns=["Date", "Event"]).with_columns(pl.col("Date").str.to_datetime("%d-%m-%Y").alias("Date"))


### Missing dates class initialization ###
miss_con = MissingDates()

### Clickhouse object and client initialization ###
clickhouse_details = config.get('clickhouse_database_params')
clickhouse_obj = ClickHouse(host=clickhouse_details['host'],
                            username=clickhouse_details['username'],
                            password=clickhouse_details['password'],
                            database_name=clickhouse_details['database_name'],
                            port=clickhouse_details['port'],
                            options_table=clickhouse_details['option_table'],
                            spot_table=clickhouse_details['spot_table'])
clickhouse_client = clickhouse_obj.get_client()


#### initializing data extractor class ###
query_loader = QueryTemplateLoader()




##### loading all the trading dates #####
db_initial_extraction_date = dt.strptime(entry_para_dict['start_date'], '%d/%m/%Y').strftime('%Y-%m-%d')
db_end_extraction_date = dt.strptime(entry_para_dict['end_date'], '%d/%m/%Y').strftime('%Y-%m-%d')
query = query_loader.get_template(TRADING_DAYS_QUERY_NUM, table_name=clickhouse_details['spot_table'])
        
parameters = {
    "symbol": entry_para_dict['indices'].upper()+"50" if entry_para_dict['indices'] == "nifty" else entry_para_dict['indices'].upper(),
    "start_date": db_initial_extraction_date,
    "end_date": db_end_extraction_date
}
trading_days = [row[0] for row in clickhouse_client.query(query, parameters=parameters).result_rows]
days_to_trade = []

#### Loading full spot df ####
query = query_loader.get_template(FULL_DATA_QUERY_NUM, table_name=clickhouse_details['spot_table'])
spot_arrow = clickhouse_client.query_arrow(query, parameters=parameters)
full_spot_df = pl.from_arrow(spot_arrow)
if 'Timestamp' in full_spot_df.columns:
    full_spot_df = full_spot_df.with_columns(pl.from_epoch("Timestamp", time_unit="s"))
float_cols = [col for col, dtype in zip(full_spot_df.columns, full_spot_df.dtypes) if dtype in (pl.Float32, pl.Float64)]
full_spot_df = full_spot_df.with_columns(pl.col(float_cols).cast(pl.Float64).round(2))



### Querying VIX data from database ###
parameters['symbol'] = "VIX"
vix_arrow = clickhouse_client.query_arrow(query, parameters=parameters)
full_vix_df = pl.from_arrow(vix_arrow)
if 'Timestamp' in full_vix_df.columns:
    full_vix_df = full_vix_df.with_columns(pl.from_epoch("Timestamp", time_unit="s"))
float_cols = [col for col, dtype in zip(full_vix_df.columns, full_vix_df.dtypes) if dtype in (pl.Float32, pl.Float64)]
full_vix_df = full_vix_df.with_columns(pl.col(float_cols).cast(pl.Float64).round(2))



# Define minimum allowed start dates for each index
min_start_dates = {
    "banknifty": "01/11/2016",
    "nifty": "01/03/2019",
    "finnifty": "01/01/2023",
    "sensex": "01/05/2023",
    "bankex": "01/11/2023"
}

# Convert input dates to datetime objects
start_dt = dt.strptime(entry_para_dict['start_date'], "%d/%m/%Y")
end_date = dt.strptime(entry_para_dict['end_date'], "%d/%m/%Y")

# Get minimum date for the index if defined
min_date_str = min_start_dates.get(entry_para_dict['indices'].lower())
if min_date_str:
    min_dt = dt.strptime(min_date_str, "%d/%m/%Y")
    if start_dt < min_dt:
        start_dt = min_dt

start_date = start_dt

### Querying spot data from database ###
prev_dates_to_fetch = dt.strptime(db_initial_extraction_date, "%Y-%m-%d") - relativedelta(days=5)
prev_dates_to_fetch_str = dt.strftime(prev_dates_to_fetch, "%Y-%m-%d")
query = query_loader.get_template(FULL_DATA_QUERY_NUM, table_name=clickhouse_details['spot_table'])
parameters = {
            "symbol": entry_para_dict['indices'].upper()+"50" if entry_para_dict['indices'] == "nifty" else entry_para_dict['indices'].upper(),
            "start_date": prev_dates_to_fetch_str,
            "end_date": db_initial_extraction_date
        }


prev_spot_required_data = clickhouse_client.query_df(query, parameters=parameters)
prev_spot_required_data = prev_spot_required_data[prev_spot_required_data['Timestamp'].dt.date != dt.strptime(db_initial_extraction_date, "%Y-%m-%d").date()] = prev_spot_required_data[prev_spot_required_data['Timestamp'].dt.date != dt.strptime(db_initial_extraction_date, "%Y-%m-%d").date()]
prev_day_close = prev_spot_required_data['Close'].iloc[-1]

## Class which handles generated results ###
legs_handler_con = LegsHandler()

### DuckDB initializations ###
day_option_frame_con = DayOptionFrame()


for current_date in trading_days:
    # storing date both in str and datetime fi
    current_date_str = dt.strftime(current_date, "%Y-%m-%d")
    print("Processing date: ", current_date_str)

    # Create builder instance
    builder = MonthlyParquetBuilder(
        clickhouse_client=clickhouse_client,
        clickhouse_object=clickhouse_obj
    )
    ### creating monthly parquet cached files ###
    builder.export_monthly(symbol=entry_para_dict['indices'].upper(), year=current_date.year, month=current_date.month)

    spot_df = full_spot_df.filter(pl.col("Timestamp").dt.date() == current_date)
    spot_df = spot_df.filter((pl.col("Timestamp").dt.time() >= dt.strptime('09:15:00', "%H:%M:%S").time()) & (
                pl.col("Timestamp").dt.time() <= dt.strptime('15:30:00', "%H:%M:%S").time()))
    vix_df = full_vix_df.filter(pl.col("Timestamp").dt.date() == current_date)
    vix_df = vix_df.filter((pl.col("Timestamp").dt.time() >= dt.strptime('09:15:00', "%H:%M:%S").time()) & (
                pl.col("Timestamp").dt.time() <= dt.strptime('15:30:00', "%H:%M:%S").time()))

    ########## lot Changes on the given day and nearest expiry calculation ###############
    entry_para_dict['symbol_lotsize'] = LotSize.lotsize(current_date, entry_para_dict['indices'])
    
    if current_date.strftime("%A") == "Sunday" or current_date.strftime("%A") == "Saturday":
        miss_con.missing_dict_update(current_date, f"Saturday/Sunday Occured")
        continue


    ####### Breaking Day if Holiday Occur #######
    if not holidays_df.filter(pl.col("DATE") == current_date).is_empty():
        logger.info(f"{current_date} Holiday happened no trading day")
        miss_con.missing_dict_update(current_date, "Holiday, no trading day")
        day_breaker = True

    ### Initilizing day processor for each day ###
    day_processor_con = DayProcessor(current_date_str, entry_para_dict, day_option_frame_con)

    # Generate legs from CSV files using LegsHandler
    # Smart reload: Only reloads if weekday-specific stoploss is present, otherwise uses cached data
    orders, lazy_leg_dict, option_types, expiry_types, synthetic_checking = legs_handler_con.legs_generator(
        param_csv_file_dir, 
        current_date=current_date)
    
    ### Saving Directory Initializer ###
    strategy_save_dir = result_save_dir / entry_para_dict['strategy_name'] / f"legs{legs_handler_con.total_orders}_{start_date.date().strftime('%m_%Y')}_{end_date.date().strftime('%m_%Y')}_{day_processor_con.entry_time.time().strftime('%H%M')}_{day_processor_con.exit_time.time().strftime('%H%M')}"
    day_processor_con.strategy_save_dir = strategy_save_dir
    day_processor_con.orders = orders
    day_processor_con.lazy_leg_dict = lazy_leg_dict
    day_processor_con.option_types = option_types
    day_processor_con.expiry_types = expiry_types

    if synthetic_checking:
        logger.info(f"Rolling Straddle file not available for indice {entry_para_dict['indices']} on Timestamp {current_date}")
        miss_con.missing_dict_update(current_date,
                                     f"Rolling Straddle file not available for indice {entry_para_dict['indices']} on Timestamp {current_date}")
        continue
    else:
        synthetic_df = pd.DataFrame()

    ####### Saving Occured Event ########
    event = "No Event"

    day_processor_con.options_frame_initilizer()

    day_processor_con.process_day(spot_df, vix_df, prev_day_close, charges_params_dict, logger, synthetic_df)


    # Update prev_day_close for next iteration
    # if not spot_df.is_empty():
    #     prev_day_close = spot_df.sort("Timestamp", reverse=True)['Close'][0]

# End of Backtest Engine Main File
EODFileManager_con = EODFileManager(strategy_save_dir=strategy_save_dir)
eod_file_path = EODFileManager_con.realized_file_creator(indices=entry_para_dict['indices'])
drawdown_cal(path=eod_file_path)
heat_map(filepath=eod_file_path, indices=entry_para_dict['indices'])
print("Total Execution Time: %s seconds" % (time.time() - start_time))



