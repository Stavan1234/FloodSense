@echo off
REM FloodSense - one-time setup (Windows): creates .venv and installs packages
cd /d "%~dp0"

python --version >nul 2>&1 || (
    echo Python was not found. Install Python 3.10+ from https://www.python.org
    echo and tick "Add python.exe to PATH" during installation, then run this again.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment...
    python -m venv .venv || (
        echo Could not create the virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [1/3] Virtual environment already exists.
)

echo [2/3] Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip

echo [3/3] Installing packages, this can take a few minutes...
".venv\Scripts\python.exe" -m pip install -r requirements.txt || (
    echo Package installation failed. Check your internet connection and try again.
    pause
    exit /b 1
)

echo.
echo Setup complete. Double-click run.bat to start FloodSense.
if not "%~1"=="--no-pause" pause
