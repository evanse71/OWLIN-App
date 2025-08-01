# OWLIN Production Integration Guide

## Overview

This guide describes how to fully integrate the new modules (`field_extractor.py`, `upload_validator.py`, `ocr_processing.py`, `db_manager.py`, and `multi_upload_ui.py`) into the production OWLIN application. The integration provides enhanced OCR processing, validation, database persistence, and multi-file upload capabilities.

## Architecture

### Production Setup
```
OWLIN-App-main/
├── app/                          # Production modules
│   ├── main.py                   # Main Streamlit app entry point
│   ├── streamlit_app.py          # Production Streamlit application
│   ├── field_extractor.py        # Enhanced field extraction
│   ├── upload_validator.py       # Upload validation and duplicate detection
│   ├── ocr_processing.py         # OCR processing with fallback
│   ├── db_manager.py             # Database management
│   └── multi_upload_ui.py        # Multi-upload UI module
├── pages/                        # Next.js frontend
│   ├── upload.tsx                # Enhanced upload page
│   └── ...                       # Other pages
├── components/                   # React components
│   └── invoices/
│       └── EnhancedUploadPanel.tsx  # Enhanced upload component
├── pages/api/                    # API endpoints
│   └── upload-enhanced.ts        # Enhanced upload API
├── data/                         # Database and data files
│   └── owlin.db                  # SQLite database
├── start_production.sh           # Production startup script
└── ...                          # Other files
```

## Integration Steps

### 1. Module Placement

All new modules have been placed in the `app/` directory:

```bash
# Copy modules to app directory
cp backend/ocr/field_extractor.py app/
cp backend/upload_validator.py app/
cp backend/ocr/ocr_processing.py app/
cp backend/db_manager.py app/
cp backend/multi_upload_ui.py app/
```

### 2. Database Initialization

The database is automatically initialized on startup:

```python
# In app/main.py and app/streamlit_app.py
from db_manager import init_db

# Initialize database on startup
db_path = "data/owlin.db"
init_db(db_path)
```

### 3. Frontend Integration

The existing upload page has been updated to use the enhanced functionality:

```typescript
// pages/upload.tsx
import EnhancedUploadPanel from '@/components/invoices/EnhancedUploadPanel';

// Use the enhanced upload component
<EnhancedUploadPanel
  userRole={userRole}
  documentType={selectedDocumentType}
  onUploadComplete={handleUploadComplete}
/>
```

### 4. API Integration

A new API endpoint provides enhanced upload functionality:

```typescript
// pages/api/upload-enhanced.ts
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  // Enhanced upload processing with validation and database storage
}
```

## Production Startup

### Using the Startup Script

The `start_production.sh` script handles the complete production setup:

```bash
# Make executable and run
chmod +x start_production.sh
./start_production.sh
```

### Manual Startup

If you prefer to start services manually:

```bash
# 1. Initialize database
cd app
python3 -c "from db_manager import init_db; init_db('data/owlin.db')"
cd ..

# 2. Start Next.js app
npm run dev

# 3. Start Streamlit app (in another terminal)
cd app
streamlit run streamlit_app.py --server.port 8501
```

## Features

### 🔄 **Enhanced Upload Processing**
- **Multi-file Upload**: Process multiple files simultaneously
- **OCR Processing**: PaddleOCR → Tesseract fallback
- **Field Extraction**: Enhanced invoice field parsing
- **Validation**: Duplicate detection and data validation
- **Database Storage**: Automatic persistence to SQLite

### 🔐 **Role-Based Access Control**
- **Permission Checking**: Role-based upload permissions
- **User Interface**: Clear permission feedback
- **Audit Logging**: Comprehensive activity tracking
- **Security**: Secure file handling and validation

### 📊 **Database Integration**
- **Data Persistence**: Automatic saving to SQLite database
- **Duplicate Detection**: File hash and invoice number checking
- **Audit Logging**: Comprehensive processing logs
- **Statistics**: Real-time database statistics

