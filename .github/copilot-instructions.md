## Purpose
This file tells AI coding assistants how this repo is organized, the project's conventions, and where to look for examples so they can make safe, high-value changes quickly.

**Big picture**
- **Engine core:** the backtest loop and orchestration live in [Engines/Main_Engine.py](Engines/Main_Engine.py#L1-L40). Treat this as the canonical flow for data ingestion → per-day processing → result persistence.
- **Managers:** strategy-level logic, EOD/result handling, and LLM integration are under [Managers/](Managers). Key examples: [Managers/llm_optimizer.py](Managers/llm_optimizer.py#L1-L40) (local Ollama-based optimizer) and [Managers/llm_chain_optimizer.py](Managers/llm_chain_optimizer.py#L1-L40) (chain-aware optimizer).
- **Utilities:** shared helpers and connectors are under [Utilities/](Utilities) (ClickHouse client, YAML loader, Legs generator, Day processor). Use these for consistent I/O, logging and config handling.
- **Data & results:** runtime caches in `local_data/`, SQL templates in `queries/`, and backtest outputs in `results/<index>/<strategy>/...` (EOD files and `*_tradelog.parquet` files are canonical inputs for analyzers).

**Prerequisites & external integrations**
- ClickHouse: connection configured in `settings/config.yaml` — code expects ClickHouse credentials and option/spot table names used by [Engines/Main_Engine.py](Engines/Main_Engine.py#L50-L90).
- Local LLM (optional): `Managers/llm_optimizer.py` documents Ollama + `qwen2.5-coder` usage and how to run `ollama serve` and `ollama pull` — follow those instructions when changing LLM logic.
- Polars/Pandas: this codebase uses `polars` heavily for performance; prefer `pl.DataFrame` operations where present.

**Repository conventions & patterns**
- Config-first: behavior is driven by YAMLs in `settings/` and entry-parameter CSVs in each strategy folder. Prefer reading/updating those over hardcoding values.
- Strategy layout: a strategy directory typically contains `leg_data/` (main legs), optional `sub_leg_data/` (lazy legs), and `entry_parameter_*.csv`. See [Managers/llm_chain_optimizer.py](Managers/llm_chain_optimizer.py#L1-L120) for code expecting this layout.
- Results expectations: EOD results file is expected as `EOD_File.csv` inside a results folder; trade logs are `*_tradelog.parquet` (see `LocalLLMParameterOptimizer.load_trade_logs`).
- Safety-first for AI changes: LLM-based optimizers implement explicit safe bounds (see `SAFE_BOUNDS` in [Managers/llm_optimizer.py](Managers/llm_optimizer.py#L1-L80)). Any parameter edits should respect these bounds or update the bounds intentionally and cautiously.

**Developer workflows (concrete)**
- Run a backtest locally: edit the `param_csv_file` path in [Engines/Main_Engine.py](Engines/Main_Engine.py#L1-L40) or use the runner under `Engine_Runners/` to point at the strategy CSV, then run `python Engines/Main_Engine.py` (the file contains a self-contained main loop).
- Analyze & optimize with local LLM: start Ollama (`ollama serve`), pull `qwen2.5-coder` (`ollama pull qwen2.5-coder:32b`), then run the optimizer examples at the bottom of [Managers/llm_optimizer.py](Managers/llm_optimizer.py#L560-L680).
- UI testing: the Streamlit integration is demonstrated in [UI/llm_optimizer_integration.py](UI/llm_optimizer_integration.py#L1-L40). Run Streamlit for manual QA: `streamlit run path/to/Main_Engine_UI.py`.

**When modifying code, prefer small, focused changes**
- Follow existing module boundaries (Engines orchestrate, Managers encapsulate strategy logic, Utilities provide IO/helpers).
- When touching strategy files, preserve `leg_data/` and `sub_leg_data/` formats (CSV key/value rows) — `llm_chain_optimizer` reads them as `header=None` CSVs.

**Quick pointers for the assistant**
- Look for examples in `Managers/*.py` when implementing new optimizer behavior.
- Use `results/<index>/<strategy>/.../EOD_File.csv` and `*_tradelog.parquet` as canonical test inputs when validating metric calculations.
- Respect `SAFE_BOUNDS` and JSON output expectations in LLM prompt builders to avoid breaking integrations.

If any section is unclear or you want this tightened to a different audience (new contributor, CI bot, reviewer), tell me which parts to expand or compress.
