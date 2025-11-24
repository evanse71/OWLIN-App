# backend/ocr/owlin_scan_pipeline.py
"""
Offline OCR pipeline scaffolding for Owlin.

Stage: PHASE 1 SCAFFOLD (safe stubs; no production wiring).
- Preprocessing (OpenCV) â€” stubbed but callable
- Layout detection (LayoutParser) â€” optional import; returns empty results if unavailable
- OCR (PaddleOCR) â€” optional import; returns empty text with low confidence if unavailable
- Table extraction â€” placeholder
- Confidence scoring â€” simple weighted example
- Artifacts â€” deterministic file layout under data/uploads/<slug>/

Notes:
- Import heavy libs lazily & defensively.
- All functions typed and documented.
- Safe to import without installing optional deps.
"""

from __future__ import annotations
import io
import json
import logging
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Import Phase 2 config flags
from backend.config import FEATURE_OCR_V2_PREPROC, FEATURE_OCR_V2_LAYOUT, CONF_FIELD_MIN, CONF_PAGE_MIN

# Import Phase 3 config flags
from backend.config import (
    FEATURE_OCR_V3_TABLES, FEATURE_OCR_V3_TEMPLATES,
    FEATURE_OCR_V3_DONUT, FEATURE_OCR_V3_LLM,
    CONF_FALLBACK_PAGE, CONF_FALLBACK_OVERALL,
)

# Import HTR config flags
from backend.config import (
    FEATURE_HTR_ENABLED, HTR_CONFIDENCE_THRESHOLD,
    HTR_MODEL_TYPE, HTR_SAVE_SAMPLES, HTR_REVIEW_QUEUE_ENABLED
)

# Import Donut fallback config flags
from backend.config import (
    FEATURE_DONUT_FALLBACK, DONUT_CONFIDENCE_THRESHOLD,
    DONUT_MODEL_PATH, DONUT_ENABLE_WHEN_NO_LINE_ITEMS
)

try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover
    fitz = None  # type: ignore

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    cv2, np = None, None  # type: ignore

# Phase 3 imports (lazy loading)
try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

try:
    from rapidfuzz import fuzz  # type: ignore
except Exception:  # pragma: no cover
    fuzz = None  # type: ignore

# Optional heavy deps â€” load lazily in ModelRegistry
# - paddleocr
# - layoutparser
# - layoutparser.models

LOGGER = logging.getLogger("owlin.ocr.pipeline")
LOGGER.setLevel(logging.INFO)


@dataclass
class BlockResult:
    type: str
    bbox: Tuple[int, int, int, int]  # x, y, w, h
    ocr_text: str
    confidence: float
    table_data: Optional[List[List[str]]] = None


@dataclass
class PageResult:
    page_num: int
    confidence: float
    preprocessed_image_path: str
    blocks: List[BlockResult]


class ModelRegistry:
    """Lazy singleton for optional models (PaddleOCR, LayoutParser)."""

    _instance: Optional["ModelRegistry"] = None

    def __init__(self) -> None:
        self._paddle_ocr = None
        self._layout_model = None

    @classmethod
    def get(cls) -> "ModelRegistry":
        if cls._instance is None:
            cls._instance = ModelRegistry()
        return cls._instance

    def paddle(self):
        if self._paddle_ocr is not None:
            return self._paddle_ocr
        try:
            from paddleocr import PaddleOCR  # type: ignore
            # Keep light; user can change params later
            self._paddle_ocr = PaddleOCR(lang="en")
            LOGGER.info("PaddleOCR initialized.")
        except Exception as e:  # pragma: no cover
            LOGGER.warning("PaddleOCR unavailable: %s", e)
            self._paddle_ocr = None
        return self._paddle_ocr

    def layout(self):
        if self._layout_model is not None:
            return self._layout_model
        try:
            import layoutparser as lp  # type: ignore
            self._layout_model = lp.AutoLayoutModel("lp://EfficientDet/PubLayNet")
            LOGGER.info("LayoutParser model initialized.")
        except Exception as e:  # pragma: no cover
            LOGGER.warning("LayoutParser unavailable: %s", e)
            self._layout_model = None
        return self._layout_model


def _ensure_dirs(base: Path) -> None:
    (base / "pages").mkdir(parents=True, exist_ok=True)


def _slug_for(pdf_path: Path) -> str:
    return pdf_path.stem.replace(" ", "_").lower()


