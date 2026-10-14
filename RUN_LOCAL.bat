@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title AEGIS Enterprise - Student Helpdesk Command Center
color 0B
echo.
echo  ======================================================
echo        AEGIS V3  ^|  AI Student Helpdesk
 eCHO       FastAPI + HTML/CSS/JS + Gemini + SQLite
 eCHO  ======================================================
echo.
set "PY=python"
python -c "import sys; assert sys.version_info >= (3,10)" >nul 2>&1
if errorlevel 1 (
  set "PY=py -3"
  py -3 -c "import sys; assert sys.version_info >= (3,10)" >nul 2>&1
  if errorlevel 1 (
    echo [ERROR] Python 3.10 or newer is required.
    echo Install Python from https://python.org/downloads and enable Add Python to PATH.
    pause
    exit /b 1
  )
)
if not exist ".venv\Scripts\python.exe" (
  echo [1/4] Creating lightweight environment that can reuse existing packages...
  %PY% -m venv --system-site-packages ".venv"
  if errorlevel 1 (
    echo [ERROR] Could not create Python virtual environment.
    echo Verify Python installation and permissions, then retry.
    pause
    exit /b 1
  )
) else (
  echo [1/4] Existing virtual environment found.
)
set "VENV_PY=.venv\Scripts\python.exe"
%VENV_PY% -c "import fastapi, uvicorn" >nul 2>&1
if errorlevel 1 (
  echo [2/4] Installing FastAPI + Uvicorn only. First setup requires Internet...
  %VENV_PY% -m pip install --disable-pip-version-check --prefer-binary --timeout 20 --retries 1 -r requirements.txt
  if errorlevel 1 (
    echo [ERROR] Package installation failed. Check Internet / proxy or run:
    echo .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
  )
) else (
  echo [2/4] Required packages already available - no download.
)
echo [3/4] Checking local app dependencies...
%VENV_PY% -c "import server, agent, storage, security; print('AEGIS startup checks passed')"
if errorlevel 1 (
  echo [ERROR] App failed to initialize. Please copy the error shown above.
  pause
  exit /b 1
)
echo [4/4] Starting http://127.0.0.1:8765
echo.
echo Enterprise mode: approved mail can be sent only when enabled in Settings.
echo Keep this window open while using the browser.
echo Press CTRL+C to stop the server.
echo.
%VENV_PY% launcher.py
if errorlevel 1 (
  echo [ERROR] Server could not start. Close other AEGIS RUN.bat windows and retry.
  pause
)
