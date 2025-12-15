# TASK: Run the Owlin backup immediately and show me the result.

## Steps:
1) Open a terminal at the Owlin project root (contains Backup-Everything.bat)
2) Execute:
   - **Windows PowerShell:**
     ```powershell
     $ts = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
     $logDir = "$env:USERPROFILE\Documents\Owlin Backups\logs"
     New-Item -ItemType Directory -Force -Path $logDir | Out-Null
     $log = Join-Path $logDir "run_$ts.log"
     cmd /c ".\Backup-Everything.bat" *>> "$log"
     Get-Content -Tail 200 "$log"
     ```

   - **Windows Command Prompt:**
     ```cmd
     .\Backup-Everything.bat
     ```

   - **Linux/macOS:**
     ```bash
     ./Backup-Everything.sh
     ```

## Deliverable:
- Paste the final lines of the log output and confirm the ZIP path and SHA256 file were created.
- Show the backup file size and location.
- Verify the backup directory contains the new files.

## Expected Output:
- ✅ Backup created successfully
- 📦 Archive path and size
- 🧾 SHA256 checksum file created
- 📂 List of existing backups in the directory