def _export_page_image(doc: Any, page_index: int, out_path: Path) -> Path:
    """Render a PDF page as PNG using PyMuPDF. Returns image path."""
    if fitz is None:
        raise RuntimeError("PyMuPDF not installed; cannot render page.")
    page = doc.load_page(page_index)
    pix = page.get_pixmap(dpi=200)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(out_path))
    return out_path


def preprocess_image(img_path: Path) -> Path:
    """
    Phase 2 enhanced preprocessing with OpenCV:
    - If FEATURE_OCR_V2_PREPROC=false: minimal preprocessing (Phase 1 behavior)
    - If FEATURE_OCR_V2_PREPROC=true: advanced pipeline (deskew, denoise, CLAHE, morphology, threshold, dewarp)
    - If OpenCV missing: copy through gracefully

    Returns the path to the preprocessed image.
    """
    out_path = img_path.with_suffix(".pre.png")
    
    # Phase 1 behavior when flag is off
    if not FEATURE_OCR_V2_PREPROC:
        if cv2 is None or np is None:
            shutil.copyfile(img_path, out_path)
            return out_path

        img = cv2.imread(str(img_path))
        if img is None:
            shutil.copyfile(img_path, out_path)
            return out_path

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Adaptive threshold as placeholder (tunable later)
        th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 35, 11)
        cv2.imwrite(str(out_path), th)
        return out_path
    
    # Phase 2 advanced preprocessing
    if cv2 is None or np is None:
        LOGGER.warning("OpenCV not available for advanced preprocessing, copying through")
        shutil.copyfile(img_path, out_path)
        return out_path

    try:
        img = cv2.imread(str(img_path))
        if img is None:
            LOGGER.warning("Could not load image for preprocessing, copying through")
            shutil.copyfile(img_path, out_path)
            return out_path

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 1. Deskew using Hough line detection
        try:
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            if lines is not None and len(lines) > 0:
                angles = []
                for line in lines:
                    rho, theta = line[0]
                    angle = theta - np.pi/2
                    angles.append(angle)
                if angles:
                    median_angle = np.median(angles)
                    if abs(median_angle) > 0.1:  # Only rotate if significant skew
                        h, w = gray.shape
                        center = (w // 2, h // 2)
                        rotation_matrix = cv2.getRotationMatrix2D(center, np.degrees(median_angle), 1.0)
                        gray = cv2.warpAffine(gray, rotation_matrix, (w, h), flags=cv2.INTER_CUBIC)
        except Exception as e:
            LOGGER.warning("Deskew failed: %s", e)
        
        # 2. Denoise with bilateral filter
        try:
            gray = cv2.bilateralFilter(gray, 9, 75, 75)
        except Exception as e:
            LOGGER.warning("Bilateral filter failed: %s", e)
        
        # 3. CLAHE (Contrast Limited Adaptive Histogram Equalization)
        try:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
        except Exception as e:
            LOGGER.warning("CLAHE failed: %s", e)
        
        # 4. Morphology opening to remove noise
        try:
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            gray = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
        except Exception as e:
            LOGGER.warning("Morphology opening failed: %s", e)
        
        # 5. Adaptive threshold with Gaussian fallback to Otsu
        try:
            # Try Gaussian adaptive threshold first
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                        cv2.THRESH_BINARY, 11, 2)
        except Exception as e:
            LOGGER.warning("Gaussian adaptive threshold failed: %s", e)
            try:
                # Fallback to Otsu
                _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            except Exception as e2:
                LOGGER.warning("Otsu threshold failed: %s", e2)
                thresh = gray
        
        # 6. Best-effort dewarp using 4-point contour detection
        try:
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                # Find largest contour
                largest_contour = max(contours, key=cv2.contourArea)
                epsilon = 0.02 * cv2.arcLength(largest_contour, True)
                approx = cv2.approxPolyDP(largest_contour, epsilon, True)
                
                if len(approx) == 4:
                    # Found 4-point contour, apply perspective transform
                    pts = approx.reshape(4, 2)
                    # Order points: top-left, top-right, bottom-right, bottom-left
                    rect = np.zeros((4, 2), dtype=np.float32)
                    s = pts.sum(axis=1)
                    rect[0] = pts[np.argmin(s)]  # top-left
                    rect[2] = pts[np.argmax(s)]  # bottom-right
                    diff = np.diff(pts, axis=1)
                    rect[1] = pts[np.argmin(diff)]  # top-right
                    rect[3] = pts[np.argmax(diff)]  # bottom-left
                    
                    # Calculate dimensions
                    width = max(np.linalg.norm(rect[0] - rect[1]), np.linalg.norm(rect[2] - rect[3]))
                    height = max(np.linalg.norm(rect[0] - rect[3]), np.linalg.norm(rect[1] - rect[2]))
                    
                    # Destination points
                    dst = np.array([
                        [0, 0],
                        [width - 1, 0],
                        [width - 1, height - 1],
                        [0, height - 1]
                    ], dtype=np.float32)
                    
                    # Apply perspective transform
                    matrix = cv2.getPerspectiveTransform(rect, dst)
                    thresh = cv2.warpPerspective(thresh, matrix, (int(width), int(height)))
        except Exception as e:
            LOGGER.warning("Dewarp failed: %s", e)
        
        cv2.imwrite(str(out_path), thresh)
        return out_path
        
    except Exception as e:
        LOGGER.warning("Advanced preprocessing failed: %s, copying through", e)
        shutil.copyfile(img_path, out_path)
        return out_path


