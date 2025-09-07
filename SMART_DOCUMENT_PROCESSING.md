# 🧠 Smart Document Processing Pipeline

## Overview

The Smart Document Processing Pipeline is a comprehensive solution that automatically processes mixed-content PDFs, intelligently splits them into logical documents, and provides a user-friendly review interface. This implementation transforms Owlin from a simple upload tool into an intelligent document processing system.

## 🏗️ Architecture

### Backend Structure
```
backend/
├── services/
│   └── smart_upload_processor.py    # Core processing logic
├── routes/
│   ├── upload_review.py             # PDF upload and processing endpoint
│   └── confirm_splits.py            # Document confirmation endpoint
├── main.py                          # FastAPI app with new routes
└── database.py                      # Database utilities
```

### Frontend Components
```
components/document-queue/
└── SmartDocumentReviewModal.tsx     # Document review interface

pages/
└── invoices-new.tsx                 # Updated upload page

services/
└── api.ts                           # Enhanced API methods
```

## 🔄 Processing Pipeline

### 1. Upload & Preprocessing
- **Endpoint**: `POST /api/upload/review`
- **Input**: PDF file (multipart/form-data)
- **Process**:
  - Save PDF to temp directory
  - Split PDF into individual pages using PyMuPDF
  - Run OCR on each page using Tesseract
  - Classify document type using keyword matching
  - Extract metadata (supplier, dates, amounts, numbers)
  - Generate preview images

### 2. Document Grouping
- **Logic**: Group consecutive pages with same type and supplier
- **Heuristics**:
  - Same document type (invoice, delivery note, etc.)
  - Same supplier name
  - Consecutive page numbers
  - Layout similarity

### 3. User Review
- **Interface**: Modal with document cards
- **Features**:
  - Preview thumbnails for each page
  - Confidence scores for each suggestion
  - Editable document type and supplier
  - Metadata display
  - Document removal capability

### 4. Confirmation & Storage
- **Endpoint**: `POST /api/upload/confirm-splits`
- **Process**:
  - Save confirmed documents to database
  - Create appropriate table entries (invoices, delivery_notes, etc.)
  - Store page information
  - Add audit log entries

## 🛠️ Technical Implementation

### SmartUploadProcessor Class

```python
class SmartUploadProcessor:
    def __init__(self, temp_dir="temp", previews_dir="data/previews")
    
    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        # Main processing pipeline
        pages = self._split_pdf(pdf_path)
        processed_pages = [self._process_page(page) for page in pages]
        return self._group_pages_into_documents(processed_pages)
```

#### Key Methods:
- `_split_pdf()`: Split PDF into pages using PyMuPDF
- `_run_ocr()`: Extract text using Tesseract OCR
- `_classify_document()`: Classify using keyword matching
- `_extract_metadata()`: Extract supplier, dates, amounts
- `_save_preview_image()`: Generate preview thumbnails
- `_group_pages_into_documents()`: Group related pages

### Document Classification

#### Keyword Categories:
```python
DOCUMENT_KEYWORDS = {
    'invoice': [
        'invoice', 'tax total', 'vat', 'subtotal', 'net', 
        'invoice number', 'invoice date', 'total amount'
    ],
    'delivery_note': [
        'delivery note', 'goods received', 'pod', 'driver',
        'delivery date', 'delivery number'
    ],
    'utility': [
        'energy', 'kwh', 'standing charge', 'edf', 'gas',
        'electricity', 'utility bill', 'meter reading'
    ],
    'receipt': [
        'thank you', 'receipt', 'cash tendered', 'pos',
        'transaction', 'payment received'
    ]
}
```

### Metadata Extraction

#### Patterns Supported:
- **Supplier Names**: `from:`, `supplier:`, `company:`, regex patterns
- **Dates**: Multiple date formats (DD/MM/YYYY, YYYY-MM-DD, etc.)
- **Amounts**: Currency symbols, total amounts, net amounts
- **Document Numbers**: Invoice numbers, delivery note numbers

## 📊 API Endpoints

### 1. Upload for Review
```http
POST /api/upload/review
Content-Type: multipart/form-data

file: PDF file
```

**Response:**
```json
{
  "suggested_documents": [
    {
      "id": "doc_abc123",
      "type": "invoice",
      "confidence": 91,
      "supplier_name": "Bidfood",
      "pages": [1, 2],
      "preview_urls": ["/previews/doc_abc123_page1.jpg"],
      "metadata": {
        "invoice_date": "2025-01-15",
        "total_amount": 245.50,
        "invoice_number": "INV-447812"
      }
    }
  ]
}
```

### 2. Confirm Document Splits
```http
POST /api/upload/confirm-splits
Content-Type: application/json

{
  "file_name": "mixed_documents.pdf",
  "documents": [
    {
      "id": "doc_abc123",
      "type": "invoice",
      "supplier_name": "Bidfood",
      "pages": [1, 2],
      "metadata": {
        "invoice_date": "2025-01-15",
        "total_amount": 245.50,
        "invoice_number": "INV-447812"
      }
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully saved 1 document(s)",
  "document_count": 1
}
```

