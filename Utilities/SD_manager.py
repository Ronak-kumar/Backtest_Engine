import numpy as np

class SDManager:
    def __init__(self):
        self.flag = False

    def saved_values(self, ce_df, pe_df, spot_df, indice_base):
        spot = spot_df["Close"]
        combined_premium = ce_df["Close"] + pe_df["Close"]
        self.ce_strike = ce_df["Ticker"]
        self.pe_strike = pe_df["Ticker"]
        self.sd1_ub = spot + combined_premium
        self.sd1_lb = spot - combined_premium
        self.sd2_ub = spot + (combined_premium*2)
        self.sd2_lb = spot - (combined_premium*2)
        self.sd3_ub = spot + (combined_premium*3)
        self.sd3_lb = spot - (combined_premium*3)
        self.indice_base = indice_base

        sd_df = spot_df.to_frame().T
        sd_df["CE_Strike"] = self.ce_strike
        sd_df["PE_Strike"] = self.pe_strike
        sd_df["CE_Price"] = ce_df["Close"]
        sd_df["PE_Price"] = pe_df["Close"]
        sd_df["Combined_Price"] = combined_premium
        sd_df["-1sd"] = self.sd1_lb
        sd_df["+1sd"] = self.sd1_ub
        sd_df["-2sd"] = self.sd2_lb
        sd_df["+2sd"] = self.sd2_ub
        sd_df["-3sd"] = self.sd3_lb
        sd_df["+3sd"] = self.sd3_ub

        self.flag = True
        return sd_df


    def sd_range_calculation(self, sd_df):
        sd_df = sd_df.to_frame().T
        spot = sd_df["Close"].item()
        if not self.flag:
            sd_df["CE_Strike"] = ""
            sd_df["PE_Strike"] = ""
            sd_df["CE_Price"] = ""
            sd_df["PE_Price"] = ""
            sd_df["Combined_Price"] = ""
            sd_df["-1sd"] = ""
            sd_df["+1sd"] = ""
            sd_df["-2sd"] = ""
            sd_df["+2sd"] = ""
            sd_df["-3sd"] = ""
            sd_df["+3sd"] = ""
        else:
            sd_df["CE_Strike"] = self.ce_strike
            sd_df["PE_Strike"] = self.pe_strike
            sd_df["CE_Price"] = ""
            sd_df["PE_Price"] = ""
            sd_df["Combined_Price"] = ""
            sd_df["-1sd"] = self.sd1_lb
            sd_df["+1sd"] = self.sd1_ub
            sd_df["-2sd"] = self.sd2_lb
            sd_df["+2sd"] = self.sd2_ub
            sd_df["-3sd"] = self.sd3_lb
            sd_df["+3sd"] = self.sd3_ub

        return sd_df

    def sd_level(self, sd_df):
        if self.flag:
            if sd_df["Close"].item() < sd_df["+1sd"].item() and sd_df["Close"].item() > sd_df["-1sd"].item():
                sd_df["Sd_range"] = "Between -1sd and +1sd"
            elif sd_df["Close"].item() < sd_df["+2sd"].item() and sd_df["Close"].item() > sd_df["-2sd"].item():
                sd_df["Sd_range"] = "Between -2sd and +2sd"
            else:
                sd_df["Sd_range"] = "Between -3sd and +3sd"

            return sd_df
        else:
             return sd_df

    def entry_manager_sd(self, row):
        value = float(row['+1sd'])
        if np.isnan(value):
            return ""
        elif row['Close'] < row['+1sd'] and row['Close'] > row['-1sd']:
            return "Between -1sd and +1sd"
        elif row['Close'] < row['+2sd'] and row['Close'] > row['-2sd']:
            return "Between -2sd and +2sd"
        else:
            return "Between -3sd and +3sd"


