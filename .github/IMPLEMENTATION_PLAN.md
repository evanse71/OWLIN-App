# IMPLEMENTATION PLAN: OCR Pipeline Development

## Executive Summary

This plan outlines the phased implementation of a production-grade OCR pipeline for the Owlin system, transforming it from a mock OCR system to a comprehensive document processing platform capable of handling printed invoices, receipts, delivery notes, and handwritten annotations.

## Phased Development Strategy

### 🎯 STAGE 1: Core Pipeline Foundation (Weeks 1-4)
**Goal:** Implement basic OCR pipeline with LayoutParser + PaddleOCR + table extraction

### 🚀 STAGE 2: Advanced Capabilities (Weeks 5-8)  
**Goal:** Add confidence routing, normalization, and local LLM integration

### 🔥 STAGE 3: Fallback & Intelligence (Weeks 9-12)
**Goal:** Implement Donut fallback, HTR training, and performance optimizations

---

## STAGE 1: Core Pipeline Foundation

### Work Item WI-001: LayoutParser Integration
**Owner:** TBD  
**ETA:** 16 hours  
**Risk:** Medium (model download, dependency conflicts)  
**Acceptance Tests:** 
- Document segmentation into header/table/footer blocks
- Bounding box extraction for each block type
- Block-type classification accuracy >90% on test set

**Changed Files:**
- `backend/ocr/layout_detector.py` (NEW)
- `backend/ocr/engine.py` (modify lines 8-40)
- `requirements.txt` (add layoutparser[paddledetection]>=0.3.4)

**New Files:**
- `backend/ocr/layout_detector.py`
- `tests/test_layout_detection.py`
- `tests/fixtures/sample_invoice.pdf`

**Touch Points:**
- `backend/ocr/engine.py:8-40` - Integrate layout detection
- `backend/ocr/engine.py:23-35` - Replace mock OCR with real pipeline

**Tests:**
```python
def test_layout_detection():
    # Verify block detection on sample invoice
    # Test header/table/footer classification
    # Validate bounding box accuracy
```

**Done When:** LayoutParser successfully segments test documents into semantic blocks with >90% accuracy

**Roll-back Plan:** Revert to mock OCR if layout detection fails, maintain existing upload flow

---

### Work Item WI-002: PaddleOCR Integration  
**Owner:** TBD  
**ETA:** 20 hours  
**Risk:** High (model size, GPU requirements)  
**Acceptance Tests:**
- Text extraction accuracy >95% on printed invoices
- Multilingual support (English, basic European languages)
- Structure understanding for tables and forms

**Changed Files:**
- `backend/ocr/engine.py` (replace lines 23-35)
- `backend/ocr/paddle_ocr_wrapper.py` (NEW)
- `requirements.txt` (add paddleocr>=2.7.0)

**New Files:**
- `backend/ocr/paddle_ocr_wrapper.py`
- `tests/test_paddle_ocr.py`
- `tests/fixtures/printed_invoice.png`

**Touch Points:**
- `backend/ocr/engine.py:23-35` - Replace mock with PaddleOCR
- `backend/ocr/engine.py:8-22` - Add OCR result processing

**Tests:**
```python
def test_paddle_ocr_accuracy():
    # Test on labeled invoice samples
    # Verify text extraction quality
    # Check confidence scoring
```

**Done When:** PaddleOCR extracts text with >95% accuracy on test invoices

**Roll-back Plan:** Fallback to mock OCR if PaddleOCR fails, log errors for debugging

---

### Work Item WI-003: Table Extraction
**Owner:** TBD  
**ETA:** 24 hours  
**Risk:** High (complex table layouts, merged cells)  
**Acceptance Tests:**
- Table cell detection accuracy >85%
- Line-item assembly with correct field mapping
- Heuristic fallbacks for broken layouts

**Changed Files:**
- `backend/ocr/table_extractor.py` (NEW)
- `backend/ocr/engine.py` (add table processing)
- `backend/models/line_item.py` (NEW)

**New Files:**
- `backend/ocr/table_extractor.py`
- `backend/models/line_item.py`
- `tests/test_table_extraction.py`
- `tests/fixtures/table_invoice.pdf`

**Touch Points:**
- `backend/ocr/engine.py:15-22` - Add table processing step
- `backend/ocr/engine.py:28-35` - Include table data in output

**Tests:**
```python
def test_table_extraction():
    # Test cell detection accuracy
    # Verify line-item assembly
    # Check field mapping (product, qty, price, total)
```

