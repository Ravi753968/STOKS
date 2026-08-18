@echo off
echo ====================================================================
echo  Setting up Daily Market Close Auto-Alert Task in Windows Scheduler
echo ====================================================================
echo Task Name: Stock_Breakout_Daily_Alert
echo Scheduled Time: 3:30 PM IST (Every Weekday Mon-Fri)
echo Directory: D:\STOKS
echo.

schtasks /Create /TN "Stock_Breakout_Daily_Alert" /TR "python D:\STOKS\daily_market_alert.py" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 15:30 /F

if %ERRORLEVEL% EQU 0 (
    echo.
    echo SUCCESS: Windows Scheduled Task 'Stock_Breakout_Daily_Alert' created successfully!
    echo It will automatically execute daily_market_alert.py at 3:30 PM on all trading days.
) else (
    echo.
    echo WARNING: Failed to create Windows Scheduled Task automatically. Please run Command Prompt as Administrator.
)

pause