def detect_layout(img_path: Path) -> List[Dict[str, Any]]:
    """
    Enhanced layout detection using the new LayoutDetector module.
    - If FEATURE_OCR_V2_LAYOUT=false: return single full-page Text block (Phase 1 behavior)
    - If FEATURE_OCR_V2_LAYOUT=true: use LayoutParser EfficientDet PubLayNet with OpenCV fallback
    - Comprehensive error handling and artifact storage
    """
    # Phase 1 behavior when flag is off
    if not FEATURE_OCR_V2_LAYOUT:
        return [{
            "type": "Text",
            "bbox": [0, 0, 0, 0],  # unknown size
        }]
    
    # Use the new LayoutDetector module
    try:
        from ocr.layout_detector import detect_document_layout
        
        # Detect layout with comprehensive fallback
        result = detect_document_layout(img_path, page_num=1, save_artifacts=True)
        
        # Convert to legacy format for compatibility
        blocks = []
        for block in result.blocks:
            blocks.append({
                "type": block.type,
                "bbox": list(block.bbox),
                "confidence": block.confidence,
                "source": block.source
            })
        
        LOGGER.info("Layout detection completed: %d blocks, method=%s, conf=%.3f", 
                   len(blocks), result.method_used, result.confidence_avg)
        
        return blocks
        
    except Exception as e:
        LOGGER.error("Layout detection failed: %s", e)
        return [{"type": "Text", "bbox": [0, 0, 0, 0]}]


def ocr_block(img_path: Path, bbox: Tuple[int, int, int, int]) -> Tuple[str, float]:
    """
    Enhanced OCR processing using the new OCRProcessor module.
    Provides high-accuracy OCR with PaddleOCR and Tesseract fallback.
    """
    try:
        from ocr.ocr_processor import get_ocr_processor
        
        # Load image
        if cv2 is None:
            return ("", 0.05)
        
        image = cv2.imread(str(img_path))
        if image is None:
            return ("", 0.05)
        
        # Create block info for OCR processor
        block_info = {
            "type": "body",  # Default type for legacy compatibility
            "bbox": list(bbox)
        }
        
        # Process with OCR processor
        processor = get_ocr_processor()
        result = processor.process_block(image, block_info)
        
        return (result.ocr_text, result.confidence)
        
    except Exception as e:
        LOGGER.warning("Enhanced OCR failed, using fallback: %s", e)
        
        # Fallback to original method
        ocr = ModelRegistry.get().paddle()
        if ocr is None:
            return ("", 0.05)

        if cv2 is None:
            return ("", 0.05)

        try:  # pragma: no cover (model-heavy)
            x, y, w, h = bbox
            image = cv2.imread(str(img_path))
            if image is None:
                return ("", 0.05)
            if w > 0 and h > 0:
                crop = image[y:y + h, x:x + w]
            else:
                crop = image
            result = ocr.ocr(crop)
            texts: List[str] = []
            confs: List[float] = []
            if result and result[0]:
                for line in result[0]:
                    if len(line) >= 2:
                        box = line[0]
                        text_info = line[1]
                        if isinstance(text_info, tuple) and len(text_info) == 2:
                            txt, conf = text_info
                            texts.append(txt)
                            confs.append(float(conf))
                        else:
                            # Handle different result formats
                            texts.append(str(text_info))
                            confs.append(0.5)
            text = "\n".join(texts).strip()
            confidence = float(sum(confs) / len(confs)) if confs else 0.25
            return (text, confidence)
        except Exception as e:  # pragma: no cover
            LOGGER.warning("OCR failed: %s", e)
            return ("", 0.05)