**Done When:** Table extraction correctly identifies line items with >85% accuracy

**Roll-back Plan:** Skip table processing if extraction fails, return basic OCR text

---

### Work Item WI-004: Confidence Scoring
**Owner:** TBD  
**ETA:** 12 hours  
**Risk:** Low (mathematical calculation)  
**Acceptance Tests:**
- Per-field confidence calculation
- Overall confidence aggregation
- Confidence-based routing logic

**Changed Files:**
- `backend/ocr/confidence_calculator.py` (NEW)
- `backend/ocr/engine.py` (add confidence calculation)
- `backend/models/confidence.py` (NEW)

**New Files:**
- `backend/ocr/confidence_calculator.py`
- `backend/models/confidence.py`
- `tests/test_confidence_scoring.py`

**Touch Points:**
- `backend/ocr/engine.py:28-35` - Add confidence calculation
- `backend/ocr/engine.py:8-14` - Integrate confidence into pipeline

**Tests:**
```python
def test_confidence_calculation():
    # Test per-field confidence scoring
    # Verify overall confidence aggregation
    # Check routing logic for low confidence
```

**Done When:** Confidence scoring accurately reflects OCR quality and enables routing decisions

**Roll-back Plan:** Use default confidence values if calculation fails

---

### Work Item WI-005: Structured Artifact Storage
**Owner:** TBD  
**ETA:** 8 hours  
**Risk:** Low (file system operations)  
**Acceptance Tests:**
- Organized storage structure (original, preprocessed, OCR JSON)
- Artifact versioning and cleanup
- Efficient storage and retrieval

**Changed Files:**
- `backend/storage/artifact_manager.py` (NEW)
- `backend/ocr/engine.py` (integrate artifact storage)
- `backend/image_preprocess.py:120-124` (enhance artifact saving)

**New Files:**
- `backend/storage/artifact_manager.py`
- `tests/test_artifact_storage.py`

**Touch Points:**
- `backend/ocr/engine.py:15-22` - Add artifact storage calls
- `backend/image_preprocess.py:120-124` - Enhance artifact saving

**Tests:**
```python
def test_artifact_storage():
    # Test organized storage structure
    # Verify artifact versioning
    # Check cleanup functionality
```

**Done When:** Artifacts are stored in organized structure with proper versioning

**Roll-back Plan:** Use existing basic artifact storage if new system fails

---

## STAGE 2: Advanced Capabilities

### Work Item WI-006: Date Normalization
**Owner:** TBD  
**ETA:** 10 hours  
**Risk:** Low (string parsing)  
**Acceptance Tests:**
- Date parsing from various formats (DD/MM/YYYY, MM-DD-YYYY, etc.)
- Normalization to YYYY-MM-DD format
- Error handling for invalid dates

**Changed Files:**
- `backend/processing/date_normalizer.py` (NEW)
- `backend/ocr/engine.py` (add date normalization)
- `backend/matching/pairing.py:89-114` (enhance date handling)

**New Files:**
- `backend/processing/date_normalizer.py`
- `tests/test_date_normalization.py`

**Touch Points:**
- `backend/ocr/engine.py:28-35` - Add date normalization
- `backend/matching/pairing.py:89-114` - Enhance date extraction

**Tests:**
```python
def test_date_normalization():
    # Test various date formats
    # Verify YYYY-MM-DD output
    # Check error handling
```

**Done When:** Date normalization handles 95% of common date formats correctly

**Roll-back Plan:** Return raw date strings if normalization fails

---

### Work Item WI-007: Currency Conversion
**Owner:** TBD  
**ETA:** 6 hours  
**Risk:** Low (symbol mapping)  
**Acceptance Tests:**
- Currency symbol to ISO code conversion (£→GBP, €→EUR, $→USD)
- Amount parsing and validation
- Multi-currency support

**Changed Files:**
- `backend/processing/currency_normalizer.py` (NEW)
- `backend/ocr/engine.py` (add currency normalization)
- `backend/matching/pairing.py:89-114` (enhance currency handling)

**New Files:**
- `backend/processing/currency_normalizer.py`
- `tests/test_currency_conversion.py`

**Touch Points:**
- `backend/ocr/engine.py:28-35` - Add currency normalization
- `backend/matching/pairing.py:89-114` - Enhance currency extraction

**Tests:**
```python
def test_currency_conversion():
    # Test symbol to ISO conversion
    # Verify amount parsing
    # Check multi-currency support
```

**Done When:** Currency conversion handles all major currency symbols correctly

