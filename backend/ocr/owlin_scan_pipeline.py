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
    FEATURE_LLM_EXTRACTION,
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

# Import dual-path OCR config flag
from backend.config import FEATURE_DUAL_OCR_PATH

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


def _float_safe(value: Any) -> float:
    """
    Safely parse a value (string, float, int) to float.
    Handles currency strings like "1,473.36", "£1,473.36", etc.
    
    Returns:
        float value, or 0.0 if parsing fails
    """
    if value is None:
        return 0.0
    
    if isinstance(value, (int, float)):
        return float(value)
    
    if not isinstance(value, str):
        return 0.0
    
    # Remove currency symbols and whitespace
    cleaned = value.replace('£', '').replace('$', '').replace('€', '').replace('Â£', '').replace('â‚¬', '').strip()
    
    # Remove commas (thousands separators)
    cleaned = cleaned.replace(',', '')
    
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


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
            # Set protobuf environment variable before importing PaddleOCR
            import os
            os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
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


def _analyze_pdf_structure(doc: Any) -> Dict[str, Any]:
    """
    Analyze PDF structure to detect text layer vs image-only pages.
    
    Returns diagnostic dict with:
    - has_text_layer: bool (True if any page has extractable text)
    - text_pages: List[int] (page indices with text, 0-based)
    - image_only_pages: List[int] (page indices without text, 0-based)
    - page_info: List[Dict] (per-page metadata: page_num, has_text, text_length, page_size)
    """
    if fitz is None:
        raise RuntimeError("PyMuPDF not installed; cannot analyze PDF structure.")
    
    page_count = doc.page_count
    text_pages = []
    image_only_pages = []
    page_info = []
    
    for i in range(page_count):
        page = doc.load_page(i)
        
        # Try to extract text from page
        page_text = page.get_text("text")
        text_length = len(page_text.strip()) if page_text else 0
        has_text = text_length > 0
        
        # Get page dimensions
        page_rect = page.rect
        page_size = {
            "width": page_rect.width,
            "height": page_rect.height
        }
        
        if has_text:
            text_pages.append(i)
        else:
            image_only_pages.append(i)
        
        page_info.append({
            "page_num": i + 1,
            "has_text": has_text,
            "text_length": text_length,
            "page_size": page_size
        })
    
    has_text_layer = len(text_pages) > 0
    
    result = {
        "has_text_layer": has_text_layer,
        "text_pages": text_pages,
        "image_only_pages": image_only_pages,
        "page_info": page_info,
        "page_count": page_count
    }
    
    LOGGER.info(
        f"[PDF_TRUTH_CHECK] PDF analysis: pages={page_count}, "
        f"has_text_layer={has_text_layer}, text_pages={len(text_pages)}, "
        f"image_only_pages={len(image_only_pages)}"
    )
    
    return result


def _export_page_image(doc: Any, page_index: int, out_path: Path, dpi: int = 300) -> Tuple[Path, Dict[str, Any]]:
    """
    Render a PDF page as PNG using PyMuPDF with validation.
    
    Returns:
        Tuple of (image_path, metadata_dict) where metadata contains:
        - width, height: image dimensions
        - mean_intensity: mean pixel intensity (0-255, lower = darker/blank)
        - file_size: rendered file size in bytes
        - dpi: DPI used for rendering
    """
    if fitz is None:
        raise RuntimeError("PyMuPDF not installed; cannot render page.")
    page = doc.load_page(page_index)
    pix = page.get_pixmap(dpi=dpi)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(out_path))
    
    # Validate rendered image
    width = pix.width
    height = pix.height
    file_size = out_path.stat().st_size if out_path.exists() else 0
    
    # Calculate mean pixel intensity to detect blank pages
    mean_intensity = None
    if np is not None and pix.samples:
        try:
            # Convert pixmap samples to numpy array
            samples = np.frombuffer(pix.samples, dtype=np.uint8)
            # For RGB images, calculate mean across all channels
            mean_intensity = float(np.mean(samples))
        except Exception as e:
            LOGGER.warning(f"[RENDER_VALIDATION] Failed to calculate mean intensity: {e}")
    
    metadata = {
        "width": width,
        "height": height,
        "mean_intensity": mean_intensity,
        "file_size": file_size,
        "dpi": dpi
    }
    
    # Log validation results
    LOGGER.info(
        f"[RENDER_VALIDATION] Page {page_index + 1}: "
        f"dimensions={width}x{height}, mean_intensity={mean_intensity:.2f if mean_intensity else 'N/A'}, "
        f"file_size={file_size/1024:.2f}KB, dpi={dpi}"
    )
    
    # Warn if image appears blank (very low intensity)
    if mean_intensity is not None and mean_intensity < 5:
        LOGGER.warning(
            f"[RENDER_VALIDATION] Page {page_index + 1} may be blank: "
            f"mean_intensity={mean_intensity:.2f} (threshold: 5)"
        )
    
    return out_path, metadata


