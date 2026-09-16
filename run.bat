@echo off
title Atoka - Restaurant Management System

REM Check for admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo Starting Atoka server on http://localhost:80
python manage.py runserver 0.0.0.0:80

if %errorLevel% neq 0 (
    echo.
    echo Server stopped with error code %errorLevel%.
    pause
)