**Roll-back Plan:** Return raw currency symbols if conversion fails

---

### Work Item WI-008: Fuzzy Supplier Matching
**Owner:** TBD  
**ETA:** 14 hours  
**Risk:** Medium (fuzzy matching accuracy)  
**Acceptance Tests:**
- Fuzzy matching with >90% accuracy on supplier names
- Alias resolution and canonicalization
- Performance optimization for large supplier lists

**Changed Files:**
- `backend/matching/supplier_matcher.py` (NEW)
- `backend/matching/pairing.py:89-114` (enhance supplier matching)
- `migrations/0004_supplier_aliases.sql` (enhance alias system)

**New Files:**
- `backend/matching/supplier_matcher.py`
- `tests/test_supplier_matching.py`

**Touch Points:**
- `backend/matching/pairing.py:89-114` - Enhance supplier matching
- `migrations/0004_supplier_aliases.sql` - Add more aliases

**Tests:**
```python
def test_fuzzy_supplier_matching():
    # Test fuzzy matching accuracy
    # Verify alias resolution
    # Check performance with large lists
```

**Done When:** Fuzzy supplier matching achieves >90% accuracy on test data

**Roll-back Plan:** Use exact string matching if fuzzy matching fails

---

### Work Item WI-009: Local LLM Integration
**Owner:** TBD  
**ETA:** 32 hours  
**Risk:** High (model size, inference performance)  
**Acceptance Tests:**
- OCR→JSON conversion with >85% accuracy
- Date/currency normalization via LLM
- Offline inference performance <5 seconds per document

**Changed Files:**
- `backend/llm/llm_processor.py` (NEW)
- `backend/ocr/engine.py` (add LLM processing)
- `requirements.txt` (add transformers, torch)

**New Files:**
- `backend/llm/llm_processor.py`
- `backend/llm/prompts.py`
- `tests/test_llm_integration.py`

**Touch Points:**
- `backend/ocr/engine.py:28-35` - Add LLM processing
- `backend/ocr/engine.py:15-22` - Integrate LLM into pipeline

**Tests:**
```python
def test_llm_integration():
    # Test OCR→JSON conversion
    # Verify normalization accuracy
    # Check inference performance
```

**Done When:** LLM integration provides accurate OCR→JSON conversion with acceptable performance

**Roll-back Plan:** Skip LLM processing if model fails, use basic OCR results

---

### Work Item WI-010: Comprehensive Testing
**Owner:** TBD  
**ETA:** 20 hours  
**Risk:** Low (test development)  
**Acceptance Tests:**
- End-to-end pipeline tests
- Accuracy benchmarks vs ground truth
- Performance regression tests

**Changed Files:**
- `tests/test_full_pipeline.py` (NEW)
- `tests/test_accuracy_benchmarks.py` (NEW)
- `tests/test_performance.py` (NEW)

**New Files:**
- `tests/test_full_pipeline.py`
- `tests/test_accuracy_benchmarks.py`
- `tests/test_performance.py`
- `tests/fixtures/ground_truth.json`

**Touch Points:**
- All test files - Comprehensive test coverage

**Tests:**
```python
def test_full_pipeline():
    # Test end-to-end document processing
    # Verify all pipeline stages
    # Check error handling
```

**Done When:** Comprehensive test suite covers all pipeline stages with >90% coverage

**Roll-back Plan:** Maintain existing tests if new tests fail

---

## STAGE 3: Fallback & Intelligence

### Work Item WI-011: Donut Fallback
**Owner:** TBD  
**ETA:** 28 hours  
**Risk:** High (model fine-tuning, inference performance)  
**Acceptance Tests:**
- Donut model fine-tuning on 200+ labeled invoices
- Confidence-gated fallback routing
- OCR-free vision parsing accuracy >80%

**Changed Files:**
- `backend/ocr/donut_fallback.py` (NEW)
- `backend/ocr/engine.py` (add Donut fallback)
- `scripts/train_donut.py` (NEW)

**New Files:**
- `backend/ocr/donut_fallback.py`
- `scripts/train_donut.py`
- `tests/test_donut_fallback.py`

**Touch Points:**
- `backend/ocr/engine.py:15-22` - Add Donut fallback routing
- `backend/ocr/engine.py:28-35` - Include Donut results

**Tests:**
```python
def test_donut_fallback():
    # Test confidence-gated routing
    # Verify OCR-free parsing accuracy
    # Check fallback performance
```

**Done When:** Donut fallback provides accurate OCR-free parsing for low-confidence documents

