"""
Data Extractor Module

This module provides functionality to extract options data from ClickHouse
and export it to optimized Parquet files for DuckDB consumption.

Classes:
    MonthlyParquetBuilder: Handles monthly data extraction and caching
"""

import time
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import os
import sys
import calendar
import json

# Import base path of the project
base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_path)

from Utilities.Yaml_Loader import LoadYamlfile
from Utilities.clickhouse_params_holder import ClickhouseConnector
from Utilities.query_template_loader import QueryTemplateLoader


# Constants
DEFAULT_OUTPUT_DIR = '/local_data'
QUERY_TEMPLATE_BASIC = 1
QUERY_TEMPLATE_METADATA = 15
PARQUET_COMPRESSION = 'zstd'
PARQUET_COMPRESSION_LEVEL = 3
PARQUET_ROW_GROUP_SIZE = 100000


class MonthlyParquetBuilder:
    """
    Creates optimally partitioned Parquet files for DuckDB from ClickHouse data.
    
    Features:
    - Automatic metadata checking to avoid redundant queries
    - Optimized data types for storage efficiency
    - Caching mechanism with metadata tracking
    - Support for monthly data extraction
    
    Attributes:
        clickhouse_object: ClickhouseConnector instance
        ch_client: ClickHouse client connection
        output_dir: Base output directory for parquet files
        query_loader: QueryTemplateLoader instance for SQL queries
    """
    
    def __init__(
        self,
        clickhouse_client: Any,
        clickhouse_object: ClickhouseConnector,
        output_dir: str = DEFAULT_OUTPUT_DIR,
        query_loader: Optional[QueryTemplateLoader] = None
    ):
        """
        Initialize MonthlyParquetBuilder.
        
        Args:
            clickhouse_client: ClickHouse client connection
            clickhouse_object: ClickhouseConnector instance with table names
            output_dir: Relative output directory (will be joined with base_path)
            query_loader: Optional QueryTemplateLoader instance
        """
        self.clickhouse_object = clickhouse_object
        self.ch_client = clickhouse_client
        self.output_dir = Path(base_path) / output_dir.lstrip('/')
        self.query_loader = query_loader or QueryTemplateLoader()
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_metadata_path(self, symbol: str, end_date: str) -> Path:
        """
        Get the path for metadata JSON file.
        
        Args:
            symbol: Symbol name (e.g., 'NIFTY')
            end_date: End date in format 'YYYY-MM-DD'
            
        Returns:
            Path object for metadata file
        """
        month_key = end_date.replace('-', '_')[:-3]  # YYYY_MM
        meta_dir = self.output_dir / f"{symbol}_Meta_Data"
        return meta_dir / f"{symbol}_{month_key}.json"
    
    def _get_parquet_path(self, symbol: str, end_date: str) -> Path:
        """
        Get the path for parquet file.
        
        Args:
            symbol: Symbol name
            end_date: End date in format 'YYYY-MM-DD'
            
        Returns:
            Path object for parquet file
        """
        month_key = end_date.replace('-', '_')[:-3]  # YYYY_MM
        parquet_dir = self.output_dir / f"{symbol}_Parquet_Data"
        return parquet_dir / f"{symbol}_{month_key}.parquet"
    
    def clickhouse_metadata(self, start_date: str, end_date: str, symbol: str) -> Dict[str, Any]:
        """
        Fetch metadata from ClickHouse for the given date range and symbol.
        
        Args:
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            symbol: Symbol name
            
        Returns:
            Dictionary with row_count, month_last_date, and column_count
        """
        query = self.query_loader.get_template(
            QUERY_TEMPLATE_METADATA,
            table_name=self.clickhouse_object.clickhouse_options_table_name
        )
        
        parameters = {
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date
        }
        
        result = self.ch_client.query_df(query, parameters=parameters)
        
        return {
            'row_count': int(result['row_count'].iloc[0]),
            'month_last_date': str(result['last_update'].iloc[0]),
            'column_count': int(result['column_count'].iloc[0])
        }
    
    def local_metadata(self, symbol: str, end_date: str) -> Dict[str, int]:
        """
        Load local metadata from JSON file if it exists.
        
        Args:
            symbol: Symbol name
            end_date: End date in 'YYYY-MM-DD' format
            
        Returns:
            Dictionary with column_count and row_count, or defaults if file doesn't exist
        """
        meta_data_path = self._get_metadata_path(symbol, end_date)
        
        if meta_data_path.exists():
            try:
                with open(meta_data_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not read metadata file {meta_data_path}: {e}")
        
        return {"column_count": 0, "row_count": 0}
    
    def _create_metadata(self, metadata: Dict[str, Any], symbol: str, end_date: str) -> None:
        """
        Save metadata to JSON file.
        
        Args:
            metadata: Metadata dictionary to save
            symbol: Symbol name
            end_date: End date in 'YYYY-MM-DD' format
        """
        meta_data_path = self._get_metadata_path(symbol, end_date)
        meta_data_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Add timestamp to metadata
        metadata["meta_file_last_update"] = datetime.now().isoformat()
        
        try:
            with open(meta_data_path, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
        except IOError as e:
            print(f"Error: Could not write metadata file {meta_data_path}: {e}")
    
    def _needs_regeneration(self, start_date: str, end_date: str, symbol: str) -> bool:
        """
        Check if data needs to be regenerated by comparing ClickHouse and local metadata.
        
        Args:
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            symbol: Symbol name
            
        Returns:
            True if data needs regeneration, False if cached data is valid
        """
        try:
            clickhouse_meta = self.clickhouse_metadata(start_date, end_date, symbol)
            local_meta = self.local_metadata(symbol, end_date)
            
            # Check if row count and column count match
            if (clickhouse_meta["row_count"] == local_meta.get("row_count", 0) and
                clickhouse_meta["column_count"] == local_meta.get("column_count", 0)):
                return False  # Data is up to date
            
            return True  # Data needs regeneration
        except Exception as e:
            print(f"Warning: Error checking metadata, will regenerate: {e}")
            return True  # On error, regenerate to be safe
    
    def _optimize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Optimize DataFrame data types for storage efficiency.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Optimized DataFrame with efficient data types
        """
        # Convert Timestamp to datetime if present
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='s')
        
        # Convert Expiry to datetime (keep as datetime64 for Parquet compatibility)
        if 'Expiry' in df.columns:
            df['Expiry'] = pd.to_datetime(df['Expiry'].astype('int32'), unit='D')
        
        # Convert Instrument_type to categorical (saves ~90% space)
        if 'Instrument_type' in df.columns:
            df['Instrument_type'] = (
                df['Instrument_type']
                .astype(str)
                .replace({'1': 'CE', '2': 'PE'})
                .astype('category')
            )
        
        # Optimize numeric types
        if 'Strike' in df.columns:
            df['Strike'] = df['Strike'].astype('float32')
        
        # Convert float64 columns to float32 and round to 2 decimals
        float_cols = df.select_dtypes(include=["float", "float64"]).columns
        for col in float_cols:
            df[col] = df[col].astype('float32').round(2)
        
        return df
    
    def _query_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Query data from ClickHouse and return as optimized DataFrame.
        
        Args:
            symbol: Symbol name
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            
        Returns:
            Optimized pandas DataFrame
        """
        query_start_time = time.time()
        
        query = self.query_loader.get_template(
            QUERY_TEMPLATE_BASIC,
            table_name=self.clickhouse_object.clickhouse_options_table_name
        )
        
        parameters = {
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date
        }
        
        # Query with Arrow format for better performance
        table = self.ch_client.query_arrow(query, parameters=parameters)
        print(f"Query time: {time.time() - query_start_time:.2f}s")
        
        # Convert to pandas with Arrow types
        df_preprocess_start_time = time.time()
        df = table.to_pandas(types_mapper=pd.ArrowDtype)
        
        # Optimize DataFrame
        df = self._optimize_dataframe(df)
        
        # Set Timestamp as index for efficient storage
        if 'Timestamp' in df.columns:
            df.set_index("Timestamp", inplace=True)
        
        print(f"Preprocessing time: {time.time() - df_preprocess_start_time:.2f}s")
        
        return df
    
    def _save_parquet(self, df: pd.DataFrame, symbol: str, end_date: str) -> Path:
        """
        Save DataFrame to optimized Parquet file.
        
        Args:
            df: DataFrame to save
            symbol: Symbol name
            end_date: End date in 'YYYY-MM-DD' format
            
        Returns:
            Path to saved parquet file
        """
        parquet_file = self._get_parquet_path(symbol, end_date)
        parquet_file.parent.mkdir(parents=True, exist_ok=True)
        
        df.to_parquet(
            parquet_file,
            engine='pyarrow',
            compression=PARQUET_COMPRESSION,
            compression_level=PARQUET_COMPRESSION_LEVEL,
            row_group_size=PARQUET_ROW_GROUP_SIZE,
            use_dictionary=True,
            write_statistics=True
        )
        
        file_size_mb = parquet_file.stat().st_size / (1024 * 1024)
        print(f"  ✓ Saved: {len(df):,} rows, {file_size_mb:.1f} MB")
        
        return parquet_file
    
    def export_monthly(
        self,
        symbol: str = "NIFTY",
        year: int = 2024,
        month: int = 1
    ) -> Optional[Path]:
        """
        Export one month of data to Parquet file.
        
        This method:
        1. Checks if data needs regeneration using metadata comparison
        2. Queries ClickHouse if regeneration is needed
        3. Optimizes and saves data to Parquet
        4. Creates/updates metadata file
        
        File structure:
        {output_dir}/
          {symbol}_Parquet_Data/
            {symbol}_YYYY_MM.parquet
          {symbol}_Meta_Data/
            {symbol}_YYYY_MM.json
        
        Args:
            symbol: Symbol name (e.g., 'NIFTY', 'BANKNIFTY')
            year: Year (e.g., 2024)
            month: Month (1-12)
            
        Returns:
            Path to parquet file if created, None if skipped or no data
        """
        # Calculate date range for the month
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{calendar.monthrange(year, month)[1]}"
        
        print(f"Processing {symbol} data for {year}-{month:02d} ({start_date} to {end_date})")
        
        # Check if regeneration is needed
        if not self._needs_regeneration(start_date, end_date, symbol):
            print("  ✓ Data is already cached and up to date")
            return self._get_parquet_path(symbol, end_date) if self._get_parquet_path(symbol, end_date).exists() else None
        
        # Query and process data
        try:
            df = self._query_data(symbol, start_date, end_date)
            
            if df.empty:
                print(f"  ⚠ No data found for {symbol} - {year}-{month:02d}")
                return None
            
            # Save to parquet
            parquet_file = self._save_parquet(df, symbol, end_date)
            
            # Create metadata
            metadata = {
                'row_count': int(df.shape[0]),
                'month_last_date': str(df.index.max()),
                'column_count': int(df.shape[1] + 1)  # +1 for index
            }
            self._create_metadata(metadata, symbol, end_date)
            
            return parquet_file
            
        except Exception as e:
            print(f"  ✗ Error processing data: {e}")
            raise
    
    def export_year(self, symbol: str, year: int) -> None:
        """
        Export all 12 months for a given year.
        
        Args:
            symbol: Symbol name
            year: Year to export
        """
        print(f"\n{'='*60}")
        print(f"Exporting {symbol} for year {year}")
        print(f"{'='*60}\n")
        
        for month in range(1, 13):
            self.export_monthly(symbol=symbol, year=year, month=month)
    
    def export_range(self, symbol: str, start_year: int, end_year: int) -> None:
        """
        Export multiple years of data.
        
        Args:
            symbol: Symbol name
            start_year: Starting year (inclusive)
            end_year: Ending year (inclusive)
        """
        print(f"\n{'='*60}")
        print(f"Exporting {symbol} from {start_year} to {end_year}")
        print(f"{'='*60}\n")
        
        for year in range(start_year, end_year + 1):
            self.export_year(symbol, year)


if __name__ == "__main__":
    # Load configuration
    settings_path = os.path.join(base_path, 'settings', 'config.yaml')
    clickhouse_params = LoadYamlfile(file_path=settings_path).get('clickhouse_database_params')
    
    # Initialize ClickHouse connection
    clickhouse_connector = ClickhouseConnector(clickhouse_params)
    clickhouse_client = clickhouse_connector.get_clickhouse_client()
    
    # Create builder instance
    builder = MonthlyParquetBuilder(
        clickhouse_client=clickhouse_client,
        clickhouse_object=clickhouse_connector
    )
    
    builder.export_monthly(symbol="NIFTY", year=2024, month=2)
    
