import polars as pl

class ResultHolder:
    def __init__(self):
        self.day_pnl_df = []
        self.day_end_realized_pnl_df = []
        self.day_end_unrealized_pnl_df = []
        self.day_margin_df = []
        self.order_book_df = []
        self.eod_trade_logs_list = []

        self.strategy_save_dir = None

    def strategy_save_path_initializer(self, result_save, strategy_name, total_orders, start_date, end_date, entry_time, exit_time):
        if self.strategy_save_dir is None:
            self.strategy_save_dir = result_save / strategy_name / f"legs{total_orders}_{start_date.date().strftime('%m_%Y')}_{end_date.date().strftime('%m_%Y')}_{entry_time.time().strftime('%H%M')}_{exit_time.time().strftime('%H%M')}"

class IntradayResultHolder:
    def __init__(self):
        # Initializing day values and Dataframe
        df = []
        temp_df = pl.DataFrame()
        day_pnl_var = 0
        sd_df = []

