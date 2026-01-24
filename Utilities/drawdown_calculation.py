import pandas as pd
import warnings

warnings.filterwarnings("ignore")

def drawdown_cal(path, margin_type="hedged"):
    full_path = path 
    df = pd.read_csv(full_path)

    df['Timestamp'] = pd.to_datetime(df['Timestamp'])

    if margin_type == "hedged":
        df["Equity Return"] = (df["PnL"] / df["Hedged Margin"]) * 100
    elif margin_type == "normal":
        df["Equity Return"] = (df["PnL"] / df["Margin"]) * 100

    elif margin_type == "20%Hedge":
        df["Equity Return"] = (df["PnL"] / df["20%Hedge"]) * 100

    df["Equity Curve"] = 100
    df["Max Curve"] = 0

    for index, data in df.iterrows():
        df["Equity Curve"].iloc[index] = df["Equity Return"].iloc[index] + df["Equity Curve"].iloc[index - 1]
        df["Max Curve"].iloc[index] = max(df["Equity Curve"].iloc[index], df["Max Curve"].iloc[index - 1])

    df["Drawdown"] = df["Max Curve"] - df["Equity Curve"]


    df["Hedged Margin"] = df["Hedged Margin"].apply(lambda x: round(x, 2))
    df["PnL"] = df["PnL"].apply(lambda x: round(x, 2))
    df["Equity Return"] = df["Equity Return"].apply(lambda x: round(x, 2))
    df["Equity Curve"] = df["Equity Curve"].apply(lambda x: round(x, 2))
    df["Max Curve"] = df["Max Curve"].apply(lambda x: round(x, 2))
    df["Drawdown"] = df["Drawdown"].apply(lambda x: round(x, 2))

    df.to_csv(full_path, index=False)