## 🗄️ Database Schema

### New Tables Created:
- `invoices`: Invoice-specific data
- `delivery_notes`: Delivery note data
- `utility_bills`: Utility bill data
- `receipts`: Receipt data
- `document_pages`: Page-to-document mapping
- `audit_log`: Processing audit trail

### Example Invoice Table:
```sql
CREATE TABLE invoices (
    id TEXT PRIMARY KEY,
    invoice_number TEXT,
    invoice_date TEXT,
    supplier_name TEXT,
    total_amount REAL,
    status TEXT,
    confidence REAL,
    upload_timestamp TEXT,
    original_filename TEXT,
    page_numbers TEXT
);
```

## 🎨 Frontend Interface

### Smart Upload Page
- **Single Upload Panel**: Unified interface for all PDFs
- **Smart Features Info**: Visual explanation of capabilities
- **Progress Tracking**: Real-time processing feedback
- **Error Handling**: Comprehensive error messages

### Document Review Modal
- **Document Cards**: Each suggestion in its own card
- **Confidence Badges**: Visual confidence indicators
- **Editable Fields**: Type and supplier editing
- **Page Previews**: Thumbnail previews
- **Metadata Display**: Extracted information
- **Bulk Actions**: Confirm all documents at once

## 🚀 Installation & Setup

### Dependencies
```bash
pip install -r requirements.txt
```

### Required System Dependencies
- **Tesseract OCR**: `brew install tesseract` (macOS) or `apt-get install tesseract-ocr` (Ubuntu)
- **Python Dependencies**: See `requirements.txt`

### Directory Structure
```bash
mkdir -p data/previews temp
```

## 🔧 Configuration

### Environment Variables
- `NEXT_PUBLIC_API_URL`: Backend API URL (default: http://localhost:8000/api)

### File Paths
- **Temp Directory**: `temp/` (for processing)
- **Previews Directory**: `data/previews/` (for preview images)
- **Database**: `backend/data/owlin.db`

## 🧪 Testing

### Backend Tests
```bash
python3 test_smart_backend.py
```

### Manual Testing
1. Start backend: `uvicorn backend.main:app --reload`
2. Start frontend: `npm run dev`
3. Upload a mixed-content PDF
4. Review suggested splits
5. Confirm documents

## 📈 Performance Considerations

### Optimization Strategies:
- **Parallel Processing**: OCR can be parallelized for multiple pages
- **Caching**: Preview images cached for reuse
- **Batch Processing**: Multiple documents in single request
- **Memory Management**: Cleanup of temp files

### Scalability:
- **Database Indexing**: Index on document_id, supplier_name
- **File Storage**: Consider cloud storage for large files
- **Queue Processing**: Background job processing for large PDFs

## 🔒 Security Considerations

### File Validation:
- File type validation (PDF only)
- File size limits
- Malicious file detection

### Data Protection:
- Secure file storage
- Audit logging
- User authentication (future enhancement)

## 🎯 Future Enhancements

### Planned Features:
- **Machine Learning**: Improved classification accuracy
- **Template Recognition**: Supplier-specific templates
- **Batch Processing**: Multiple file uploads
- **Advanced OCR**: Better text extraction
- **Integration**: ERP system integration

### Performance Improvements:
- **Async Processing**: Background job queues
- **Caching**: Redis for frequently accessed data
- **CDN**: Cloud storage for preview images

## 📝 Troubleshooting

### Common Issues:

#### OCR Not Working
```bash
# Check Tesseract installation
tesseract --version

# Install language packs if needed
sudo apt-get install tesseract-ocr-eng
```

#### Preview Images Not Loading
```bash
# Check directory permissions
chmod 755 data/previews

# Verify static file mounting in FastAPI
```

#### Database Errors
```bash
# Check database file permissions
chmod 644 backend/data/owlin.db

# Verify table creation
sqlite3 backend/data/owlin.db ".tables"
```

## 🎉 Success Metrics

### Key Performance Indicators:
- **Processing Speed**: < 30 seconds per PDF
- **Classification Accuracy**: > 85% confidence
- **User Adoption**: Increased upload volume
- **Error Rate**: < 5% processing failures

### Quality Metrics:
- **Document Detection**: Successfully identify document types
- **Metadata Extraction**: Accurate supplier, date, amount extraction
- **User Satisfaction**: Positive feedback on review interface

---

## 🏆 Implementation Summary

The Smart Document Processing Pipeline successfully implements:

✅ **Intelligent PDF Processing**: Automatic splitting and classification
✅ **OCR Integration**: Text extraction using Tesseract
✅ **Smart Grouping**: Heuristic-based document grouping
✅ **Visual Review Interface**: User-friendly confirmation modal
✅ **Database Integration**: Proper storage and audit logging
✅ **Error Handling**: Comprehensive error recovery
✅ **Performance Optimization**: Efficient processing pipeline
✅ **Security**: File validation and secure storage
✅ **Scalability**: Extensible architecture for future enhancements

This implementation transforms Owlin into a cutting-edge document processing platform that feels magical to users! 🚀 