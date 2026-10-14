@echo off
setlocal
cd /d "%~dp0"
title AEGIS - Terminal Agent
color 0B
echo.
echo === AEGIS AUTONOMOUS AGENT - TERMINAL MODE ===
echo All emails in data\inbox will be processed without manual steps.
echo Outputs: outbox.json and agent_log.jsonl.
echo No messages are sent to recipients.
echo.
where python >nul 2>&1
if errorlevel 1 (
  set "PY=py -3"
) else (
  set "PY=python"
)
if not defined GEMINI_API_KEY (
  for /f "delims=" %%K in ('powershell -NoProfile -Command "$s=Read-Host -Prompt Gemini_API_Key -AsSecureString; $p=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($s); try {[Runtime.InteropServices.Marshal]::PtrToStringBSTR($p)} finally {[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($p)}"') do set "GEMINI_API_KEY=%%K"
)
if not defined GEMINI_API_KEY (
  echo ERROR: No Gemini API key provided.
  pause
  exit /b 1
)
%PY% agent.py
if errorlevel 1 (
  echo Agent run failed. See errors above.
) else (
  echo.
  echo Success! Validating outbox...
  %PY% verify_outbox.py
  echo Open outbox.json to view decisions and reply drafts.
)
pause
