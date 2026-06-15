@echo off
chcp 65001 >nul
set "SAVE_DIR=%APPDATA%\Pokemon Anil Live"

if not exist "%SAVE_DIR%" mkdir "%SAVE_DIR%"
if not exist "%SAVE_DIR%\backups" mkdir "%SAVE_DIR%\backups"
if not exist "%SAVE_DIR%\backups\manual" mkdir "%SAVE_DIR%\backups\manual"
if not exist "%SAVE_DIR%\backups\autosaves" mkdir "%SAVE_DIR%\backups\autosaves"
if not exist "%SAVE_DIR%\backups\updates" mkdir "%SAVE_DIR%\backups\updates"

echo Carpeta de partidas Live:
echo "%SAVE_DIR%"
start "" "%SAVE_DIR%"
timeout /t 2 /nobreak >nul
