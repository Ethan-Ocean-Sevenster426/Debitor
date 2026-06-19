@echo off
REM Hourly Xero -> SQL Server sync for the FSA Debtor System.
REM Registered as a Windows Scheduled Task (see README / setup notes).
cd /d "%~dp0"
"C:\Python314\python.exe" manage.py sync_xero >> "%~dp0sync_xero.log" 2>&1

REM Also check (every hour) whether the weekly lawyer report is due to go out.
REM The command self-gates on the schedule configured in the Lawyer Report page,
REM so it only actually sends at the chosen day/time.
"C:\Python314\python.exe" manage.py send_lawyer_report >> "%~dp0lawyer_report.log" 2>&1
