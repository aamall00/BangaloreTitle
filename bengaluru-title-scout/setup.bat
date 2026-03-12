@echo off
setlocal enabledelayedexpansion

echo ================================================
echo   Bengaluru Title Scout - First Time Setup
echo ================================================
echo.

:: ─── Check Node.js ───────────────────────────────
set NODE_OK=0
where node >nul 2>&1 && set NODE_OK=1
if %NODE_OK%==0 (
    echo [ERROR] Node.js is not installed or not in PATH.
    echo.
    echo   Please install Node.js from:
    echo   https://nodejs.org/en/download  ^(choose LTS^)
    echo.
    echo   After installing, re-run this script.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('node --version') do set NODE_VER=%%v
echo [OK] Node.js found: %NODE_VER%

:: ─── Check npm ────────────────────────────────────
set NPM_OK=0
where npm >nul 2>&1 && set NPM_OK=1
if %NPM_OK%==0 (
    echo [ERROR] npm not found. Reinstall Node.js from https://nodejs.org
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('npm --version') do set NPM_VER=%%v
echo [OK] npm found: v%NPM_VER%

:: ─── Check Python (try python, py, python3) ───────
set PYTHON_CMD=
where python >nul 2>&1 && set PYTHON_CMD=python
if "!PYTHON_CMD!"=="" (
    where py >nul 2>&1 && set PYTHON_CMD=py
)
if "!PYTHON_CMD!"=="" (
    where python3 >nul 2>&1 && set PYTHON_CMD=python3
)
if "!PYTHON_CMD!"=="" (
    echo.
    echo [ERROR] Python is not installed or not in PATH.
    echo.
    echo   Please install Python 3.11+ from:
    echo   https://www.python.org/downloads/
    echo.
    echo   IMPORTANT: During installation tick:
    echo     [x] Add Python to PATH
    echo     [x] pip
    echo.
    echo   After installing, re-run this script.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('!PYTHON_CMD! --version') do set PY_VER=%%v
echo [OK] Python found ^(!PYTHON_CMD!^): !PY_VER!
echo.

:: ─── Step 1: Node deps ────────────────────────────
echo [1/3] Installing Node.js dependencies...
cd /d "%~dp0"
call npm install
if errorlevel 1 (
    echo [ERROR] npm install failed. Check internet connection.
    pause
    exit /b 1
)
echo.

:: ─── Step 2: Python deps ──────────────────────────
echo [2/3] Installing Python dependencies...
!PYTHON_CMD! -m pip install -r backend\requirements.txt --quiet
if errorlevel 1 (
    echo [WARN] Some Python packages may have failed. Continuing...
)
echo.

:: ─── Step 3: Seed knowledge base ──────────────────
echo [3/3] Seeding Karnataka law knowledge base...
!PYTHON_CMD! backend\setup.py --kb-only
if errorlevel 1 (
    echo [WARN] KB seed failed - will rebuild on first run.
)
echo.

:: ─── Copy .env if missing ─────────────────────────
if not exist backend\.env (
    if exist backend\.env.example (
        copy backend\.env.example backend\.env >nul
        echo [OK] Created backend\.env from template.
        echo      Edit it to add your API keys.
    )
)

echo ================================================
echo   Setup complete!
echo.
echo   Next: Edit backend\.env and add your keys:
echo     AZURE_DOC_ENDPOINT=...
echo     ANTHROPIC_API_KEY=...  ^(or OPENAI_API_KEY^)
echo.
echo   Then start the app:
echo     npm start
echo ================================================
pause
