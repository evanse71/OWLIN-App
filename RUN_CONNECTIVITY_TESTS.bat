@echo off
echo ========================================
echo    Port 5176 Connectivity Tests
echo ========================================
echo.

echo [1] Checking if port 5176 is listening...
netstat -ano | findstr "5176.*LISTENING"
echo.

echo [2] Testing TCP connection...
powershell -Command "Test-NetConnection -ComputerName localhost -Port 5176 -WarningAction SilentlyContinue | Select-Object TcpTestSucceeded,RemoteAddress,RemotePort | Format-List"
echo.

echo [3] Testing HTTP request to http://localhost:5176/...
powershell -Command "try { $r = Invoke-WebRequest 'http://localhost:5176/' -UseBasicParsing -TimeoutSec 5; Write-Host 'SUCCESS - Status:' $r.StatusCode 'Length:' $r.Content.Length } catch { Write-Host 'FAILED -' $_.Exception.Message }"
echo.

echo [4] Testing HTTP request to http://127.0.0.1:5176/...
powershell -Command "try { $r = Invoke-WebRequest 'http://127.0.0.1:5176/' -UseBasicParsing -TimeoutSec 5; Write-Host 'SUCCESS - Status:' $r.StatusCode 'Length:' $r.Content.Length } catch { Write-Host 'FAILED -' $_.Exception.Message }"
echo.

echo [5] Testing HTTP request to http://192.168.0.101:5176/...
powershell -Command "try { $r = Invoke-WebRequest 'http://192.168.0.101:5176/' -UseBasicParsing -TimeoutSec 5; Write-Host 'SUCCESS - Status:' $r.StatusCode 'Length:' $r.Content.Length } catch { Write-Host 'FAILED -' $_.Exception.Message }"
echo.

echo ========================================
echo    Tests Complete
echo ========================================
pause

