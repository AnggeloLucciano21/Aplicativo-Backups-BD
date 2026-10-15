@echo off
title DataShield Enterprise - Compilador PyInstaller
cd /d "%~dp0"

echo =======================================================
echo Compilando DataShield Enterprise a Ejecutable de Windows
echo =======================================================

if not exist "venv\Scripts\pyinstaller.exe" (
    echo Instalando PyInstaller en el entorno virtual...
    .\venv\Scripts\pip install pyinstaller
)

echo Generando ejecutable standalone...
.\venv\Scripts\pyinstaller.exe --noconfirm --onedir --windowed ^
    --name "DataShieldBackup" ^
    --add-data "ui;ui" ^
    --add-data "core;core" ^
    --add-data "database;database" ^
    --add-data "connectors;connectors" ^
    --add-data "security;security" ^
    --add-data "backup;backup" ^
    --add-data "restore;restore" ^
    --add-data "scheduler;scheduler" ^
    --add-data "logging_system;logging_system" ^
    app\main.py

echo =======================================================
echo Compilacion finalizada.
echo Ejecutable generado en: .\dist\DataShieldBackup\DataShieldBackup.exe
echo =======================================================
pause
