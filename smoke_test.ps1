# OWLIN Single-Port Smoke Test
# 30-second verification of all endpoints

Write-Host "🧪 OWLIN Single-Port Smoke Test" -ForegroundColor Green
Write-Host "=" * 50

Write-Host "`n1. ❤️  Health Check" -ForegroundColor Yellow
try {
    $health = Invoke-WebRequest -Uri "http://127.0.0.1:8001/api/health" -UseBasicParsing
    Write-Host "✅ Health: $($health.StatusCode) - $($health.Content)" -ForegroundColor Green
} catch {
    Write-Host "❌ Health failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n2. 📊 Status Check" -ForegroundColor Yellow
try {
    $status = Invoke-WebRequest -Uri "http://127.0.0.1:8001/api/status" -UseBasicParsing
    $statusData = $status.Content | ConvertFrom-Json
    Write-Host "✅ Status: $($status.StatusCode)" -ForegroundColor Green
    Write-Host "   API Mounted: $($statusData.api_mounted)" -ForegroundColor Cyan
    Write-Host "   API Error: $($statusData.api_error)" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Status failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n3. 🔄 Hot-Reload Test" -ForegroundColor Yellow
try {
    $retry = Invoke-WebRequest -Method POST -Uri "http://127.0.0.1:8001/api/retry-mount" -UseBasicParsing
    Write-Host "✅ Retry Mount: $($retry.StatusCode) - $($retry.Content)" -ForegroundColor Green
} catch {
    Write-Host "❌ Retry Mount failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n4. 🎯 Real API Test" -ForegroundColor Yellow
try {
    $api = Invoke-WebRequest -Uri "http://127.0.0.1:8001/api/manual/invoices" -UseBasicParsing
    Write-Host "✅ Manual Invoices: $($api.StatusCode) - $($api.Content)" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Manual Invoices: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "`n5. 🌐 Root UI Test" -ForegroundColor Yellow
try {
    $root = Invoke-WebRequest -Uri "http://127.0.0.1:8001" -UseBasicParsing
    Write-Host "✅ Root UI: $($root.StatusCode)" -ForegroundColor Green
    if ($root.Content -like "*html*") {
        Write-Host "   📄 Serving HTML UI" -ForegroundColor Cyan
    } else {
        Write-Host "   📄 Serving JSON fallback" -ForegroundColor Cyan
    }
} catch {
    Write-Host "❌ Root UI failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n6. 🧠 LLM Proxy Test" -ForegroundColor Yellow
try {
    $llm = Invoke-WebRequest -Uri "http://127.0.0.1:8001/llm/api/tags" -UseBasicParsing
    Write-Host "✅ LLM Proxy: $($llm.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "⚠️  LLM Proxy: $($_.Exception.Message) (Ollama not running?)" -ForegroundColor Yellow
}

Write-Host "`n" + "=" * 50
Write-Host "🎉 Smoke Test Complete!" -ForegroundColor Green
Write-Host "`n📋 Access Points:" -ForegroundColor Cyan
Write-Host "   UI: http://127.0.0.1:8001" -ForegroundColor White
Write-Host "   API: http://127.0.0.1:8001/api/*" -ForegroundColor White
Write-Host "   LLM: http://127.0.0.1:8001/llm/*" -ForegroundColor White
Write-Host "   Health: http://127.0.0.1:8001/api/health" -ForegroundColor White
Write-Host "   Status: http://127.0.0.1:8001/api/status" -ForegroundColor White