def _load_supplier_templates() -> List[Dict[str, Any]]:
    """Load supplier templates from YAML file."""
    if yaml is None:
        LOGGER.warning("PyYAML not available for supplier templates")
        return []
    
    try:
        template_path = Path(__file__).parent / "supplier_templates.yaml"
        if not template_path.exists():
            LOGGER.warning("Supplier templates file not found: %s", template_path)
            return []
        
        with open(template_path, 'r', encoding='utf-8') as f:
            templates = yaml.safe_load(f)
        return templates or []
    except Exception as e:
        LOGGER.warning("Failed to load supplier templates: %s", e)
        return []


def _match_supplier_template(page_text: str, templates: List[Dict[str, Any]]) -> Optional[str]:
    """Match page text against supplier templates."""
    if fuzz is None:
        LOGGER.warning("rapidfuzz not available for template matching")
        return None
    
    best_match = None
    best_score = 0.0
    
    for template in templates:
        score = 0.0
        matches = 0
        
        # Check logo hint
        if template.get("logo_hint"):
            logo_score = fuzz.partial_ratio(template["logo_hint"], page_text)
            if logo_score > 70:
                score += logo_score * 0.3
                matches += 1
        
        # Check invoice number patterns
        if template.get("invoice_no"):
            for pattern in template["invoice_no"]:
                if pattern.lower() in page_text.lower():
                    score += 20
                    matches += 1
                    break
        
        # Check date patterns
        if template.get("date"):
            for pattern in template["date"]:
                if pattern.lower() in page_text.lower():
                    score += 15
                    matches += 1
                    break
        
        # Check table headers
        if template.get("table_headers"):
            for header in template["table_headers"]:
                if header.lower() in page_text.lower():
                    score += 10
                    matches += 1
        
        # Check currency
        if template.get("currency"):
            for currency in template["currency"]:
                if currency in page_text:
                    score += 15
                    matches += 1
                    break
        
        if matches > 0 and score > best_score:
            best_score = score
            best_match = template.get("supplier")
    
    return best_match if best_score > 50 else None


def _extract_table_data(blocks: List[Dict[str, Any]], image_path: str) -> Optional[List[List[str]]]:
    """Extract table data from table blocks."""
    if not FEATURE_OCR_V3_TABLES:
        return None
    
    try:
        from ocr.table_extractor import extract_table_data
        return extract_table_data(blocks, image_path)
    except Exception as e:
        LOGGER.warning("Table extraction failed: %s", e)
        return None


def _apply_donut_fallback(page_conf: float, overall_conf: float, image_path: str) -> Optional[Dict[str, Any]]:
    """Apply Donut fallback for low-confidence pages."""
    if not FEATURE_OCR_V3_DONUT:
        return None
    
    if page_conf >= CONF_FALLBACK_PAGE and overall_conf >= CONF_FALLBACK_OVERALL:
        return None
    
    try:
        from ocr.donut_fallback import parse_with_donut
        return parse_with_donut(image_path)
    except Exception as e:
        LOGGER.warning("Donut fallback failed: %s", e)
        return None


def _normalize_with_llm(block_texts: List[str]) -> Optional[Dict[str, Any]]:
    """Normalize OCR text using comprehensive field normalization system."""
    if not FEATURE_OCR_V3_LLM:
        return None
    
    try:
        from backend.llm.normalize_ocr import normalize_with_llm
        return normalize_with_llm(block_texts)
    except Exception as e:
        LOGGER.warning("Comprehensive normalization failed: %s", e)
        return None


