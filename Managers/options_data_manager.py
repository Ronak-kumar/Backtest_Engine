from pathlib import Path
import sys
MAIN_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(MAIN_DIR))
import duckdb
import polars as pl

class DayOptionFrame:
    def __init__(self) -> None:
        self.intraday_options_df = {}
        self.month_option_data = None
        self.duck_db_con = None


    def _expiry_type_checker(self, expiry_type, current_timestamp):
        if expiry_type == "Weekly":
            expiry_cte = f"""
            SELECT MIN(expiry)
            FROM opt_data
            WHERE Timestamp >= TIMESTAMP '{current_timestamp:%Y-%m-%d} 09:15:00'
            AND Timestamp <  TIMESTAMP '{current_timestamp:%Y-%m-%d} 15:31:00'
            """

        elif expiry_type == "Next_Weekly":
            expiry_cte = f"""
            SELECT expiry
            FROM (
                SELECT DISTINCT expiry
                FROM opt_data
                WHERE Timestamp >= TIMESTAMP '{current_timestamp:%Y-%m-%d} 09:15:00'
                AND Timestamp <  TIMESTAMP '{current_timestamp:%Y-%m-%d} 15:31:00'
                ORDER BY expiry
                LIMIT 1 OFFSET 1
            )
            """

        elif expiry_type == "Monthly":
            expiry_cte = f"""
            SELECT MAX(expiry)
            FROM opt_data
            WHERE Timestamp >= TIMESTAMP '{current_timestamp:%Y-%m-%d} 09:15:00'
            AND Timestamp <  TIMESTAMP '{current_timestamp:%Y-%m-%d} 15:31:00'
            """

        
        return expiry_cte

    def _prepare_query(self, strike_price, expiry_type, current_timestamp):
        expiry_cte = self._expiry_type_checker(expiry_type, current_timestamp)

        query = f"""
                WITH min_expiry AS (
                    {expiry_cte}
                )
                SELECT *
                FROM opt_data
                WHERE Timestamp >= TIMESTAMP '{current_timestamp:%Y-%m-%d} 00:00:00'
                AND Timestamp <  TIMESTAMP '{current_timestamp:%Y-%m-%d} 15:31:00'
                AND expiry = (SELECT * FROM min_expiry)
                AND strike = {strike_price}
                """
        
        return query

    def _duckdb_initializer(self, current_timestamp, indices):
        parquet_filepath = MAIN_DIR / "local_data" / f'{indices.upper()}_Parquet_Data' / f'{indices.upper()}_{current_timestamp.strftime("%Y_%m")}.parquet'
        self.duck_db_con = duckdb.connect(database=":memory:")
        self.duck_db_con.execute(f"""
                CREATE VIEW opt_data AS
                SELECT *
                FROM read_parquet('{parquet_filepath}')
                """)

    def _get_data_from_duckdb(self, strike_price, expiry_type, current_timestamp, indices):
        if self.duck_db_con == None:
            self._duckdb_initializer(current_timestamp, indices)
        elif current_timestamp.strftime("%Y-%m-%d") not in self.duck_db_con.execute("SELECT DISTINCT DATE(Timestamp) FROM opt_data").fetchall():
            self.duck_db_con.close()
            self._duckdb_initializer(current_timestamp, indices)

        query = self._prepare_query(strike_price, expiry_type, current_timestamp)   
        df = self.duck_db_con.execute(query).df()
        df = pl.from_pandas(df)
        df = df.with_columns(pl.col(pl.FLOAT_DTYPES).round(2)).sort(['Timestamp'])
        self.intraday_options_df[expiry_type] = pl.concat(
                                                        [self.intraday_options_df[expiry_type], df],
                                                        how="vertical",
                                                        rechunk=False
                                                        ).sort(['Timestamp'])

    def data_handler(self, strike_price, expiry_type, current_timestamp, indices, ticker=None):

        options_df = self.intraday_options_df[expiry_type]

        ### Get date of certain ticker ###
        if ticker is not None:
            if options_df.height == 0 or ticker not in options_df['Ticker'].to_list():
                self._get_data_from_duckdb(strike_price, expiry_type, current_timestamp, indices)
            return self.intraday_options_df[expiry_type].filter(pl.col('Ticker') == ticker)


        if options_df.height == 0:
            self._get_data_from_duckdb(strike_price, expiry_type, current_timestamp, indices)
        elif strike_price not in options_df['Strike'].to_list():
            self._get_data_from_duckdb(strike_price, expiry_type, current_timestamp, indices)

        return self.intraday_options_df[expiry_type]

