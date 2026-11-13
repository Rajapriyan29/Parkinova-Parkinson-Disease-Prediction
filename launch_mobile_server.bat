@echo off
title Parkinova Mobile & Web Server
cd /d "%~dp0"

echo ========================================================
echo   Parkinova - Mobile & Network REST API Server
echo   Connect Android / Mobile Devices on the Same Wi-Fi
echo ========================================================
echo.
echo Launching server.py...
echo To access from your Android phone or tablet, connect to the
echo Wi-Fi address printed below.
echo.

python server.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Server exited with error code %ERRORLEVEL%.
    pause
)
