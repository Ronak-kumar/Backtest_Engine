# Backtest Engine

A **config-driven, modular backtesting engine** designed for **Indian index options & futures strategies**, with a strong focus on **performance, correctness, and scalability**.

This engine is built to support:
- Historical backtesting
- Intraday strategies
- Multi-leg option strategies
- Future live-trading integration

---

## 🚀 Key Features

- ✅ **Config-Driven Architecture**
  - YAML-based configuration for symbols, lot sizes, and strategy parameters
- ✅ **Modular Design**
  - Clean separation between engine, utilities, data access, and configs
- ✅ **ClickHouse Integration**
  - Optimized for large historical datasets
- ✅ **Polars-Ready**
  - Designed for high-performance dataframe operations
- ✅ **Trading Calendar Aware**
  - Handles holidays, missing dates, and non-trading days
- ✅ **Extensible**
  - Easy to plug in new strategies, risk models, and execution logic

---

## 📁 Project Structure

See [`Project_Structure.md`](Project_Structure.md) for a detailed breakdown.

High-level overview:
    Backtest_Engine/
    ├── Engines/ # Core execution engines
    ├── Utilities/ # Shared helpers and processors
    ├── Database_manager/ # Data extraction logic
    ├── settings/ # YAML configurations
    ├── queries/ # SQL templates
    ├── csv/ # Static reference data
    ├── local_data/ # Cached data (ignored)
    ├── logs/ # Runtime logs (ignored)
    └── .gitignore
