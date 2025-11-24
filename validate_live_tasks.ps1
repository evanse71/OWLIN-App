# Live Task UI + Anti-Stall Validation Script
# Run this after starting Agent mode to validate the implementation

Write-Host "=== Live Task UI + Anti-Stall Validation ===" -ForegroundColor Cyan
Write-Host ""

# 1) Fast Smoke Test
Write-Host "1. FAST SMOKE TEST" -ForegroundColor Yellow
Write-Host "   Start Agent mode with: 'Agent: diagnose missing invoice data'"
Write-Host "   Within 3-5 seconds, verify:" -ForegroundColor White
Write-Host "   ✓ Plan list renders (≥5 tasks)"
Write-Host "   ✓ Heartbeat dot pulses every ~2s"
Write-Host "   ✓ At least one task_update flips pending → running"
Write-Host "   ✓ Phase progress counter appears (e.g., reads 0/...)"
Write-Host ""

# 2) Backend SSE Stream Test
Write-Host "2. BACKEND SSE STREAM TEST" -ForegroundColor Yellow
Write-Host "   Run this command to capture SSE events:" -ForegroundColor White
Write-Host ""
Write-Host '   $uri = "http://127.0.0.1:8000/api/chat/stream"'
Write-Host '   $body = @{ message = "Agent: diagnose missing invoice data" ; use_agent_mode = $true } | ConvertTo-Json'
Write-Host '   Invoke-WebRequest -Uri $uri -Method POST -Body $body -ContentType "application/json" -OutFile sse.txt'
Write-Host ""
Write-Host "   Then watch in real-time:" -ForegroundColor White
Write-Host "   Get-Content .\sse.txt -Wait"
Write-Host ""
Write-Host "   Expected events:" -ForegroundColor White
Write-Host "   - data: {`"type`":`"plan`", ...}"
Write-Host "   - data: {`"type`":`"heartbeat`", ...}"
Write-Host "   - data: {`"type`":`"task_update`", ...}"
Write-Host "   - data: {`"type`":`"progress`", ...}"
Write-Host ""

# 3) Metrics Check
Write-Host "3. METRICS CHECK" -ForegroundColor Yellow
Write-Host "   Check for timing gaps:" -ForegroundColor White
Write-Host ""
if (Test-Path "data\chat_metrics.jsonl") {
    Write-Host "   Last 50 timing lines:" -ForegroundColor White
    Get-Content data\chat_metrics.jsonl -Tail 50 | Select-String '"phase":"(build_plan|searches|reads|traces|analysis_call|first_token|totals)"'
    Write-Host ""
    Write-Host "   FAIL if >10s gap between lines during active run" -ForegroundColor Red
} else {
    Write-Host "   ⚠ chat_metrics.jsonl not found - metrics may not be enabled" -ForegroundColor Yellow
}
Write-Host ""

# 4) Performance Thresholds
Write-Host "4. PERFORMANCE THRESHOLDS" -ForegroundColor Yellow
Write-Host "   Must meet:" -ForegroundColor White
Write-Host "   - Plan emitted: ≤ 1.0s"
Write-Host "   - Heartbeat cadence: 2s ± 0.5s always"
Write-Host "   - First visible task_update: ≤ 3.0s"
Write-Host "   - First token (analysis_call → first_token): ≤ 10s"
Write-Host "   - Turn timeout (Agent): ≤ 60-90s"
Write-Host "   - Overall run: ≤ 8 min"
Write-Host ""

# 5) Original Business Problem Check
Write-Host "5. ORIGINAL BUSINESS PROBLEM CHECK" -ForegroundColor Yellow
Write-Host "   A) API status payload:" -ForegroundColor White
Write-Host '   curl http://127.0.0.1:8000/api/upload/status?doc_id=REPLACE'
Write-Host "   Expected: supplier, date, total, line_items/lineItems, status"
Write-Host ""
Write-Host "   B) DB has line items?" -ForegroundColor White
if (Test-Path "data\owlin.db") {
    Write-Host '   sqlite3 data\owlin.db "SELECT invoice_id, COUNT(*) items FROM invoice_line_items GROUP BY invoice_id ORDER BY invoice_id DESC LIMIT 5;"'
} else {
    Write-Host "   ⚠ Database file not found" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "   C) Frontend normalization functions exist?" -ForegroundColor White
if (Test-Path "frontend_clean\src\lib\api.ts") {
    $found = Select-String -Path frontend_clean\src\lib\api.ts -Pattern "camelCase|normalizeInvoiceRecord|normalizeInvoicesPayload"
    if ($found) {
        Write-Host "   ✓ Found normalization functions" -ForegroundColor Green
    } else {
        Write-Host "   ⚠ Normalization functions not found" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ⚠ api.ts not found" -ForegroundColor Yellow
}
Write-Host ""

# 6) Agent Prompt
Write-Host "6. AGENT PROMPT TO EXERCISE UI" -ForegroundColor Yellow
Write-Host "   Message:" -ForegroundColor White
Write-Host '   "Agent: Diagnose why the uploaded invoice shows an empty card."'
Write-Host ""
Write-Host "   Expected plan tasks:" -ForegroundColor White
Write-Host "   - READ ocr_service.py"
Write-Host "   - READ db.py"
Write-Host "   - READ api.ts"
Write-Host "   - READ upload.ts"
Write-Host "   - READ Invoices.tsx"
Write-Host "   - GREP line_items|lineItems|doc_id|invoice_id|status|supplier|total_value"
Write-Host "   - TRACE upload.ts → ocr_service.py → db.py → API response → api.ts → Invoices.tsx"
Write-Host ""

Write-Host "=== Validation Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "If any checks fail, note which acceptance step failed:" -ForegroundColor Yellow
Write-Host "  - Plan didn't appear within 2s"
Write-Host "  - Heartbeat not pulsing"
Write-Host "  - Tasks never flip to running"
Write-Host "  - first_token > 10s"
Write-Host "  - etc."
Write-Host ""

