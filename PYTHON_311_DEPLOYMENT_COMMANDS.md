# Python 3.11 Deployment - Complete Commands

## Copy/Paste These Commands Exactly

### Terminal 1: Setup Python 3.11 Environment

```powershell
cd C:\Users\tedev\FixPack_2025-11-02_133105

# Stop current backend (Ctrl+C if running)

# Create Python 3.11 venv
py -3.11 -m venv .venv311

# Activate
& .\.venv311\Scripts\Activate.ps1

# Upgrade pip
pip install --upgrade pip

# Install core dependencies
pip install fastapi uvicorn[standard] pillow opencv-python pypdfium2 numpy

# Install PaddleOCR (Python 3.11 compatible)
pip install paddlepaddle==2.5.2 paddleocr==2.7.3

# Install remaining requirements
pip install -r requirements.txt

# Test PaddleOCR works
python -c "from paddleocr import PaddleOCR; ocr=PaddleOCR(use_angle_cls=True,lang='en'); print('✅ PADDLEOCR 3.11 WORKS!')"

# Start backend
python -m uvicorn backend.main:app --port 8000 --reload
```

### Terminal 2: Test OCR (wait 30 seconds after backend starts)

```powershell
cd C:\Users\tedev\FixPack_2025-11-02_133105

$filename = "112be37d-afe1-4fe6-8eed-723ccbd70b58__Storiinvoiceonly1.pdf"
$response = Invoke-RestMethod -Uri "http://localhost:8000/api/dev/ocr-test?filename=$filename" -TimeoutSec 180

Write-Host "`n=== RESULTS ==="
Write-Host "Line Items: $($response.ocr_result.line_items_count)"
Write-Host "Supplier: $($response.ocr_result.supplier)"
Write-Host "Total: £$($response.ocr_result.total)"
Write-Host "Confidence: $($response.ocr_result.confidence)"

$response | ConvertTo-Json -Depth 10 | Out-File "PYTHON311_VICTORY.json"
Get-Content PYTHON311_VICTORY.json -Raw
```

---

## Expected Output

```
✅ PADDLEOCR 3.11 WORKS!

=== RESULTS ===
Line Items: 6-12
Supplier: Stori Beer & Wine CYF
Total: £123.45
Confidence: 0.85
```

---

**All forensic debugging complete. Ready for Python 3.11 deployment.**

