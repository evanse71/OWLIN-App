@echo off
setlocal EnableExtensions EnableDelayedExpansion

:: ============================================
:: Owlin - Backup-Everything.bat
:: Full-folder backup with fallbacks + SHA256
:: ============================================

:: 1) Resolve OWLIN_ROOT (folder where this .bat lives)
set "OWLIN_ROOT=%~dp0"
:: remove trailing backslash if present
if "%OWLIN_ROOT:~-1%"=="\" set "OWLIN_ROOT=%OWLIN_ROOT:~0,-1%"

:: Always operate from script directory
cd /d "%~dp0"

echo.
echo ==========================================================
echo    OWLIN BACKUP - FULL FOLDER SNAPSHOT (Windows 10/11)
echo ==========================================================
echo  Root: "%OWLIN_ROOT%"
echo.

:: 2) Candidate destinations (in order)
set "DEST_1=C:\Owlin Backups"
set "DEST_2=%USERPROFILE%\Documents\Owlin Backups"
set "DEST_3=%USERPROFILE%\Desktop\Owlin Backups"
set "DEST_4=%TEMP%\OwlinBackups"

:: 3) Pick first writable destination
set "BACKUP_DIR="
for %%D in ("%DEST_1%" "%DEST_2%" "%DEST_3%" "%DEST_4%") do (
  if not defined BACKUP_DIR (
    set "try=%%~fD"
    if not exist "%%~fD" (
      mkdir "%%~fD" >nul 2>&1
    )
    rem Write test
    echo test > "%%~fD\.write_test.tmp" 2>nul
    if exist "%%~fD\.write_test.tmp" (
      del "%%~fD\.write_test.tmp" >nul 2>&1
      set "BACKUP_DIR=%%~fD"
      echo ✅ Using backup destination: "%%~fD"
    ) else (
      echo ⚠️  Not writable: "%%~fD" — trying next...
    )
  )
)

if not defined BACKUP_DIR (
  echo ❌ ERROR: No writable backup destination found.
  echo Tried: 
  echo   - %DEST_1%
  echo   - %DEST_2%
  echo   - %DEST_3%
  echo   - %DEST_4%
  echo.
  echo Exiting.
  pause
  exit /b 1
)

echo.

:: 4) Clean timestamp via PowerShell (locale-safe)
for /f "usebackq delims=" %%T in (`powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'"`) do set "TS=%%T"

:: 5) Build archive filename
set "ZIP_NAME=Owlin_Backup_%TS%.zip"
set "ZIP_PATH=%BACKUP_DIR%\%ZIP_NAME%"
echo 📦 Archive: "%ZIP_PATH%"
echo.

:: 6) Prefer 7-Zip if available; else use PowerShell+Robocopy staging
set "SEVENZIP_EXE="
:: Try PATH
where 7z >nul 2>&1 && for /f "delims=" %%p in ('where 7z') do if not defined SEVENZIP_EXE set "SEVENZIP_EXE=%%~fp"
:: Try default install
if not defined SEVENZIP_EXE if exist "%ProgramFiles%\7-Zip\7z.exe" set "SEVENZIP_EXE=%ProgramFiles%\7-Zip\7z.exe"
if not defined SEVENZIP_EXE if exist "%ProgramFiles(x86)%\7-Zip\7z.exe" set "SEVENZIP_EXE=%ProgramFiles(x86)%\7-Zip\7z.exe"

:: 7) Run compression
if defined SEVENZIP_EXE (
  echo 🛠 Using 7-Zip: "%SEVENZIP_EXE%"
  echo 🔍 Excluding: node_modules, __pycache__, .git, .venv
  pushd "%OWLIN_ROOT%"
  "%SEVENZIP_EXE%" a -tzip "%ZIP_PATH%" ".\*" -mx=5 ^
    -xr!node_modules -xr!__pycache__ -xr!.git -xr!.venv -xr!*.log -xr!*.tmp >nul
  set "ZIP_RC=%ERRORLEVEL%"
  popd
) else (
  echo 🛠 7-Zip not found. Using PowerShell + Robocopy staging...
  set "STAGE=%TEMP%\OwlinBackupStage_%RANDOM%%RANDOM%"
  echo 🧪 Creating staging folder: "%STAGE%"
  mkdir "%STAGE%" >nul 2>&1

  echo 🔍 Mirroring (robocopy) with exclusions...
  rem /E = include subdirs, including empty; /XD excludes dirs
  robocopy "%OWLIN_ROOT%" "%STAGE%" /E /NFL /NDL /NJH /NJS /NP ^
    /XD node_modules __pycache__ .git .venv ^
    /XF *.log *.tmp >nul
  set "RC=%ERRORLEVEL%"
  rem Robocopy exit codes: 0,1 are OK; 2+ mean some mismatches but still may be OK for backup.
  if %RC% GEQ 8 (
    echo ❌ Robocopy failed with code %RC%.
    rmdir /s /q "%STAGE%" >nul 2>&1
    pause
    exit /b 2
  )

  echo 🗜 Compressing staging folder with PowerShell...
  powershell -NoProfile -Command ^
    "Compress-Archive -Path '%STAGE%\*' -DestinationPath '%ZIP_PATH%' -CompressionLevel Optimal -Force" >nul 2>&1
  set "ZIP_RC=%ERRORLEVEL%"

  echo 🧹 Cleaning staging folder...
  rmdir /s /q "%STAGE%" >nul 2>&1
)

