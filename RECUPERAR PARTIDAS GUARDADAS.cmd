@echo off
chcp 65001 >nul
setlocal
set "ROOT=%~dp0"
set "IMPORT_DIR=%ROOT%MeterPartidasGuardadas"
set "SAVE_DIR=%APPDATA%\Pokemon Anil Live"

if not exist "%IMPORT_DIR%" mkdir "%IMPORT_DIR%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%runtime\recuperar_partidas.ps1" -ImportDir "%IMPORT_DIR%" -SaveDir "%SAVE_DIR%"
pause
