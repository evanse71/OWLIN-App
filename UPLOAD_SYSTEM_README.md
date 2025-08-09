# Enhanced Upload Box with OCR Processing System

## Overview

The Enhanced Upload Box with OCR Processing System is a robust, feature-rich file upload solution that provides comprehensive file validation, reliable storage, and advanced OCR (Optical Character Recognition) processing. It's designed to handle invoice and delivery note uploads with real-time feedback, error recovery, and accessibility support.

## Architecture

### Core Components

1. **Upload Box Interface** (`render_upload_box`)
   - Modern, accessible UI with drag-and-drop support
   - Real-time file validation and status tracking
   - Comprehensive error handling and user feedback

2. **File Processing Pipeline**
   - File validation (size, format, content integrity)
   - Reliable file storage with retry mechanisms
   - Database metadata persistence
   - OCR processing with confidence scoring

3. **OCR Engine Factory** (`ocr_factory.py`)
   - Unified interface for multiple OCR engines
   - Support for Tesseract and EasyOCR
   - Automatic fallback mechanisms

4. **Enhanced OCR Preprocessing** (`ocr_preprocessing.py`)
   - Advanced image preprocessing for improved OCR accuracy
   - Multiple preprocessing algorithms and configurations
   - Real-time quality assessment and statistics

5. **Database Integration** (`file_processor.py`)
   - File metadata storage and retrieval
   - Processing status tracking
   - Invoice record creation from processed files

## Key Features

### 🛡️ Comprehensive File Validation

```python
# File size validation
file_size_mb = uploaded_file.size / (1024 * 1024)
if file_size_mb > max_size_mb:
    # Handle size limit exceeded

# File format validation
accepted_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.zip']
if file_extension not in accepted_extensions:
    # Handle unsupported format

# File content validation
if not is_valid_file_signature(header, file_extension):
    # Handle corrupted file
```

**Supported Formats:**
- **PDF**: Invoice and delivery note documents
- **Images**: JPG, JPEG, PNG files
- **Archives**: ZIP files containing multiple documents
- **Max Size**: 10MB per file (configurable)

### 🔄 Reliable File Storage

The system implements a robust file saving mechanism with retry logic:

```python
def save_file_to_disk_with_retry(uploaded_file, file_type, max_retries=3):
    """Save file to disk with retry logic for reliability."""
    for attempt in range(max_retries):
        try:
            file_id = save_file_to_disk(uploaded_file, file_type)
            return file_id
        except Exception as e:
            if attempt == max_retries - 1:
                raise Exception(f"Failed to save file after {max_retries} attempts: {str(e)}")
            time.sleep(0.5)  # Brief delay before retry
```

**Storage Structure:**
```
data/
├── uploads/
│   ├── invoices/
│   │   ├── {file_id}.pdf
│   │   └── {file_id}.jpg
│   └── delivery_notes/
│       ├── {file_id}.pdf
│       └── {file_id}.png
```

### 🔍 Enhanced OCR Processing with Advanced Preprocessing

The OCR system now includes a comprehensive preprocessing pipeline that significantly improves accuracy:

#### OCR Preprocessing Pipeline
```python
class OCRPreprocessor:
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Apply comprehensive preprocessing pipeline to improve OCR accuracy."""
        # 1. Resize image to optimal dimensions
        # 2. Deskew the image (correct rotation)
        # 3. Denoise the image (remove noise while preserving edges)
        # 4. Enhance contrast (improve text visibility)
        # 5. Apply thresholding (convert to binary)
        # 6. Apply morphological operations (clean up text)
```

#### Preprocessing Features

**🔄 Image Resizing**
- Automatic resizing to optimal OCR dimensions
- Maintains aspect ratio
- Configurable minimum and maximum widths

**📐 Deskewing**
- Automatic detection and correction of document rotation
- Uses contour analysis to find document boundaries
- Configurable maximum rotation angle

**🧹 Denoising**
- **Bilateral Filtering**: Preserves edges while removing noise
- **Total Variation**: Removes noise while maintaining structure
- **Gaussian Blur**: Simple noise reduction for fast processing

**📈 Contrast Enhancement**
- **CLAHE**: Contrast Limited Adaptive Histogram Equalization
- **Histogram Equalization**: Global contrast improvement
- **Gamma Correction**: Adjustable brightness and contrast

