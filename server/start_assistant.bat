@echo off
title AI Assistive Vision & Tamil Voice Assistant
echo ====================================================================
echo    AI ASSISTIVE VISION & TAMIL VOICE ASSISTANT (MOBILE & ESP32)
echo ====================================================================
echo.
echo [SERVER RUNNING ON SECURE HTTPS]
echo.
echo   >>> Open this link on your MOBILE PHONE CHROME BROWSER:
echo   >>> https://192.168.29.89:8000/camera
echo.
echo   NOTE: When Chrome says "Connection is not private", 
echo   click "Advanced" and then click "Proceed to 192.168.29.89 (unsafe)".
echo.
echo ====================================================================
echo.
cd /d "%~dp0"
python app.py
pause
