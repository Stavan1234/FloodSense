@echo off
REM FloodSense - one-click launcher (Windows)
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo First run: setting things up...
    call "%~dp0setup.bat" --no-pause || exit /b 1
)

echo Starting FloodSense... your browser will open shortly. Press Ctrl+C to stop.
".venv\Scripts\python.exe" -m streamlit run app.py
pause
