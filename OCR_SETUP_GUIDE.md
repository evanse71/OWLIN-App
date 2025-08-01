# OCR Setup and Configuration Guide

## Overview

This guide provides comprehensive instructions for setting up and configuring OCR (Optical Character Recognition) functionality in the OWLIN application. The system supports both Tesseract OCR and PaddleOCR with automatic fallback mechanisms.

## ✅ Current Status

**All OCR functionality is working correctly!**
- ✅ Tesseract OCR: Fully functional
- ✅ PaddleOCR: Working with fallback to Tesseract
- ✅ Field Extraction: Working with enhanced parsing
- ✅ Upload Pipeline: Complete end-to-end processing
- ✅ Database Integration: Proper schema and persistence

## Dependencies

### Required System Dependencies

#### 1. **Tesseract OCR**
```bash
# macOS (using Homebrew)
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# CentOS/RHEL
sudo yum install tesseract

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

#### 2. **Poppler Utils** (for PDF processing)
```bash
# macOS
brew install poppler

# Ubuntu/Debian
sudo apt-get install poppler-utils

# CentOS/RHEL
sudo yum install poppler-utils

# Windows
# Download from: https://blog.alivate.com.au/poppler-windows/
```

### Required Python Dependencies

```bash
# Core OCR packages
pip install pytesseract
pip install Pillow
pip install pdf2image

# PaddleOCR (optional but recommended)
pip install paddlepaddle
pip install paddleocr

# Additional dependencies
pip install opencv-python
pip install numpy
```

## Configuration

### 1. **Tesseract Configuration**

Verify Tesseract installation:
```bash
# Check Tesseract version
tesseract --version

# Expected output: tesseract 5.5.1
```

### 2. **PaddleOCR Configuration**

The system automatically handles PaddleOCR configuration. If you encounter issues:

```python
# Manual PaddleOCR initialization (if needed)
from paddleocr import PaddleOCR

ocr = PaddleOCR(
    use_angle_cls=True,
    lang='en'
)
```

### 3. **Database Schema**

The system automatically creates the correct database schema:

```sql
-- Invoices table
CREATE TABLE invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_name TEXT,
    invoice_number TEXT UNIQUE,
    invoice_date TEXT,
    net_amount REAL,
    vat_amount REAL,
    total_amount REAL,
    currency TEXT,
    file_path TEXT,
    file_hash TEXT,
    ocr_confidence REAL,
    processing_status TEXT DEFAULT 'processed',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Delivery notes table
CREATE TABLE delivery_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_name TEXT,
    delivery_number TEXT UNIQUE,
    delivery_date TEXT,
    total_items INTEGER,
    file_path TEXT,
    file_hash TEXT,
    ocr_confidence REAL,
    processing_status TEXT DEFAULT 'processed',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Testing OCR Functionality

### 1. **Run the OCR Test Suite**

```bash
python3 test_ocr_functionality.py
```

**Expected Output:**
```
🚀 Starting OCR Functionality Tests
==================================================
🧪 Testing OCR Dependencies
✅ pytesseract imported successfully
   Tesseract version: 5.5.1
✅ Pillow imported successfully
✅ pdf2image imported successfully
✅ poppler-utils (pdftoppm) available
✅ OCR Dependencies PASSED

🧪 Testing Tesseract OCR
✅ Tesseract OCR successful: 7 text blocks
✅ Tesseract OCR PASSED

🧪 Testing PaddleOCR
✅ PaddleOCR successful: 7 text blocks
✅ PaddleOCR PASSED

🧪 Testing Field Extraction
✅ Field extraction successful
✅ Field Extraction PASSED

🧪 Testing Upload Pipeline
✅ Upload pipeline successful
✅ Upload Pipeline PASSED

==================================================
📊 Test Results: 5/5 tests passed
🎉 All OCR functionality tests passed!
✅ OCR is properly configured and working
```

### 2. **Test Individual Components**

#### Test Tesseract Only:
```python
from backend.ocr.ocr_processing import run_ocr

# Test with a sample image
results = run_ocr("path/to/test/image.png")
print(f"Found {len(results)} text blocks")
```

#### Test PaddleOCR with Fallback:
```python
from backend.ocr.ocr_processing import run_ocr_with_fallback

# Test with fallback
results = run_ocr_with_fallback("path/to/test/image.png", use_paddle_first=True)
print(f"Found {len(results)} text blocks")
```

#### Test Field Extraction:
```python
from backend.ocr.field_extractor import extract_invoice_fields

# Test with OCR results
fields = extract_invoice_fields(ocr_results)
print(f"Supplier: {fields.get('supplier_name')}")
print(f"Invoice Number: {fields.get('invoice_number')}")
```

## Error Handling

### 1. **Fail Loudly Configuration**

The system is configured to fail loudly when OCR dependencies are missing:

```python
# In ocr_processing.py
if not TESSERACT_AVAILABLE or pytesseract is None:
    error_msg = "OCR functionality is unavailable: install pytesseract and dependencies"
    logger.error(f"❌ {error_msg}")
    raise RuntimeError(error_msg)
```

### 2. **Common Error Messages and Solutions**

