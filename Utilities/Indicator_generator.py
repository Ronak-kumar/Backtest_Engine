import pandas as pd
import pandas_ta_classic as ta
import polars as pl

class IndicatorGenerator:
    def __init__(self, current_day_df, prev_day_df):
        self.current_date = current_day_df["Timestamp"].iloc[-1].date()
        self.spot_df = pd.concat([prev_day_df, current_day_df])

    def generate_indicators(self):
        spot_df = self._generate_rsi()
        spot_df = pl.from_pandas(spot_df)
        return spot_df

    def _generate_rsi(self):
        self.spot_df.ta.rsi(length=14, append=True)
        self.spot_df['RSI'] = self.spot_df['RSI_14'].values
        self.spot_df = self.spot_df[self.spot_df['Timestamp'].dt.date == self.current_date]
        return self.spot_df