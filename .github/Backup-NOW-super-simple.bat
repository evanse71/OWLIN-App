@echo off
setlocal
set DEST=C:\Owlin (new contents)
set TS=%date:~10,4%-%date:~4,2%-%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TS=%TS: =0%
if not exist "%DEST%" mkdir "%DEST%"
set ZIP=%DEST%\owlin_quick_backup_%TS%.zip
echo Backing up "%cd%" to "%ZIP%" ...
powershell -NoProfile -Command "Compress-Archive -Path '.\*' -DestinationPath '%ZIP%' -Force"
if exist "%ZIP%" (
  echo OK: %ZIP%
) else (
  echo ERROR: ZIP not created. Check permissions or try running as Administrator.
)
pause
