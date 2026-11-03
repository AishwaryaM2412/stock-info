@echo off
REM Run script for Windows: sets up a virtual environment, installs requests, starts the program.
cd /d "%~dp0"
if not exist .venv ( python -m venv .venv )
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt
python stockinfo.py
