import polars as pl
from pathlib import Path


class MissingDates:
    def __init__(self):
        self.missing_dates = {"Timestamp": [],
                         "Reason": []}
    def missing_dict_update(self, Timestamp, reson):
        self.missing_dates["Timestamp"].append(Timestamp)
        self.missing_dates["Reason"].append(reson)
    def file_creator(self, filepath):
        missing_df = pl.DataFrame({"date": self.missing_dates}, schema={"date": pl.Date})
        csv_path = Path(filepath) / "Missing_Dates.csv"
        if not csv_path.exists():
            missing_df.write_csv(csv_path)
        else:
            missing_df.write_csv(
                csv_path,
                mode="a",
                include_header=False
            )