@echo off
cd /d "%~dp0"
set "AEGIS_ENTERPRISE_MODE="
set "AEGIS_ADMIN_PASSWORD="
call "%~dp0RUN_LOCAL.bat"
