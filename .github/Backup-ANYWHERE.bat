@echo off
setlocal enabledelayedexpansion

rem --- self-root to the folder where this BAT lives ---
set "ROOT=%~dp0"
for %%# in ("%ROOT:~0,-1%") do set "ROOT=%%~f#\"

rem --- candidate destinations (in order) ---
set "CAND1=C:\Owlin (new contents)"
set "CAND2=%USERPROFILE%\Documents\Owlin Backups"
set "CAND3=%USERPROFILE%\Desktop\Owlin Backups"
set "CAND4=%TEMP%\OwlinBackups"

rem --- pick first writable destination ---
for %%D in ("%CAND1%" "%CAND2%" "%CAND3%" "%CAND4%") do (
  2>nul (mkdir "%%~D") && (
    >nul 2>&1 (echo test> "%%~D\.__owlin_write_probe") && (
      del /q "%%~D\.__owlin_write_probe" >nul 2>&1
      set "DEST=%%~D"
      goto :dest_ok
    )
  )
)
echo ERROR: No writable destination found. Try running as Administrator.
pause
exit /b 1

:dest_ok
set "TS=%date:~10,4%-%date:~4,2%-%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"
set "ZIP=%DEST%\owlin_quick_backup_%TS%.zip"
set "LOG=%DEST%\owlin_quick_backup_%TS%.log"
set "SHA=%ZIP%.sha256.txt"

echo [%date% %time%] BACKUP START > "%LOG%"
echo ROOT="%ROOT%" >> "%LOG%"
echo DEST="%DEST%" >> "%LOG%"
echo ZIP ="%ZIP%"  >> "%LOG%"

rem stop common dev servers (best-effort)
for %%P in (uvicorn python node streamlit) do (
  >nul 2>&1 taskkill /im %%P.exe /f
)

rem zip everything under ROOT (top-level)
powershell -NoProfile -Command ^
  "Compress-Archive -Path '%ROOT%*' -DestinationPath '%ZIP%' -Force" ^
  >> "%LOG%" 2>&1

if not exist "%ZIP%" (
  echo [%date% %time%] ERROR: zip not created >> "%LOG%"
  echo ERROR: ZIP not created. See log: "%LOG%"
  pause
  exit /b 1
)

rem make SHA256 sidecar
powershell -NoProfile -Command ^
  "$h=(Get-FileHash -Algorithm SHA256 -LiteralPath '%ZIP%').Hash; '^!^!^!'|Out-Null; Set-Content -Path '%SHA%' -Value ($h+'  '+[System.IO.Path]::GetFileName('%ZIP%')) -Encoding ASCII" ^
  >> "%LOG%" 2>&1

echo [%date% %time%] OK: "%ZIP%" >> "%LOG%"
echo.
echo ✅ Backup created:
echo   %ZIP%
echo   %SHA%
echo   Log: %LOG%
echo.
echo (Saved to: %DEST%)
pause
