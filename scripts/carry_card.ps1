# OWLIN - Carry Card (Quick Reference)
# Copy-paste these commands for instant Owlin launch

Write-Host "🎯 OWLIN CARRY CARD" -ForegroundColor Cyan
Write-Host "==================" -ForegroundColor Cyan
Write-Host ""

Write-Host "🚀 LAUNCH (Single Port):" -ForegroundColor Green
Write-Host "  .\scripts\start_and_verify.ps1" -ForegroundColor White
Write-Host "  # OR" -ForegroundColor Gray
Write-Host "  python -m backend.final_single_port" -ForegroundColor White
Write-Host ""

Write-Host "🌐 OPEN:" -ForegroundColor Green
Write-Host "  http://127.0.0.1:8001" -ForegroundColor White
Write-Host ""

Write-Host "⚡ 10-SECOND SANITY:" -ForegroundColor Green
Write-Host "  irm http://127.0.0.1:8001/api/health | % Content" -ForegroundColor White
Write-Host "  irm http://127.0.0.1:8001/api/status | % Content" -ForegroundColor White
Write-Host ""

Write-Host "🔧 FULL NEXT.JS SSR (One Port):" -ForegroundColor Green
Write-Host "  # Terminal 1:" -ForegroundColor Gray
Write-Host "  npm run build && npm run start" -ForegroundColor White
Write-Host "  # Terminal 2:" -ForegroundColor Gray
Write-Host "  `$env:NEXT_BASE=`"http://127.0.0.1:3000`"" -ForegroundColor White
Write-Host "  `$env:UI_MODE=`"PROXY_NEXT`"" -ForegroundColor White
Write-Host "  python -m backend.final_single_port" -ForegroundColor White
Write-Host ""

Write-Host "🛠️ QUICK FIXES:" -ForegroundColor Green
Write-Host "  # API not mounted:" -ForegroundColor Gray
Write-Host "  irm -Method POST http://127.0.0.1:8001/api/retry-mount | % Content" -ForegroundColor White
Write-Host "  # Browser cached:" -ForegroundColor Gray
Write-Host "  Ctrl+F5 (hard refresh)" -ForegroundColor White
Write-Host ""

Write-Host "✅ GUARDRAILS:" -ForegroundColor Green
Write-Host "  • Route order: /api/* → /llm/* → UI catch-all last" -ForegroundColor Gray
Write-Host "  • Frontend calls: fetch('/api/...') with leading slash" -ForegroundColor Gray
Write-Host "  • Static mode: ensure out/index.html exists" -ForegroundColor Gray
Write-Host ""
