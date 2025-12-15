# Fix Cursor Serialization Error
# Run this script AFTER closing Cursor completely

Write-Host "🔧 Fixing Cursor Serialization Error..." -ForegroundColor Cyan
Write-Host ""

# Step 1: Check if Cursor is running
$cursorProcesses = Get-Process -Name "Cursor*" -ErrorAction SilentlyContinue
if ($cursorProcesses) {
    Write-Host "⚠️  Cursor is still running. Please close Cursor completely first." -ForegroundColor Yellow
    Write-Host "   Running processes:" -ForegroundColor Yellow
    $cursorProcesses | ForEach-Object { Write-Host "   - $($_.ProcessName) (PID: $($_.Id))" -ForegroundColor Yellow }
    Write-Host ""
    Write-Host "Press any key after closing Cursor to continue..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

# Step 2: Clear Cursor cache
Write-Host "🧹 Clearing Cursor cache..." -ForegroundColor Green
$cachePaths = @(
    "$env:APPDATA\Cursor\User\workspaceStorage",
    "$env:APPDATA\Cursor\CachedData",
    "$env:APPDATA\Cursor\logs",
    "$env:LOCALAPPDATA\Cursor\User\workspaceStorage"
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

# Step 3: Create optimized workspace configuration
Write-Host ""
Write-Host "📁 Creating optimized workspace configuration..." -ForegroundColor Green

$workspaceConfig = @"
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
        },
        "search.exclude": {
            "**/__pycache__": true,
            "**/node_modules": true,
            "**/.venv": true,
            "**/backups": true,
            "**/logs": true,
            "**/uploads": true
        },
        "files.watcherExclude": {
            "**/__pycache__": true,
            "**/node_modules": true,
            "**/.venv": true,
            "**/backups": true,
            "**/logs": true,
            "**/uploads": true
        }
    }
}
"@

$workspaceFile = "C:\Users\tedev\Desktop\owlin_backup_2025-10-02_225554\owlin.code-workspace"
$workspaceConfig | Out-File -FilePath $workspaceFile -Encoding UTF8
Write-Host "   ✅ Created workspace file: $workspaceFile" -ForegroundColor Green

# Step 4: Create .gitignore to exclude problematic files
Write-Host ""
Write-Host "📝 Creating .gitignore for better performance..." -ForegroundColor Green

$gitignoreContent = @"
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
ENV/
env/

# Logs
*.log
logs/

# Temporary files
*.tmp
*.temp
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/

# Backup files
backups/
*.zip
*.tar.gz

# Upload directories
uploads/
data/uploads/

# Node modules (if any)
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
"@

$gitignoreFile = "C:\Users\tedev\Desktop\owlin_backup_2025-10-02_225554\.gitignore"
$gitignoreContent | Out-File -FilePath $gitignoreFile -Encoding UTF8
Write-Host "   ✅ Created .gitignore: $gitignoreFile" -ForegroundColor Green

Write-Host ""
Write-Host "🎉 Cursor serialization fix completed!" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Open Cursor" -ForegroundColor White
Write-Host "2. Open the workspace file: $workspaceFile" -ForegroundColor White
Write-Host "3. Or open the main folder: C:\Users\tedev\Desktop\owlin_backup_2025-10-02_225554" -ForegroundColor White
Write-Host ""
Write-Host "This should resolve the serialization error!" -ForegroundColor Green
