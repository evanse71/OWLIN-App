# REQUIREMENTS DIFF: Spec vs Current Implementation

## Core OCR Pipeline Requirements

### 1. OpenCV Preprocessing Pipeline
**Spec Requirement:** "Deskew detection and rotation correction, Denoising (bilateral filter, morphological operations), Adaptive thresholding for photos vs scans, Perspective correction (dewarp) for phone captures, Contrast normalization (CLAHE)"

**Current Evidence:** ✅ **PARTIAL** - `backend/image_preprocess.py:88-119`
```python
def preprocess_bgr_page(img_bgr: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
    # Deskew detection: ✅ IMPLEMENTED
    deskewed, angle = _deskew(gray)
    
    # Denoising: ✅ IMPLEMENTED  
    den = cv2.bilateralFilter(deskewed, 5, 75, 75)
    
    # CLAHE: ✅ IMPLEMENTED
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(den)
    
    # Adaptive threshold: ✅ IMPLEMENTED
    bw = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 9)
```

**Missing:** Advanced dewarping, thermal receipt preprocessing, quality metrics

### 2. LayoutParser Integration
**Spec Requirement:** "Use pre-trained models (PubLayNet/EfficientDet) to segment pages into: Header/logo blocks, Invoice metadata region, Table regions (line items), Footer/totals block, Handwritten annotation zones"

**Current Evidence:** ❌ **MISSING** - No LayoutParser imports or usage found

**Required Implementation:**
```python
# MISSING: LayoutParser integration
import layoutparser as lp
model = lp.AutoLayoutModel('lp://EfficientDet/PubLayNet')
layout = model.detect(image)
```

### 3. PaddleOCR PP-Structure
**Spec Requirement:** "State-of-the-art accuracy for multilingual printed text, Built-in structure understanding (PP-StructureV2), Mobile/embedded deployment support, Trainable on custom fonts/layouts, Offline-first architecture"

**Current Evidence:** ❌ **MISSING** - `backend/ocr/engine.py:23-35`
```python
# CURRENT: Mock implementation
return {
    "supplier": "Unknown",
    "date": None, 
    "value": None,
    "confidence": 0.0,
    "status": "mock"
}
```

**Required Implementation:**
```python
# MISSING: PaddleOCR integration
from paddleocr import PaddleOCR
ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False)
result = ocr.ocr(img, cls=True)
```

### 4. Table Extraction Module
**Spec Requirement:** "Cell detection in table regions, Text association per cell, Line-item assembly (product, qty, unit price, VAT), Heuristic fallbacks for merged cells and broken layouts"

**Current Evidence:** ❌ **MISSING** - No table extraction logic found

**Required Implementation:**
```python
# MISSING: Table extraction
def extract_table_cells(table_region):
    # Cell detection using layout model
    # Text association per cell
    # Line-item assembly
    pass
```

### 5. Handwriting Recognition
**Spec Requirement:** "Dedicated HTR models for cursive/print handwriting, Trainable on venue-specific writing styles, Language model post-correction, Confidence scoring per character/word"

**Current Evidence:** ❌ **MISSING** - No HTR libraries found

**Required Implementation:**
```python
# MISSING: Kraken/PyLaia integration
import kraken
model = kraken.models.load_model('path/to/trained/model')
result = model.segment_and_recognize(image)
```

### 6. Donut Fallback
**Spec Requirement:** "End-to-end image → JSON without explicit OCR, Robust to layout variations that break cascade pipelines, Requires fine-tuning on 100-500 labeled invoices per supplier style, Use as fallback when traditional OCR confidence drops below threshold"

**Current Evidence:** ❌ **MISSING** - No Donut model integration

**Required Implementation:**
```python
# MISSING: Donut model integration
from transformers import DonutProcessor, VisionEncoderDecoderModel
processor = DonutProcessor.from_pretrained("naver-clova-ix/donut-base-finetuned-docvqa")
model = VisionEncoderDecoderModel.from_pretrained("naver-clova-ix/donut-base-finetuned-docvqa")
```

### 7. Confidence Routing
**Spec Requirement:** "Calculate per-field confidence scores, Route sub-threshold fields to manual review queue, Build review UI in existing Card system"

**Current Evidence:** ⚠️ **PARTIAL** - `backend/ocr/engine.py:32`
```python
# CURRENT: Hardcoded confidence
"confidence": 0.0,
```

**Required Implementation:**
```python
# MISSING: Confidence calculation and routing
def calculate_confidence(ocr_result):
    # Per-field confidence scoring
    # Overall confidence aggregation
    # Routing logic for manual review
    pass
```

### 8. Post-processing Normalization
**Spec Requirement:** "Date/currency/unit canonicalization, Fuzzy supplier matching, Draft credit request emails, Run fully offline (4-bit quantization on 16-32GB RAM)"

**Current Evidence:** ⚠️ **PARTIAL** - `backend/matching/pairing.py:89-114`
```python
# CURRENT: Basic metadata extraction
def extract_doc_metadata(parsed: Dict, filename: str) -> Dict:
    return {
        "supplier": parsed.get("supplier") if parsed else None,
        "invoice_no": parsed.get("invoice_number") if parsed else None,
        # ... basic extraction only
    }
```

