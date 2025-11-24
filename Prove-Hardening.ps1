# Prove-Hardening.ps1
# BRJ Reality Check: Prove all hardening features work
# Run with backend already started on port 8000

$ErrorActionPreference = "Continue"
$baseUrl = "http://127.0.0.1:8000"
$artifactsDir = "tests\artifacts\api"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "BRJ HARDENING PROOF SCRIPT" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Ensure artifacts directory exists
if (-not (Test-Path $artifactsDir)) {
    New-Item -ItemType Directory -Path $artifactsDir -Force | Out-Null
}

$results = @()

# ============================================
# 1. Check WAL Mode
# ============================================
Write-Host "[1/6] Checking SQLite WAL mode..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod "$baseUrl/api/health/details"
    
    if ($health.db_wal -eq $true) {
        Write-Host "  ✅ journal_mode: WAL" -ForegroundColor Green
        $results += "✅ WAL Mode: Enabled"
    } else {
        Write-Host "  ❌ journal_mode: NOT WAL (got: $($health.db_wal))" -ForegroundColor Red
        $results += "❌ WAL Mode: Disabled"
    }
    
    # Save health details
    $health | ConvertTo-Json -Depth 10 | Out-File "$artifactsDir\health_details.json" -Encoding UTF8
    Write-Host "  📄 Saved: $artifactsDir\health_details.json" -ForegroundColor Gray
} catch {
    Write-Host "  ❌ Failed to check health endpoint: $_" -ForegroundColor Red
    $results += "❌ WAL Mode: ERROR"
}

# ============================================
# 2. Check OCR Metrics
# ============================================
Write-Host "`n[2/6] Checking OCR concurrency metrics..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod "$baseUrl/api/health/details"
    
    $inflight = $health.ocr_inflight
    $queue = $health.ocr_queue
    $maxConc = $health.ocr_max_concurrency
    
    Write-Host "  ocr_inflight: $inflight" -ForegroundColor Gray
    Write-Host "  ocr_queue: $queue" -ForegroundColor Gray
    Write-Host "  ocr_max_concurrency: $maxConc" -ForegroundColor Gray
    
    if ($inflight -le $maxConc) {
        Write-Host "  ✅ ocr_inflight ≤ $maxConc" -ForegroundColor Green
        $results += "✅ OCR Metrics: inflight=$inflight, queue=$queue, max=$maxConc"
    } else {
        Write-Host "  ⚠️  ocr_inflight ($inflight) > max ($maxConc)" -ForegroundColor Yellow
        $results += "⚠️ OCR Metrics: inflight exceeds max"
    }
    
    if ($null -ne $health.build_sha) {
        Write-Host "  build_sha: $($health.build_sha)" -ForegroundColor Gray
    }
    if ($null -ne $health.last_doc_id) {
        Write-Host "  last_doc_id: $($health.last_doc_id)" -ForegroundColor Gray
    }
} catch {
    Write-Host "  ❌ Failed to check OCR metrics: $_" -ForegroundColor Red
    $results += "❌ OCR Metrics: ERROR"
}

# ============================================
# 3. Check Lifecycle Debug Endpoint
# ============================================
Write-Host "`n[3/6] Checking lifecycle debug endpoint..." -ForegroundColor Yellow
try {
    # Get a recent document ID from invoices
    $invoices = Invoke-RestMethod "$baseUrl/api/invoices"
    
    if ($invoices.invoices.Count -gt 0) {
        $docId = $invoices.invoices[0].id
        Write-Host "  Using doc_id: $docId" -ForegroundColor Gray
        
        $lifecycle = Invoke-RestMethod "$baseUrl/api/debug/lifecycle?doc_id=$docId"
        
        if ($lifecycle.markers.Count -gt 0) {
            Write-Host "  ✅ Lifecycle markers returned (count: $($lifecycle.markers.Count))" -ForegroundColor Green
            Write-Host "  📋 First marker: $($lifecycle.markers[0].Substring(0, [Math]::Min(80, $lifecycle.markers[0].Length)))..." -ForegroundColor Gray
            
            if ($lifecycle.truncated) {
                Write-Host "  ⚠️  Response was truncated at 2KB" -ForegroundColor Yellow
            }
            
            $results += "✅ Lifecycle: $($lifecycle.markers.Count) markers"
        } else {
            Write-Host "  ⚠️  No lifecycle markers found for doc_id: $docId" -ForegroundColor Yellow
            $results += "⚠️ Lifecycle: No markers"
        }
        
        # Save lifecycle
        $lifecycle | ConvertTo-Json -Depth 10 | Out-File "$artifactsDir\lifecycle_$docId.json" -Encoding UTF8
        Write-Host "  📄 Saved: $artifactsDir\lifecycle_$docId.json" -ForegroundColor Gray
    } else {
        Write-Host "  ⚠️  No invoices found to test lifecycle endpoint" -ForegroundColor Yellow
        $results += "⚠️ Lifecycle: No test data"
    }
} catch {
    Write-Host "  ❌ Failed to check lifecycle endpoint: $_" -ForegroundColor Red
    $results += "❌ Lifecycle: ERROR"
}

