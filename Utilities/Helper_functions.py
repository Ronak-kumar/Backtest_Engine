import pandas as pd
import yaml
from datetime import datetime, date
from functools import lru_cache
import copy
from pathlib import Path

MAIN_DIR = Path(__file__).resolve().parent.parent


class OrderSequenceMapper:
    def __init__(self):
        self.all_order_dict = {}
    def legid_mapping(self, main_order, lazy_legs_order):

        for index, lazy_leg in lazy_legs_order.items():
            lazy_legs_order[index]["unique_legid"] = index
            self.all_order_dict[index] = lazy_leg.copy()

        for key, value in main_order.items():
            main_order[key]["unique_legid"] = key
            self.all_order_dict[key] = value.copy()

        return main_order, lazy_legs_order


    def get_next_order(self, next_leg_tobe_executed_leg_id, main_leg_id):

        main_leg_id = main_leg_id.split("_")[1]
        next_leg_tobe_executed_leg_id = next_leg_tobe_executed_leg_id.replace(".", "_")
        next_order = self.all_order_dict.get(next_leg_tobe_executed_leg_id)
        if next_order is None:
            return None
        next_order["leg_id"] = main_leg_id
        return copy.deepcopy(next_order)

    def hopping_count_manager(self, unique_leg_id, hopping_type):
        if hopping_type != "":
            ### Changing Hopping Count ###
            self.all_order_dict[unique_leg_id][hopping_type] -= 1


class LotSize:
    LOT_SIZE_CONFIG_PATH = MAIN_DIR / 'settings' / 'lotsize_config.yaml'

    @staticmethod
    @lru_cache(maxsize=1)
    def _load_rules():
        with open(LotSize.LOT_SIZE_CONFIG_PATH, "r") as f:
            raw = yaml.safe_load(f)

        rules = {}
        for index, entries in raw.items():
            rules[index.lower()] = [
                {
                    "from": e["from"],
                    "to": e["to"] if e["to"] else None,
                    "size": int(e["size"])
                }
                for e in entries
            ]
        return rules

    @staticmethod
    def lotsize(trade_date: date, index: str) -> int:
        index = index.lower()
        rules = LotSize._load_rules()

        if index not in rules:
            raise ValueError(f"Unknown index: {index}")

        for r in rules[index]:
            if trade_date >= r["from"] and (r["to"] is None or trade_date <= r["to"]):
                return r["size"]

        raise ValueError(
            f"No lot size defined for {index} on {trade_date}"
        )


def get_expiry_days_offset(trading_days, expiry_dates_list):
    trading_day_index = {d: i for i, d in enumerate(trading_days)}
    expiry_dates = sorted(
        row[0]
        for row in expiry_dates_list
    )
    expiry_offset_map = {}
    trading_days_df = pd.DataFrame(trading_days, columns=["date"])
    expiry_dates = pd.DataFrame(expiry_dates, columns=["date"])
    for index, expiry in expiry_dates.iterrows():
        if index != 0:
            trading_days_before_expiry = trading_days_df[(trading_days_df["date"] <= expiry["date"]) & (trading_days_df["date"] > expiry_dates.loc[index-1].date)]
            trading_days_before_expiry.sort_values('date', ascending=False, inplace=True)
        else:
            trading_days_before_expiry = trading_days_df[(trading_days_df["date"] <= expiry["date"])]
            trading_days_before_expiry.sort_values('date', ascending=False, inplace=True)

        initial_offset = 0
        for date in trading_days_before_expiry["date"].tolist():
            expiry_offset_map[date] = initial_offset
            initial_offset -= 1
    return expiry_offset_map

