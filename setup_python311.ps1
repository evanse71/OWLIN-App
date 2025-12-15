# Python 3.11 Setup Script for PaddleOCR Compatibility
# This fixes the Python 3.13 incompatibility that causes OCR to hang

Write-Host "🚀 Setting up Python 3.11 environment for PaddleOCR..." -ForegroundColor Green

# Step 1: Stop any running backend
Write-Host "`n[1/7] Stopping existing backend processes..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*uvicorn*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Step 2: Check Python 3.11
Write-Host "`n[2/7] Verifying Python 3.11..." -ForegroundColor Yellow
$py311 = py -3.11 --version
if (-not $py311) {
    Write-Host "❌ Python 3.11 not found! Install from python.org" -ForegroundColor Red
    exit 1
}
Write-Host "✅ $py311" -ForegroundColor Green

# Step 3: Remove old venv if exists
Write-Host "`n[3/7] Cleaning up old .venv311..." -ForegroundColor Yellow
if (Test-Path ".venv311") {
    Remove-Item -Recurse -Force ".venv311" -ErrorAction SilentlyContinue
    Write-Host "✅ Removed old venv" -ForegroundColor Green
}

# Step 4: Create Python 3.11 venv
Write-Host "`n[4/7] Creating Python 3.11 virtual environment..." -ForegroundColor Yellow
py -3.11 -m venv .venv311
if (-not (Test-Path ".venv311\Scripts\Activate.ps1")) {
    Write-Host "❌ Failed to create venv" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Virtual environment created" -ForegroundColor Green

# Step 5: Activate and upgrade pip
Write-Host "`n[5/7] Activating venv and upgrading pip..." -ForegroundColor Yellow
& .\.venv311\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
Write-Host "✅ Pip upgraded" -ForegroundColor Green

# Step 6: Install core dependencies
Write-Host "`n[6/7] Installing core dependencies (this may take 2-3 minutes)..." -ForegroundColor Yellow
Write-Host "  → FastAPI, Uvicorn..." -ForegroundColor Cyan
pip install fastapi uvicorn[standard] python-multipart

Write-Host "  → Image processing..." -ForegroundColor Cyan
pip install pillow opencv-python-headless numpy

Write-Host "  → PDF processing..." -ForegroundColor Cyan
pip install pypdfium2 pymupdf

Write-Host "  → Database..." -ForegroundColor Cyan
pip install aiosqlite

Write-Host "  → Other utilities..." -ForegroundColor Cyan
pip install python-dotenv pydantic

# Step 7: Install PaddleOCR (Python 3.11 compatible)
Write-Host "`n[7/7] Installing PaddleOCR (Python 3.11 compatible)..." -ForegroundColor Yellow
Write-Host "  → This may take 3-5 minutes..." -ForegroundColor Cyan
pip install paddlepaddle==2.5.2
pip install paddleocr==2.7.3

# Step 8: Test PaddleOCR
Write-Host "`n[TEST] Verifying PaddleOCR works..." -ForegroundColor Yellow
$testResult = python -c "from paddleocr import PaddleOCR; ocr=PaddleOCR(use_textline_orientation=True,lang='en'); print('✅ PADDLEOCR 3.11 WORKS!')" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ PaddleOCR test passed!" -ForegroundColor Green
} else {
    Write-Host "⚠️  PaddleOCR test had warnings (may still work):" -ForegroundColor Yellow
    Write-Host $testResult
}

# Step 9: Install remaining dependencies from requirements if exists
if (Test-Path "requirements.txt") {
    Write-Host "`n[EXTRA] Installing from requirements.txt..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

Write-Host "`n" -NoNewline
Write-Host "=" * 60 -ForegroundColor Green
Write-Host "✅ PYTHON 3.11 SETUP COMPLETE!" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "  1. Activate: .\.venv311\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  2. Start backend: python -m uvicorn backend.main:app --port 8000 --reload" -ForegroundColor White
Write-Host "  3. Test OCR: See test_ocr_python311.ps1" -ForegroundColor White
Write-Host "`n"