**⚡ Thresholding**
- **Otsu's Method**: Automatic threshold selection
- **Adaptive Thresholding**: Local threshold adaptation
- **Local Thresholding**: Region-based thresholding

**🔧 Morphological Operations**
- **Opening**: Removes noise and small artifacts
- **Closing**: Fills gaps in text characters
- **Combined**: Both opening and closing operations

#### Tesseract OCR
```python
class TesseractRecognizer:
    def recognize(self, image: np.ndarray) -> Tuple[str, float]:
        # Convert image to PIL format
        # Run OCR with confidence data
        # Extract text and confidence scores
        return recognized_text, avg_confidence
```

#### EasyOCR Integration
```python
class EasyOcrRecognizer:
    def recognize(self, image: np.ndarray) -> Tuple[str, float]:
        # Process image with EasyOCR
        # Extract text with bounding boxes
        # Calculate confidence scores
        return recognized_text, avg_confidence
```

**OCR Features:**
- **Multi-engine support**: Tesseract and EasyOCR
- **Confidence scoring**: Quality assessment of extracted text
- **Image preprocessing**: Advanced preprocessing pipeline
- **Batch processing**: Handle multiple images per document
- **Quality metrics**: Real-time assessment of preprocessing improvements

### 📊 Real-time Status Tracking

The system provides comprehensive status updates throughout the processing pipeline:

```python
status_update = {
    'status': 'processing',
    'message': f"🔄 Processing {uploaded_file.name}...",
    'stage': 'uploading',
    'progress': 0
}
```

**Processing Stages:**
1. **Uploading** (0-25%): File validation and initial processing
2. **Saving** (25-50%): File storage to disk
3. **Metadata** (50-75%): Database record creation
4. **Preprocessing** (75-85%): Image enhancement and cleanup
5. **OCR Processing** (85-95%): Text extraction
6. **Completed** (95-100%): Final processing and cleanup

### 🎯 Error Handling and Recovery

The system implements comprehensive error handling with specific error types:

```python
# Size limit errors
if file_size_mb > max_size_mb:
    status_update = {
        'status': 'error',
        'message': f"❌ {uploaded_file.name} exceeds {max_size_mb}MB limit",
        'error_type': 'size_limit',
        'file_size_mb': file_size_mb,
        'max_size_mb': max_size_mb
    }

# Format errors
if file_extension not in accepted_extensions:
    status_update = {
        'status': 'error',
        'message': f"❌ {uploaded_file.name} has unsupported format",
        'error_type': 'unsupported_format',
        'file_extension': file_extension
    }

# Processing errors
except Exception as processing_error:
    status_update = {
        'status': 'error',
        'message': f"❌ Failed to process {uploaded_file.name}",
        'error_type': 'processing_error',
        'error_details': str(processing_error)
    }
```

### ♿ Accessibility Support

The upload system includes comprehensive accessibility features:

```python
# Screen reader announcements
announce_to_screen_reader(f"Processing {uploaded_file.name}")

# ARIA labels and roles
st.markdown('<div class="owlin-upload-box-modern" role="region" aria-label="File upload area">', unsafe_allow_html=True)

# Keyboard navigation support
# Focus management and keyboard shortcuts
```

## OCR Preprocessing Configuration

### Default Configuration
```python
default_config = {
    'denoising': {
        'enabled': True,
        'method': 'bilateral',  # 'bilateral', 'tv_chambolle', 'gaussian'
        'sigma_color': 75,
        'sigma_spatial': 75
    },
    'thresholding': {
        'enabled': True,
        'method': 'adaptive',  # 'otsu', 'adaptive', 'local'
        'block_size': 35,
        'offset': 10
    },
    'deskewing': {
        'enabled': True,
        'max_angle': 15
    },
    'contrast_enhancement': {
        'enabled': True,
        'method': 'clahe',  # 'clahe', 'histogram_equalization', 'gamma'
        'clip_limit': 2.0
    },
    'morphology': {
        'enabled': True,
        'operation': 'opening',  # 'opening', 'closing', 'both'
        'kernel_size': 2
    },
    'resize': {
        'enabled': True,
        'min_width': 800,
        'max_width': 2000
    }
}
```

