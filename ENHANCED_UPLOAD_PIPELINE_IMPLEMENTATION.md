# Enhanced Upload Pipeline Implementation

## Overview

This document describes the implementation of the enhanced upload pipeline for the OWLIN application, which provides unified document processing with confidence scoring, manual review logic, and template parsing.

## Architecture

### A. File Upload and Initial Handling

**Location**: `backend/upload_pipeline.py` - `process_document()`

**Process Flow**:
1. Users upload documents via dual-drop interface (Finance/Shift Lead roles)
2. File path sent to `process_document()` in `backend/upload_pipeline.py`
3. System recognizes PDF vs image files
4. PDFs converted to images via `pypdfium2`
5. Each page image passed to centralized OCR engine

**Key Benefits**:
- Single entry point for all document processing
- Consistent handling of every document
- No need for explicit backend calls in multiple functions

### B. Unified OCR Pipeline

**Main Method**: `backend/ocr/ocr_engine.py` - `run_invoice_ocr()`

**Processing Steps**:

1. **Raw PaddleOCR Run**
   - PaddleOCR attempts OCR on unmodified image
   - Uses `use_angle_cls=True` for rotated text detection
   - Lazy initialization with lightweight English model
   - CPU-only operation for compatibility

2. **Confidence Calculation**
   - System computes mean confidence score for page
   - Confidence values range from 0 to 1 in PaddleOCR

3. **Pre-processing Invocation** (if mean confidence < 70%)
   - Converts to grayscale
   - Applies adaptive thresholding to binarize image
   - Runs median filtering to reduce noise
   - Calculates skew via Hough lines and corrects angle
   - Adds orientation correction (90°, 180° rotations)

4. **Second Paddle Run**
   - OCR run again on pre-processed image
   - Engine chooses results with higher average confidence

5. **Tesseract Fallback**
   - If PaddleOCR fails, uses `pytesseract.image_to_data()`
   - Returns bounding box coordinates and confidence scores
   - Converts 0-100 scale to 0-1 scale
   - Logs to `data/logs/ocr_fallback.log`

6. **Result Packaging**
   - Results stored as `OCRResult` dataclasses
   - Includes text, polygon bounding boxes, per-word confidences, page number

7. **Artifact Storage**
   - Pre-processed images and JSON results saved in `data/debug_ocr/`
   - Page-based filename convention for visual checks

8. **Post-run Heuristics**
   - `assign_field_types()` looks for keywords like "supplier", "date", "invoice number"
   - Tags each OCR result with high-level field type
   - Groups results by page for accurate confidence scoring

### C. Confidence Scoring & Manual Review Logic

**Threshold Definitions**:
- `CONFIDENCE_RERUN_THRESHOLD = 0.70`: Triggers pre-processing and second OCR pass
- `CONFIDENCE_REVIEW_THRESHOLD = 0.65`: Flags document for manual review

**Manual Review Flag**:
- After grouping results by page, computes mean confidence for each page
- If any page falls below 65%, includes `"manual_review_required": True`
- Triggers visible badge in UI

**Implementation**: Encapsulated in `process_document()` so rest of codebase only needs to read this flag

### D. Template Parsing & Metadata Extraction

**Heuristic Parser**: `backend/ocr/parse_invoice.py` - `parse_invoice()`

**Extraction Methods**:
- Regular expressions for invoice number patterns
- Date recognition (DD/MM/YYYY, DD-MM-YYYY, etc.)
- Net/VAT/gross total detection (finds three largest numeric values)
- Supplier name inference via top-of-page bounding boxes
- Line item detection by grouping text rows using Y coordinates

**Result Structure**: Returns `ParsedInvoice` dataclass with:
- Invoice number, date, supplier
- Net total, VAT total, gross total
- List of line items (`LineItem` objects)
- Each item has description, quantity, unit price, total price

**Integration**: When `parse_templates=True` in `process_document()`, parsed invoice object included in final dictionary

### E. Role-Based UI Integration

**Invoice Upload View**:
- Frontend calls `process_document()` after file upload
- Displays `ocr_results` in preview table with editable text
- Shows `parsed_invoice` fields to pre-populate form inputs
- Progress bar during document processing

**Card Representation**:
- Shows supplier name, invoice date, total value, filename, overall confidence
- If `manual_review_required` is true, shows red/amber badge
- Disables auto-save for manual review items

**Expanded Line-item Table**:
- Click card to expand showing line items
- Role-limited editing (Finance can adjust quantities, Shift Lead cannot)

**Alerts & Tooltips**:
- Shows tooltip if Tesseract fallback was needed
- Warns user if confidence is very low

### F. Backend Implementation

**New Files Created**:
- `backend/upload_pipeline.py`: Unified processing pipeline
- `backend/routes/upload_enhanced.py`: Enhanced upload endpoints
- `backend/ocr/ocr_engine.py`: Updated with confidence scoring
- `backend/ocr/parse_invoice.py`: Updated with structured parsing

**Key Classes**:
```python
@dataclass
class OCRResult:
    text: str
    confidence: float
    bounding_box: List[Tuple[int, int]]
    page_number: int
    field_type: Optional[str] = None

@dataclass
class ParsedInvoice:
    invoice_number: str
    date: str
    supplier: str
    net_total: float
    vat_total: float
    gross_total: float
    line_items: List[LineItem]
    confidence: float
```

