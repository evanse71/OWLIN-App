# Final Integration Test - PowerShell Commands

## Quick Start (Copy & Paste)

### Step 1: Navigate to Project Directory
```powershell
cd C:\Users\tedev\FixPack_2025-11-02_133105
```

### Step 2: Start Log Monitoring (Run in a NEW PowerShell Window)
```powershell
cd C:\Users\tedev\FixPack_2025-11-02_133105
Get-Content backend_stdout.log -Tail 50 -Wait
```

**OR use the monitoring script:**
```powershell
cd C:\Users\tedev\FixPack_2025-11-02_133105
.\watch_llm_logs.ps1
```

### Step 3: Upload the File
1. Open your browser: `http://localhost:5176`
2. Go to Invoices page
3. Click "Upload" button
4. Select: `C:\Users\tedev\Downloads\Stori DN only _Fresh_20251204_211434.pdf`
5. Watch the PowerShell window for logs

---

## Alternative: Check Logs After Upload

If you already uploaded, check recent logs:

```powershell
cd C:\Users\tedev\FixPack_2025-11-02_133105
Get-Content backend_stdout.log -Tail 100 | Select-String -Pattern "LLM|PaddleOCR|EXTRACTION"
```

---

## What to Look For

The logs should show this sequence:

```
✅ PaddleOCR initialized
✅ [LLM_EXTRACTION] ⚡ Starting LLM reconstruction
✅ [LLM_PARSER] Sending ... text lines
✅ [LLM_PARSER] Extracted X line items
✅ [LLM_PARSER] Math check passed
✅ [LLM_PARSER] Aligned X/X items
✅ [LLM_PARSER] Success
```

---

## Troubleshooting

### If backend is not running:
```powershell
cd C:\Users\tedev\FixPack_2025-11-02_133105
.\start_backend_5176.bat
```

### Check backend health:
```powershell
curl http://localhost:5176/api/health
```

### View all recent LLM-related logs:
```powershell
cd C:\Users\tedev\FixPack_2025-11-02_133105
Get-Content backend_stdout.log | Select-String -Pattern "LLM" | Select-Object -Last 20
```

