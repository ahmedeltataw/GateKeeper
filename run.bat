@echo off
REM ============================================================================
REM  GateKeeper - one-click launcher for Windows
REM  - creates a virtual environment if missing
REM  - installs requirements.txt
REM  - bootstraps .env from the template on first run
REM  - starts the gateway and opens it in your browser
REM ============================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "HOST=127.0.0.1"
set "PORT=8000"
set "VENV=.venv"

echo.
echo  ==== GateKeeper launcher ====
echo.

REM --- 1. Locate Python ------------------------------------------------------
where py >nul 2>&1
if %errorlevel%==0 (
    set "PY=py -3"
) else (
    where python >nul 2>&1
    if %errorlevel%==0 (
        set "PY=python"
    ) else (
        echo [ERROR] Python 3.12+ was not found on PATH.
        echo         Install it from https://www.python.org/downloads/ and re-run.
        pause
        exit /b 1
    )
)

REM --- 2. Create the virtual environment if it does not exist -----------------
if not exist "%VENV%\Scripts\python.exe" (
    echo [setup] Creating virtual environment in %VENV% ...
    %PY% -m venv "%VENV%"
    if errorlevel 1 (
        echo [ERROR] Failed to create the virtual environment.
        pause
        exit /b 1
    )
)

set "VPY=%VENV%\Scripts\python.exe"

REM --- 3. Install / update dependencies --------------------------------------
echo [setup] Installing dependencies (requirements.txt) ...
"%VPY%" -m pip install --upgrade pip >nul
"%VPY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
)

REM --- 4. Ensure a local .env with a valid ENCRYPTION_KEY --------------------
REM Generates and saves a fresh AES-256-GCM key on first run (local only),
REM so no external key file is ever required.
"%VPY%" scripts\ensure_env_key.py
if errorlevel 1 (
    echo [ERROR] Could not prepare the encryption key.
    pause
    exit /b 1
)
echo [setup] Remember to add at least ONE provider API key to .env
echo         (or add it later from the dashboard Keys page).

REM --- 5. Launch the gateway and open the browser ----------------------------
echo [run] Starting the gateway on http://%HOST%:%PORT% ...
start "" "http://%HOST%:%PORT%/docs"
"%VPY%" -m uvicorn src.api.server:app --host %HOST% --port %PORT%

endlocal
