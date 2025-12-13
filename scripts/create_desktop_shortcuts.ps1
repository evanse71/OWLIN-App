# Create Desktop Shortcuts for Owlin Launchers
# Run this from the repo root to create desktop shortcuts

$ErrorActionPreference = "Stop"

Write-Host "Creating desktop shortcuts for Owlin launchers..." -ForegroundColor Cyan

# Get current directory (should be repo root)
$RepoRoot = Get-Location
$Desktop = [Environment]::GetFolderPath("Desktop")

# Create Windows shortcut
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$Desktop\Owlin - Start & Verify.lnk")
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$RepoRoot\scripts\start_and_verify.ps1`""
$Shortcut.WorkingDirectory = $RepoRoot
$Shortcut.Description = "Start Owlin with health verification"
$Shortcut.IconLocation = "powershell.exe,0"
$Shortcut.Save()

Write-Host "✅ Created: $Desktop\Owlin - Start & Verify.lnk" -ForegroundColor Green

# Create Linux/macOS .command file
$CommandFile = "$Desktop\Owlin - Start & Verify.command"
$CommandContent = @"
#!/bin/bash
cd "$($RepoRoot -replace '\\', '/')"
chmod +x scripts/start_and_verify.sh
./scripts/start_and_verify.sh
"@

# Note: On Windows, this creates a .command file that can be used on macOS
# The actual executable permissions will be set when used on macOS/Linux
[System.IO.File]::WriteAllText($CommandFile, $CommandContent)

Write-Host "✅ Created: $Desktop\Owlin - Start & Verify.command" -ForegroundColor Green
Write-Host ""
Write-Host "Desktop shortcuts created!" -ForegroundColor Yellow
Write-Host "• Windows: Double-click 'Owlin - Start & Verify.lnk'" -ForegroundColor Gray
Write-Host "• macOS: Double-click 'Owlin - Start & Verify.command'" -ForegroundColor Gray
Write-Host "• Linux: Make executable with 'chmod +x' then double-click" -ForegroundColor Gray
