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
if not exist "%ROOT%logs" mkdir "%ROOT%logs"

if not exist "%PYTHON%" (
  echo.
  echo ERROR: No existe Python portable:
  echo "%PYTHON%"
  echo Descarga de nuevo el ZIP completo del repositorio.
  pause
  exit /b 1
)

if not exist "%ROOT%controller.py" (
  echo.
  echo ERROR: Falta controller.py en:
  echo "%ROOT%"
  echo Descarga de nuevo el ZIP completo del repositorio.
  pause
  exit /b 1
)

if not exist "%CONFIG%" (
  echo.
  echo ERROR: Falta la config:
  echo "%CONFIG%"
  echo Descarga de nuevo el ZIP completo del repositorio.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%runtime\sincronizar_partidas.ps1" -GameDir "%GAME_DIR%" -SaveDir "%SAVE_DIR%"
if errorlevel 1 (
  echo.
  echo ERROR: No se pudo sincronizar la partida al iniciar.
  echo No se tocara ninguna partida. Cierra esta ventana y avisa el error.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$conn = Get-NetTCPConnection -LocalPort 8877 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1; if ($conn) { Stop-Process -Id $conn.OwningProcess -Force }"

type nul > "%GAME_DIR%\live_chaos_queue.txt"

start "Pokemon Anil Live - Event Bus" cmd /k call "%ROOT%runtime\iniciar_event_bus.cmd"

echo.
echo Pokemon Anil Live y el event bus estan abiertos.
echo Manifest: http://127.0.0.1:8877/manifest
echo Deja esta ventana abierta para sincronizar la partida al cerrar.

start "Pokemon Anil Live" /D "%GAME_DIR%" /WAIT "%GAME_DIR%\Game.exe"

echo.
echo Pokemon Anil se cerro. Sincronizando partida final...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%runtime\sincronizar_partidas.ps1" -GameDir "%GAME_DIR%" -SaveDir "%SAVE_DIR%"
if errorlevel 1 (
  echo.
  echo ERROR: No se pudo sincronizar la partida final.
  echo Por seguridad NO se limpiaran partidas temporales de la carpeta del juego.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$stamp=Get-Date -Format 'yyyyMMdd_HHmmss'; $cleanupBackup=Join-Path '%BACKUP_DIR%\autosaves' ('cleanup_' + $stamp); $saves=Get-ChildItem -LiteralPath '%GAME_DIR%' -Filter 'Partida *.rxdata' -File -ErrorAction SilentlyContinue; if ($saves) { New-Item -ItemType Directory -Force -Path $cleanupBackup | Out-Null; $saves | Copy-Item -Destination $cleanupBackup -Force; $saves | Remove-Item -Force }"
echo Partida protegida en "%SAVE_DIR%".
timeout /t 3 /nobreak >nul
exit