if not "%ZIP_RC%"=="0" (
  echo ❌ ERROR: Compression failed (code %ZIP_RC%).
  if exist "%ZIP_PATH%" del "%ZIP_PATH%" >nul 2>&1
  pause
  exit /b 3
)

:: 8) Show size
for %%A in ("%ZIP_PATH%") do set "ZIP_SIZE=%%~zA"
echo ✅ Backup created.
echo    → %ZIP_PATH%
echo    → Size: %ZIP_SIZE% bytes
echo.

:: 9) Generate SHA256 checksum (PowerShell preferred; fallback to certutil)
set "SHA_PATH=%ZIP_PATH%.sha256.txt"
powershell -NoProfile -Command ^
  "$h=Get-FileHash -Algorithm SHA256 -LiteralPath '%ZIP_PATH%'; ('{0} *{1}' -f $h.Hash, Split-Path -Leaf '%ZIP_PATH%') | Out-File -FilePath '%SHA_PATH%' -Encoding ascii" >nul 2>&1

if not exist "%SHA_PATH%" (
  echo ⚠️  PowerShell hashing failed. Trying certutil...
  certutil -hashfile "%ZIP_PATH%" SHA256 > "%SHA_PATH%.tmp" 2>nul
  if exist "%SHA_PATH%.tmp" (
    rem Normalize certutil output: keep the hash line only
    for /f "tokens=1 delims= " %%H in ('findstr /R "^[0-9A-F][0-9A-F]" "%SHA_PATH%.tmp"') do (
      >"%SHA_PATH%" echo %%H *%ZIP_NAME%
    )
    del "%SHA_PATH%.tmp" >nul 2>&1
  )
)

if exist "%SHA_PATH%" (
  echo 🧾 SHA256: "%SHA_PATH%"
) else (
  echo ⚠️  Could not create SHA256 file.
)

echo.
echo 📂 Existing backups in "%BACKUP_DIR%":
dir "%BACKUP_DIR%\Owlin_Backup_*.zip" /O:-D 2>nul | more
echo.

echo ℹ️  RESTORE: 
echo    1) Unzip "%ZIP_PATH%" to your target folder.
echo    2) Replace the existing Owlin folder or keep as a dated snapshot.
echo.

echo 🎉 Done.
echo.

:: Show last backup result
for /f "delims=" %%F in ('dir "%BACKUP_DIR%\Owlin_Backup_*.zip" /B /O:-D 2^>nul ^| findstr /R "Owlin_Backup_.*\.zip$" ^| findstr /V "MONTHLY" ^| findstr /N "^" ^| findstr "^1:"') do (
  set "LATEST_BACKUP=%%F"
  set "LATEST_BACKUP=!LATEST_BACKUP:*:=!"
)
if defined LATEST_BACKUP (
  echo 📋 Latest backup: !LATEST_BACKUP!
  for %%A in ("%BACKUP_DIR%\!LATEST_BACKUP!") do (
    set "LATEST_SIZE=%%~zA"
    set /a "LATEST_SIZE_MB=!LATEST_SIZE!/1024/1024"
    echo    Size: !LATEST_SIZE_MB! MB
  )
  if exist "%BACKUP_DIR%\!LATEST_BACKUP!.sha256.txt" (
    echo    ✅ SHA256 checksum available
  ) else (
    echo    ⚠️  No SHA256 checksum found
  )
) else (
  echo 📋 No previous backups found
)

pause
exit /b 0
