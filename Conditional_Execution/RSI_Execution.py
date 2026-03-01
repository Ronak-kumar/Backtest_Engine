import polars as pl

class RSIExecution:
    def __init__(self):
        self.rsi_execution = False
        self.rsi_value = 0

    def reset(self):
        self.rsi_execution = False
        self.rsi_value = 0

    def executor(self, spot_df, timestamp):
        rsi_value = spot_df.filter(pl.col('Timestamp') == timestamp).select('RSI_14').item()
        if rsi_value <= 30 or rsi_value >= 70:
            if self.rsi_value == 0:
                self.rsi_value = rsi_value
                return True
            else:
                if (rsi_value <= 30 and rsi_value < self.rsi_value) or (rsi_value >= 70 and rsi_value > self.rsi_value):
                    self.rsi_value = rsi_value
                    return True
        return False
    