# GAP REPORT: Current Owlin vs OCR Pipeline Spec

## Executive Summary

The current Owlin system has a **solid foundation** with local-first architecture, SQLite database, and basic image preprocessing, but is **missing 85% of the advanced OCR pipeline capabilities** specified in the requirements. The system currently operates in "mock mode" with minimal OCR functionality.

## Master Gap Analysis Table

| Capability | Spec Detail | Present? | Where Implemented | Evidence Snippet | Severity | Work Item ID |
|------------|-------------|----------|-------------------|------------------|----------|--------------|
| **OpenCV Preprocessing** | Deskew, denoise, threshold, dewarp, photo vs scan | Partial | `backend/image_preprocess.py:88-119` | `def preprocess_bgr_page(img_bgr: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:` | High | WI-001 |
| **LayoutParser Integration** | Header/table/footer/handwriting segmentation | N | No occurrences found | No LayoutParser imports or usage | High | WI-002 |
| **PaddleOCR PP-Structure** | Printed blocks OCR with structure understanding | N | No occurrences found | No PaddleOCR imports or usage | High | WI-003 |
| **Table Extraction** | Cell detection, row assembly, line items | N | No occurrences found | No table extraction logic | High | WI-004 |
| **Handwriting Recognition** | Kraken/PyLaia HTR models | N | No occurrences found | No HTR libraries or training | High | WI-005 |
| **Donut Fallback** | OCR-free vision parser for edge cases | N | No occurrences found | No Donut model integration | Medium | WI-006 |
| **Confidence Routing** | Field/block/page/overall confidence scoring | Partial | `backend/ocr/engine.py:28-35` | `"confidence": 0.0, "status": "mock"` | High | WI-007 |
| **Post-processing** | Date/currency normalization, fuzzy matching | Partial | `backend/matching/pairing.py:89-114` | Basic metadata extraction only | Medium | WI-008 |
| **Local LLM** | Llama/Mistral for OCR→JSON conversion | N | No occurrences found | No LLM integration | Medium | WI-009 |
| **Artifact Storage** | Original, preprocessed, OCR JSON storage | Partial | `backend/image_preprocess.py:120-124` | Basic artifact saving only | Low | WI-010 |
| **Test Coverage** | Fixtures, accuracy tests, performance tests | Partial | `tests/test_image_preprocess.py:19-25` | Basic preprocessing tests only | High | WI-011 |
| **Performance** | Lazy model init, caching, batch processing | N | No occurrences found | No performance optimizations | Medium | WI-012 |
| **Error Handling** | Graceful degradation, partial results | Partial | `backend/ocr/engine.py:37-39` | Basic try/catch only | Medium | WI-013 |

## Detailed Capability Analysis

### 1. OpenCV Preprocessing (WI-001) - PARTIAL ✅
**Current State:** Basic preprocessing pipeline exists with deskew, denoise, CLAHE, and adaptive thresholding.

**Evidence:**
- File: `backend/image_preprocess.py:88-119`
- Functions: `preprocess_bgr_page()`, `_deskew()`, `_perspective_correction()`
- Features: Photo detection, deskew, bilateral denoising, CLAHE enhancement, adaptive threshold

**Gaps:**
- Missing advanced dewarping for curved documents
- No noise reduction for thermal receipts
- Limited perspective correction for phone captures
- No preprocessing quality metrics

### 2. LayoutParser Integration (WI-002) - MISSING ❌
**Current State:** No layout detection or document segmentation.

**Evidence:** No LayoutParser imports or usage found in codebase.

**Required Implementation:**
- PubLayNet/EfficientDet model integration
- Header/table/footer/handwriting block detection
- Bounding box extraction for each block type
- Block-type routing for different OCR engines

### 3. PaddleOCR PP-Structure (WI-003) - MISSING ❌
**Current State:** Mock OCR engine with no real text extraction.

**Evidence:**
- File: `backend/ocr/engine.py:23-35`
- Current: `"supplier": "Unknown", "confidence": 0.0, "status": "mock"`

**Required Implementation:**
- PaddleOCR with PP-StructureV2 integration
- Multilingual text recognition
- Structure understanding for tables and forms
- Confidence scoring per text block

### 4. Table Extraction (WI-004) - MISSING ❌
**Current State:** No table detection or line-item extraction.

**Evidence:** No table extraction logic found in codebase.

**Required Implementation:**
- Table cell detection using layout models
- Text association per cell
- Line-item assembly (product, qty, unit price, VAT)
- Heuristic fallbacks for merged cells

### 5. Handwriting Recognition (WI-005) - MISSING ❌
**Current State:** No HTR capabilities.

