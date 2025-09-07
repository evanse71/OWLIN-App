# Multi-Page PDF Processing Implementation

## Overview

This implementation adds comprehensive support for multi-page PDF processing, utility invoice detection, and enhanced database storage to the Owlin invoice management system.

## 🚀 Key Features Implemented

### 1. **Multi-Page PDF Processing**
- **PDF Splitting**: Automatically splits multi-page PDFs into individual pages
- **Page-by-Page OCR**: Processes each page independently with Tesseract OCR
- **Individual Invoice Records**: Creates separate database records for each page
- **Page Metadata**: Tracks page numbers and parent PDF filenames

### 2. **Utility Invoice Detection**
- **Keyword-Based Detection**: Identifies utility/service invoices using comprehensive keyword lists
- **Automatic Classification**: Sets `delivery_note_required = False` for utility invoices
- **Status Management**: Assigns `status = 'utility'` for utility invoices
- **Keyword Tracking**: Stores detected utility keywords in the database

### 3. **Enhanced Database Schema**
- **New Columns Added**:
  - `ocr_text`: Full OCR text for each page
  - `parent_pdf_filename`: Original PDF filename for multi-page PDFs
  - `page_number`: Page number within the PDF
  - `is_utility_invoice`: Boolean flag for utility invoices
  - `utility_keywords`: Keywords that triggered utility classification
  - `delivery_note_required`: Boolean flag for delivery note requirement

## 📋 Technical Implementation

### Database Schema Updates

```sql
ALTER TABLE invoices ADD COLUMN ocr_text TEXT;
ALTER TABLE invoices ADD COLUMN parent_pdf_filename TEXT;
ALTER TABLE invoices ADD COLUMN page_number INTEGER DEFAULT 1;
ALTER TABLE invoices ADD COLUMN is_utility_invoice BOOLEAN DEFAULT FALSE;
ALTER TABLE invoices ADD COLUMN utility_keywords TEXT;
ALTER TABLE invoices ADD COLUMN delivery_note_required BOOLEAN DEFAULT TRUE;
```

### Utility Invoice Keywords

```python
UTILITY_KEYWORDS = [
    "electricity", "edf", "octopus", "british gas", "utility", "water", "rates", 
    "gas", "tv license", "energy", "power", "electric", "british gas", "sse", 
    "npower", "eon", "scottish power", "thames water", "severn trent", "united utilities",
    "south west water", "wessex water", "anglia water", "yorkshire water", "northumbrian water",
    "tv licence", "council tax", "rates", "service charge", "maintenance", "insurance",
    "telephone", "internet", "broadband", "mobile", "phone", "telecom", "bt", "sky",
    "virgin media", "talktalk", "vodafone", "o2", "ee", "three", "giffgaff"
]
```

### Core Functions

#### 1. `process_upload(file_bytes: bytes, filename: str) -> List[Dict[str, Any]]`
- Main function for processing uploaded files
- Handles both PDFs and images
- Returns list of processed page results

#### 2. `convert_pdf_to_images(file_bytes: bytes) -> List[Image.Image]`
- Converts PDF bytes to list of PIL Images using PyMuPDF
- High-resolution rendering (2x zoom) for better OCR quality
- Handles multi-page PDFs automatically

#### 3. `process_single_page_ocr(image: Image.Image, page_number: int, filename: str) -> Dict[str, Any]`
- Processes OCR for a single page/image
- Extracts text and metadata
- Detects utility invoices
- Returns comprehensive result dictionary

#### 4. `detect_utility_invoice(text: str, supplier_name: str) -> tuple[bool, List[str]]`
- Analyzes text and supplier name for utility keywords
- Returns boolean flag and list of detected keywords
- Supports multiple utility patterns and providers

#### 5. `create_invoice_record(file_id: str, parsed_data: Dict, confidence: float, ...) -> str`
- Enhanced database record creation
- Supports all new fields for multi-page PDFs
- Handles utility invoice classification
- Returns invoice ID for further processing

## 🔄 Processing Flow

### Multi-Page PDF Processing
1. **File Upload**: User uploads PDF or image file
2. **File Validation**: Check file type, size, and format
3. **PDF Conversion**: Convert PDF to list of images (if PDF)
4. **Page Processing**: Process each page individually:
   - OCR text extraction
   - Field parsing (invoice number, date, supplier, total)
   - Utility invoice detection
   - Status determination
5. **Database Storage**: Create separate records for each page
6. **Matching**: Attempt delivery note matching (skip for utility invoices)
7. **Response**: Return comprehensive results with page details

### Utility Invoice Detection
1. **Text Analysis**: Extract OCR text from page
2. **Keyword Matching**: Check for utility keywords in text and supplier name
3. **Pattern Matching**: Additional checks for common utility provider patterns
4. **Classification**: Set appropriate flags and status
5. **Database Storage**: Store utility classification and keywords

## 📊 API Response Format

