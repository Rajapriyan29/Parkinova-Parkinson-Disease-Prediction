@echo off
title Parkinova - Parkinson's MRI Research Platform
cd /d "%~dp0"

echo ========================================================
echo   Parkinova - Parkinson's MRI Research Platform
echo   Clinical Evaluation & Pattern Analysis System
echo ========================================================
echo.
echo Starting Parkinova Desktop Application...

python main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Application exited with error code %ERRORLEVEL%.
    pause
)