### 🎯 **Streamlit Interface**
- **Complete Web App**: Full-featured Streamlit application
- **Tabbed Interface**: Separate tabs for invoices and delivery notes
- **Real-Time Progress**: Progress bars and status updates
- **Permission Display**: Clear permission feedback
- **Database Statistics**: Real-time database monitoring

## Configuration

### Environment Variables
```bash
# Database path
export OWLIN_DB_PATH="data/owlin.db"

# Streamlit configuration
export STREAMLIT_SERVER_PORT=8501
export STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Logging configuration
export OWLIN_LOG_LEVEL=INFO
export OWLIN_AUDIT_LOG="data/audit.log"
```

### Dependencies
```bash
# Python dependencies
pip install streamlit paddleocr pytesseract pdf2image Pillow

# Node.js dependencies
npm install formidable @types/formidable
```

## Usage

### 1. Start Production Environment
```bash
./start_production.sh
```

### 2. Access Applications
- **Next.js Frontend**: http://localhost:3000
- **Streamlit Upload**: http://localhost:8501

### 3. Upload Documents
1. Navigate to the upload page
2. Select user role and document type
3. Choose files to upload
4. Monitor progress and results

### 4. View Results
- Check the Document Queue for processed files
- Review database statistics
- Monitor audit logs

## API Endpoints

### Enhanced Upload API
```typescript
POST /api/upload-enhanced
Content-Type: multipart/form-data

Parameters:
- file: File(s) to upload
- userRole: User role for permission checking
- documentType: Type of document being uploaded

Response:
{
  success: boolean,
  message: string,
  data: {
    results: Array<UploadResult>,
    summary: {
      total: number,
      successful: number,
      failed: number
    }
  }
}
```

## Database Schema

### Tables
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

-- File hashes table
CREATE TABLE file_hashes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_hash TEXT UNIQUE,
    file_path TEXT,
    file_size INTEGER,
    mime_type TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Processing logs table
CREATE TABLE processing_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT,
    status TEXT,
    ocr_confidence REAL,
    error_message TEXT,
    processing_time REAL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Error Handling

### Graceful Degradation
1. **OCR Failures**: Automatic fallback to Tesseract
2. **Validation Errors**: Clear error messages and suggestions
3. **Permission Denied**: Clear feedback for unauthorized actions
4. **Database Errors**: Continue processing with error logging

### Error Recovery
```python
try:
    # Process file
    ocr_results = run_ocr_with_fallback(tmp_path)
    if not ocr_results:
        st.error(f"❌ OCR failed for {file_name}")
        continue
    
    # Extract and validate
    extracted_data = extract_invoice_fields(ocr_results)
    allowed, messages, validation_data = validate_upload(tmp_path, extracted_data, db_path)
    
    if not allowed:
        st.error(f"❌ {file_name}: {messages.get('error')}")
        continue
    
    # Save to database
    save_success = save_invoice(extracted_data, db_path)
    if save_success:
        st.success(f"✅ {file_name}: Uploaded successfully")
    else:
        st.error(f"❌ {file_name}: Failed to save to database")
        
except Exception as e:
    st.error(f"❌ {file_name}: Processing error - {str(e)}")
    logging.error(f"Processing error for {file_name}: {str(e)}")
```

## Performance Considerations

### Processing Optimization
- **Sequential Processing**: Process files one at a time to avoid memory issues
- **Temporary Files**: Efficient temporary file management
- **Progress Updates**: Real-time progress tracking
- **Error Isolation**: Individual file error handling

### Memory Management
- **File Streaming**: Stream large files efficiently
- **Temporary Cleanup**: Automatic cleanup of temporary files
- **Database Connections**: Efficient database connection management
- **Resource Monitoring**: Track memory and processing usage

## Monitoring and Logging

