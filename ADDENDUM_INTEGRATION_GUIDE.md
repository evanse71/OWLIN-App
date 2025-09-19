# OWLIN Addendum Features Integration Guide

This guide provides comprehensive instructions for integrating the addendum features into the existing OWLIN application.

## Overview

The addendum features include:
1. **Document Type Classification** - Rule-based classifier for invoices, delivery notes, receipts, etc.
2. **Enhanced Pairing** - Comprehensive pairing logic with fuzzy matching and line-item similarity
3. **Annotation Detection** - Advanced annotation detection with shape recognition
4. **API Endpoints** - RESTful APIs for annotations and pairings
5. **Database Schema** - New tables and fields for the features

## Installation Steps

### 1. Database Migration

Run the database migration to create the required tables:

```bash
cd backend
python run_addendum_migration.py
```

This will:
- Create new tables: `doc_pairs`, `annotations`, `document_classification`, `pairing_rules`, `annotation_mappings`
- Add new fields to existing tables
- Insert default pairing rules
- Create necessary indexes

### 2. Install Dependencies

Ensure the following Python packages are installed:

```bash
pip install opencv-python rapidfuzz python-multipart
```

### 3. Update Application

The main application (`backend/main.py`) has been updated to include the new routers:
- `/api/annotations` - Annotation management
- `/api/pairings` - Document pairing management

### 4. Verify Integration

Test the integration by running:

```bash
# Start the application
uvicorn backend.main:app --reload

# Test the new endpoints
curl http://localhost:8000/api/annotations/
curl http://localhost:8000/api/pairings/
```

## API Endpoints

### Annotations API

#### Get Annotations
```http
GET /api/annotations/
Query Parameters:
- invoice_id (optional): Filter by invoice ID
- delivery_note_id (optional): Filter by delivery note ID
- kind (optional): Filter by annotation kind (TICK, CROSS, CIRCLE, etc.)
- page_number (optional): Filter by page number
- limit (default: 100): Maximum number of results
- offset (default: 0): Number of results to skip
```

#### Create Annotation
```http
POST /api/annotations/
Content-Type: application/json

{
  "invoice_id": "inv_123",
  "kind": "TICK",
  "x": 0.5,
  "y": 0.3,
  "w": 0.1,
  "h": 0.1,
  "confidence": 0.8,
  "color": "green"
}
```

#### Update Annotation
```http
PUT /api/annotations/{annotation_id}
Content-Type: application/json

{
  "kind": "CROSS",
  "confidence": 0.9
}
```

#### Delete Annotation
```http
DELETE /api/annotations/{annotation_id}
```

### Pairings API

#### Get Pairings
```http
GET /api/pairings/
Query Parameters:
- invoice_id (optional): Filter by invoice ID
- delivery_note_id (optional): Filter by delivery note ID
- status (optional): Filter by status (active, inactive, disputed, confirmed)
- min_score (optional): Minimum score threshold
- pairing_method (optional): Filter by pairing method
- limit (default: 100): Maximum number of results
- offset (default: 0): Number of results to skip
```

#### Create Pairing
```http
POST /api/pairings/
Content-Type: application/json

{
  "invoice_id": "inv_123",
  "delivery_note_id": "dn_456",
  "score": 0.85,
  "pairing_method": "manual",
  "supplier_match_score": 0.9,
  "date_proximity_score": 0.8,
  "total_confidence": 0.85
}
```

#### Auto-Pair Documents
```http
POST /api/pairings/auto-pair
Content-Type: application/json

{
  "force_recalculate": false,
  "min_confidence": 0.6
}
```

#### Get Pairing Candidates
```http
GET /api/pairings/invoice/{invoice_id}/candidates
Query Parameters:
- limit (default: 10): Maximum number of candidates
```

## Usage Examples

### Document Classification

```python
from backend.services.document_classifier import classify_document_text

# Classify a document
text = "INVOICE\nInvoice Number: INV-001\nAmount Due: £100.00"
result = classify_document_text(text)

print(f"Document Type: {result.doc_type}")
print(f"Confidence: {result.confidence}")
print(f"Keywords Found: {result.keywords_found}")
```

### Enhanced Pairing

```python
from backend.services.enhanced_pairing import auto_pair_enhanced
import sqlite3

# Run automatic pairing
db = sqlite3.connect('data/owlin.db')
result = auto_pair_enhanced(db)

print(f"Pairs Created: {result['pairs_created']}")
print(f"High Confidence Pairs: {result['high_confidence_pairs']}")
```

### Annotation Detection

```python
from backend.extraction.parsers.invoice_parser import detect_annotations

# Detect annotations in an image
annotations = detect_annotations("path/to/image.png")

for ann in annotations:
    print(f"Type: {ann['kind']}, Confidence: {ann['confidence']}")
    print(f"Position: ({ann['x']}, {ann['y']})")
    print(f"Size: {ann['w']} x {ann['h']}")
```

## Configuration

### Pairing Rules

The pairing rules can be configured in the `pairing_rules` table:

```sql
-- Update supplier matching threshold
UPDATE pairing_rules 
SET parameters = '{"threshold": 0.9, "fuzzy": true}' 
WHERE rule_type = 'supplier_match';

-- Update date window
UPDATE pairing_rules 
SET parameters = '{"window_days": 45, "strict": false}' 
WHERE rule_type = 'date_window';
```

### Document Classification

The document classifier uses rule-based classification. To add new document types or improve classification:

1. Edit `backend/services/document_classifier.py`
2. Add new rules to the `_initialize_rules()` method
3. Update the `doc_type` CHECK constraint in the database

## Testing

Run the comprehensive test suite:

```bash
# Run all addendum feature tests
python -m pytest backend/tests/test_addendum_features.py -v

# Run specific test categories
python -m pytest backend/tests/test_addendum_features.py::TestDocumentClassifier -v
python -m pytest backend/tests/test_addendum_features.py::TestEnhancedPairing -v
python -m pytest backend/tests/test_addendum_features.py::TestAnnotationDetection -v
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed and the Python path is correct
2. **Database Errors**: Run the migration script to ensure all tables exist
3. **OpenCV Errors**: Ensure OpenCV is properly installed: `pip install opencv-python`
4. **API Errors**: Check that the routers are properly included in the main application

### Debug Mode

Enable debug logging by setting the log level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Database Inspection

Check the database schema:

```bash
python backend/run_addendum_migration.py --check
```

## Performance Considerations

1. **Annotation Detection**: Uses OpenCV for image processing - ensure adequate memory
2. **Pairing**: Can be CPU intensive for large datasets - consider running as background task
3. **Database**: Ensure proper indexes are created for optimal query performance

## Security Considerations

1. **File Uploads**: Validate file types and sizes
2. **API Access**: Implement proper authentication and authorization
3. **Database**: Use parameterized queries to prevent SQL injection

## Future Enhancements

1. **Machine Learning**: Replace rule-based classification with ML models
2. **Real-time Processing**: Implement WebSocket support for real-time updates
3. **Batch Processing**: Add support for bulk operations
4. **Advanced Analytics**: Add reporting and analytics features

## Support

For issues or questions:
1. Check the test suite for usage examples
2. Review the API documentation
3. Check the database schema and migration logs
4. Enable debug logging for detailed error information