# ============================================
# 4. Check Audit Export
# ============================================
Write-Host "`n[4/6] Checking audit export endpoint..." -ForegroundColor Yellow
try {
    $fromDate = (Get-Date).AddDays(-7).ToString('yyyy-MM-dd')
    $toDate = (Get-Date).ToString('yyyy-MM-dd')
    
    Write-Host "  Exporting audit logs from $fromDate to $toDate..." -ForegroundColor Gray
    
    $auditCsvPath = "$artifactsDir\audit_export.csv"
    Invoke-WebRequest "$baseUrl/api/audit/export?from=$fromDate&to=$toDate" -OutFile $auditCsvPath
    
    if (Test-Path $auditCsvPath) {
        $lines = (Get-Content $auditCsvPath).Count
        Write-Host "  ✅ audit_export.csv generated ($lines lines)" -ForegroundColor Green
        Write-Host "  📄 Saved: $auditCsvPath" -ForegroundColor Gray
        
        # Show first few lines
        $preview = Get-Content $auditCsvPath -Head 3
        Write-Host "  Preview:" -ForegroundColor Gray
        $preview | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
        
        $results += "✅ Audit Export: $lines lines"
    } else {
        Write-Host "  ❌ audit_export.csv not generated" -ForegroundColor Red
        $results += "❌ Audit Export: Failed"
    }
} catch {
    Write-Host "  ❌ Failed to export audit logs: $_" -ForegroundColor Red
    $results += "❌ Audit Export: ERROR"
}

# ============================================
# 5. Check Log Rotation
# ============================================
Write-Host "`n[5/6] Checking log rotation..." -ForegroundColor Yellow
try {
    $logFiles = Get-ChildItem . -Filter "backend_stdout.log*" | Sort-Object Name
    
    if ($logFiles.Count -gt 0) {
        Write-Host "  ✅ Found $($logFiles.Count) log file(s):" -ForegroundColor Green
        foreach ($log in $logFiles) {
            $sizeMB = [math]::Round($log.Length / 1MB, 2)
            Write-Host "    - $($log.Name) ($sizeMB MB)" -ForegroundColor Gray
        }
        $results += "✅ Log Rotation: $($logFiles.Count) files"
    } else {
        Write-Host "  ⚠️  No log files found (backend_stdout.log*)" -ForegroundColor Yellow
        $results += "⚠️ Log Rotation: No log files"
    }
} catch {
    Write-Host "  ❌ Failed to check log files: $_" -ForegroundColor Red
    $results += "❌ Log Rotation: ERROR"
}

# ============================================
# 6. Check Footer on Static Build
# ============================================
Write-Host "`n[6/6] Checking footer on static build..." -ForegroundColor Yellow
try {
    # Check if static files exist
    $staticIndexPath = "backend\static\index.html"
    
    if (Test-Path $staticIndexPath) {
        Write-Host "  ✅ Static build exists: $staticIndexPath" -ForegroundColor Green
        
        # Check if footer component is in the bundled JS
        $jsFiles = Get-ChildItem "backend\static\assets" -Filter "index-*.js" -ErrorAction SilentlyContinue
        
        if ($jsFiles.Count -gt 0) {
            $jsContent = Get-Content $jsFiles[0].FullName -Raw
            
            if ($jsContent -match "invoices-footer-bar") {
                Write-Host "  ✅ Footer component found in bundle" -ForegroundColor Green
                $results += "✅ Footer: In static build"
            } else {
                Write-Host "  ⚠️  Footer component not found in bundle (may need rebuild)" -ForegroundColor Yellow
                $results += "⚠️ Footer: Not in bundle"
            }
        } else {
            Write-Host "  ⚠️  No JS bundle found in backend\static\assets" -ForegroundColor Yellow
            $results += "⚠️ Footer: No bundle"
        }
    } else {
        Write-Host "  ⚠️  Static build not found (run: npm run build && copy to backend\static)" -ForegroundColor Yellow
        $results += "⚠️ Footer: No static build"
    }
} catch {
    Write-Host "  ❌ Failed to check static build: $_" -ForegroundColor Red
    $results += "❌ Footer: ERROR"
}

# ============================================
# Summary
# ============================================
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "SUMMARY" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

foreach ($result in $results) {
    Write-Host $result
}

Write-Host "`n📁 Artifacts saved to: $artifactsDir" -ForegroundColor Cyan
Write-Host ""

# Check if all passed
$failedCount = ($results | Where-Object { $_ -match "❌" }).Count
$warningCount = ($results | Where-Object { $_ -match "⚠️" }).Count

if ($failedCount -eq 0 -and $warningCount -eq 0) {
    Write-Host "✅ ALL CHECKS PASSED - Production Ready!" -ForegroundColor Green
    exit 0
} elseif ($failedCount -eq 0) {
    Write-Host "⚠️  ALL CHECKS PASSED WITH WARNINGS" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "❌ SOME CHECKS FAILED - Review above" -ForegroundColor Red
    exit 1
}