def preprocess_image(img_path: Path, is_original_image: bool = False) -> Tuple[Path, str]:
    """
    Phase 2 enhanced preprocessing with OpenCV:
    - If FEATURE_OCR_V2_PREPROC=false: minimal preprocessing (Phase 1 behavior)
    - If FEATURE_OCR_V2_PREPROC=true: advanced pipeline (dewarp for photos, deskew, denoise, CLAHE, morphology, threshold)
    - If FEATURE_DUAL_OCR_PATH=true and is_original_image=true: run dual-path comparison and choose better result
    - If OpenCV missing: copy through gracefully
    
    For photos: Applies perspective correction (dewarping) BEFORE deskewing to handle skewed/trapezoid photos.

    Args:
        img_path: Path to image file to preprocess
        is_original_image: True if this is an original image file (not a rendered PDF page)

    Returns:
        Tuple of (Path to the preprocessed image, preprocessing_path_string)
        preprocessing_path_string: "enhanced", "minimal", "dual_path_chosen", or "none"
    """
    out_path = img_path.with_suffix(".pre.png")
    preprocessing_path = "none"
    
    # Dual-path mode: compare minimal vs enhanced for original image files
    if FEATURE_DUAL_OCR_PATH and is_original_image and FEATURE_OCR_V2_PREPROC:
        if cv2 is None or np is None:
            LOGGER.warning("OpenCV not available for dual-path preprocessing, using enhanced path")
        else:
            try:
                from backend.image_preprocess import compare_preprocessing_paths
                
                img = cv2.imread(str(img_path))
                if img is not None:
                    LOGGER.info(f"[DUAL_PATH] Running dual-path comparison for {img_path.name}")
                    comparison = compare_preprocessing_paths(img)
                    
                    chosen_path = comparison.get("chosen_path", "enhanced")
                    reason = comparison.get("comparison_metrics", {}).get("choice_reason", "unknown")
                    LOGGER.info(f"[DUAL_PATH] Chosen path: {chosen_path} - {reason}")
                    
                    # Get the chosen preprocessed image
                    if chosen_path == "minimal":
                        from backend.image_preprocess import preprocess_minimal
                        chosen_img, _ = preprocess_minimal(img)
                    else:
                        from backend.image_preprocess import preprocess_bgr_page
                        chosen_img, _ = preprocess_bgr_page(img)
                    
                    # Save chosen preprocessed image
                    cv2.imwrite(str(out_path), chosen_img)
                    
                    # Store comparison metadata for debugging and later use
                    comparison_meta_path = img_path.with_suffix(".comparison.json")
                    chosen_confidence = comparison.get(chosen_path, {}).get("avg_confidence", 0.0)
                    try:
                        import json
                        with open(comparison_meta_path, 'w') as f:
                            json.dump({
                                "chosen_path": chosen_path,
                                "chosen_confidence": chosen_confidence,  # Store chosen path's confidence
                                "minimal_confidence": comparison.get("minimal", {}).get("avg_confidence", 0.0),
                                "enhanced_confidence": comparison.get("enhanced", {}).get("avg_confidence", 0.0),
                                "minimal_words": comparison.get("minimal", {}).get("word_count", 0),
                                "enhanced_words": comparison.get("enhanced", {}).get("word_count", 0),
                                "reason": reason
                            }, f, indent=2)
                    except Exception as e:
                        LOGGER.warning(f"Failed to save comparison metadata: {e}")
                    
                    LOGGER.info(f"[DUAL_PATH] Chosen path confidence: {chosen_confidence:.3f}")
                    preprocessing_path = f"dual_path_chosen_{chosen_path}"
                    return out_path, preprocessing_path
            except Exception as e:
                LOGGER.warning(f"Dual-path preprocessing failed: {e}, falling back to enhanced path", exc_info=True)
                # Fall through to enhanced path
    
    # Phase 1 behavior when flag is off
    if not FEATURE_OCR_V2_PREPROC:
        preprocessing_path = "minimal"
        if cv2 is None or np is None:
            shutil.copyfile(img_path, out_path)
            return out_path, preprocessing_path

        img = cv2.imread(str(img_path))
        if img is None:
            shutil.copyfile(img_path, out_path)
            return out_path, preprocessing_path

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Adaptive threshold as placeholder (tunable later)
        th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 35, 11)
        cv2.imwrite(str(out_path), th)
        return out_path, preprocessing_path
    
    # Phase 2 advanced preprocessing
    preprocessing_path = "enhanced"
    if cv2 is None or np is None:
        LOGGER.warning("OpenCV not available for advanced preprocessing, copying through")
        preprocessing_path = "none"
        shutil.copyfile(img_path, out_path)
        return out_path, preprocessing_path

    try:
        # Import centralized preprocessing functions
        from backend.image_preprocess import detect_and_dewarp, _is_photo
        
        img = cv2.imread(str(img_path))
        if img is None:
            LOGGER.warning("Could not load image for preprocessing, copying through")
            shutil.copyfile(img_path, out_path)
            return out_path

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 0. Apply dewarping for photos BEFORE deskewing
        # This handles skewed/trapezoid photos by flattening perspective first
        if _is_photo(img):
            gray_before = gray.copy()
            gray = detect_and_dewarp(gray)
            if not np.array_equal(gray, gray_before):
                LOGGER.info("Applied perspective correction (dewarping) for photo input")
        
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
        
        cv2.imwrite(str(out_path), thresh)
        return out_path, preprocessing_path
        
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
        from backend.ocr.layout_detector import detect_document_layout
        
        # Detect layout with comprehensive fallback
        result = detect_document_layout(img_path, page_num=1, save_artifacts=True)
        LOGGER.info(f"[LAYOUT] Detected {len(result.blocks)} blocks from layout detector")
        
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
        
    except ImportError as e:
        LOGGER.error("[LAYOUT_IMPORT_FAIL] Layout detector import failed: %s", e)
        return [{"type": "Text", "bbox": [0, 0, 0, 0]}]
    except Exception as e:
        LOGGER.error("[LAYOUT_FAIL] Layout detection failed: %s", e)
        return [{"type": "Text", "bbox": [0, 0, 0, 0]}]


def ocr_block(img_path: Path, bbox: Tuple[int, int, int, int]) -> Tuple[str, float]:
    """
    Enhanced OCR processing using the new OCRProcessor module.
    Provides high-accuracy OCR with PaddleOCR and Tesseract fallback.
    """
    try:
        from backend.ocr.ocr_processor import get_ocr_processor
        
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
        from backend.ocr.table_extractor import extract_table_data
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


