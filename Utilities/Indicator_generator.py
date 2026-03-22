import os

import pandas as pd
import pandas_ta_classic as ta
import polars as pl

class IndicatorGenerator:
    def __init__(self, current_day_df, prev_day_df, strategy_save_dir):
        self.current_date = current_day_df["Timestamp"].iloc[-1].date()
        self.spot_df = pd.concat([prev_day_df, current_day_df])
        self.strategy_save_dir = strategy_save_dir

    def generate_indicators(self):
        spot_df = self._generate_rsi()
        spot_df = self._generate_adx(spot_df)
        try:
            spot_df = spot_df[spot_df['Timestamp'].dt.date == self.current_date]
        except:
            spot_df["Timestamp"] = pd.to_datetime(spot_df["Timestamp"])
            spot_df = spot_df[spot_df['Timestamp'].dt.date == self.current_date]

        spot_df = pl.from_pandas(spot_df)

        os.makedirs(os.path.join(self.strategy_save_dir, "indicators"), exist_ok=True)
        spot_df.write_csv(self.strategy_save_dir / "indicators" / f'Spot_{self.current_date.strftime("%Y_%m_%d")}.csv')
        return spot_df

    def _generate_rsi(self):
        self.spot_df.ta.rsi(length=14, append=True)
        self.spot_df['RSI'] = self.spot_df['RSI_14'].values
        return self.spot_df

    def _generate_adx(self, spot_df):
        adx_values = spot_df.ta.adx(length=14)
        spot_df['ADX'] = adx_values['ADX_14'].values
        return spot_df