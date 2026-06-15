@echo off
chcp 65001 >nul
title Pokemon Anil Live - Event Bus
setlocal

set "RUNTIME_DIR=%~dp0"
for %%I in ("%RUNTIME_DIR%..") do set "ROOT=%%~fI\"
set "PYTHON=%ROOT%runtime\python\python.exe"
set "CONFIG=%ROOT%config\actions_anil.json"

if not exist "%ROOT%logs" mkdir "%ROOT%logs"

echo Pokemon Anil Live - Event Bus
echo.
echo Carpeta:
echo "%ROOT%"
echo.
echo Manifest:
echo http://127.0.0.1:8877/manifest
echo.

if not exist "%PYTHON%" (
  echo ERROR: No existe Python portable:
  echo "%PYTHON%"
  echo.
  echo Descarga de nuevo el ZIP completo del repositorio.
  pause
  exit /b 1
)

if not exist "%ROOT%controller.py" (
  echo ERROR: Falta controller.py:
  echo "%ROOT%controller.py"
  echo.
  echo Descarga de nuevo el ZIP completo del repositorio.
  pause
  exit /b 1
)

if not exist "%CONFIG%" (
  echo ERROR: Falta la config:
  echo "%CONFIG%"
  echo.
  echo Descarga de nuevo el ZIP completo del repositorio.
  pause
  exit /b 1
)

set "POKEMON_ANIL_LIVE_CONFIG=%CONFIG%"
cd /d "%ROOT%"
"%PYTHON%" "%ROOT%controller.py" --serve

echo.
echo El event bus se cerro. Si ves un error arriba, mandame captura.
pause