**API Endpoints**:
- `POST /api/upload/enhanced`: Single document upload
- `POST /api/upload/batch`: Batch document upload
- `GET /api/upload/status/{document_id}`: Processing status
- `DELETE /api/upload/{document_id}`: Delete document

### G. Frontend Implementation

**New Components**:
- `components/invoices/EnhancedUploadPanel.tsx`: Enhanced upload interface
- `components/invoices/EnhancedInvoiceCard.tsx`: Card with confidence display
- `pages/enhanced-upload-demo.tsx`: Demo page showcasing features

**Key Features**:
- Drag-and-drop file upload
- Real-time progress tracking
- Confidence score visualization
- Manual review flagging
- Role-based permissions
- Template parsing results display

### H. Testing & Validation

**Test Script**: `test_enhanced_upload_pipeline.py`

**Test Coverage**:
- OCR engine initialization
- Confidence scoring functionality
- Manual review logic
- Template parsing
- Error handling and fallbacks
- Performance testing
- Debug artifact generation

**Test Results**: Saved to `test_results_enhanced_pipeline.json`

## Configuration

### Confidence Thresholds
```python
CONFIDENCE_RERUN_THRESHOLD = 0.70  # Trigger pre-processing
CONFIDENCE_REVIEW_THRESHOLD = 0.65  # Flag for manual review
```

### File Support
- **Formats**: PDF, JPG, JPEG, PNG
- **Size Limit**: 50MB
- **Processing**: Multi-page PDF support

### Debug Options
- `save_debug=True`: Saves pre-processed images and OCR results
- Debug artifacts stored in `data/debug_ocr/`
- Fallback logs in `data/logs/ocr_fallback.log`

## Usage Examples

### Basic Document Processing
```python
from backend.upload_pipeline import process_document

result = process_document(
    file_path="path/to/invoice.pdf",
    parse_templates=True,
    save_debug=False
)

print(f"Confidence: {result['overall_confidence']:.3f}")
print(f"Manual Review Required: {result['manual_review_required']}")
```

### Frontend Integration
```typescript
import EnhancedUploadPanel from '@/components/invoices/EnhancedUploadPanel';

<EnhancedUploadPanel
  userRole="finance"
  onUploadComplete={(results) => {
    console.log('Upload completed:', results);
  }}
/>
```

## Performance Considerations

### Processing Times
- **High-quality images**: 2-5 seconds per page
- **Low-quality images**: 5-15 seconds per page (includes pre-processing)
- **PDFs**: Additional 1-2 seconds per page for conversion

### Memory Usage
- PaddleOCR model: ~200MB (lazy loaded)
- Pre-processed images: Temporary storage in `data/debug_ocr/`
- Batch processing: Sequential to avoid memory issues

### Optimization Strategies
- Lazy initialization of OCR models
- Sequential batch processing
- Configurable debug artifact cleanup
- Fallback to Tesseract for failed PaddleOCR runs

## Error Handling

### OCR Failures
- Automatic fallback to Tesseract
- Logging of fallback usage
- Graceful degradation of confidence scores

### File Processing Errors
- Invalid file type detection
- File size validation
- Corrupted PDF/image handling

### Network/API Errors
- Timeout handling (2 minutes for uploads)
- Retry logic for transient failures
- User-friendly error messages

## Future Enhancements

### Planned Features
1. **Multi-language Support**: Extend PaddleOCR for non-English documents
2. **Custom Templates**: Supplier-specific parsing templates
3. **Machine Learning**: Confidence score improvement over time
4. **Batch Optimization**: Parallel processing for large batches
5. **Cloud Integration**: Optional cloud OCR for high-volume processing

### Configuration Management
- Admin interface for threshold adjustment
- Per-supplier confidence requirements
- Custom field extraction rules

### Monitoring & Analytics
- Processing time metrics
- Confidence score distribution
- Error rate tracking
- User feedback integration

## Deployment Notes

### Dependencies
```bash
pip install paddlepaddle paddleocr pypdfium2 pytesseract pillow opencv-python
```

### Environment Variables
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

### File Permissions
- Ensure write access to `data/uploads/`
- Ensure write access to `data/debug_ocr/`
- Ensure write access to `data/logs/`

## Troubleshooting

### Common Issues

1. **PaddleOCR Initialization Fails**
   - Check Python version compatibility
   - Verify paddlepaddle installation
   - Check available memory

2. **Low Confidence Scores**
   - Enable debug artifacts to inspect pre-processing
   - Check image quality and resolution
   - Verify OCR model loading

3. **Slow Processing**
   - Disable debug artifact saving
   - Check system resources
   - Consider batch size reduction

4. **Template Parsing Issues**
   - Verify invoice format compatibility
   - Check field extraction patterns
   - Review confidence thresholds

### Debug Tools
- `test_enhanced_upload_pipeline.py`: Comprehensive test suite
- Debug artifacts in `data/debug_ocr/`
- Logs in `data/logs/`
- Frontend demo at `/enhanced-upload-demo`

## Conclusion

The enhanced upload pipeline provides a robust, scalable solution for document processing with intelligent confidence scoring and manual review workflows. The unified architecture ensures consistent processing across all document types while maintaining flexibility for future enhancements.

The implementation successfully addresses the requirements outlined in the original specification, providing:
- ✅ Unified processing pipeline
- ✅ Confidence scoring and manual review
- ✅ Template parsing and metadata extraction
- ✅ Role-based UI integration
- ✅ Comprehensive error handling
- ✅ Performance optimization
- ✅ Extensive testing and validation 