def _normalize_with_context(block_texts: List[str], context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Normalize OCR text using context-aware field normalization."""
    if not FEATURE_OCR_V3_LLM:
        return None
    
    try:
        from backend.llm.normalize_ocr import normalize_with_context
        return normalize_with_context(block_texts, context)
    except Exception as e:
        LOGGER.warning("Context-aware normalization failed: %s", e)
        return None


def _process_handwriting_blocks(image_path: Path, layout_blocks: List[Dict[str, Any]], 
                               page_num: int = 1) -> Optional[Dict[str, Any]]:
    """Process handwriting blocks using HTR."""
    if not FEATURE_HTR_ENABLED:
        return None
    
    try:
        from htr import get_htr_processor, HTRConfig, HTRModelType
        
        # Create HTR configuration
        config = HTRConfig(
            enabled=FEATURE_HTR_ENABLED,
            confidence_threshold=HTR_CONFIDENCE_THRESHOLD,
            model_type=HTRModelType(HTR_MODEL_TYPE),
            save_samples=HTR_SAVE_SAMPLES,
            review_queue_enabled=HTR_REVIEW_QUEUE_ENABLED
        )
        
        # Get HTR processor
        processor = get_htr_processor(config)
        
        # Process handwriting blocks
        result = processor.process_handwriting_blocks(image_path, layout_blocks, page_num)
        
        if result.status.value == "success" and result.blocks:
            LOGGER.info("HTR processing completed: %d blocks processed, %d need review",
                       len(result.blocks), len(result.review_candidates))
            
            # Convert to dictionary format
            htr_data = {
                "htr_blocks": [block.to_dict() for block in result.blocks],
                "review_candidates": processor.get_review_candidates(result),
                "processing_stats": {
                    "total_blocks": result.total_blocks,
                    "high_confidence_blocks": result.high_confidence_blocks,
                    "processing_time": result.processing_time,
                    "model_used": result.model_used.value
                }
            }
            
            return htr_data
        else:
            LOGGER.info("HTR processing skipped or failed: %s", result.status.value)
            return None
            
    except Exception as e:
        LOGGER.warning("HTR processing failed: %s", e)
        return None


def _process_donut_fallback(image_path: Path, page_confidence: float, 
                          overall_confidence: float, line_items: List[Any] = None) -> Optional[Dict[str, Any]]:
    """Process document with Donut fallback when confidence is low or no line items."""
    if not FEATURE_DONUT_FALLBACK:
        return None
    
    # Check if Donut fallback should be triggered
    should_trigger = False
    
    # Trigger on low confidence
    if page_confidence < DONUT_CONFIDENCE_THRESHOLD or overall_confidence < DONUT_CONFIDENCE_THRESHOLD:
        should_trigger = True
        LOGGER.info("Donut fallback triggered: low confidence (page: %.3f, overall: %.3f)", 
                   page_confidence, overall_confidence)
    
    # Trigger when no line items (if enabled)
    if DONUT_ENABLE_WHEN_NO_LINE_ITEMS and (not line_items or len(line_items) == 0):
        should_trigger = True
        LOGGER.info("Donut fallback triggered: no line items found")
    
    if not should_trigger:
        return None
    
    try:
        from fallbacks import get_donut_fallback, map_donut_to_invoice_card, merge_invoice_cards
        
        # Get Donut fallback processor
        donut_processor = get_donut_fallback(
            enabled=FEATURE_DONUT_FALLBACK,
            model_path=DONUT_MODEL_PATH if DONUT_MODEL_PATH else None
        )
        
        # Process with Donut
        result = donut_processor.process_document(image_path)
        
        if result.ok and result.confidence >= DONUT_CONFIDENCE_THRESHOLD:
            LOGGER.info("Donut processing successful: confidence=%.3f, took=%.3fs", 
                       result.confidence, result.took_s)
            
            # Map Donut output to invoice card
            donut_card = map_donut_to_invoice_card(result.parsed or {})
            
            # Create Donut fallback data
            donut_data = {
                "donut_attempt": True,
                "donut_success": True,
                "donut_confidence": result.confidence,
                "donut_processing_time": result.took_s,
                "donut_parsed": donut_card,
                "donut_metadata": result.meta
            }
            
            return donut_data
        else:
            LOGGER.info("Donut processing failed or low confidence: ok=%s, confidence=%.3f", 
                       result.ok, result.confidence)
            
            # Return failure data for audit
            return {
                "donut_attempt": True,
                "donut_success": False,
                "donut_confidence": result.confidence,
                "donut_processing_time": result.took_s,
                "donut_error": result.meta.get("reason", "unknown"),
                "donut_metadata": result.meta
            }
            
    except Exception as e:
        LOGGER.warning("Donut fallback processing failed: %s", e)
        return {
            "donut_attempt": True,
            "donut_success": False,
            "donut_error": str(e),
            "donut_processing_time": 0.0
        }


def process_page_ocr_enhanced(img_path: Path, blocks_raw: List[Dict[str, Any]], page_index: int = 0) -> PageResult:
    """
    Enhanced OCR processing for all blocks on a page using the new OCRProcessor.
    Provides high-accuracy OCR with PaddleOCR and comprehensive fallbacks.
    """
    try:
        from ocr.ocr_processor import process_document_ocr
        from ocr.table_extractor import extract_table_from_block
        
        # Process all blocks with enhanced OCR
        result = process_document_ocr(img_path, blocks_raw, page_index + 1, save_artifacts=True)
        
        # Load image for table extraction
        if cv2 is None:
            LOGGER.warning("OpenCV not available for table extraction")
            image = None
        else:
            image = cv2.imread(str(img_path))
        
        # Convert to legacy PageResult format with table extraction
        # Step 2: Verify layout detection is finding tables
        LOGGER.info(f"[LAYOUT] Processing {len(result.blocks)} blocks from layout detection")
        blocks = []
        for idx, ocr_result in enumerate(result.blocks):
            LOGGER.info(f"[LAYOUT] Block {idx}: type={ocr_result.type}, bbox={ocr_result.bbox}, ocr_text_len={len(ocr_result.ocr_text)}")
            # Extract table data if this is a table block
            table_data = None
            if ocr_result.type == "table" and image is not None:
                # Step 1: Add critical logging to verify table extraction
                LOGGER.info(f"[TABLE_EXTRACT] Triggering extraction for table block, bbox={ocr_result.bbox}")
                try:
                    block_info = {
                        "type": ocr_result.type,
                        "bbox": list(ocr_result.bbox)
                    }
                    table_result = extract_table_from_block(image, block_info, ocr_result.ocr_text)
                    LOGGER.info(f"[TABLE_EXTRACT] Result: {len(table_result.line_items)} items, method={table_result.method_used}, conf={table_result.confidence:.3f}")
                    table_data = table_result.to_dict()
                    LOGGER.info(f"[TABLE_EXTRACT] table_data keys: {list(table_data.keys())}, line_items count: {len(table_data.get('line_items', []))}")
                    if table_data.get('line_items'):
                        LOGGER.info(f"[TABLE_EXTRACT] First item sample: {table_data['line_items'][0]}")
                except Exception as e:
                    LOGGER.error(f"[TABLE_EXTRACT] Error during extraction: {e}", exc_info=True)
                    table_data = None
            else:
                # Log why table extraction wasn't triggered
                LOGGER.debug(f"[TABLE_EXTRACT] Skipped: type={ocr_result.type}, image_available={image is not None}")
            
            block = BlockResult(
                type=ocr_result.type,
                bbox=ocr_result.bbox,
                ocr_text=ocr_result.ocr_text,
                confidence=ocr_result.confidence,
                table_data=table_data
            )
            blocks.append(block)
        
        return PageResult(
            page_num=page_index + 1,
            confidence=result.confidence_avg,
            preprocessed_image_path=str(img_path),
            blocks=blocks
        )
        
    except Exception as e:
        LOGGER.error("Enhanced OCR processing failed: %s", e)
        # Fallback to original method
        return assemble_page_result(page_index, img_path, blocks_raw)


def assemble_page_result(page_index: int, prep_img: Path, blocks_raw: List[Dict[str, Any]]) -> PageResult:
    """
    Phase 2 + Phase 3 enhanced page result assembly:
    - Penalize blocks with confidence < CONF_FIELD_MIN
    - Down-weight page confidence if < CONF_PAGE_MIN
    - Apply confidence penalties to low-quality blocks
    - Extract table data for table blocks
    - Apply Donut fallback for low-confidence pages
    """
    blocks: List[BlockResult] = []
    confs: List[float] = []
    
    for b in blocks_raw:
        bbox = tuple(b.get("bbox", [0, 0, 0, 0]))  # type: ignore
        btype = str(b.get("type", "Text"))
        text, conf = ocr_block(prep_img, bbox)  # safe if no OCR installed
        
        # Phase 2 confidence routing: penalize low-confidence fields
        if conf < CONF_FIELD_MIN:
            # Apply penalty to low-confidence blocks
            penalty_factor = 0.5  # Reduce confidence by 50% for low-confidence blocks
            conf = conf * penalty_factor
            LOGGER.debug("Applied confidence penalty to block (conf=%.3f < %.3f)", conf, CONF_FIELD_MIN)
        
        # Phase 3: Extract table data for table blocks
        table_data = None
        if btype.lower() == "table":
            table_data = _extract_table_data([b], str(prep_img))
        
        blocks.append(BlockResult(type=btype, bbox=bbox, ocr_text=text, confidence=conf, table_data=table_data))
        confs.append(conf)
    
    # Calculate page confidence
    page_conf = float(sum(confs) / len(confs)) if confs else 0.0
    
    # Phase 2 confidence routing: down-weight page if below threshold
    if page_conf < CONF_PAGE_MIN:
        # Apply page-level penalty for low overall confidence
        page_penalty_factor = 0.7  # Reduce page confidence by 30% for low-confidence pages
        page_conf = page_conf * page_penalty_factor
        LOGGER.debug("Applied page confidence penalty (page_conf=%.3f < %.3f)", page_conf, CONF_PAGE_MIN)
    
    return PageResult(
        page_num=page_index + 1,
        confidence=page_conf,
        preprocessed_image_path=str(prep_img),
        blocks=blocks,
    )


def process_document(pdf_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Process a PDF/image path and emit a structured dict with pages and confidences.
    Always returns a dict with status 'ok' or 'partial' (best-effort).
    """
    t0 = time.time()
    pdf_path = Path(pdf_path).resolve()
    if not pdf_path.exists():
        return {"status": "error", "error": f"File not found: {pdf_path}"}

    slug = _slug_for(pdf_path)
    base = Path("data") / "uploads" / slug
    _ensure_dirs(base)

    # Save original
    orig_target = base / "original.pdf"
    try:
        if pdf_path.suffix.lower() == ".pdf":
            shutil.copyfile(pdf_path, orig_target)
        else:
            # If image, wrap later; for now copy to original.pdf if PDF, else keep original image as is
            orig_target = base / pdf_path.name
            shutil.copyfile(pdf_path, orig_target)
    except Exception as e:
        return {"status": "error", "error": f"Failed to copy original: {e}"}

    pages: List[PageResult] = []
    try:
        if fitz is None:
            raise RuntimeError("PyMuPDF not installed.")
        if orig_target.suffix.lower() != ".pdf":
            # Create a simple one-page PDF wrapper if needed (optional later)
            pass
        doc = fitz.open(str(orig_target)) if orig_target.suffix.lower() == ".pdf" else None
        page_count = doc.page_count if doc is not None else 1
        for i in range(page_count):
            # Render to PNG
            page_img_path = base / "pages" / f"page_{i+1:03d}.png"
            if doc is not None:
                _export_page_image(doc, i, page_img_path)
            else:
                # If not a PDF, we assume original is already an image
                shutil.copyfile(orig_target, page_img_path)

            prep_img = preprocess_image(page_img_path)
            blocks_raw = detect_layout(prep_img)
            
            # Use enhanced OCR processing if available
            try:
                page_res = process_page_ocr_enhanced(prep_img, blocks_raw, i)
            except Exception as e:
                LOGGER.warning("Enhanced OCR failed, using fallback: %s", e)
                page_res = assemble_page_result(i, prep_img, blocks_raw)
            
            # Process handwriting blocks with HTR if enabled
            htr_data = _process_handwriting_blocks(prep_img, blocks_raw, i + 1)
            if htr_data:
                # Add HTR data to page result
                page_res.htr_data = htr_data
                LOGGER.info("HTR data added to page %d: %d blocks processed", i + 1, len(htr_data.get("htr_blocks", [])))
            
            pages.append(page_res)
    except Exception as e:
        LOGGER.error("Processing error during page extraction: %s", e, exc_info=True)
        # If we have no pages and it's a critical error, return error status
        if not pages:
            return {
                "status": "error",
                "error": f"Failed to extract pages from document: {str(e)}",
                "pages": [],
                "overall_confidence": 0.0
            }

    overall_conf = float(sum(p.confidence for p in pages) / len(pages)) if pages else 0.0

    # Phase 3: Apply Donut fallback to low-confidence pages
    for page in pages:
        if page.confidence < CONF_FALLBACK_PAGE or overall_conf < CONF_FALLBACK_OVERALL:
            fallback_result = _apply_donut_fallback(page.confidence, overall_conf, page.preprocessed_image_path)
            if fallback_result:
                # Add fallback_text to page (new field)
                page.fallback_text = fallback_result.get("text", "")
        
        # Apply new Donut fallback processing
        donut_data = _process_donut_fallback(
            Path(page.preprocessed_image_path), 
            page.confidence, 
            overall_conf,
            getattr(page, 'line_items', None)
        )
        if donut_data:
            page.donut_data = donut_data
            LOGGER.info("Donut fallback data added to page %d: success=%s, confidence=%.3f", 
                       page.page_num, donut_data.get("donut_success", False), 
                       donut_data.get("donut_confidence", 0.0))

    # Phase 3: Template matching
    template_match = None
    if FEATURE_OCR_V3_TEMPLATES and pages:
        try:
            templates = _load_supplier_templates()
            if templates:
                # Concatenate all page text for template matching
                all_text = " ".join([
                    " ".join([b.ocr_text for b in p.blocks])
                    for p in pages
                ])
                template_match = _match_supplier_template(all_text, templates)
        except Exception as e:
            LOGGER.warning("Template matching failed: %s", e)

    # Phase 3: Comprehensive field normalization
    normalized_json = None
    if FEATURE_OCR_V3_LLM and pages:
        try:
            # Collect high-confidence block texts
            high_conf_texts = []
            for page in pages:
                for block in page.blocks:
                    if block.confidence >= 0.6:  # High confidence threshold
                        high_conf_texts.append(block.ocr_text)
            
            if high_conf_texts:
                # Create context for better normalization
                context = {
                    "region": "UK",  # Could be inferred from content or user settings
                    "industry": "general",
                    "document_type": "invoice"
                }
                
                # Try context-aware normalization first
                normalized_json = _normalize_with_context(high_conf_texts, context)
                
                # Fallback to standard normalization if context-aware fails
                if not normalized_json:
                    normalized_json = _normalize_with_llm(high_conf_texts)
                
                # Apply supplier template overrides if available
                if normalized_json and FEATURE_OCR_V3_TEMPLATES:
                    try:
                        from templates.integration import apply_template_overrides
                        
                        # Extract header text from high confidence blocks
                        header_text = " ".join(high_conf_texts[:3])  # Use first 3 blocks as header
                        
                        # Extract line item texts
                        raw_line_texts = [block.ocr_text for block in page.blocks if block.type == "text"]
                        
                        # Apply template overrides
                        normalized_json = apply_template_overrides(
                            invoice_card=normalized_json,
                            header_text=header_text,
                            raw_line_texts=raw_line_texts
                        )
                        
                        LOGGER.info("Applied supplier template overrides to normalized JSON")
                        
                    except Exception as e:
                        LOGGER.warning("Template override processing failed: %s", e)
        except Exception as e:
            LOGGER.warning("Comprehensive normalization failed: %s", e)

    out = {
        "status": "ok" if pages else "partial",
        "pages": [
            {
                "page_num": p.page_num,
                "confidence": p.confidence,
                "preprocessed_image_path": p.preprocessed_image_path,
                "blocks": [
                    {
                        "type": b.type,
                        "bbox": list(b.bbox),
                        "ocr_text": b.ocr_text,
                        "confidence": b.confidence,
                        "table_data": b.table_data,
                    } for b in p.blocks
                ],
                # Phase 3: Add fallback_text if available
                **({"fallback_text": p.fallback_text} if hasattr(p, 'fallback_text') else {}),
                # HTR: Add HTR data if available
                **({"htr_data": p.htr_data} if hasattr(p, 'htr_data') else {}),
                # Donut: Add Donut fallback data if available
                **({"donut_data": p.donut_data} if hasattr(p, 'donut_data') else {}),
            } for p in pages
        ],
        "overall_confidence": overall_conf,
        "artifact_dir": str(base),
        "elapsed_sec": round(time.time() - t0, 3),
        # Phase 3: Add template match if available
        **({"template_match": template_match} if template_match else {}),
        # Phase 3: Add normalized JSON if available
        **({"normalized_json": normalized_json} if normalized_json else {}),
    }

    # Persist OCR JSON
    try:
        (base).mkdir(parents=True, exist_ok=True)
        with open(base / "ocr_output.json", "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    except Exception as e:
        LOGGER.warning("Failed to save OCR JSON: %s", e)

    return out



