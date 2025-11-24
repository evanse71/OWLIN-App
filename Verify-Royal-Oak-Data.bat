@echo off
title OWLIN - Verify Royal Oak
echo ?? Checking that backend is up and pointing at your backup...

REM Check health
powershell -NoProfile -Command ^
  "try { Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/docs | Out-Null; '? Backend reachable on :8000' } catch { '? Backend not reachable' }"

REM Show a few venues
echo.
echo ?? Venues:
powershell -NoProfile -Command ^
  "try { (Invoke-RestMethod http://127.0.0.1:8000/api/venues) | ConvertTo-Json -Depth 4 } catch { 'No venues endpoint' }"

REM Count docs
echo.
echo ?? Documents count:
powershell -NoProfile -Command ^
  "$d = Invoke-RestMethod http://127.0.0.1:8000/api/docs; 'Count = ' + $d.Count; if($d.Count -gt 0){ $d | Select-Object -First 3 | ConvertTo-Json -Depth 5 }"
pause
