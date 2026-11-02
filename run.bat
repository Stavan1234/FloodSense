@echo off
REM FloodSense - one-click launcher (Windows)
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [1/2] Creating virtual environment...
    python -m venv .venv || (
        echo Python was not found. Install Python 3.10+ from https://www.python.org and try again.
        pause
        exit /b 1
    )
    echo [2/2] Installing packages, this can take a few minutes...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || (
        echo Package installation failed.
        pause
        exit /b 1
    )
)

echo Starting FloodSense... your browser will open shortly. Press Ctrl+C to stop.
".venv\Scripts\python.exe" -m streamlit run app.py
pause
