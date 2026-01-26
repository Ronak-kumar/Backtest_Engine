@echo off
REM Activate virtual environment
call "D:\Development\Coding_Projects\market_project\.venv\Scripts\activate.bat"

REM Run Python script inside venv
streamlit run "D:\Development\Coding_Projects\market_project\Backtest_Engine\UI\Main_Engine_UI.py"


pause