def process_page_ocr_enhanced(img_path: Path, blocks_raw: List[Dict[str, Any]], page_index: int = 0, 
                              preprocessing_path: Optional[str] = None,
                              force_ocr_engine: Optional[str] = None) -> PageResult:
    """
    Enhanced OCR processing for all blocks on a page using the new OCRProcessor.
    Provides high-accuracy OCR with PaddleOCR and comprehensive fallbacks.
    
    Now supports LLM-first extraction when FEATURE_LLM_EXTRACTION is enabled.
    """
    try:
        from backend.ocr.ocr_processor import process_document_ocr
        from backend.ocr.table_extractor import extract_table_from_block
        from backend.config import FEATURE_LLM_EXTRACTION, LLM_BBOX_MATCH_THRESHOLD
        
        # Process all blocks with enhanced OCR
        # Log engine selection if forced
        if force_ocr_engine:
            LOGGER.info(f"[OCR_ENGINE] Forcing OCR engine: {force_ocr_engine}")
        result = process_document_ocr(img_path, blocks_raw, page_index + 1, save_artifacts=True, 
                                     preprocessing_path=preprocessing_path,
                                     force_ocr_engine=force_ocr_engine)
        
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
        
        # Check if LLM extraction is enabled
        use_llm_extraction = FEATURE_LLM_EXTRACTION
        LOGGER.info(f"[LLM_EXTRACTION] Config check: FEATURE_LLM_EXTRACTION = {FEATURE_LLM_EXTRACTION} (type: {type(FEATURE_LLM_EXTRACTION)})")
        LOGGER.info(f"[LLM_EXTRACTION] use_llm_extraction = {use_llm_extraction}")
        llm_parser = None
        bbox_aligner = None
        
        if use_llm_extraction:
            try:
                from backend.llm.invoice_parser import create_invoice_parser, BBoxAligner
                llm_parser = create_invoice_parser()
                bbox_aligner = BBoxAligner(match_threshold=LLM_BBOX_MATCH_THRESHOLD)
                LOGGER.info("🔥🔥🔥 BRUTE FORCE: LLM EXTRACTION IS ON! 🔥🔥🔥")
                LOGGER.info("[LLM_EXTRACTION] ✓ LLM-first extraction ENABLED")
                LOGGER.info(f"[LLM_EXTRACTION] ✓ Model: {llm_parser.model_name}")
                LOGGER.info(f"[LLM_EXTRACTION] ✓ Timeout: {llm_parser.timeout}s")
                LOGGER.info(f"[LLM_EXTRACTION] ✓ Ollama URL: {llm_parser.ollama_url}")
            except Exception as e:
                LOGGER.error(f"[LLM_EXTRACTION] ✗ CRITICAL: Failed to initialize LLM parser!", exc_info=True)
                LOGGER.error(f"[LLM_EXTRACTION] ✗ Error: {str(e)}")
                # TEMPORARY: Crash instead of silently falling back
                raise RuntimeError(f"LLM initialization failed: {e}") from e
        else:
            LOGGER.warning(f"[LLM_EXTRACTION] ⚠ LLM extraction is DISABLED (FEATURE_LLM_EXTRACTION={FEATURE_LLM_EXTRACTION})")
            LOGGER.warning(f"[LLM_EXTRACTION] ⚠ Will use geometric extraction instead")
        
        # NEW: Assemble full-page OCR text for header/footer extraction
        full_page_text_parts = []
        for ocr_result in result.blocks:
            if ocr_result.ocr_text and ocr_result.ocr_text.strip():
                full_page_text_parts.append(ocr_result.ocr_text)
        full_page_text = "\n".join(full_page_text_parts)
        LOGGER.info(f"[LLM_EXTRACTION] Assembled full-page text: {len(full_page_text)} chars from {len(result.blocks)} blocks")
        
        # NEW: Parse full page once for header/footer fields (supplier, totals)
        page_level_result = None
        if use_llm_extraction and llm_parser and full_page_text:
            try:
                LOGGER.info("[LLM_EXTRACTION] ⚡ Parsing full-page text for header/footer extraction")
                # #region agent log
                import json
                log_path = Path(__file__).parent.parent.parent.parent / ".cursor" / "debug.log"
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "B", "location": "owlin_scan_pipeline.py:820", "message": "before LLM parse_document", "data": {"page_index": page_index, "ocr_text_length": len(full_page_text), "blocks_count": len(result.blocks)}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
                except: pass
                # #endregion
                page_level_result = llm_parser.parse_document(
                    ocr_text=full_page_text,
                    page_number=page_index + 1
                )
                # #region agent log
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "B", "location": "owlin_scan_pipeline.py:824", "message": "after LLM parse_document", "data": {"page_index": page_index, "success": page_level_result.success, "supplier": page_level_result.supplier_name, "line_items_count": len(page_level_result.line_items), "confidence": page_level_result.confidence, "error": page_level_result.error_message}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
                except: pass
                # #endregion
                if page_level_result.success:
                    LOGGER.info(
                        f"[LLM_EXTRACTION] ✓ Full-page extraction: supplier='{page_level_result.supplier_name}', "
                        f"total={page_level_result.grand_total:.2f}, confidence={page_level_result.confidence:.3f}, "
                        f"needs_review={getattr(page_level_result, 'needs_review', False)}"
                    )
                else:
                    LOGGER.warning(f"[LLM_EXTRACTION] ⚠ Full-page extraction failed: {page_level_result.error_message}")
            except Exception as e:
                LOGGER.error(f"[LLM_EXTRACTION] ✗ Full-page extraction error: {e}", exc_info=True)
                # #region agent log
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "B", "location": "owlin_scan_pipeline.py:833", "message": "LLM parse_document exception", "data": {"page_index": page_index, "error": str(e)}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
                except: pass
                # #endregion
                # Continue with block-level extraction as fallback
        
        for idx, ocr_result in enumerate(result.blocks):
            LOGGER.info(f"[LAYOUT] Block {idx}: type={ocr_result.type}, bbox={ocr_result.bbox}, ocr_text_len={len(ocr_result.ocr_text)}")
            # Extract table data if this is a table block
            table_data = None
            if ocr_result.type == "table" and image is not None:
                # Step 1: Add critical logging to verify table extraction
                LOGGER.info(f"[TABLE_EXTRACT] Triggering extraction for table block, bbox={ocr_result.bbox}")
                try:
                    if use_llm_extraction and llm_parser and bbox_aligner:
                        # LLM-First Extraction (NEW APPROACH)
                        # Use full-page text for better context, but focus on table block for line items
                        LOGGER.info("[LLM_EXTRACTION] ⚡ Starting LLM reconstruction for table extraction")
                        
                        # IMPROVED: Use full-page text for context, but table block for line items
                        # This gives the LLM header/footer context while focusing on the table
                        table_ocr_text = ocr_result.ocr_text
                        if full_page_text and len(full_page_text) > len(table_ocr_text):
                            # Prepend header context to table text
                            # Use first 2000 chars of full-page text as context
                            context_text = full_page_text[:2000] + "\n\n--- TABLE BLOCK ---\n\n" + table_ocr_text
                            LOGGER.info(f"[LLM_EXTRACTION] Using full-page context ({len(context_text)} chars) for table extraction")
                        else:
                            context_text = table_ocr_text
                        
                        # Step 1: Parse document with LLM (with full-page context)
                        llm_result = llm_parser.parse_document(
                            ocr_text=context_text,
                            page_number=page_index + 1
                        )
                        
                        # IMPROVED: Merge page-level result (header/footer) with table result (line items)
                        if page_level_result and page_level_result.success:
                            # Use page-level result for header fields and totals
                            llm_result.supplier_name = page_level_result.supplier_name or llm_result.supplier_name
                            llm_result.invoice_number = page_level_result.invoice_number or llm_result.invoice_number
                            llm_result.invoice_date = page_level_result.invoice_date or llm_result.invoice_date
                            llm_result.currency = page_level_result.currency or llm_result.currency
                            # Use page-level totals (more reliable from full-page context)
                            if page_level_result.grand_total > 0:
                                llm_result.subtotal = page_level_result.subtotal
                                llm_result.vat_amount = page_level_result.vat_amount
                                llm_result.grand_total = page_level_result.grand_total
                            # Merge needs_review flag
                            llm_result.needs_review = llm_result.needs_review or getattr(page_level_result, 'needs_review', False)
                            # Use lower confidence of the two
                            llm_result.confidence = min(llm_result.confidence, page_level_result.confidence)
                            LOGGER.info("[LLM_EXTRACTION] ✓ Merged page-level header/totals with table-level line items")
                        
                        if llm_result.success:
                            # Step 2: Align LLM results to OCR bounding boxes
                            ocr_blocks = getattr(ocr_result, 'word_blocks', None)
                            if ocr_blocks:
                                aligned_items = bbox_aligner.align_llm_to_ocr(
                                    llm_result.line_items,
                                    ocr_blocks
                                )
                            else:
                                LOGGER.warning("[LLM_EXTRACTION] ⚠ No word_blocks available for bbox alignment")
                                aligned_items = llm_result.line_items
                            
                            # Step 3: Convert to table_data format
                            table_data = {
                                "type": "table",
                                "bbox": list(ocr_result.bbox),
                                "line_items": [item.to_dict() for item in aligned_items],
                                "confidence": llm_result.confidence,
                                "method_used": "llm_reconstruction",
                                "processing_time": llm_result.processing_time,
                                "fallback_used": False,
                                "cell_count": len(aligned_items),
                                "row_count": len(aligned_items),
                                "document_type": llm_result.document_type.value,
                                "needs_review": getattr(llm_result, 'needs_review', False),
                                "metadata": {
                                    "supplier_name": llm_result.supplier_name,
                                    "invoice_number": llm_result.invoice_number,
                                    "invoice_date": llm_result.invoice_date,
                                    "currency": llm_result.currency,
                                    "subtotal": llm_result.subtotal,
                                    "vat_amount": llm_result.vat_amount,
                                    "grand_total": llm_result.grand_total,
                                    "validation_errors": llm_result.metadata.get("validation_errors", [])
                                }
                            }
                            
                            LOGGER.info(
                                f"[LLM_EXTRACTION] ✓ SUCCESS: {len(aligned_items)} items, "
                                f"confidence={llm_result.confidence:.3f}, "
                                f"needs_review={getattr(llm_result, 'needs_review', False)}, "
                                f"time={llm_result.processing_time:.2f}s"
                            )
                        else:
                            # LLM FAILED - Make it LOUD
                            LOGGER.error(f"[LLM_EXTRACTION] ✗ FAILED: {llm_result.error_message}")
                            LOGGER.error(f"[LLM_EXTRACTION] ✗ Processing time: {llm_result.processing_time:.2f}s")
                            LOGGER.error(f"[LLM_EXTRACTION] ✗ Confidence: {llm_result.confidence}")
                            
                            # TEMPORARY DEBUG MODE: Crash instead of marking for review
                            # This helps us see the exact error instead of silent fallback
                            if FEATURE_LLM_EXTRACTION:
                                error_msg = f"LLM extraction failed: {llm_result.error_message}"
                                LOGGER.error(f"[LLM_EXTRACTION] ✗ CRASHING to show error (debug mode)")
                                raise RuntimeError(error_msg)
                            
                            # Mark for manual review but don't fall back to geometric
                            table_data = {
                                "type": "table",
                                "bbox": list(ocr_result.bbox),
                                "line_items": [],
                                "confidence": 0.0,
                                "method_used": "llm_failed",
                                "processing_time": llm_result.processing_time,
                                "fallback_used": False,
                                "cell_count": 0,
                                "row_count": 0,
                                "error": llm_result.error_message,
                                "needs_manual_review": True
                            }
                    else:
                        # Geometric Extraction (LEGACY APPROACH)
                        LOGGER.warning("[TABLE_EXTRACT] ⚠ Using GEOMETRIC method (LLM not enabled)")
                        block_info = {
                            "type": ocr_result.type,
                            "bbox": list(ocr_result.bbox)
                        }
                        # Pass word_blocks for spatial clustering (if available)
                        ocr_blocks = getattr(ocr_result, 'word_blocks', None)
                        table_result = extract_table_from_block(image, block_info, ocr_result.ocr_text, ocr_blocks)
                        LOGGER.info(f"[TABLE_EXTRACT] Result: {len(table_result.line_items)} items, method={table_result.method_used}, conf={table_result.confidence:.3f}")
                        table_data = table_result.to_dict()
                        LOGGER.info(f"[TABLE_EXTRACT] table_data keys: {list(table_data.keys())}, line_items count: {len(table_data.get('line_items', []))}")
                        if table_data.get('line_items'):
                            LOGGER.info(f"[TABLE_EXTRACT] First item sample: {table_data['line_items'][0]}")
                except Exception as e:
                    LOGGER.error(f"[TABLE_EXTRACT] ✗✗✗ CRITICAL ERROR during extraction ✗✗✗", exc_info=True)
                    LOGGER.error(f"[TABLE_EXTRACT] Error type: {type(e).__name__}")
                    LOGGER.error(f"[TABLE_EXTRACT] Error message: {str(e)}")
                    # Re-raise to make it loud (temporary debug mode)
                    if use_llm_extraction and FEATURE_LLM_EXTRACTION:
                        LOGGER.error("[TABLE_EXTRACT] ✗ Re-raising exception for debugging")
                        raise
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
        
        # ENTERPRISE PIPELINE: Run dual extraction per page
        # Aggregate all OCR results from the page and run best extraction
        all_line_items = []
        all_debug = []
        
        try:
            from backend.ocr.table_extractor import get_table_extractor
            from backend.ocr.ocr_processor import OCRResult as OCRResultType
            
            extractor = get_table_extractor()
            
            # Aggregate all OCR text and word blocks from the page
            page_ocr_text_parts = []
            page_word_blocks = []
            page_confidence_sum = 0.0
            page_confidence_count = 0
            
            for ocr_result in result.blocks:
                if ocr_result.ocr_text and ocr_result.ocr_text.strip():
                    page_ocr_text_parts.append(ocr_result.ocr_text)
                
                # Collect word blocks if available
                if hasattr(ocr_result, 'word_blocks') and ocr_result.word_blocks:
                    for wb in ocr_result.word_blocks:
                        if isinstance(wb, dict):
                            page_word_blocks.append(wb)
                        else:
                            # Convert object to dict
                            page_word_blocks.append({
                                'text': getattr(wb, 'text', ''),
                                'bbox': getattr(wb, 'bbox', [0, 0, 0, 0])
                            })
                
                # Collect confidence
                if ocr_result.confidence > 0:
                    page_confidence_sum += ocr_result.confidence
                    page_confidence_count += 1
            
            # Calculate page-level base confidence
            page_base_confidence = page_confidence_sum / page_confidence_count if page_confidence_count > 0 else result.confidence_avg
            
            # Create aggregated OCRResult-like object for the page
            page_ocr_text = "\n".join(page_ocr_text_parts)
            
            if page_ocr_text.strip():
                # Create a synthetic OCRResult for the entire page
                class PageOCRResult:
                    def __init__(self, ocr_text, word_blocks, confidence, bbox):
                        self.ocr_text = ocr_text
                        self.word_blocks = word_blocks
                        self.confidence = confidence
                        self.bbox = bbox
                
                # Get page bbox (full image)
                if image is not None:
                    h, w = image.shape[:2]
                    page_bbox = (0, 0, w, h)
                else:
                    page_bbox = (0, 0, 0, 0)
                
                page_ocr_result = PageOCRResult(
                    ocr_text=page_ocr_text,
                    word_blocks=page_word_blocks if page_word_blocks else None,
                    confidence=page_base_confidence,
                    bbox=page_bbox
                )
                
                # Run dual extraction
                LOGGER.info(f"[ENTERPRISE_PIPELINE] Running dual extraction for page {page_index + 1}")
                best_items, debug_info = extractor.extract_best_line_items(
                    ocr_result=page_ocr_result,
                    page_index=page_index,
                    base_confidence=page_base_confidence,
                    image=image
                )
                
                all_line_items.extend(best_items)
                all_debug.append(debug_info)
                
                LOGGER.info(f"[ENTERPRISE_PIPELINE] Page {page_index + 1}: {len(best_items)} items using {debug_info.get('method_chosen', 'unknown')} method")
            else:
                LOGGER.warning(f"[ENTERPRISE_PIPELINE] Page {page_index + 1}: No OCR text available for dual extraction")
                all_debug.append({
                    "page_index": page_index,
                    "items_table_count": 0,
                    "items_fallback_count": 0,
                    "table_score": 0.0,
                    "fallback_score": 0.0,
                    "method_chosen": "none",
                    "error": "No OCR text available"
                })
        except Exception as e:
            LOGGER.error(f"[ENTERPRISE_PIPELINE] Dual extraction failed for page {page_index + 1}: {e}", exc_info=True)
            all_debug.append({
                "page_index": page_index,
                "items_table_count": 0,
                "items_fallback_count": 0,
                "table_score": 0.0,
                "fallback_score": 0.0,
                "method_chosen": "none",
                "error": str(e)
            })
        
        # Store line items and debug info in page result
        page_result = PageResult(
            page_num=page_index + 1,
            confidence=result.confidence_avg,
            preprocessed_image_path=str(img_path),
            blocks=blocks
        )
        
        # Add line items and debug info as attributes
        page_result.line_items = all_line_items
        page_result.line_items_debug = all_debug
        
        # Store PageOCRResult for telemetry collection
        page_result._ocr_result = result
        
        return page_result
        
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


