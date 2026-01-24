import polars as pl

class EODFileManager:
    def __init__(self, strategy_save_dir):
        self.strategy_save_dir = strategy_save_dir
        parquet_files = list(strategy_save_dir.rglob("*.parquet"))
        self.parquet_df = pl.concat(
            [pl.read_parquet(p) for p in parquet_files],
            how="diagonal",
            rechunk=True
        )

        if not self.parquet_df.shape[0]:
            raise ValueError("No parquet trade logs found")
        
    def realized_file_creator(self, indices: str) -> None:
        """Create realized PNL file for the day."""

        # Charges Chunk - Unrealized PnL
        charges_chunk_unrealized = (
                    self.parquet_df
                    .filter(pl.col("RowType") == "CHARGES")
                    .with_columns(
                        pl.col("Timestamp")
                        .dt.date()
                        .alias("TradeDate")
                    )
                    .group_by("TradeDate")
                    .agg(
                        pl.col("PnL").sum().alias("Unrealized PnL")
                    )
                )

        # Charges Chunk - Realized PnL
        charges_chunk = (
            self.parquet_df
            .filter(
                (pl.col("Final PnL").is_null() == False) & (pl.col("RowType") == 'CHARGES')
            )
        )

        charges_chunk = charges_chunk.with_columns(
            pl.col("Timestamp")
            .dt.date()
            .alias("TradeDate")
        )

        day_stats = (
            charges_chunk
            .sort("Timestamp")
            .group_by("TradeDate")
            .agg([
                pl.col("Qty").max().alias("Qty"),
                pl.col("Spot").first().alias("Spot"),
            ])
        )

        charges_chunk = charges_chunk.select(
            pl.col("Timestamp"),
            pl.col("Final PnL").cast(pl.Float64).alias("PnL"), 
            pl.col("TradeDate"),
        )


        # Join Day Stats Realized with Unrealized
        out_df = charges_chunk.join(
                                    charges_chunk_unrealized,
                                    on="TradeDate",
                                    how="left"
                                )

        out_df = out_df.join(
                                    day_stats,
                                    on="TradeDate",
                                    how="left"
                                )

        if indices.lower() in ["nifty", "banknifty", "finnifty"]:
            multiplier = .65
        else:
            multiplier = .85

        out_df = out_df.with_columns(
            pl.col('Spot') * pl.col('Qty').alias('Exposure'),
            (pl.col('Spot') * pl.col('Qty') * 0.15).alias('Margin'),
            (pl.col('Spot') * pl.col('Qty') * 0.10).alias('Hedged Margin'),
            )
        
        out_df = out_df.with_columns(
                        (pl.col('Hedged Margin') * multiplier).alias('20%Hedge')
        )

        out_df.write_csv(self.strategy_save_dir / "EOD_File.csv")

        return self.strategy_save_dir / "EOD_File.csv"