### Custom Configurations

**High Quality Configuration**
```python
high_quality_config = create_preprocessing_config(
    denoising_method='bilateral',
    thresholding_method='adaptive',
    contrast_method='clahe',
    enable_deskewing=True
)
```

**Fast Processing Configuration**
```python
fast_config = create_preprocessing_config(
    denoising_method='gaussian',
    thresholding_method='otsu',
    contrast_method='histogram_equalization',
    enable_deskewing=False
)
```

### Preprocessing Statistics

The system provides detailed statistics about preprocessing improvements:

```python
stats = preprocessor.get_preprocessing_stats(original_image, processed_image)
# Returns:
# {
#     'contrast_improvement': float,  # Improvement in contrast
#     'noise_reduction': float,       # Reduction in noise
#     'edge_preservation': float,     # Edge preservation metric
#     'text_clarity': float          # Text clarity metric
# }
```

## Database Schema

### Uploaded Files Table
```sql
CREATE TABLE uploaded_files (
    id TEXT PRIMARY KEY,
    original_filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    upload_timestamp TEXT NOT NULL,
    processing_status TEXT DEFAULT 'pending',
    extracted_text TEXT,
    confidence REAL,
    processed_images INTEGER,
    extraction_timestamp TEXT
);
```

### Invoices Table
```sql
CREATE TABLE invoices (
    id TEXT PRIMARY KEY,
    file_id TEXT,
    invoice_number TEXT,
    invoice_date TEXT,
    supplier TEXT,
    total_amount REAL,
    extracted_text TEXT,
    confidence REAL,
    upload_timestamp TEXT,
    processing_status TEXT
);
```

## Usage Examples

### Basic Upload Box
```python
render_upload_box(
    label="Invoice Documents",
    key="invoice_upload",
    accepted_formats="PDF, PNG, JPG, JPEG, ZIP",
    file_type="invoice",
    max_size_mb=10
)
```

### Custom Upload Box
```python
render_upload_box(
    label="Delivery Notes",
    key="delivery_upload",
    accepted_formats="PDF, PNG, JPG",
    file_type="delivery_note",
    max_size_mb=5
)
```

### Advanced OCR Preprocessing
```python
from app.ocr_preprocessing import OCRPreprocessor, create_preprocessing_config

# Create custom preprocessing configuration
config = create_preprocessing_config(
    denoising_method='bilateral',
    thresholding_method='adaptive',
    contrast_method='clahe',
    enable_deskewing=True
)

# Initialize preprocessor
preprocessor = OCRPreprocessor(config)

# Preprocess image
enhanced_image = preprocessor.preprocess_image(original_image)

# Get preprocessing statistics
stats = preprocessor.get_preprocessing_stats(original_image, enhanced_image)
print(f"Contrast improvement: {stats['contrast_improvement']:.2f}")
```

## Configuration Options

### OCR Engine Selection
```python
# Set OCR engine in session state
st.session_state['ocr_engine'] = 'Tesseract (default)'
# or
st.session_state['ocr_engine'] = 'EasyOCR'
```

### File Size Limits
```python
# Configure maximum file size
max_size_mb = 10  # Default: 10MB
```

### Accepted Formats
```python
# Configure accepted file formats
accepted_formats = "PDF, PNG, JPG, JPEG, ZIP"
```

### Preprocessing Configuration
```python
# Configure preprocessing parameters
preprocessing_config = {
    'denoising': {'enabled': True, 'method': 'bilateral'},
    'thresholding': {'enabled': True, 'method': 'adaptive'},
    'deskewing': {'enabled': True, 'max_angle': 15},
    'contrast_enhancement': {'enabled': True, 'method': 'clahe'},
    'morphology': {'enabled': True, 'operation': 'opening'},
    'resize': {'enabled': True, 'min_width': 800, 'max_width': 2000}
}
```

## Performance Considerations

### Batch Processing
- Files are processed individually to prevent memory issues
- Progress tracking for each file
- Parallel processing support for multiple files

### Memory Management
- Images are processed in chunks
- Temporary files are cleaned up automatically
- Database connections are properly closed