def process_document(pdf_path: Union[str, Path], render_dpi: int = 300, 
                     preprocess_profile: str = "enhanced", 
                     force_ocr_engine: Optional[str] = None) -> Dict[str, Any]:
    """
    Process a PDF/image path and emit a structured dict with pages and confidences.
    Always returns a dict with status 'ok' or 'partial' (best-effort).
    
    Args:
        pdf_path: Path to PDF or image file
        render_dpi: DPI to use for rendering PDF pages (default: 300)
        preprocess_profile: Preprocessing profile ("enhanced" or "minimal", default: "enhanced")
        force_ocr_engine: Force specific OCR engine ("paddleocr" or "tesseract", default: None = auto)
    """
    # Import Path at function level with alias to avoid scoping issues
    from pathlib import Path as _Path
    t0 = time.time()
    pdf_path = _Path(pdf_path).resolve()
    if not pdf_path.exists():
        return {"status": "error", "error": f"File not found: {pdf_path}"}

    slug = _slug_for(pdf_path)
    base = _Path("data") / "uploads" / slug
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
    pdf_structure = None
    render_metadata_list = []
    
    # Determine file type and handle accordingly
    file_ext = orig_target.suffix.lower()
    is_pdf = file_ext == ".pdf"
    is_image = file_ext in {".png", ".jpg", ".jpeg", ".jpe"}
    
    # PyMuPDF is only required for PDF files
    if is_pdf and fitz is None:
        return {"status": "error", "error": "PyMuPDF not installed. PDF processing requires PyMuPDF."}
    
    try:
        # Handle PDF files
        if is_pdf:
            doc = fitz.open(str(orig_target))
            page_count = doc.page_count
            
            # PDF Truth Check: Analyze structure before processing
            pdf_structure = _analyze_pdf_structure(doc)
            
            # If PDF has text layer, extract text directly (fast path)
            if pdf_structure["has_text_layer"]:
                LOGGER.info(f"[PDF_TRUTH_CHECK] PDF has text layer - using fast text extraction path")
                # Extract text from pages with text layer
                for page_idx in pdf_structure["text_pages"]:
                    page = doc.load_page(page_idx)
                    page_text = page.get_text("text")
                    if page_text and page_text.strip():
                        # Create a minimal PageResult with extracted text
                        # This will be processed normally but with text already available
                        LOGGER.info(f"[PDF_TRUTH_CHECK] Extracted {len(page_text)} chars from page {page_idx + 1} text layer")
        # Handle image files (PNG, JPG, JPEG)
        elif is_image:
            doc = None
            page_count = 1
            # #region agent log
            import json
            # Use _Path (imported at function level) to avoid scoping issues
            log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "owlin_scan_pipeline.py:1378", "message": "image file detected", "data": {"file_ext": file_ext, "orig_target": str(orig_target), "orig_exists": orig_target.exists()}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
            except: pass
            # #endregion
        else:
            return {"status": "error", "error": f"Unsupported file format: {file_ext}. Supported: PDF, PNG, JPG, JPEG"}
        
        for i in range(page_count):
            # Render to PNG
            page_img_path = base / "pages" / f"page_{i+1:03d}.png"
            if doc is not None:
                # PDF: render page to image with validation
                page_img_path, render_metadata = _export_page_image(doc, i, page_img_path, dpi=render_dpi)
                render_metadata_list.append(render_metadata)
                # Log page processing
                if page_img_path.exists():
                    LOGGER.info(f"[PAGE_PROC] Page {i+1}/{page_count}: {page_img_path.name}, size={page_img_path.stat().st_size/1e6:.2f}MB")
            else:
                # Image file: copy directly - it will be processed as a single-page document
                # #region agent log
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "owlin_scan_pipeline.py:1396", "message": "copying image file", "data": {"orig_target": str(orig_target), "page_img_path": str(page_img_path), "orig_exists": orig_target.exists()}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
                except: pass
                # #endregion
                if orig_target.exists():
                    shutil.copyfile(orig_target, page_img_path)
                    LOGGER.info(f"[PAGE_PROC] Image file copied: {orig_target.name} -> {page_img_path.name}")
                    # #region agent log
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "owlin_scan_pipeline.py:1398", "message": "image file copied", "data": {"page_img_path": str(page_img_path), "copied_exists": page_img_path.exists(), "file_size": page_img_path.stat().st_size if page_img_path.exists() else 0}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
                    except: pass
                    # #endregion
                else:
                    LOGGER.error(f"[PAGE_PROC] Source image not found: {orig_target}")
                    continue

            # For image files, pass is_original_image=True to enable dual-path comparison
            # For PDF pages, pass False (they're rendered pages, not original images)
            # #region agent log
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "D", "location": "owlin_scan_pipeline.py:1405", "message": "before preprocessing", "data": {"page_img_path": str(page_img_path), "is_original_image": is_image, "preprocess_profile": preprocess_profile}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
            except: pass
            # #endregion
            prep_img, preprocessing_path = preprocess_image(page_img_path, is_original_image=is_image)
            # #region agent log
            try:
                prep_img_str = str(prep_img) if prep_img else None
                prep_img_exists = prep_img.exists() if prep_img and hasattr(prep_img, 'exists') else None
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "D", "location": "owlin_scan_pipeline.py:1405", "message": "after preprocessing", "data": {"prep_img": prep_img_str, "prep_img_exists": prep_img_exists, "preprocessing_path": preprocessing_path}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
            except: pass
            # #endregion
            blocks_raw = detect_layout(prep_img)
            # #region agent log
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "E", "location": "owlin_scan_pipeline.py:1406", "message": "layout detected", "data": {"blocks_count": len(blocks_raw) if blocks_raw else 0}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
            except: pass
            # #endregion
            
            # Use enhanced OCR processing if available
            # CRITICAL: If LLM extraction is enabled, DO NOT fall back to geometric method
            # Let it fail loudly so we can see the actual LLM error
            if FEATURE_LLM_EXTRACTION:
                # LLM extraction enabled - fail loudly, no silent fallback
                LOGGER.info("[LLM_EXTRACTION] LLM extraction enabled - will fail loudly on errors (no fallback)")
                page_res = process_page_ocr_enhanced(prep_img, blocks_raw, i, preprocessing_path=preprocessing_path)
            else:
                # LLM extraction disabled - allow fallback to geometric method
                try:
                    page_res = process_page_ocr_enhanced(prep_img, blocks_raw, i, preprocessing_path=preprocessing_path)
                except Exception as e:
                    LOGGER.warning("Enhanced OCR failed, using fallback: %s", e)
                    page_res = assemble_page_result(i, prep_img, blocks_raw)
            
            # Process handwriting blocks with HTR if enabled
            htr_data = _process_handwriting_blocks(prep_img, blocks_raw, i + 1)
            if htr_data:
                # Add HTR data to page result
                page_res.htr_data = htr_data
                LOGGER.info("HTR data added to page %d: %d blocks processed", i + 1, len(htr_data.get("htr_blocks", [])))
            
            # #region agent log
            try:
                page_text = getattr(page_res, 'text', None) or getattr(page_res, 'ocr_text', None) or ""
                page_text_length = len(page_text) if page_text else 0
                page_blocks_count = len(getattr(page_res, 'blocks', [])) if hasattr(page_res, 'blocks') else 0
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "E", "location": "owlin_scan_pipeline.py:1430", "message": "page result created", "data": {"page_idx": i, "page_text_length": page_text_length, "page_blocks_count": page_blocks_count, "has_text_attr": hasattr(page_res, 'text'), "has_ocr_text_attr": hasattr(page_res, 'ocr_text')}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
            except: pass
            # #endregion
            
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

    # Calculate overall confidence
    # If dual-path was used, try to load the chosen path's confidence from comparison metadata
    overall_conf = float(sum(p.confidence for p in pages) / len(pages)) if pages else 0.0
    
    # For image files with dual-path, use the chosen path's confidence if available
    if is_image and FEATURE_DUAL_OCR_PATH:
        try:
            # Look for comparison metadata file
            comparison_meta_path = orig_target.with_suffix(".comparison.json")
            if comparison_meta_path.exists():
                import json
                with open(comparison_meta_path, 'r') as f:
                    comparison_meta = json.load(f)
                    chosen_conf = comparison_meta.get("chosen_confidence")
                    if chosen_conf is not None:
                        overall_conf = float(chosen_conf)
                        LOGGER.info(f"[DUAL_PATH] Using chosen path confidence: {overall_conf:.3f} (from comparison metadata)")
        except Exception as e:
            LOGGER.warning(f"Failed to load comparison metadata for confidence: {e}")

    # Phase 3: Apply Donut fallback to low-confidence pages
    for page in pages:
        if page.confidence < CONF_FALLBACK_PAGE or overall_conf < CONF_FALLBACK_OVERALL:
            fallback_result = _apply_donut_fallback(page.confidence, overall_conf, page.preprocessed_image_path)
            if fallback_result:
                # Add fallback_text to page (new field)
                page.fallback_text = fallback_result.get("text", "")
        
        # Apply new Donut fallback processing
        donut_data = _process_donut_fallback(
            _Path(page.preprocessed_image_path), 
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

    # ENTERPRISE PIPELINE: Document-level aggregation
    all_line_items = []
    all_debug = []
    
    # Collect OCR telemetry from all pages
    from backend.ocr.ocr_telemetry import OCRTelemetryReport, OverallTelemetry, determine_engine_mix
    from backend.ocr.ocr_processor import get_ocr_processor
    
    telemetry_report = OCRTelemetryReport()
    ocr_processor = get_ocr_processor()
    all_page_telemetry = []
    all_block_telemetry = []
    all_methods = []
    total_duration = 0.0
    
    for page in pages:
        # Collect line items from page (if available)
        if hasattr(page, 'line_items') and page.line_items:
            all_line_items.extend(page.line_items)
        
        # Collect debug info from page (if available)
        if hasattr(page, 'line_items_debug') and page.line_items_debug:
            all_debug.extend(page.line_items_debug)
        
        # Collect OCR telemetry if PageOCRResult is available
        if hasattr(page, '_ocr_result') and page._ocr_result:
            page_telemetry = ocr_processor.generate_telemetry(page._ocr_result)
            block_telemetry = ocr_processor.generate_block_telemetry(page._ocr_result)
            all_page_telemetry.append(page_telemetry)
            all_block_telemetry.extend(block_telemetry)
            all_methods.append(page_telemetry.engine)
            total_duration += page_telemetry.duration_ms
        else:
            # Fallback: try to extract from page attributes
            # This handles cases where PageResult doesn't have direct access to PageOCRResult
            page_index = page.page_num - 1
            page_confidence = page.confidence
            page_words = sum(len(b.ocr_text.split()) for b in page.blocks if hasattr(b, 'ocr_text') and b.ocr_text)
            
            # Try to determine engine from blocks
            methods = []
            for block in page.blocks:
                if hasattr(block, 'method_used'):
                    methods.append(block.method_used)
                elif hasattr(block, 'confidence') and block.confidence > 0:
                    methods.append("paddleocr")  # Default assumption
            
            engine = determine_engine_mix(methods) if methods else "unknown"
            all_methods.append(engine)
            
            # Estimate duration (we don't have exact timing, use 0)
            from backend.ocr.ocr_telemetry import PageTelemetry, BlockTelemetry, categorize_block_type, count_words
            page_telemetry = PageTelemetry(
                page_index=page_index,
                engine=engine,
                preprocessing="unknown",  # We don't have this info in PageResult
                confidence=page_confidence,
                word_count=page_words,
                duration_ms=0.0,
                errors=[]
            )
            all_page_telemetry.append(page_telemetry)
            
            # Generate block telemetry from PageResult blocks
            for block in page.blocks:
                if hasattr(block, 'type') and hasattr(block, 'bbox') and hasattr(block, 'confidence'):
                    all_block_telemetry.append(BlockTelemetry(
                        page_index=page_index,
                        block_type=categorize_block_type(block.type),
                        bbox=list(block.bbox) if hasattr(block.bbox, '__iter__') else [0, 0, 0, 0],
                        confidence=block.confidence if hasattr(block, 'confidence') else 0.0,
                        word_count=count_words(block.ocr_text) if hasattr(block, 'ocr_text') else 0
                    ))
    
    # Build telemetry report
    telemetry_report.pages = all_page_telemetry
    telemetry_report.blocks = all_block_telemetry
    
    # Calculate overall telemetry
    if all_page_telemetry:
        avg_confidence = sum(p.confidence for p in all_page_telemetry) / len(all_page_telemetry)
        engine_mix = determine_engine_mix(all_methods)
    else:
        avg_confidence = overall_conf
        engine_mix = "unknown"
    
    telemetry_report.overall = OverallTelemetry(
        confidence=avg_confidence,
        engine_mix=engine_mix,
        duration_ms=total_duration if total_duration > 0 else (time.time() - t0) * 1000.0
    )
    
    # Compute document-level metrics
    doc_total_items = len(all_line_items)
    doc_items_with_pack = sum(1 for item in all_line_items if hasattr(item, 'pack_size') and item.pack_size and item.pack_size.strip())
    doc_items_with_prices = sum(
        1 for item in all_line_items 
        if (hasattr(item, 'unit_price') and item.unit_price and item.unit_price.strip()) or
           (hasattr(item, 'total_price') and item.total_price and item.total_price.strip())
    )
    
    # Calculate weighted average confidence
    if all_line_items:
        confidences = [item.confidence for item in all_line_items if hasattr(item, 'confidence') and item.confidence > 0]
        doc_avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Calculate weighted average of page scores (from debug info)
        page_scores = []
        for debug in all_debug:
            method_chosen = debug.get('method_chosen', 'none')
            if method_chosen == 'table':
                score = debug.get('table_score', 0.0)
            elif method_chosen == 'fallback':
                score = debug.get('fallback_score', 0.0)
            else:
                score = 0.0
            
            if score > 0:
                page_scores.append(score)
        
        if page_scores:
            line_items_confidence = sum(page_scores) / len(page_scores)
        else:
            line_items_confidence = doc_avg_confidence
    else:
        doc_avg_confidence = 0.0
        line_items_confidence = 0.0
    
    LOGGER.info(
        f"[ENTERPRISE_PIPELINE] Document-level aggregation: {doc_total_items} items, "
        f"avg_conf={doc_avg_confidence:.3f}, items_with_pack={doc_items_with_pack}, "
        f"items_with_prices={doc_items_with_prices}, line_items_confidence={line_items_confidence:.3f}"
    )
    
    # PARITY COMPUTATION: Extract totals and compute mismatch metrics
    invoice_subtotal = None
    invoice_vat_total = None
    invoice_grand_total = None
    sum_line_total = 0.0
    total_mismatch_abs = None
    total_mismatch_pct = None
    parity_rating = "unknown"
    parity_detail = "unknown"
    price_coverage = 0.0
    value_coverage = None
    
    try:
        # Helper function to check if total_price is valid
        def _is_valid_total_price(total_price):
            """Check if total_price is valid (numeric, > 0, within sanity bounds)."""
            if total_price is None or total_price == "" or total_price == "0" or total_price == 0:
                return False
            try:
                price_val = _float_safe(total_price)
                # Valid if > 0 and within sanity bounds (0 < value <= 100000)
                return 0 < price_val <= 100000
            except (ValueError, TypeError):
                return False
        
        # Compute sum_line_total from extracted line items
        for item in all_line_items:
            total_price = None
            if hasattr(item, 'total_price'):
                total_price = item.total_price
            elif isinstance(item, dict):
                total_price = item.get('total_price')
            
            if total_price and total_price not in (None, "", "0", 0):
                price_val = _float_safe(total_price)
                if price_val > 0:
                    sum_line_total += price_val
        
        # Compute price_coverage: count of items with valid total_price / total items
        valid_price_count = 0
        for item in all_line_items:
            total_price = None
            if hasattr(item, 'total_price'):
                total_price = item.total_price
            elif isinstance(item, dict):
                total_price = item.get('total_price')
            if _is_valid_total_price(total_price):
                valid_price_count += 1
        price_coverage = valid_price_count / max(len(all_line_items), 1) if all_line_items else 0.0
        
        # FIX: Add value_coverage metric - how much of invoice total is explained by line items
        # value_coverage = sum(total_price for valid rows) / invoice_grand_total
        value_coverage = None
        if invoice_grand_total is not None and invoice_grand_total > 0:
            if sum_line_total > 0:
                value_coverage = sum_line_total / invoice_grand_total
            else:
                # If invoice total exists but no line items have prices, return 0.0
                value_coverage = 0.0
        # If invoice_grand_total is None or 0, value_coverage remains None
        
        # Extract full OCR text from all pages
        all_page_text_parts = []
        for page in pages:
            for block in page.blocks:
                if hasattr(block, 'ocr_text') and block.ocr_text:
                    all_page_text_parts.append(block.ocr_text)
        
        all_page_text = "\n".join(all_page_text_parts)
        
        # Extract document totals using TableExtractor
        if all_page_text.strip():
            from backend.ocr.table_extractor import get_table_extractor
            extractor = get_table_extractor()
            totals = extractor.extract_document_totals_from_text(all_page_text)
            invoice_subtotal = totals.get("invoice_subtotal")
            invoice_vat_total = totals.get("invoice_vat_total")
            invoice_grand_total = totals.get("invoice_grand_total")
        
        # Compute parity metrics if we have both grand total and line items sum
        if invoice_grand_total is not None and invoice_grand_total > 0 and sum_line_total > 0:
            total_mismatch_abs = abs(invoice_grand_total - sum_line_total)
            denom = max(invoice_grand_total, 1.0)
            total_mismatch_pct = total_mismatch_abs / denom
            
            # Determine parity rating
            if total_mismatch_pct < 0.01:  # < 1%
                parity_rating = "excellent"
            elif total_mismatch_pct < 0.03:  # < 3%
                parity_rating = "good"
            elif total_mismatch_pct < 0.08:  # < 8%
                parity_rating = "ok"
            else:  # >= 8%
                parity_rating = "poor"
            
            # Determine parity_detail based on rating and price_coverage
            if parity_rating in ("excellent", "good", "ok"):
                parity_detail = "ok"
            elif parity_rating == "poor":
                if price_coverage < 0.3:
                    parity_detail = "low_price_coverage"
                else:
                    parity_detail = "high_mismatch_despite_good_coverage"
            else:
                parity_detail = "unknown"
            
            LOGGER.info(
                f"[PARITY] invoice_grand_total={invoice_grand_total:.2f}, "
                f"sum_line_total={sum_line_total:.2f}, "
                f"mismatch_abs={total_mismatch_abs:.2f}, "
                f"mismatch_pct={total_mismatch_pct*100:.2f}%, "
                f"rating={parity_rating}, detail={parity_detail}"
            )
        else:
            LOGGER.info(
                f"[PARITY] Cannot compute parity: "
                f"invoice_grand_total={invoice_grand_total}, sum_line_total={sum_line_total}"
            )
    except Exception as e:
        LOGGER.warning(f"[PARITY] Parity computation failed: {e}", exc_info=True)
    
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

    # Convert line items to dict format for JSON serialization
    line_items_dict = []
    for item in all_line_items:
        if hasattr(item, 'to_dict'):
            line_items_dict.append(item.to_dict())
        elif isinstance(item, dict):
            line_items_dict.append(item)
        else:
            # Fallback: try to convert to dict manually
            line_items_dict.append({
                "description": getattr(item, 'description', ''),
                "quantity": getattr(item, 'quantity', ''),
                "unit_price": getattr(item, 'unit_price', ''),
                "total_price": getattr(item, 'total_price', ''),
                "vat": getattr(item, 'vat', ''),
                "confidence": getattr(item, 'confidence', 0.0),
                "pack_size": getattr(item, 'pack_size', None),
            })
    
    # Initialize flags list
    flags = []
    
    # Add total_mismatch_high flag if parity is poor
    if parity_rating == "poor" and invoice_grand_total is not None and sum_line_total > 0:
        flags.append("total_mismatch_high")
        LOGGER.warning(
            f"[PARITY] High mismatch detected: {total_mismatch_pct*100:.2f}% "
            f"(invoice_total={invoice_grand_total:.2f}, sum_line_items={sum_line_total:.2f})"
        )
    
    # Add price_coverage_low flag if coverage is low
    if price_coverage < 0.3:
        flags.append("price_coverage_low")
    
    # Build pages dict, aggregating text from blocks for page-level text field
    pages_dict = []
    for p in pages:
        # Aggregate text from all blocks for page-level text field
        page_text_parts = []
        for b in p.blocks:
            if b.ocr_text and b.ocr_text.strip():
                page_text_parts.append(b.ocr_text)
        page_text = "\n".join(page_text_parts)
        
        page_dict = {
            "page_num": p.page_num,
            "confidence": p.confidence,
            "preprocessed_image_path": p.preprocessed_image_path,
            "text": page_text,  # Add page-level text field
            "ocr_text": page_text,  # Alias for compatibility
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
        }
        pages_dict.append(page_dict)
    
    out = {
        "status": "ok" if pages else "partial",
        "pages": pages_dict,
        "overall_confidence": overall_conf,
        "artifact_dir": str(base),
        "elapsed_sec": round(time.time() - t0, 3),
        # ENTERPRISE PIPELINE: Add line items and debug info
        "line_items": line_items_dict,
        "line_items_debug": all_debug,
        "line_items_confidence": line_items_confidence,
        # PARITY: Add totals and parity metrics
        "invoice_subtotal": invoice_subtotal,
        "invoice_vat_total": invoice_vat_total,
        "invoice_grand_total": invoice_grand_total,
        "sum_line_total": sum_line_total,
        "total_mismatch_abs": total_mismatch_abs,
        "total_mismatch_pct": total_mismatch_pct,
        "parity_rating": parity_rating,
        "parity_detail": parity_detail,
        "price_coverage": price_coverage,
        "value_coverage": value_coverage,
        "flags": flags,
        # Phase 3: Add template match if available
        **({"template_match": template_match} if template_match else {}),
        # Phase 3: Add normalized JSON if available
        **({"normalized_json": normalized_json} if normalized_json else {}),
        # OCR Telemetry: Add telemetry report
        "ocr_telemetry": telemetry_report.to_dict(),
        # PDF structure analysis metadata
        **({"pdf_structure": pdf_structure} if pdf_structure else {}),
        # Render metadata
        **({"render_metadata": render_metadata_list} if render_metadata_list else {}),
    }

    # Persist OCR JSON
    try:
        (base).mkdir(parents=True, exist_ok=True)
        with open(base / "ocr_output.json", "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    except Exception as e:
        LOGGER.warning("Failed to save OCR JSON: %s", e)

    return out



