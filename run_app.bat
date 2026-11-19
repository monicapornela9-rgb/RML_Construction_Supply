@echo off
cd /d "%~dp0"

if exist "RML\.venv\Scripts\python.exe" (
    "RML\.venv\Scripts\python.exe" app.py
) else (
    python app.py
)
