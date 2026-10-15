@echo off
title DataShield Enterprise - Backups BD
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] No se encontro el entorno virtual en .\venv.
    echo Por favor ejecute: python -m venv venv ^&^& .\venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

echo Iniciando DataShield Enterprise Backup & Recovery...
start "" ".\venv\Scripts\pythonw.exe" "app\main.py"
exit /b 0
