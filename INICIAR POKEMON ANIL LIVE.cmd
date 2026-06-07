@echo off
chcp 65001 >nul
title Pokemon Anil Live

set "ROOT=%~dp0"
set "GAME_DIR=%ROOT%POKEMON_ANIL\Pokemon Anil"
set "PYTHON=%ROOT%runtime\python\python.exe"
set "CONFIG=%ROOT%config\actions_anil.json"
set "SAVE_DIR=%APPDATA%\Pokemon Anil Live"
set "BACKUP_DIR=%SAVE_DIR%\backups"

echo Iniciando Pokemon Anil Live...
echo Partidas Live: "%SAVE_DIR%"

if not exist "%SAVE_DIR%" mkdir "%SAVE_DIR%"
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
if not exist "%BACKUP_DIR%\autosaves" mkdir "%BACKUP_DIR%\autosaves"
if not exist "%BACKUP_DIR%\manual" mkdir "%BACKUP_DIR%\manual"
if not exist "%BACKUP_DIR%\updates" mkdir "%BACKUP_DIR%\updates"

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%runtime\sincronizar_partidas.ps1" -GameDir "%GAME_DIR%" -SaveDir "%SAVE_DIR%"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$conn = Get-NetTCPConnection -LocalPort 8877 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1; if ($conn) { Stop-Process -Id $conn.OwningProcess -Force }"

type nul > "%GAME_DIR%\live_chaos_queue.txt"

start "Pokemon Anil Live" /MIN powershell -NoProfile -ExecutionPolicy Bypass -Command "$env:POKEMON_ANIL_LIVE_CONFIG='%CONFIG%'; Set-Location '%ROOT%'; & '%PYTHON%' '.\controller.py' --serve"

echo.
echo Pokemon Anil Live y el event bus estan abiertos.
echo Deja esta ventana abierta para sincronizar la partida al cerrar.

start "Pokemon Anil Live" /D "%GAME_DIR%" /WAIT "%GAME_DIR%\Game.exe"

echo.
echo Pokemon Anil se cerro. Sincronizando partida final...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%runtime\sincronizar_partidas.ps1" -GameDir "%GAME_DIR%" -SaveDir "%SAVE_DIR%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -LiteralPath '%GAME_DIR%' -Filter 'Partida *.rxdata' -File -ErrorAction SilentlyContinue | Remove-Item -Force"
echo Partida protegida en "%SAVE_DIR%".
timeout /t 3 /nobreak >nul
exit
