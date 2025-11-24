# Monitor-Production.ps1
# Live production monitoring with alert thresholds
# BRJ Release Lock - Continuous health monitoring

param(
    [int]$IntervalSeconds = 10,
    [int]$QueueWarning = 10,
    [int]$QueueCritical = 20
)

$ErrorActionPreference = "Continue"
$baseUrl = "http://127.0.0.1:8000"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "PRODUCTION MONITOR - LIVE PULSE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Base URL: $baseUrl" -ForegroundColor Gray
Write-Host "Interval: $IntervalSeconds seconds" -ForegroundColor Gray
Write-Host "Queue Warning: $QueueWarning | Critical: $QueueCritical" -ForegroundColor Gray
Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Gray

# Header
Write-Host ("{0,-10} {1,-10} {2,-10} {3,-10} {4,-10} {5,-10}" -f `
    "TIME", "WAL", "QUEUE", "INFLIGHT", "ERRORS", "STATUS") -ForegroundColor Yellow

$iteration = 0
$lastErrorCount = 0

while ($true) {
    $iteration++
    
    try {
        # Get health details
        $health = Invoke-RestMethod "$baseUrl/api/health/details" -TimeoutSec 5
        
        # Extract metrics
        $time = (Get-Date).ToString("HH:mm:ss")
        $wal = if ($health.db_wal) { "✓" } else { "✗" }
        $queue = $health.ocr_queue
        $inflight = $health.ocr_inflight
        $errors = $health.total_errors
        
        # Determine status and color
        $status = "OK"
        $color = "Green"
        
        # Check alert conditions
        if (-not $health.db_wal) {
            $status = "CRIT:WAL"
            $color = "Red"
        }
        elseif ($queue -gt $QueueCritical) {
            $status = "CRIT:Q"
            $color = "Red"
        }
        elseif ($queue -gt $QueueWarning) {
            $status = "WARN:Q"
            $color = "Yellow"
        }
        elseif ($inflight -eq $health.ocr_max_concurrency -and $queue -gt 5) {
            $status = "WARN:FULL"
            $color = "Yellow"
        }
        
        # Check for new errors
        if ($errors -gt $lastErrorCount) {
            $newErrors = $errors - $lastErrorCount
            $status = "NEW:E($newErrors)"
            $color = "Yellow"
            $lastErrorCount = $errors
        }
        
        # Display row
        Write-Host ("{0,-10} {1,-10} {2,-10} {3,-10} {4,-10} {5,-10}" -f `
            $time, $wal, $queue, "$inflight/$($health.ocr_max_concurrency)", $errors, $status) `
            -ForegroundColor $color
        
        # Critical alerts with detail
        if ($color -eq "Red") {
            Write-Host "  ⚠️  CRITICAL ALERT: $status" -ForegroundColor Red
            
            if (-not $health.db_wal) {
                Write-Host "  Action: STOP BACKEND → Check DB initialization → Restart" -ForegroundColor Red
            }
            elseif ($queue -gt $QueueCritical) {
                Write-Host "  Action: Throttle uploads OR increase OCR_MAX_CONCURRENCY" -ForegroundColor Red
            }
        }
        
    }
    catch {
        Write-Host ("{0,-10} {1,-50}" -f `
            (Get-Date).ToString("HH:mm:ss"), "ERROR: $_") `
            -ForegroundColor Red
    }
    
    # Sleep interval
    Start-Sleep -Seconds $IntervalSeconds
}

