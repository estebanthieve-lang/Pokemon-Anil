@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if not exist "%~dp0runtime" mkdir "%~dp0runtime"
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/estebanthieve-lang/Pokemon-Anil/main/runtime/actualizar_juego.ps1' -UseBasicParsing -OutFile '%~dp0runtime\actualizar_juego.ps1' } catch { Write-Host 'No se pudo refrescar el actualizador, se usara el local.' -ForegroundColor Yellow }"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0runtime\actualizar_juego.ps1" -InstallRoot "%~dp0"
pause