**Missing:** Date normalization, currency conversion, fuzzy matching, LLM integration

### 9. Local LLM Integration
**Spec Requirement:** "Convert raw OCR tokens → normalized JSON, Date/currency/unit canonicalization, Fuzzy supplier matching, Draft credit request emails, Run fully offline (4-bit quantization on 16-32GB RAM)"

**Current Evidence:** ❌ **MISSING** - No LLM integration found

**Required Implementation:**
```python
# MISSING: Local LLM integration
from transformers import LlamaForCausalLM, LlamaTokenizer
model = LlamaForCausalLM.from_pretrained("path/to/quantized/model")
tokenizer = LlamaTokenizer.from_pretrained("path/to/tokenizer")
```

### 10. Artifact Storage
**Spec Requirement:** "Original PDF → data/uploads/<filename>/original.pdf, Preprocessed page images → data/uploads/<filename>/pages/page_001.png, OCR JSON → data/uploads/<filename>/ocr_output.json"

**Current Evidence:** ⚠️ **PARTIAL** - `backend/image_preprocess.py:120-124`
```python
# CURRENT: Basic artifact saving
def save_preprocessed_artifact(bw_or_gray: np.ndarray, artifact_dir: str, basename: str) -> str:
    os.makedirs(artifact_dir, exist_ok=True)
    out_path = os.path.join(artifact_dir, f"{basename}.png")
    cv2.imwrite(out_path, bw_or_gray)
    return out_path
```

**Missing:** Structured artifact organization, OCR JSON storage, versioning

### 11. Test Coverage
**Spec Requirement:** "Test fixtures for each stage, Accuracy tests vs ground truth, Performance benchmarks, End-to-end pipeline tests"

**Current Evidence:** ⚠️ **PARTIAL** - `tests/test_image_preprocess.py:19-25`
```python
# CURRENT: Basic preprocessing test
def test_preprocess_basic():
    bgr = _synthetic_doc()
    proc, meta = preprocess_bgr_page(bgr)
    assert proc is not None
    assert isinstance(proc, np.ndarray)
    assert len(meta.get("steps", [])) >= 3
```

**Missing:** OCR accuracy tests, confidence scoring tests, table extraction tests, performance benchmarks

### 12. Performance Optimization
**Spec Requirement:** "Lazy-load models (singleton pattern), Cache preprocessed images if processing multiple times, Use multiprocessing for batch processing"

**Current Evidence:** ❌ **MISSING** - No performance optimizations found

**Required Implementation:**
```python
# MISSING: Performance optimizations
class ModelSingleton:
    _instance = None
    _ocr_model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

## Stage-1 Conformance Checklist

### ✅ IMPLEMENTED (3/20 items)
- [x] Basic OpenCV preprocessing (deskew, denoise, CLAHE, threshold)
- [x] Image upload and storage infrastructure
- [x] Basic artifact saving for preprocessed images

### ❌ MISSING (17/20 items)
- [ ] LayoutParser integration for document segmentation
- [ ] PaddleOCR PP-Structure integration for printed text
- [ ] Table extraction with cell detection and line-item assembly
- [ ] Confidence scoring per field and overall
- [ ] Confidence-based routing to manual review
- [ ] Date normalization (YYYY-MM-DD format)
- [ ] Currency symbol conversion (£→GBP, €→EUR, $→USD)
- [ ] Fuzzy supplier matching with aliases
- [ ] Local LLM integration for OCR→JSON conversion
- [ ] Donut fallback for low-confidence documents
- [ ] Handwriting recognition with Kraken/PyLaia
- [ ] Structured artifact storage (original, preprocessed, OCR JSON)
- [ ] Comprehensive test coverage for all pipeline stages
- [ ] Performance optimization with lazy loading and caching
- [ ] Error handling with graceful degradation
- [ ] Batch processing for multiple documents
- [ ] GPU acceleration support

### 🎯 STAGE-1 TARGET (Must implement for basic OCR pipeline)
1. **LayoutParser Integration** - Document segmentation into blocks
2. **PaddleOCR Integration** - Primary OCR engine with structure understanding  
3. **Table Extraction** - Cell detection and line-item assembly
4. **Confidence Scoring** - Per-field and overall confidence calculation
5. **Confidence Routing** - Manual review queue for low-confidence results
6. **Date Normalization** - Standardized date format (YYYY-MM-DD)
7. **Currency Conversion** - Symbol to ISO code conversion
8. **Fuzzy Supplier Matching** - Improved supplier name matching
9. **Structured Artifact Storage** - Organized storage for all pipeline outputs
10. **Comprehensive Testing** - Accuracy tests for all pipeline stages

### 📊 CONFORMANCE STATUS
- **Current Conformance:** 15% (3/20 items)
- **Stage-1 Target:** 50% (10/20 items) 
- **Full Conformance:** 100% (20/20 items)

### 🚀 IMPLEMENTATION PRIORITY
1. **Week 1-2:** LayoutParser + PaddleOCR integration (Items 1-2)
2. **Week 3-4:** Table extraction + confidence scoring (Items 3-4)  
3. **Week 5-6:** Normalization + fuzzy matching (Items 6-8)
4. **Week 7-8:** Artifact storage + testing (Items 9-10)
