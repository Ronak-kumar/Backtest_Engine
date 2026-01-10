from datetime import datetime as dt

class DayProcessor:
    def __init__(self, current_date_str: str, entry_para_dict: dict):

        # Day start time & end time
        self.entry_time = dt.strptime(f"{current_date_str}  {entry_para_dict['strategy_entry_time']}", "%Y-%m-%d %H:%M:%S")
        self.exit_time = dt.strptime(f"{current_date_str}  {entry_para_dict['strategy_exit_time']}", "%Y-%m-%d %H:%M:%S")

        # Trade dictionary
        self.TRADE_DICT = {"leg_id": [],
                'Timestamp': [],
                'TradingSymbol': [],
                'Instrument_type': [],
                "SD": [],
                'SellPrice': [],
                'LTP': [],
                'PnL': [],
                'stop_loss': [],
                'target_price': [],
                'strike': [],
                'Position_type': [],
                'Trailing': []}

        # Order book dictionary
        self.order_book = {'Timestamp': [],
                        'Ticker': [],
                        'Order_side': [],
                        'Price': [],
                        'Summary': []}

        # Closed position dictionary
        self.CLOSE_DICT = {'Timestamp': [],
                        'TradingSymbol': [],
                        'Instrument_type': [],
                        "SD": [],
                        'SellPrice': [],
                        'LTP': [],
                        'PnL': []}

        self.day_breaker = False
        self.entry_spot = None
        self.sd = None

        #### Flags for the Engine #####
        self.initial_entry = False
        self.overall_tp_activated = False