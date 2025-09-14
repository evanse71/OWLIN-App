@echo off
setlocal
REM Location-proof: jump to repo root regardless of where this .bat is run
pushd "%~dp0.."

REM Run the PowerShell launcher with safe flags
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\start_full_dev.ps1"

popd
endlocal
