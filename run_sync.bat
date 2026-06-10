@echo off
REM Hourly Xero -> SQL Server sync for the FSA Debtor System.
REM Registered as a Windows Scheduled Task (see README / setup notes).
cd /d "%~dp0"
"C:\Python314\python.exe" manage.py sync_xero >> "%~dp0sync_xero.log" 2>&1
