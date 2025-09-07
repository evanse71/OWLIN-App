# Database Manager Integration Documentation

## Overview

This document describes the integration of a comprehensive database manager module into the OWLIN platform. The database manager provides SQLite database management for invoice storage, delivery note tracking, duplicate detection, and role-based access control.

## Architecture

### Core Components

1. **Database Manager Module** (`backend/db_manager.py`)
   - SQLite database initialization and schema management
   - Invoice and delivery note data persistence
   - File hash-based duplicate detection
   - Role-based permission system
   - Processing log tracking and statistics

2. **Enhanced Upload Pipeline** (`backend/upload_pipeline.py`)
   - Integration with database manager for data persistence
   - Automatic database initialization
   - File hash generation and duplicate checking
   - Processing result logging

3. **Database Schema**
   - **invoices**: Invoice metadata and processing information
   - **delivery_notes**: Delivery note metadata and processing information
   - **file_hashes**: File hash tracking for duplicate detection
   - **processing_logs**: Processing result tracking and monitoring

## Key Features

### 💾 **Data Persistence**
- **Invoice Storage**: Complete invoice metadata with OCR confidence
- **Delivery Note Storage**: Delivery note information with item counts
- **File Hash Tracking**: MD5-based duplicate file detection
- **Processing Logs**: Comprehensive processing result tracking

### 🔍 **Duplicate Detection**
- **Invoice Numbers**: Unique constraint on invoice numbers
- **File Hashes**: MD5 hash-based file content checking
- **Smart Validation**: Prevents duplicate uploads automatically
- **Graceful Handling**: Clear feedback for duplicate attempts

### 🎯 **Role-Based Access Control**
- **Permission System**: Granular permissions per user role
- **Upload Control**: Role-based upload restrictions
- **View Permissions**: Controlled access to invoice data
- **Admin Functions**: Administrative capabilities for authorized roles

### 📊 **Database Statistics**
- **Invoice Counts**: Total invoices and recent uploads
- **Delivery Notes**: Delivery note statistics
- **Processing Metrics**: Success rates and error tracking
- **Financial Totals**: Invoice amount summaries

## Implementation Details

### Database Schema

#### Invoices Table
```sql
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
```

#### Delivery Notes Table
```sql
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

#### File Hashes Table
```sql
CREATE TABLE file_hashes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_hash TEXT UNIQUE,
    file_path TEXT,
    file_size INTEGER,
    mime_type TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Processing Logs Table
```sql
CREATE TABLE processing_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT,
    processing_status TEXT,
    ocr_confidence REAL,
    error_message TEXT,
    processing_time REAL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Core Functions

#### Database Management
```python
def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initialize SQLite database with all required tables"""
    
def save_invoice(extracted_data: Dict[str, Any], db_path: str = DEFAULT_DB_PATH) -> bool:
    """Save invoice data to database"""
    
def save_delivery_note(extracted_data: Dict[str, Any], db_path: str = DEFAULT_DB_PATH) -> bool:
    """Save delivery note data to database"""
    
def save_file_hash(file_hash: str, file_path: str, file_size: int, mime_type: str, 
                  db_path: str = DEFAULT_DB_PATH) -> bool:
    """Save file hash for duplicate detection"""
```

#### Duplicate Detection
```python
def check_duplicate_invoice(invoice_number: str, db_path: str = DEFAULT_DB_PATH) -> bool:
    """Check if invoice number already exists"""
    
def check_duplicate_file_hash(file_hash: str, db_path: str = DEFAULT_DB_PATH) -> bool:
    """Check if file hash already exists"""
```

#### Data Retrieval
```python
def get_all_invoices(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Retrieve all invoices from database"""
    