**Roll-back Plan:** Skip Donut processing if model fails, use traditional OCR only

---

### Work Item WI-012: Handwriting Recognition
**Owner:** TBD  
**ETA:** 40 hours  
**Risk:** High (model training, data labeling)  
**Acceptance Tests:**
- HTR model training on 500+ labeled handwriting samples
- Character-level confidence scoring
- Language model post-correction

**Changed Files:**
- `backend/ocr/htr_processor.py` (NEW)
- `backend/ocr/engine.py` (add HTR processing)
- `scripts/train_htr.py` (NEW)

**New Files:**
- `backend/ocr/htr_processor.py`
- `scripts/train_htr.py`
- `tests/test_htr_processing.py`

**Touch Points:**
- `backend/ocr/engine.py:15-22` - Add HTR processing
- `backend/ocr/engine.py:28-35` - Include HTR results

**Tests:**
```python
def test_htr_processing():
    # Test handwriting recognition accuracy
    # Verify confidence scoring
    # Check post-correction quality
```

**Done When:** HTR processing achieves >80% accuracy on handwritten text

**Roll-back Plan:** Skip HTR processing if model fails, use traditional OCR only

---

### Work Item WI-013: Performance Optimization
**Owner:** TBD  
**ETA:** 16 hours  
**Risk:** Medium (caching complexity, memory usage)  
**Acceptance Tests:**
- Lazy model initialization
- Preprocessed image caching
- Batch processing for multiple documents
- GPU acceleration support

**Changed Files:**
- `backend/performance/model_cache.py` (NEW)
- `backend/performance/batch_processor.py` (NEW)
- `backend/ocr/engine.py` (add performance optimizations)

**New Files:**
- `backend/performance/model_cache.py`
- `backend/performance/batch_processor.py`
- `tests/test_performance_optimization.py`

**Touch Points:**
- `backend/ocr/engine.py:8-14` - Add lazy loading
- `backend/ocr/engine.py:15-22` - Add caching

**Tests:**
```python
def test_performance_optimization():
    # Test lazy model initialization
    # Verify caching effectiveness
    # Check batch processing performance
```

**Done When:** Performance optimizations reduce processing time by >50% for batch operations

**Roll-back Plan:** Disable optimizations if they cause instability

---

## Risk Management

### High-Risk Items
1. **PaddleOCR Integration** - Model size, GPU requirements
2. **Table Extraction** - Complex layouts, merged cells
3. **Local LLM Integration** - Model size, inference performance
4. **Donut Fallback** - Model fine-tuning complexity
5. **Handwriting Recognition** - Training data requirements

### Mitigation Strategies
1. **Incremental Implementation** - Implement features one at a time
2. **Fallback Mechanisms** - Graceful degradation on failures
3. **Performance Monitoring** - Track processing times and accuracy
4. **User Feedback Loop** - Collect corrections for continuous improvement
5. **Rollback Plans** - Maintain working system at each stage

## Success Metrics

### Stage 1 Targets
- OCR accuracy >95% on printed invoices
- Table extraction accuracy >85%
- Processing time <10 seconds per document
- Test coverage >90%

### Stage 2 Targets
- Date normalization accuracy >95%
- Currency conversion accuracy >98%
- Fuzzy supplier matching accuracy >90%
- LLM integration performance <5 seconds per document

### Stage 3 Targets
- Donut fallback accuracy >80%
- HTR accuracy >80% on handwritten text
- Overall pipeline accuracy >90%
- Performance improvement >50% for batch processing

## Resource Requirements

### Development Time
- **Stage 1:** 80 hours (4 weeks @ 20 hours/week)
- **Stage 2:** 92 hours (4 weeks @ 23 hours/week)  
- **Stage 3:** 84 hours (4 weeks @ 21 hours/week)
- **Total:** 256 hours (12 weeks)

### Hardware Requirements
- **Development:** 16GB RAM, modern CPU, optional GPU
- **Production:** 32GB RAM, GPU recommended for LLM inference
- **Storage:** 50GB for models and training data

### Dependencies
- LayoutParser, PaddleOCR, Kraken, Donut, Local LLM
- OpenCV, NumPy, PIL, PyMuPDF
- Transformers, Torch, CUDA (optional)

## Conclusion

This implementation plan provides a structured approach to building a production-grade OCR pipeline for the Owlin system. The phased approach ensures incremental progress while maintaining system stability, with clear rollback plans for each stage. The focus on testing and performance monitoring ensures the final system meets production requirements.