### Audit Logging
```python
# Log processing results
log_processing_result(
    file_path=tmp_path,
    status='success',
    ocr_confidence=overall_confidence * 100,
    processing_time=processing_time
)
```

### Database Statistics
```python
# Get database statistics
stats = get_database_stats(db_path)
print(f"Invoices: {stats.get('invoice_count', 0)}")
print(f"Delivery Notes: {stats.get('delivery_count', 0)}")
print(f"Total Amount: £{stats.get('total_amount', 0):,.2f}")
```

## Troubleshooting

### Common Issues

#### 1. Database Initialization Failures
**Symptoms**: Database creation errors
**Solutions**:
- Check file permissions for data directory
- Ensure SQLite is properly installed
- Verify disk space availability

#### 2. OCR Processing Failures
**Symptoms**: OCR results empty or poor quality
**Solutions**:
- Install Tesseract: `brew install tesseract` (macOS)
- Check PaddleOCR installation
- Verify image quality and format
- Check OCR dependencies

#### 3. Permission Errors
**Symptoms**: Users cannot upload despite correct role
**Solutions**:
- Verify user role assignments
- Check permission matrix
- Review role-based access logic
- Test permission functions

#### 4. Streamlit Connection Issues
**Symptoms**: Streamlit app not accessible
**Solutions**:
- Check if port 8501 is available
- Verify Streamlit installation
- Check firewall settings
- Review Streamlit configuration

### Debug Tools
1. **Streamlit Debug**: `streamlit run --debug`
2. **Log Analysis**: Review audit.log for errors
3. **Database Inspection**: Direct SQLite database examination
4. **Performance Monitoring**: Track processing time and resource usage

## Security Considerations

### File Upload Security
- **File Type Validation**: Strict file type checking
- **Size Limits**: Configurable file size limits
- **Virus Scanning**: Consider implementing virus scanning
- **Secure Storage**: Encrypted file storage

### Access Control
- **Role-Based Permissions**: Strict role-based access control
- **Audit Logging**: Comprehensive activity tracking
- **Input Validation**: Validate all user inputs
- **Error Handling**: Secure error messages

### Data Protection
- **Database Security**: Secure database configuration
- **File Encryption**: Encrypt sensitive files
- **Backup Strategy**: Regular database backups
- **Access Logging**: Log all database access

## Future Enhancements

### Planned Features
1. **Advanced UI**: Enhanced drag-and-drop interface
2. **Batch Processing**: Parallel file processing
3. **Real-time Updates**: WebSocket-based progress updates
4. **Advanced Validation**: Machine learning-based validation
5. **Export Functionality**: CSV/Excel export of upload results

### Performance Improvements
1. **Parallel Processing**: Multi-threaded file processing
2. **Caching**: Result caching for repeated uploads
3. **Streaming**: Memory-efficient large file handling
4. **Optimization**: Enhanced OCR and processing algorithms

### Security Enhancements
1. **File Encryption**: Encrypted file storage
2. **Access Logging**: Comprehensive access tracking
3. **Audit Controls**: Advanced audit trail
4. **Secure Upload**: HTTPS and secure file transfer

## Support and Maintenance

### Documentation
- **API Reference**: Complete function documentation
- **User Guide**: Step-by-step usage instructions
- **Troubleshooting**: Common issues and solutions
- **Performance Guide**: Optimization recommendations

### Maintenance Tasks
1. **Dependency Updates**: Regular package updates
2. **Performance Monitoring**: Track processing metrics
3. **Error Analysis**: Review and address common issues
4. **User Feedback**: Collect and implement user suggestions

### Contact Information
- **Development Team**: OWLIN Development Team
- **Version**: 1.0.0
- **Last Updated**: January 2024

---

This production integration provides a comprehensive, secure, and scalable solution for document processing with enhanced OCR capabilities, validation, and database persistence. The system is designed to handle real-world production scenarios while providing excellent user experience and performance monitoring. 