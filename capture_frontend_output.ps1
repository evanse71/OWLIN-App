# Capture Frontend Startup Output
$ErrorActionPreference = "Continue"

$frontendDir = "C:\Users\tedev\FixPack_2025-11-02_133105\frontend_clean"
$outputFile = "C:\Users\tedev\FixPack_2025-11-02_133105\frontend_startup_output.txt"
$errorFile = "C:\Users\tedev\FixPack_2025-11-02_133105\frontend_startup_errors.txt"

Write-Host "Starting frontend and capturing output..." -ForegroundColor Yellow
Write-Host "Output will be saved to: $outputFile" -ForegroundColor Yellow
Write-Host "Errors will be saved to: $errorFile" -ForegroundColor Yellow
Write-Host ""

Push-Location $frontendDir

# Start npm run dev and capture both stdout and stderr
$process = Start-Process -FilePath "npm" `
    -ArgumentList "run","dev","--","--port","5176" `
    -NoNewWindow `
    -PassThru `
    -RedirectStandardOutput $outputFile `
    -RedirectStandardError $errorFile

Write-Host "Process started (PID: $($process.Id))" -ForegroundColor Green
Write-Host "Waiting 15 seconds for server to start or show errors..." -ForegroundColor Yellow

Start-Sleep -Seconds 15

# Check if process is still running
$stillRunning = Get-Process -Id $process.Id -ErrorAction SilentlyContinue
if ($stillRunning) {
    Write-Host "Process is still running - server may have started successfully!" -ForegroundColor Green
} else {
    Write-Host "Process has exited - check error file for details" -ForegroundColor Red
}

# Read and display output
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   OUTPUT (last 30 lines)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
if (Test-Path $outputFile) {
    Get-Content $outputFile -Tail 30 | ForEach-Object { Write-Host $_ }
} else {
    Write-Host "Output file not created yet" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   ERRORS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
if (Test-Path $errorFile) {
    $errorContent = Get-Content $errorFile -Raw
    if ($errorContent -and $errorContent.Trim().Length -gt 0) {
        Get-Content $errorFile | ForEach-Object { Write-Host $_ -ForegroundColor Red }
    } else {
        Write-Host "No errors captured" -ForegroundColor Green
    }
} else {
    Write-Host "Error file not created yet" -ForegroundColor Yellow
}

# Check port
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   PORT 5176 STATUS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
$portCheck = netstat -ano | Select-String "5176.*LISTENING"
if ($portCheck) {
    Write-Host "SUCCESS: Port 5176 is LISTENING!" -ForegroundColor Green
    $portCheck | ForEach-Object { Write-Host $_ -ForegroundColor Gray }
} else {
    Write-Host "FAILED: Port 5176 is NOT listening" -ForegroundColor Red
}

Write-Host ""
Write-Host "Full output saved to: $outputFile" -ForegroundColor Yellow
Write-Host "Full errors saved to: $errorFile" -ForegroundColor Yellow

Pop-Location