#### Error: "OCR functionality is unavailable"
**Solution:** Install Tesseract OCR
```bash
# macOS
brew install tesseract

# Ubuntu
sudo apt-get install tesseract-ocr
```

#### Error: "pdftoppm: command not found"
**Solution:** Install Poppler Utils
```bash
# macOS
brew install poppler

# Ubuntu
sudo apt-get install poppler-utils
```

#### Error: "PaddleOCR failed: Unknown argument"
**Solution:** Update PaddleOCR configuration
```python
# The system automatically handles this, but if manual configuration is needed:
ocr = PaddleOCR(
    use_angle_cls=True,
    lang='en'
    # Remove unsupported parameters like use_gpu, show_log
)
```

#### Error: "Database schema mismatch"
**Solution:** Recreate database
```bash
# Remove old database
rm data/owlin.db

# Let the system recreate it with correct schema
python3 -c "from backend.db_manager import init_db; init_db('data/owlin.db')"
```

## Performance Optimization

### 1. **OCR Confidence Thresholds**

The system uses configurable confidence thresholds:

```python
# In ocr_engine.py
CONFIDENCE_RERUN_THRESHOLD = 0.70  # Trigger pre-processing if below this
CONFIDENCE_REVIEW_THRESHOLD = 0.65  # Flag for manual review if below this
```

### 2. **Image Preprocessing**

Automatic image preprocessing improves OCR accuracy:

- **Deskewing**: Corrects rotated images
- **Noise Removal**: Reduces image noise
- **Contrast Enhancement**: Improves text visibility
- **Adaptive Thresholding**: Optimizes for different lighting conditions

### 3. **Fallback Strategy**

The system implements a robust fallback strategy:

1. **Primary**: PaddleOCR (if available)
2. **Fallback**: Tesseract OCR
3. **Preprocessing**: Enhanced image processing
4. **Validation**: Quality assessment of results

## Production Deployment

### 1. **System Requirements**

**Minimum Requirements:**
- Python 3.8+
- 4GB RAM
- 2GB free disk space
- Tesseract OCR 5.0+

**Recommended Requirements:**
- Python 3.9+
- 8GB RAM
- 5GB free disk space
- Tesseract OCR 5.5+
- GPU support (for PaddleOCR)

### 2. **Environment Variables**

```bash
# Optional: Set Tesseract path (if not in PATH)
export TESSERACT_CMD=/usr/local/bin/tesseract

# Optional: Set PaddleOCR model path
export PADDLEOCR_MODEL_PATH=/path/to/models
```

### 3. **Docker Deployment**

```dockerfile
# Example Dockerfile for OCR-enabled deployment
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . /app
WORKDIR /app

# Run the application
CMD ["python", "app/main.py"]
```

## Monitoring and Logging

### 1. **OCR Performance Monitoring**

The system provides comprehensive logging:

```python
# Log levels for OCR operations
logger.info("🔄 Running OCR on page 1")
logger.info("✅ OCR completed: 7 text blocks found")
logger.warning("⚠️ Low confidence results detected")
logger.error("❌ OCR processing failed")
```

### 2. **Quality Metrics**

Track OCR quality with these metrics:

- **Confidence Scores**: Average confidence per document
- **Text Extraction Rate**: Percentage of text successfully extracted
- **Field Recognition Rate**: Percentage of invoice fields correctly identified
- **Processing Time**: Time taken for OCR processing

### 3. **Error Tracking**

Monitor common OCR errors:

- **Missing Dependencies**: Tesseract/PaddleOCR not available
- **Low Confidence**: Results below threshold
- **Processing Failures**: File format issues
- **Database Errors**: Schema mismatches

## Troubleshooting

### 1. **OCR Not Working**

**Checklist:**
- [ ] Tesseract installed and in PATH
- [ ] Python packages installed (pytesseract, Pillow, pdf2image)
- [ ] Poppler Utils installed (for PDF processing)
- [ ] Database schema is correct
- [ ] File permissions allow reading uploaded files

### 2. **Low OCR Accuracy**

**Solutions:**
- Ensure high-quality input images (300 DPI minimum)
- Use proper lighting and contrast
- Avoid heavily skewed or damaged documents
- Consider preprocessing images before upload

### 3. **Slow Processing**

**Optimizations:**
- Use SSD storage for better I/O performance
- Increase RAM allocation
- Consider GPU acceleration for PaddleOCR
- Implement batch processing for multiple files

### 4. **Database Issues**

**Common Solutions:**
- Recreate database with correct schema
- Check file permissions for database directory
- Verify SQLite version compatibility
- Clear old database files if corrupted

## Support

### 1. **Testing Your Setup**

Run the comprehensive test suite:
```bash
python3 test_ocr_functionality.py
```

### 2. **Getting Help**

If you encounter issues:

1. **Check the logs** for detailed error messages
2. **Run the test suite** to identify specific problems
3. **Verify dependencies** are correctly installed
4. **Check system requirements** are met

### 3. **Reporting Issues**

When reporting issues, include:

- **System information** (OS, Python version)
- **Dependency versions** (Tesseract, PaddleOCR)
- **Error logs** from the application
- **Test results** from `test_ocr_functionality.py`

---

**Status**: ✅ OCR functionality is fully operational
**Last Updated**: July 30, 2024
**Version**: 1.0.0 