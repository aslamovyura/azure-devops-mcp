@echo off
REM Wrapper to launch the MCP server via docker compose on Windows.
REM Requires Docker Desktop with compose. Uses .env for configuration.

setlocal ENABLEDELAYEDEXPANSION
set SCRIPT_DIR=%~dp0
REM Remove trailing backslash if present
if "%SCRIPT_DIR:~-1%"=="\" set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%
for %%I in ("%SCRIPT_DIR%\..") do set ROOT_DIR=%%~fI

cd /d "%ROOT_DIR%"
docker compose run --rm azure-devops-mcp %*
endlocal

