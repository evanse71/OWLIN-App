# Watch LLM Extraction Logs - Real-time Monitoring
# This script monitors backend logs for the "Golden Sequence" of LLM processing

Write-Host "=" -NoNewline
Write-Host ("=" * 79)
Write-Host "🔍 LLM EXTRACTION LOG MONITOR"
Write-Host ("=" * 80)
Write-Host ""
Write-Host "Watching for Golden Sequence markers..."
Write-Host ""
Write-Host "Expected sequence:"
Write-Host "  1. PaddleOCR initialized"
Write-Host "  2. [LLM_EXTRACTION] ⚡ Starting LLM reconstruction"
Write-Host "  3. [LLM_PARSER] Sending ... text lines"
Write-Host "  4. [LLM_PARSER] Success"
Write-Host ""
Write-Host ("=" * 80)
Write-Host ""

$logFile = "backend_stdout.log"
$lastPosition = 0

# Check if log file exists
if (-not (Test-Path $logFile)) {
    Write-Host "⚠️  Log file not found: $logFile"
    Write-Host "   Waiting for backend to create log file..."
    Write-Host ""
    
    # Wait for log file to appear
    $timeout = 30
    $elapsed = 0
    while (-not (Test-Path $logFile) -and $elapsed -lt $timeout) {
        Start-Sleep -Seconds 1
        $elapsed++
        Write-Host "." -NoNewline
    }
    Write-Host ""
    
    if (-not (Test-Path $logFile)) {
        Write-Host "❌ Log file not found after $timeout seconds"
        Write-Host "   Make sure the backend is running"
        exit 1
    }
}

Write-Host "✓ Monitoring: $logFile"
Write-Host "   (Press Ctrl+C to stop)"
Write-Host ""

# Track golden sequence markers
$markers = @{
    "PaddleOCR initialized" = $false
    "LLM_EXTRACTION" = $false
    "LLM_PARSER.*Sending" = $false
    "LLM_PARSER.*Success" = $false
    "LLM_PARSER.*Extracted" = $false
    "LLM_PARSER.*Math check" = $false
    "LLM_PARSER.*Aligned" = $false
}

function Test-Marker {
    param($line, $pattern, $name)
    
    if ($line -match $pattern) {
        if (-not $markers[$name]) {
            $markers[$name] = $true
            Write-Host "✅ $name" -ForegroundColor Green
            Write-Host "   $line" -ForegroundColor Gray
            return $true
        }
    }
    return $false
}

try {
    while ($true) {
        if (Test-Path $logFile) {
            $file = Get-Item $logFile
            $currentSize = $file.Length
            
            if ($currentSize -gt $lastPosition) {
                $stream = [System.IO.File]::OpenRead($logFile)
                $stream.Position = $lastPosition
                $reader = New-Object System.IO.StreamReader($stream)
                
                while ($null -ne ($line = $reader.ReadLine())) {
                    # Check for golden sequence markers
                    Test-Marker $line "PaddleOCR.*initialized" "PaddleOCR initialized" | Out-Null
                    Test-Marker $line "\[LLM_EXTRACTION\].*Starting" "LLM_EXTRACTION" | Out-Null
                    Test-Marker $line "\[LLM_PARSER\].*Sending" "LLM_PARSER.*Sending" | Out-Null
                    Test-Marker $line "\[LLM_PARSER\].*Success" "LLM_PARSER.*Success" | Out-Null
                    Test-Marker $line "\[LLM_PARSER\].*Extracted" "LLM_PARSER.*Extracted" | Out-Null
                    Test-Marker $line "\[LLM_PARSER\].*Math check" "LLM_PARSER.*Math check" | Out-Null
                    Test-Marker $line "\[LLM_PARSER\].*Aligned" "LLM_PARSER.*Aligned" | Out-Null
                    
                    # Show any LLM-related lines
                    if ($line -match "\[LLM") {
                        Write-Host $line -ForegroundColor Cyan
                    }
                }
                
                $reader.Close()
                $stream.Close()
                $lastPosition = $currentSize
            }
        }
        
        Start-Sleep -Milliseconds 500
    }
}
catch {
    Write-Host ""
    Write-Host "❌ Error: $_" -ForegroundColor Red
}
finally {
    Write-Host ""
    Write-Host ("=" * 80)
    Write-Host "Monitoring stopped"
}