def get_all_delivery_notes(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Retrieve all delivery notes from database"""
    
def get_invoice_by_number(invoice_number: str, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    """Retrieve specific invoice by number"""
```

#### Access Control
```python
def user_has_permission(user_role: Optional[str]) -> bool:
    """Check if user role has upload permission"""
    
def get_user_permissions(user_role: Optional[str]) -> Dict[str, bool]:
    """Get comprehensive permissions for user role"""
```

#### Statistics and Monitoring
```python
def get_database_stats(db_path: str = DEFAULT_DB_PATH) -> Dict[str, Any]:
    """Get comprehensive database statistics"""
    
def log_processing_result(file_path: str, status: str, ocr_confidence: float = 0.0, 
                        error_message: str = "", processing_time: float = 0.0,
                        db_path: str = DEFAULT_DB_PATH) -> None:
    """Log processing results for monitoring"""
```

## Upload Pipeline Integration

### Enhanced Processing Flow
1. **Database Initialization**: Automatic database setup
2. **File Processing**: OCR and field extraction
3. **Duplicate Checking**: File hash and invoice number validation
4. **Data Persistence**: Save processed data to database
5. **Result Logging**: Track processing results and statistics

### Database Operations
```python
# Initialize database
init_db(db_path)

# Generate file hash
import hashlib
with open(file_path, 'rb') as f:
    file_hash = hashlib.md5(f.read()).hexdigest()

# Save file hash
save_file_hash(file_hash, file_path, file_size, mime_type, db_path)

# Save invoice data
invoice_data = {
    'supplier_name': parsed_invoice.supplier,
    'invoice_number': parsed_invoice.invoice_number,
    'invoice_date': parsed_invoice.date,
    'net_amount': parsed_invoice.net_total,
    'vat_amount': parsed_invoice.vat_total,
    'total_amount': parsed_invoice.gross_total,
    'currency': 'GBP',
    'file_path': file_path,
    'file_hash': file_hash,
    'ocr_confidence': overall_confidence * 100
}
save_invoice(invoice_data, db_path)

# Log processing result
log_processing_result(
    file_path=file_path,
    status='success',
    ocr_confidence=overall_confidence * 100,
    processing_time=processing_time
)
```

## Role-Based Access Control

### Supported Roles
- **viewer**: Read-only access to invoices and delivery notes
- **finance**: Upload invoices and delivery notes, view all data
- **admin**: Full access including deletion and user management
- **GM**: Full access including deletion (no user management)

### Permission Matrix
```python
permissions = {
    "viewer": {
        "upload_invoices": False,
        "upload_delivery_notes": False,
        "view_invoices": True,
        "view_delivery_notes": True,
        "delete_invoices": False,
        "delete_delivery_notes": False,
        "view_statistics": True,
        "manage_users": False
    },
    "finance": {
        "upload_invoices": True,
        "upload_delivery_notes": True,
        "view_invoices": True,
        "view_delivery_notes": True,
        "delete_invoices": False,
        "delete_delivery_notes": False,
        "view_statistics": True,
        "manage_users": False
    },
    "admin": {
        "upload_invoices": True,
        "upload_delivery_notes": True,
        "view_invoices": True,
        "view_delivery_notes": True,
        "delete_invoices": True,
        "delete_delivery_notes": True,
        "view_statistics": True,
        "manage_users": True
    },
    "GM": {
        "upload_invoices": True,
        "upload_delivery_notes": True,
        "view_invoices": True,
        "view_delivery_notes": True,
        "delete_invoices": True,
        "delete_delivery_notes": True,
        "view_statistics": True,
        "manage_users": False
    }
}
```

## Configuration

### Database Settings
```python
# Default database path
DEFAULT_DB_PATH = "data/owlin.db"

# Supported user roles
SUPPORTED_ROLES = {"viewer", "finance", "admin", "GM"}

# Database indexes for performance
CREATE INDEX idx_invoices_number ON invoices(invoice_number);
CREATE INDEX idx_invoices_supplier ON invoices(supplier_name);
CREATE INDEX idx_invoices_date ON invoices(invoice_date);
CREATE INDEX idx_delivery_number ON delivery_notes(delivery_number);
CREATE INDEX idx_file_hashes ON file_hashes(file_hash);
```

### Environment Variables
```bash
# Database path (optional)
export OWLIN_DB_PATH="data/owlin.db"

# Database backup location
export OWLIN_BACKUP_PATH="data/backups/"
```

## API Integration

### Database Operations
```python
from backend.db_manager import (
    init_db, save_invoice, save_delivery_note, save_file_hash,
    check_duplicate_invoice, check_duplicate_file_hash,
    get_all_invoices, get_all_delivery_notes, get_database_stats,
    user_has_permission, get_user_permissions, log_processing_result
)

# Initialize database
init_db("data/owlin.db")

# Check permissions
if user_has_permission(user_role):
    # Save invoice
    success = save_invoice(invoice_data, db_path)
    if success:
        print("✅ Invoice saved successfully")
    else:
        print("⚠️ Invoice already exists")
```

### Upload Pipeline Integration
```python
from backend.upload_pipeline import process_document

# Process document with database integration
result = process_document(
    file_path="invoice.pdf",
    parse_templates=True,
    validate_upload=True,
    db_path="data/owlin.db"
)

# Check database operations
if result.get('database_saved'):
    print("✅ Document saved to database")
else:
    print("⚠️ Database save failed")
```

## Error Handling

### Graceful Degradation
1. **Database Unavailable**: Continue processing without persistence
2. **Duplicate Detection**: Clear error messages for duplicate files
3. **Permission Denied**: Clear feedback for unauthorized actions
4. **Data Corruption**: Automatic validation and error logging

### Error Recovery
```python
try:
    success = save_invoice(invoice_data, db_path)
    if not success:
        logger.warning("Invoice already exists in database")
        return {"status": "duplicate", "message": "Invoice already exists"}
except Exception as e:
    logger.error(f"Database operation failed: {e}")
    return {"status": "error", "message": "Database operation failed"}
```

## Performance Considerations

### Database Optimization
- **Indexes**: Optimized indexes for common queries
- **Connection Pooling**: Efficient database connection management
- **Batch Operations**: Bulk operations for multiple records
- **Query Optimization**: Efficient SQL queries with proper joins

### Memory Management
- **Lazy Loading**: Load data only when needed
- **Connection Cleanup**: Proper connection closing
- **Transaction Management**: Efficient transaction handling
- **Resource Monitoring**: Track database resource usage

## Testing and Validation

### Test Coverage
```python
# Test database initialization
test_database_initialization()

# Test invoice operations
test_invoice_operations()

# Test delivery note operations
test_delivery_note_operations()

# Test file hash operations
test_file_hash_operations()

# Test user permissions
test_user_permissions()

# Test database stats
test_database_stats()

# Test upload pipeline integration
test_upload_pipeline_integration()

# Test backend imports
test_backend_imports()
```

### Quality Metrics
- **Data Integrity**: Validation of saved data accuracy
- **Performance**: Database operation timing
- **Concurrency**: Multi-user access testing
- **Recovery**: Error handling and recovery testing

## Usage Examples

### Basic Database Operations
```python
from backend.db_manager import init_db, save_invoice, get_all_invoices

# Initialize database
init_db("data/owlin.db")

# Save invoice
invoice_data = {
    'supplier_name': 'ACME Corp',
    'invoice_number': 'INV-2024-001',
    'invoice_date': '2024-01-15',
    'net_amount': 1000.00,
    'vat_amount': 200.00,
    'total_amount': 1200.00,
    'currency': 'GBP',
    'file_path': '/uploads/invoice.pdf',
    'file_hash': 'abc123def456',
    'ocr_confidence': 85.5
}

success = save_invoice(invoice_data)
if success:
    print("✅ Invoice saved successfully")

# Retrieve all invoices
invoices = get_all_invoices()
print(f"📊 Total invoices: {len(invoices)}")
```

### Duplicate Detection
```python
from backend.db_manager import check_duplicate_invoice, check_duplicate_file_hash

# Check for duplicate invoice number
if check_duplicate_invoice('INV-2024-001'):
    print("⚠️ Invoice number already exists")

# Check for duplicate file
file_hash = "abc123def456"
if check_duplicate_file_hash(file_hash):
    print("⚠️ File already uploaded")
```

### Permission Checking
```python
from backend.db_manager import user_has_permission, get_user_permissions

# Check upload permission
if user_has_permission("Finance"):
    print("✅ User can upload invoices")
else:
    print("❌ User cannot upload invoices")

# Get comprehensive permissions
permissions = get_user_permissions("admin")
if permissions["delete_invoices"]:
    print("✅ User can delete invoices")
```

### Database Statistics
```python
from backend.db_manager import get_database_stats

# Get database statistics
stats = get_database_stats()
print(f"📊 Invoice count: {stats['invoice_count']}")
print(f"📊 Delivery note count: {stats['delivery_count']}")
print(f"📊 Total amount: £{stats['total_amount']:,.2f}")
print(f"📊 Recent uploads: {stats['recent_uploads']}")
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors
**Symptoms**: Database operations fail, connection errors
**Solutions**:
- Check database file permissions
- Verify database path is writable
- Ensure SQLite is properly installed
- Check for disk space issues

#### 2. Duplicate Detection Issues
**Symptoms**: Duplicate files not detected
**Solutions**:
- Verify file hash generation
- Check database constraints
- Review duplicate detection logic
- Validate file content integrity

#### 3. Permission Errors
**Symptoms**: Users cannot perform expected actions
**Solutions**:
- Verify user role assignments
- Check permission matrix
- Review role-based access logic
- Test permission functions

#### 4. Performance Issues
**Symptoms**: Slow database operations
**Solutions**:
- Check database indexes
- Optimize query performance
- Monitor connection pooling
- Review transaction management

### Debug Tools
1. **Database Inspection**: Direct SQLite database examination
2. **Log Analysis**: Processing log review and analysis
3. **Permission Testing**: Role-based access verification
4. **Performance Monitoring**: Database operation timing

## Future Enhancements

### Planned Features
1. **Database Migration**: Schema version management
2. **Backup System**: Automated database backups
3. **Advanced Queries**: Complex reporting and analytics
4. **Data Export**: CSV/Excel export functionality
5. **Audit Trail**: Comprehensive change tracking

### Performance Improvements
1. **Connection Pooling**: Enhanced connection management
2. **Query Optimization**: Advanced query optimization
3. **Caching Layer**: Result caching for frequent queries
4. **Batch Operations**: Bulk data processing

### Security Enhancements
1. **Data Encryption**: Database encryption at rest
2. **Access Logging**: Comprehensive access tracking
3. **Audit Controls**: Advanced audit trail
4. **Backup Encryption**: Encrypted backup storage

## Support and Maintenance

### Documentation
- **API Reference**: Complete function documentation
- **Schema Guide**: Database schema documentation
- **Migration Guide**: Database upgrade procedures
- **Troubleshooting**: Common issues and solutions

### Maintenance Tasks
1. **Regular Backups**: Automated database backups
2. **Performance Monitoring**: Database performance tracking
3. **Data Integrity**: Regular data validation checks
4. **Security Updates**: Database security patches

### Contact Information
- **Development Team**: OWLIN Development Team
- **Version**: 1.0.0
- **Last Updated**: January 2024

---

This database manager integration provides a robust, scalable solution for invoice and delivery note data persistence with comprehensive duplicate detection, role-based access control, and monitoring capabilities. The system is designed to handle real-world document processing scenarios while providing excellent data integrity and performance. 