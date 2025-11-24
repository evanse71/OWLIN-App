@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0backup_now.ps1" -Mode FULL -DestRoot "C:\Owlin (new contents)" -Keep 10
echo.
echo If nothing appeared in the destination, open the most recent *.log in "C:\Owlin (new contents)" to see details.
pause
