@echo off
title Stock Breakout Workstation Enterprise Server V3.0
cd /d "d:\STOKS"
echo ================================================================
echo  ENTERPRISE PRODUCTION WORKSTATION SERVER V3.0
echo ================================================================
echo.
echo  Opening browser at: http://localhost:5005
echo.
start "" "http://localhost:5005"
python server.py
pause