### Multi-Page PDF Response
```json
{
  "success": true,
  "file_id": "uuid",
  "filename": "processed_filename.pdf",
  "original_name": "original_filename.pdf",
  "uploaded_at": "2025-07-23T22:00:00.000000",
  "file_size": 1024000,
  "status": "completed",
  "page_count": 3,
  "successful_pages": 3,
  "invoice_ids": ["uuid1", "uuid2", "uuid3"],
  "match_results": [...],
  "multiple_invoices": true,
  "message": "Successfully processed 3/3 pages from PDF",
  "page_details": [
    {
      "page_number": 1,
      "success": true,
      "status": "waiting",
      "is_utility_invoice": false,
      "supplier_name": "Test Company",
      "invoice_number": "INV-2024-001",
      "total_amount": 1500.0,
      "confidence_score": 85.5,
      "error": null
    }
  ]
}
```

### Single Page Response
```json
{
  "success": true,
  "file_id": "uuid",
  "invoice_id": "uuid",
  "filename": "processed_filename.pdf",
  "original_name": "original_filename.pdf",
  "uploaded_at": "2025-07-23T22:00:00.000000",
  "file_size": 1024000,
  "status": "utility",
  "confidence_score": 90.0,
  "parsed_data": {...},
  "match_result": null,
  "multiple_invoices": false,
  "is_utility_invoice": true,
  "delivery_note_required": false,
  "utility_keywords": ["british gas", "energy"],
  "error": null
}
```

## 🗄️ Database Records

### Invoice Table Structure
```sql
CREATE TABLE invoices (
    id TEXT PRIMARY KEY,
    file_id TEXT NOT NULL,
    invoice_number TEXT,
    invoice_date TEXT,
    supplier_name TEXT,
    total_amount REAL,
    currency TEXT DEFAULT 'GBP',
    status TEXT DEFAULT 'pending',  -- 'pending', 'scanned', 'matched', 'unmatched', 'error', 'utility', 'waiting'
    confidence REAL,
    upload_timestamp TEXT NOT NULL,
    processing_timestamp TEXT,
    delivery_note_id TEXT,
    venue TEXT,
    delivery_note_required BOOLEAN DEFAULT TRUE,
    ocr_text TEXT,  -- Full OCR text for each page
    parent_pdf_filename TEXT,  -- Original PDF filename for multi-page PDFs
    page_number INTEGER DEFAULT 1,  -- Page number within the PDF
    is_utility_invoice BOOLEAN DEFAULT FALSE,  -- Flag for utility/service invoices
    utility_keywords TEXT,  -- Keywords that triggered utility classification
    FOREIGN KEY (file_id) REFERENCES uploaded_files (id),
    FOREIGN KEY (delivery_note_id) REFERENCES delivery_notes (id)
);
```

## 🧪 Testing

### Test Script: `test_multi_page_processing.py`
- Tests multi-page PDF processing
- Tests utility invoice detection
- Verifies database record creation
- Checks API response formats

### Test Results
- ✅ Multi-page PDF processing working
- ✅ Database schema migration successful
- ✅ API endpoints responding correctly
- ✅ Utility invoice detection functional
- ✅ Enhanced database storage operational

## 🔧 Configuration

### Dependencies
- **PyMuPDF**: PDF processing and image conversion
- **PIL/Pillow**: Image processing
- **Tesseract**: OCR text extraction
- **SQLite**: Database storage

### Environment Setup
```bash
# Install dependencies
pip install PyMuPDF Pillow pytesseract

# Run database migration
python3 migrate_database.py

# Start servers
python3 start_servers.py
```

## 🚀 Usage Examples

### Upload Multi-Page PDF
```bash
curl -X POST http://localhost:8000/api/upload/invoice \
  -F "file=@multi_page_invoices.pdf"
```

### Check Database Records
```bash
curl http://localhost:8000/api/documents/invoices
```

### Test Utility Detection
```bash
python3 test_multi_page_processing.py
```

## 📈 Benefits

### 1. **Improved Efficiency**
- Process multiple invoices from single PDF upload
- Automatic page separation and processing
- Reduced manual intervention

### 2. **Enhanced Accuracy**
- Page-by-page OCR processing
- Individual confidence scoring
- Detailed error tracking per page

### 3. **Utility Invoice Support**
- Automatic detection of utility/service invoices
- Skip unnecessary delivery note matching
- Proper status classification

### 4. **Comprehensive Metadata**
- Full OCR text storage
- Page number tracking
- Parent PDF filename tracking
- Utility keyword storage

### 5. **Scalable Architecture**
- Modular processing functions
- Extensible keyword system
- Database migration support

## 🔮 Future Enhancements

### Potential Improvements
1. **Advanced OCR**: Implement enhanced OCR with better text recognition
2. **Machine Learning**: Add ML-based utility invoice classification
3. **Batch Processing**: Support for multiple file uploads
4. **Real-time Processing**: WebSocket-based real-time status updates
5. **Export Features**: PDF generation with processing results
6. **Analytics**: Processing statistics and performance metrics

## 📝 Notes

- The system automatically handles both PDFs and images
- Utility invoices are automatically flagged and skip delivery note matching
- Each page is processed independently for maximum accuracy
- Database migration preserves existing data while adding new functionality
- Comprehensive logging provides detailed processing information

---

**Implementation Status**: ✅ Complete and Functional
**Test Status**: ✅ All tests passing
**Database Status**: ✅ Schema updated and migrated
**API Status**: ✅ All endpoints working correctly 