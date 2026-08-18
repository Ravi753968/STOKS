@echo off
title STOKS V5.0 Enterprise Breakout Workstation
color 0A
cls

echo =======================================================================
echo          STOKS V5.0 — Enterprise Breakout Workstation Launcher
echo =======================================================================
echo.
echo Starting Production Server on http://localhost:5005 ...
echo.

start "" http://localhost:5005
python main.py server

pause
