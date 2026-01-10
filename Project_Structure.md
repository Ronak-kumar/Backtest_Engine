Backtest_Engine/
├── .gitignore
│
├── csv/
│ ├── Charges_Values.csv
│ ├── Events List.csv
│ └── Holidays inc Sat & Sunday.csv
│
├── Database_manager/
│ └── data_extractor.py
│
├── Engines/
│ └── Main_Engine.py
│
├── local_data/ # Ignored (local cache)
│ ├── NIFTY_Meta_Data/
│ │ ├── NIFTY_2024_01.json
│ │ ├── NIFTY_2024_02.json
│ │ ├── NIFTY_2024_03.json
│ │ └── NIFTY_2024_04.json
│ │
│ └── NIFTY_Parquet_Data/
│ ├── NIFTY_2024_01.parquet
│ ├── NIFTY_2024_02.parquet
│ ├── NIFTY_2024_03.parquet
│ └── NIFTY_2024_04.parquet
│
├── logs/ # Ignored (runtime logs)
│ ├── 2025_12_28/
│ ├── 2026_01_09/
│ └── 2026_01_10/
│
├── queries/ (SQL Template)
│ └── options_sql
│
├── settings/
│ ├── config.yaml
│ ├── lotsize_config.yaml
│ └── symbol_configration.yaml
│
├── Utilities/
│ ├── clickhouse_connector.py
│ ├── clickhouse_params_holder.py
│ ├── Day_Processor.py
│ ├── Helper_functions.py
│ ├── Legs_generator.py
│ ├── Logger.py
│ ├── missing_date_handler.py
│ ├── parameter_parser.py
│ ├── query_template_loader.py
│ ├── Result_handler.py
│ ├── SD_manager.py
│ └── Yaml_Loader.py
│
└── .idea/ # IDE config (ignored)