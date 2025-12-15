# Fix Cursor Serialization Error - Simple Version
Write-Host "🔧 Fixing Cursor Serialization Error..." -ForegroundColor Cyan

# Check if Cursor is running
$cursorProcesses = Get-Process -Name "Cursor*" -ErrorAction SilentlyContinue
if ($cursorProcesses) {
    Write-Host "⚠️  Cursor is still running. Please close Cursor completely first." -ForegroundColor Yellow
    Write-Host "Press any key after closing Cursor to continue..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

# Clear Cursor cache
Write-Host "🧹 Clearing Cursor cache..." -ForegroundColor Green
$cachePaths = @(
    "$env:APPDATA\Cursor\User\workspaceStorage",
    "$env:APPDATA\Cursor\CachedData",
    "$env:APPDATA\Cursor\logs"
)

foreach ($path in $cachePaths) {
    if (Test-Path $path) {
        try {
            Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "   ✅ Cleared: $path" -ForegroundColor Green
        } catch {
            Write-Host "   ⚠️  Could not clear: $path" -ForegroundColor Yellow
        }
    }
}

# Create workspace file
Write-Host "📁 Creating optimized workspace..." -ForegroundColor Green
$workspaceFile = "C:\Users\tedev\Desktop\owlin_backup_2025-10-02_225554\owlin.code-workspace"
$workspaceContent = @'
{
    "folders": [
        {
            "path": "C:\\Users\\tedev\\Desktop\\owlin_backup_2025-10-02_225554"
        }
    ],
    "settings": {
        "files.exclude": {
            "**/__pycache__": true,
            "**/node_modules": true,
            "**/.venv": true,
            "**/*.pyc": true,
            "**/*.log": true,
            "**/*.tmp": true,
            "**/backups": true,
            "**/logs": true,
            "**/uploads": true
        }
    }
}
'@

$workspaceContent | Out-File -FilePath $workspaceFile -Encoding UTF8
Write-Host "   ✅ Created workspace file: $workspaceFile" -ForegroundColor Green

Write-Host ""
Write-Host "🎉 Fix completed! Now:" -ForegroundColor Cyan
Write-Host "1. Open Cursor" -ForegroundColor White
Write-Host "2. Open: $workspaceFile" -ForegroundColor White
Write-Host "3. The serialization error should be resolved!" -ForegroundColor Green
