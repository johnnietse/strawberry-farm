@echo off
REM G.O.S. (Greenhouse Operating System) - Windows Setup Script
REM This script prepares your local environment for development and simulation.

echo.
echo ==================================================================
echo G.O.S. LOCAL FARM - ENVIRONMENT SETUP
echo ==================================================================
echo.

REM 1. Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo [STEP 1/4] Creating Python virtual environment...
    python -m venv .venv
) else (
    echo [STEP 1/4] Virtual environment already exists.
)

REM 2. Activate and install dependencies
echo [STEP 2/4] Installing Python dependencies...
call .venv\Scripts\activate
pip install -r requirements.txt

REM 3. Create data directory
echo [STEP 3/4] Creating data directory for ML outputs...
if not exist "data" mkdir data

REM 4. Initialize the database schema (if running locally with Docker)
echo [STEP 4/4] Checking Docker status...
docker info >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Docker is running. You can start the cluster with:
    echo   python run.py --up
) else (
    echo [WARNING] Docker Desktop is not running.
    echo   Start Docker Desktop, then run: python run.py --up
)

echo.
echo ==================================================================
echo SETUP COMPLETE! Next steps:
echo   1. Start Docker Desktop
echo   2. Run: python run.py --up
echo   3. Open: http://localhost:8080
echo ==================================================================