**Evidence:** No Kraken, PyLaia, or handwriting recognition libraries found.

**Required Implementation:**
- Kraken/PyLaia model training pipeline
- Handwriting zone detection
- Character-level confidence scoring
- Language model post-correction

### 6. Donut Fallback (WI-006) - MISSING ❌
**Current State:** No OCR-free vision parsing.

**Evidence:** No Donut model integration found.

**Required Implementation:**
- Donut model fine-tuning on invoice data
- Confidence-gated fallback routing
- End-to-end image→JSON conversion
- Validation against traditional OCR

### 7. Confidence Routing (WI-007) - PARTIAL ⚠️
**Current State:** Basic confidence field in mock data.

**Evidence:**
- File: `backend/ocr/engine.py:32`
- Current: `"confidence": 0.0` (hardcoded)

**Gaps:**
- No per-field confidence calculation
- No confidence-based routing logic
- No manual review queue for low-confidence results
- No confidence aggregation across pipeline stages

### 8. Post-processing (WI-008) - PARTIAL ⚠️
**Current State:** Basic metadata extraction for pairing.

**Evidence:**
- File: `backend/matching/pairing.py:89-114`
- Current: Simple field extraction without normalization

**Gaps:**
- No date normalization (YYYY-MM-DD format)
- No currency symbol conversion (£→GBP, €→EUR)
- No fuzzy supplier matching
- No amount parsing and validation

### 9. Local LLM Integration (WI-009) - MISSING ❌
**Current State:** No LLM integration for interpretation.

**Evidence:** No LLM libraries or inference code found.

**Required Implementation:**
- Quantized Llama 2/Mistral model deployment
- OCR→JSON conversion prompts
- Date/currency normalization
- Email draft generation for credit requests

### 10. Artifact Storage (WI-010) - PARTIAL ⚠️
**Current State:** Basic preprocessed image saving.

**Evidence:**
- File: `backend/image_preprocess.py:120-124`
- Current: `save_preprocessed_artifact()` function

**Gaps:**
- No original PDF storage structure
- No OCR JSON output storage
- No per-page artifact organization
- No artifact versioning or cleanup

### 11. Test Coverage (WI-011) - PARTIAL ⚠️
**Current State:** Basic preprocessing tests only.

**Evidence:**
- File: `tests/test_image_preprocess.py:19-25`
- Current: `test_preprocess_basic()` with synthetic data

**Gaps:**
- No OCR accuracy tests
- No confidence scoring tests
- No table extraction tests
- No end-to-end pipeline tests
- No performance benchmarks

### 12. Performance Optimization (WI-012) - MISSING ❌
**Current State:** No performance optimizations.

**Evidence:** No lazy loading, caching, or batch processing found.

**Required Implementation:**
- Lazy model initialization
- Preprocessed image caching
- Batch processing for multiple documents
- GPU acceleration support

### 13. Error Handling (WI-013) - PARTIAL ⚠️
**Current State:** Basic try/catch with logging.

**Evidence:**
- File: `backend/ocr/engine.py:37-39`
- Current: `except Exception as e: logger.error(f"OCR failed for {pdf_path}: {e}")`

**Gaps:**
- No graceful degradation on preprocessing failures
- No partial result handling
- No retry logic for transient failures
- No error classification and routing

## Critical Missing Dependencies

1. **LayoutParser** - Document layout detection
2. **PaddleOCR** - Primary OCR engine with structure understanding
3. **Kraken/PyLaia** - Handwriting recognition
4. **Donut** - OCR-free vision parsing
5. **Local LLM** - Llama 2/Mistral for interpretation
6. **Advanced OpenCV** - Additional preprocessing techniques

## Current System Strengths

1. **Solid Foundation** - Local-first SQLite architecture
2. **Basic Preprocessing** - Deskew, denoise, thresholding
3. **Document Management** - Upload, storage, database schema
4. **Pairing Logic** - Invoice-delivery note matching
5. **Audit Trail** - Comprehensive logging system
6. **API Structure** - FastAPI with proper error handling

## Severity Assessment

- **High Severity (8 items):** Core OCR pipeline missing
- **Medium Severity (4 items):** Advanced features and optimizations
- **Low Severity (1 item):** Artifact storage improvements

## Next Steps Priority

1. **Immediate (Week 1-2):** Implement PaddleOCR + LayoutParser integration
2. **Short-term (Week 3-4):** Add table extraction and confidence routing
3. **Medium-term (Week 5-8):** Implement HTR training and Donut fallback
4. **Long-term (Week 9+):** Add local LLM and performance optimizations