### Error Recovery
- Retry mechanisms for file operations
- Graceful degradation when OCR fails
- Partial success handling

### Preprocessing Performance
- **Fast Mode**: Uses simpler algorithms for quick processing
- **Quality Mode**: Uses advanced algorithms for maximum accuracy
- **Adaptive Mode**: Automatically selects algorithms based on image quality

## Security Features

### File Validation
- File signature verification
- Content type checking
- Size limit enforcement

### Path Security
- Secure file path generation
- Directory traversal prevention
- File extension validation

### Data Protection
- Secure database connections
- Input sanitization
- Error message filtering

## Monitoring and Logging

### Processing Logs
```python
log_processing_step("Starting batch file processing", details=f"Files: {len(file_ids)}")
log_processing_step("OCR extraction successful", file_id, f"Text length: {len(text)}")
log_processing_step("Preprocessing completed", details=f"Contrast improvement: {stats['contrast_improvement']:.2f}")
```

### Error Tracking
- Detailed error logging with stack traces
- Error categorization and reporting
- Performance metrics collection

### Preprocessing Analytics
- Real-time preprocessing statistics
- Quality improvement metrics
- Performance benchmarking

## Testing and Validation

### OCR Preprocessing Test Suite
```bash
# Run comprehensive preprocessing tests
python test_ocr_preprocessing.py

# Expected output:
# 🧪 Testing Enhanced OCR Preprocessing Pipeline
# ============================================================
# 📋 Testing Configuration: Default
# 🖼️  Processing: Noisy Text
#   ✅ Original OCR: 0.750 confidence, 45 chars
#   ✅ Processed OCR: 0.890 confidence, 67 chars
#   📈 Improvement: +0.140 confidence, +22 chars
#   🔧 Preprocessing: Contrast +12.34, Noise -8.76
```

### Test Coverage
- **Image Quality Tests**: Various noise levels and contrast conditions
- **Configuration Tests**: Different preprocessing configurations
- **Performance Tests**: Processing time and memory usage
- **Accuracy Tests**: OCR confidence and text extraction improvements

## Troubleshooting

### Common Issues

1. **OCR Engine Not Available**
   ```python
   # Check available engines
   available_engines = get_available_ocr_engines()
   print(f"Available: {available_engines}")
   ```

2. **File Upload Failures**
   - Check file size limits
   - Verify file format support
   - Ensure sufficient disk space

3. **Database Connection Issues**
   - Verify database file permissions
   - Check database schema
   - Ensure proper connection handling

4. **Preprocessing Performance Issues**
   - Adjust preprocessing configuration
   - Use fast processing mode for large batches
   - Monitor memory usage

### Debug Mode
```python
# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Test preprocessing pipeline
from app.ocr_preprocessing import OCRPreprocessor
preprocessor = OCRPreprocessor()
enhanced_image = preprocessor.preprocess_image(test_image)
```

## Future Enhancements

### Planned Features
- **Cloud OCR Integration**: Google Vision API, Azure Computer Vision
- **Advanced Preprocessing**: Machine learning-based image enhancement
- **Multi-language Support**: Additional language models
- **Real-time Collaboration**: Shared upload sessions
- **Advanced Analytics**: Processing statistics and insights

### Performance Improvements
- **Async Processing**: Non-blocking file operations
- **Caching**: OCR result caching
- **Compression**: File compression for storage
- **CDN Integration**: Cloud storage for files
- **GPU Acceleration**: GPU-accelerated preprocessing

### Preprocessing Enhancements
- **AI-powered Enhancement**: Deep learning-based image improvement
- **Adaptive Preprocessing**: Automatic algorithm selection
- **Quality Prediction**: Predict OCR accuracy before processing
- **Custom Filters**: User-defined preprocessing pipelines

## Contributing

When contributing to the upload system:

1. **Follow Error Handling Patterns**: Use the established error handling structure
2. **Add Accessibility Features**: Include ARIA labels and screen reader support
3. **Update Documentation**: Document new features and changes
4. **Test Thoroughly**: Test with various file types and error conditions
5. **Performance Testing**: Ensure changes don't impact performance
6. **Preprocessing Validation**: Test preprocessing improvements with real documents

## License

This upload system is part of the Owlin App project and follows the same licensing terms. 