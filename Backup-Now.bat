@echo off
setlocal
title OWLIN - Backup Now

REM Set project root to this .bat's parent folder by default
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"

set "STAMP=%DATE:/=-%_%TIME::=-%"
set "STAMP=%STAMP: =0%"
set "STAMP=%STAMP:,=.%"
for /f "tokens=1 delims=." %%a in ("%STAMP%") do set "STAMP=%%a"
set "OUTDIR=%ROOT%\backups"
set "ZIP=%OUTDIR%\owlin_save_%STAMP%.zip"

if not exist "%OUTDIR%" mkdir "%OUTDIR%"

echo ?? Creating backup:
echo   From: %ROOT%
echo   To:   %ZIP%
echo.

REM Include key folders/files; add more lines if needed
powershell -NoProfile -Command ^
  "Add-Type -A 'System.IO.Compression.FileSystem';" ^
  "$zip = '%ZIP%';" ^
  "if (Test-Path $zip) { Remove-Item $zip }" ^
  "[IO.Compression.ZipFile]::CreateFromDirectory('%ROOT%', $zip);"

if errorlevel 1 (
  echo ? Backup failed.
  pause & exit /b 1
)

echo ? Backup created: %ZIP%
explorer.exe "/select,\"%ZIP%\""
pause
