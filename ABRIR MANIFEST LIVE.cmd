@echo off
chcp 65001 >nul
setlocal
set "ROOT=%~dp0"
set "PYTHON=%ROOT%runtime\python\python.exe"
set "CONFIG=%ROOT%config\actions_anil.json"

echo Probando manifest de Pokemon Anil Live...
echo URL: http://127.0.0.1:8877/manifest
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:8877/health' -UseBasicParsing -TimeoutSec 2; $ok=($r.StatusCode -eq 200) } catch {}; if (-not $ok) { exit 1 }"
if errorlevel 1 (
  echo El event bus no estaba abierto. Abriendolo ahora...
  if not exist "%ROOT%logs" mkdir "%ROOT%logs"
  start "Pokemon Anil Live - Event Bus" cmd /k call "%ROOT%runtime\iniciar_event_bus.cmd"
  timeout /t 3 /nobreak >nul
)

start "" "http://127.0.0.1:8877/manifest"
echo Si el navegador no abre, copia esta URL:
echo http://127.0.0.1:8877/manifest
pause
