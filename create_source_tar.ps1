# Create source.tar.gz excluding specified directories
$excludeDirs = @('.git', 'node_modules', '.next', 'tmp_lovable/dist')
$excludePatterns = $excludeDirs | ForEach-Object { "--exclude=$_" }
$excludePatterns += "--exclude=*.pyc"
$excludePatterns += "--exclude=__pycache__"
$excludePatterns += "--exclude=*.log"

# Use tar to create the archive
$tarArgs = @('czf', "C:\Users\tedev\Desktop\owlin_backup_2025-10-02_225554\source.tar.gz") + $excludePatterns + @('.')
& tar @tarArgs

if ($LASTEXITCODE -eq 0) {
    Write-Host "Source tar.gz created successfully"
} else {
    Write-Host "Error creating source tar.gz"
}
