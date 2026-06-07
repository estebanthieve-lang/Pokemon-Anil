@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0runtime\actualizar_juego.ps1" -InstallRoot "%~dp0"
pause
