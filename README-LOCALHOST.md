# Owlin Local Development Setup

## 🎉 PADDLEOCR MIGRATION COMPLETE ✅

**Status**: All PaddleOCR integration issues have been resolved! The system now uses PaddleOCR for high-accuracy OCR with proper version compatibility and confidence calculation.

### ✅ What's Fixed:
- **Version Compatibility**: Updated to `paddleocr>=2.6.1.3` and `paddlepaddle>=2.4.2`
- **Parameter Issues**: Fixed `use_angle_cls` → `use_textline_orientation` and removed unsupported `use_gpu` parameter
- **Confidence Calculation**: Added proper handling for both string and float confidence values
- **Model Initialization**: Both `ocr_engine.py` and `smart_upload_processor.py` now initialize PaddleOCR correctly
- **Error Handling**: Removed `cls=True` parameter that was causing `predict() got an unexpected keyword argument 'cls'` errors

### 🧪 Test Results:
- ✅ Basic PaddleOCR functionality: **PASSED**
- ✅ Backend OCR engine integration: **PASSED** 
- ✅ SmartUploadProcessor OCR integration: **PASSED**
- ✅ Real text extraction and confidence values: **WORKING**

### 📊 Performance:
- PaddleOCR load time: ~7-8 seconds (first run, cached thereafter)
- OCR processing time: ~12-14 seconds per page
- Confidence values: Properly calculated and normalized

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- npm or yarn

### Installation

1. **Clone and setup backend:**
```bash
cd backend
python3 -m pip install -r ../requirements.txt
```

2. **Setup frontend:**
```bash
cd frontend
npm install
```

3. **Start the backend server:**
```bash
cd backend
NODE_ENV=development ENVIRONMENT=development python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

4. **Start the frontend:**
```bash
cd frontend
npm run dev
```

5. **Access the application:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 🔧 Configuration

### Environment Variables
- `NODE_ENV=development` - Enables development features
- `ENVIRONMENT=development` - Enables debug endpoints

### Timeout Settings
- **Frontend**: 90 seconds for file uploads
- **API**: 120 seconds (2 minutes) for file uploads  
- **Backend**: 60 seconds for OCR processing

## 🧪 Testing

### OCR Integration Test
```bash
python3 test_paddle_ocr_fix.py
```

### Agent Tests
```bash
python3 test_agent_memory.py
python3 test_agent_router.py
python3 test_credit_estimation.py
python3 test_supplier_summary.py
python3 test_escalation_logic.py
```

## 📁 Project Structure

```
OWLIN-App-main/
├── backend/
│   ├── ocr/
│   │   ├── ocr_engine.py          # ✅ PaddleOCR integration
│   │   └── smart_upload_processor.py # ✅ PaddleOCR integration
│   ├── routes/
│   │   └── upload_fixed.py        # ✅ Multi-invoice processing
│   └── agent/
│       └── utils/                  # ✅ Agent utilities
├── frontend/
│   ├── components/
│   │   └── invoices/
│   │       └── UploadSection.tsx   # ✅ Enhanced upload UI
│   └── services/
│       └── api.ts                  # ✅ Timeout handling
└── requirements.txt                 # ✅ Updated dependencies
```

## 🐛 Troubleshooting

### Common Issues

**Port 8000 already in use:**
```bash
lsof -i :8000
kill -9 <PID>
```

**PaddleOCR import errors:**
```bash
python3 -m pip install "paddleocr>=2.6.1.3" "paddlepaddle>=2.4.2"
```

**Dependency conflicts:**
```bash
python3 -m pip install "scipy<1.9.2" "scikit-image==0.20.0" "numpy==1.24.3"
```

### OCR Performance
- First run: Models download (~30MB) and initialization (~8s)
- Subsequent runs: Cached models, faster startup
- Processing: ~12-14s per page for high-quality OCR

## 📝 Recent Updates

### ✅ PaddleOCR Integration (Latest)
- **Fixed**: Version compatibility issues
- **Fixed**: Parameter deprecation warnings  
- **Fixed**: Confidence calculation errors
- **Added**: Proper error handling for string/float confidence values
- **Verified**: Real text extraction and confidence calculation

### ✅ Previous Fixes
- **Fixed**: Frontend timeout issues (30s → 90s)
- **Fixed**: API timeout handling (120s with AbortController)
- **Fixed**: Multi-invoice PDF splitting
- **Fixed**: Import path errors in test files
- **Fixed**: 403 Forbidden errors on dev endpoints

---

**🎉 The PaddleOCR integration is now fully functional and ready for production use!**