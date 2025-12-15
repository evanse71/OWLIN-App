# System Ready for Testing ✅

## Server Status

Both servers are now running and ready for document uploads:

### ✅ Backend Server
- **Status**: Running
- **Port**: 8000
- **URL**: http://localhost:8000
- **API Endpoint**: http://localhost:8000/api/upload
- **Health Check**: http://localhost:8000/api/invoices?dev=1

### ✅ Frontend Server
- **Status**: Running
- **Port**: 5176
- **URL**: http://localhost:5176
- **Interface**: Fully accessible with Upload button visible

## Upload Capabilities

The system is ready to accept document uploads with the following features:

### Supported File Formats
- PDF (`.pdf`)
- JPEG (`.jpg`, `.jpeg`)
- PNG (`.png`)
- HEIC/HEIF (`.heic`, `.heif`) - automatically converted to PNG

### File Size Limits
- Maximum file size: **25MB** per file

### Upload Features
- ✅ Duplicate detection (SHA-256 hash-based)
- ✅ Automatic OCR processing after upload
- ✅ File validation and error handling
- ✅ Progress tracking available

## How to Upload Documents

### Option 1: Via Web Interface (Recommended)
1. Open your browser to: **http://localhost:5176**
2. Click the **"Upload"** button in the top navigation bar
3. Select your document(s) to upload
4. The system will automatically process them with OCR

### Option 2: Via API (for testing/automation)
```bash
# Using curl
curl -X POST http://localhost:8000/api/upload \
  -F "file=@/path/to/your/document.pdf"

# Using PowerShell
$filePath = "C:\path\to\your\document.pdf"
$uri = "http://localhost:8000/api/upload"
$form = @{file = Get-Item $filePath}
Invoke-RestMethod -Uri $uri -Method Post -Form $form
```

### Option 3: Via Python Script
```python
import requests

url = "http://localhost:8000/api/upload"
with open("your_document.pdf", "rb") as f:
    files = {"file": f}
    response = requests.post(url, files=files)
    print(response.json())
```

## What Happens After Upload

1. **File Validation**: Format and size checks
2. **Duplicate Check**: SHA-256 hash verification
3. **File Storage**: Saved to `data/uploads/` directory
4. **Database Entry**: Document metadata stored
5. **OCR Processing**: Automatic OCR extraction (runs in background)
6. **Invoice Extraction**: LLM-based extraction of invoice data
7. **Status Updates**: Progress tracked via `/api/upload/status` endpoint

## Monitoring Upload Status

Check upload status via:
- **API**: `GET http://localhost:8000/api/upload/status`
- **Frontend**: Status shown in the UI after upload

## Troubleshooting

If you encounter issues:

1. **Backend not responding**: Check the backend window for errors
2. **Frontend not loading**: Check the frontend window for errors
3. **Upload fails**: Check file format and size limits
4. **OCR not processing**: Check backend logs in `backend_stdout.log`

## Next Steps

You can now:
1. ✅ Upload documents via the web interface
2. ✅ Test the OCR extraction pipeline
3. ✅ Verify invoice data extraction
4. ✅ Test the pairing and matching features

---

**System is ready for testing!** 🚀
