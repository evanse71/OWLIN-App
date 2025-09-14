# OWLIN - Create Start Menu and Startup Shortcuts
# Usage: .\scripts\create_shortcuts.ps1 [-AutoStart]

param(
    [switch]$AutoStart
)

# Ensure we're running from the repo root
$RepoRoot = (Split-Path -Parent $MyInvocation.MyCommand.Path) | Join-Path ".." | Resolve-Path
$LauncherPath = Join-Path $RepoRoot "scripts\launch_owlin_dev.bat"

Write-Host "OWLIN - Creating Shortcuts"
Write-Host "=========================="
Write-Host ""

# Verify launcher exists
if (-not (Test-Path $LauncherPath)) {
    Write-Host "ERROR: Launcher not found at $LauncherPath"
    exit 1
}

Write-Host "Repo Root: $RepoRoot"
Write-Host "Launcher: $LauncherPath"
Write-Host ""

# Create WScript.Shell COM object
$WshShell = New-Object -ComObject WScript.Shell

# Create Start Menu shortcut
$StartMenuPath = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$StartMenuLnk = Join-Path $StartMenuPath "Owlin Dev.lnk"

Write-Host "Creating Start Menu shortcut..."
$Shortcut = $WshShell.CreateShortcut($StartMenuLnk)
$Shortcut.TargetPath = "cmd.exe"
$Shortcut.Arguments = "/c `"$LauncherPath`""
$Shortcut.WorkingDirectory = $RepoRoot
$Shortcut.Description = "Launch Owlin Development Environment"
$Shortcut.Save()

Write-Host "Start Menu shortcut created: $StartMenuLnk"

# Create Startup shortcut if requested
if ($AutoStart) {
    $StartupPath = [System.Environment]::GetFolderPath("Startup")
    $StartupLnk = Join-Path $StartupPath "Owlin Dev.lnk"
    
    Write-Host "Creating Startup shortcut..."
    $StartupShortcut = $WshShell.CreateShortcut($StartupLnk)
    $StartupShortcut.TargetPath = "cmd.exe"
    $StartupShortcut.Arguments = "/c `"$LauncherPath`""
    $StartupShortcut.WorkingDirectory = $RepoRoot
    $StartupShortcut.Description = "Launch Owlin Development Environment (Auto-start)"
    $StartupShortcut.Save()
    
    Write-Host "Startup shortcut created: $StartupLnk"
}

Write-Host ""
Write-Host "SUCCESS! Shortcuts created successfully."
Write-Host ""
Write-Host "Start Menu: Search for 'Owlin Dev' in Start Menu"
if ($AutoStart) {
    Write-Host "Startup: Owlin will auto-start when Windows boots"
}
Write-Host ""
Write-Host "Usage: Double-click 'Owlin Dev' shortcut to launch the full app"
