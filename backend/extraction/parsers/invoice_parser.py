from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
import re
import datetime
from rapidfuzz import fuzz

DATE_RX = re.compile(r"(20\d{2}?\d{2})")
NUM_RX  = re.compile(r"\d+(?:[.,]\d+)?")
CURRENCY_RX = re.compile(r"£|€|\$|GBP|EUR|USD")
TOTAL_RX = re.compile(r"(?:total|amount due|balance|net total|grand total)[\s:]*([£€$]?\s*\d+(?:[.,]\d+)?)", re.IGNORECASE)

# Supplier lexicon for better matching
SUPPLIER_LEXICON = [
    "Brakes", "Bidfood", "Booker", "Tesco", "Makro", "JJ Foodservice", "Sysco",
    "Nisbets", "Caterlink", "Aramark", "Compass", "Sodexo", "Elior", "Mitie",
    "Bidvest", "Fresh Direct", "Ocado", "Waitrose", "Sainsbury's", "Morrisons",
    "Asda", "Lidl", "Aldi", "Iceland", "Co-op", "Marks & Spencer", "M&S"
]

def _parse_date(lines: List[str]) -> Optional[str]:
    for t in lines:
        m = DATE_RX.search(t)
        if m:
            raw = m.group(0).replace('.', '-').replace('/', '-')
            parts = raw.split('-')
            if len(parts[0])==4:
                y, mth, d = parts[0], parts[1].zfill(2), parts[2].zfill(2)
            else:
                d, mth, y = parts[0].zfill(2), parts[1].zfill(2), parts[2]
                if len(y)==2: y = "20"+y
            return f"{y}-{mth}-{d}"
    return None

def _parse_supplier_lexicon(lines: List[str]) -> Optional[str]:
    """Match supplier using lexicon with fuzzy matching (score >= 88)."""
    for line in lines:
        for supplier in SUPPLIER_LEXICON:
            score = fuzz.ratio(line.lower(), supplier.lower())
            if score >= 88:
                return supplier
    return None

def _parse_total(lines: List[str]) -> Optional[float]:
    """Extract total using regex patterns for common total labels."""
    for line in lines:
        # Look for total patterns
        match = TOTAL_RX.search(line)
        if match:
            total_str = match.group(1).replace("£", "").replace("€", "").replace("$", "").replace(",", ".").strip()
            try:
                return float(total_str)
            except ValueError:
                continue
        
        # Fallback: look for currency symbol followed by number
        if CURRENCY_RX.search(line):
            nums = NUM_RX.findall(line)
            if nums:
                try:
                    return float(nums[-1].replace(",", "."))
                except ValueError:
                    continue
    return None

def parse_invoice_from_ocr(ocr_payload: Dict[str, Any]) -> Dict[str, Any]:
    raw = [l.get("text","") for l in ocr_payload.get("lines", []) if l.get("text")]
    lower = [t.lower() for t in raw]
    
    # Enhanced supplier detection with lexicon
    supplier = _parse_supplier_lexicon(raw)
    if not supplier:
        # Fallback to original method
        for t in raw[:10]:
            if sum(c.isalpha() for c in t) >= 3:
                supplier = t.strip(); break
    
    invoice_date = _parse_date(raw)
    
    # Enhanced total extraction
    total_value = _parse_total(raw)
    
    reference = None
    for t in lower[:30]:
        if "invoice" in t and ("no" in t or "number" in t or "#" in t):
            reference = raw[lower.index(t)].strip(); break

    items = []
    for t in raw:
        nums = NUM_RX.findall(t)
        nums = [n.replace(",", ".") for n in nums]
        if len(nums) >= 2:
            try:
                qty = float(nums[-2]); unit = float(nums[-1])
                items.append({
                    "description": t[:160], "quantity": qty, "unit_price": unit,
                    "uom": None, "vat_rate": 0
                })
            except: pass

    return {
        "supplier": supplier,
        "invoice_date": invoice_date,
        "reference": reference,
        "currency": "GBP",
        "total_value": total_value,
        "line_items": items[:120]
    }


def detect_annotations(image_path: str) -> List[Dict[str, Any]]:
    """Enhanced annotation detection with shape recognition and line item mapping.

    This function detects user annotations including ticks, crosses, circles, and handwritten notes.
    It uses OpenCV for color segmentation, shape analysis, and contour detection to classify
    different types of annotations. It also attempts to map annotations to nearby line items.

    Args:
        image_path: Path to the rasterised page image (PNG).

    Returns:
        List of annotation dictionaries with keys:
        kind (str), text (str or None), x, y, w, h (floats 0..1),
        confidence (float), color (str), line_item_id (int or None).
    """
    annotations: List[Dict[str, Any]] = []
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except Exception:
        return annotations
    
    # Read image in BGR
    img = cv2.imread(image_path)
    if img is None:
        return annotations
    
    h, w, _ = img.shape
    
    # Convert to HSV for better color segmentation
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Define color ranges for common pen colors with better precision
    color_ranges = {
        'green': ((35, 40, 40), (85, 255, 255)),
        'red': [
            ((0, 50, 50), (10, 255, 255)),    # red low range
            ((160, 50, 50), (179, 255, 255))  # red high range
        ],
        'blue': ((100, 50, 50), (140, 255, 255)),
        'black': ((0, 0, 0), (180, 255, 50)),  # black/dark annotations
        'purple': ((130, 50, 50), (160, 255, 255))
    }
    
    # Process each color separately for better classification
    for color_name, ranges in color_ranges.items():
        if isinstance(ranges, list):
            # Handle multiple ranges (like red)
            mask = np.zeros((h, w), dtype=np.uint8)
            for lower, upper in ranges:
                lower_np = np.array(lower, dtype=np.uint8)
                upper_np = np.array(upper, dtype=np.uint8)
                color_mask = cv2.inRange(hsv, lower_np, upper_np)
                mask = cv2.bitwise_or(mask, color_mask)
        else:
            lower, upper = ranges
            lower_np = np.array(lower, dtype=np.uint8)
            upper_np = np.array(upper, dtype=np.uint8)
            mask = cv2.inRange(hsv, lower_np, upper_np)
        
        # Enhanced morphological operations
        kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
        kernel_medium = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        
        # Remove noise
        mask_clean = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_small, iterations=1)
        # Fill gaps
        mask_clean = cv2.morphologyEx(mask_clean, cv2.MORPH_CLOSE, kernel_medium, iterations=1)
        
        # Find contours
        contours, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours:
            # Filter by area
            area = cv2.contourArea(cnt)
            if area < 50:  # Too small
                continue
            if area > (w * h * 0.1):  # Too large (likely background)
                continue
            
            # Get bounding rectangle
            x, y, w_box, h_box = cv2.boundingRect(cnt)
            
            # Calculate features for classification
            aspect_ratio = w_box / float(h_box) if h_box > 0 else 0
            extent = area / (w_box * h_box) if w_box * h_box > 0 else 0
            
            # Classify annotation type
            annotation_type, confidence = _classify_annotation_shape(
                cnt, aspect_ratio, extent, area
            )
            
            if confidence < 0.3:  # Skip low confidence detections
                continue
            
            # Normalized coordinates
            x_norm = x / float(w)
            y_norm = y / float(h)
            w_norm = w_box / float(w)
            h_norm = h_box / float(h)
            
            # Try to extract text if it's a note/highlight
            extracted_text = None
            if annotation_type in ['NOTE', 'HIGHLIGHT']:
                extracted_text = _extract_text_from_region(img, x, y, w_box, h_box)
            
            # Map to line item if possible
            line_item_id = _map_annotation_to_line_item(x_norm, y_norm, w_norm, h_norm)
            
            annotations.append({
                'line_item_id': line_item_id,
                'kind': annotation_type,
                'text': extracted_text,
                'x': x_norm,
                'y': y_norm,
                'w': w_norm,
                'h': h_norm,
                'confidence': confidence,
                'color': color_name,
                'area': area,
                'aspect_ratio': aspect_ratio
            })
    
    return annotations


def _classify_annotation_shape(contour, aspect_ratio: float, extent: float, area: float) -> Tuple[str, float]:
    """Classify annotation shape based on contour analysis"""
    try:
        import cv2
        import numpy as np
    except Exception:
        return 'MARK', 0.5
    
    # Calculate additional shape features
    perimeter = cv2.arcLength(contour, True)
    circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
    
    # Approximate contour to detect line-like structures
    epsilon = 0.02 * perimeter
    approx = cv2.approxPolyDP(contour, epsilon, True)
    
    # Classification logic
    if circularity > 0.7 and 0.8 < aspect_ratio < 1.2:
        # Circular or square
        if len(approx) >= 8:
            return 'CIRCLE', 0.8
        else:
            return 'MARK', 0.6
    elif aspect_ratio > 3.0 or aspect_ratio < 0.3:
        # Line-like
        if len(approx) <= 4:
            return 'CROSS', 0.7
        else:
            return 'MARK', 0.5
    elif 0.5 < aspect_ratio < 2.0 and extent > 0.6:
        # Compact, filled shape
        if len(approx) <= 6:
            return 'TICK', 0.8
        else:
            return 'MARK', 0.6
    elif area > 1000 and extent < 0.3:
        # Large, sparse shape (likely highlight)
        return 'HIGHLIGHT', 0.7
    else:
        # Default classification
        return 'MARK', 0.5


def _extract_text_from_region(img, x: int, y: int, w: int, h: int) -> Optional[str]:
    """Extract text from a specific image region using OCR"""
    try:
        import pytesseract
        from PIL import Image
        import numpy as np
    except Exception:
        return None
    
    # Extract region
    region = img[y:y+h, x:x+w]
    
    # Convert to PIL Image
    region_pil = Image.fromarray(cv2.cvtColor(region, cv2.COLOR_BGR2RGB))
    
    # Extract text
    try:
        text = pytesseract.image_to_string(region_pil, config='--psm 8')
        return text.strip() if text.strip() else None
    except Exception:
        return None


def _map_annotation_to_line_item(x: float, y: float, w: float, h: float) -> Optional[int]:
    """Map annotation to nearby line item based on position"""
    # This is a simplified implementation
    # In a real system, you would query the database for line items
    # and find the closest one based on position
    
    # For now, return None - this would be implemented with actual line item data
    return None


def save_annotations_to_database(db, invoice_id: str, annotations: List[Dict[str, Any]]) -> List[str]:
    """Save detected annotations to the database"""
    import uuid
    
    annotation_ids = []
    cursor = db.cursor()
    
    for ann in annotations:
        annotation_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT INTO annotations (
                id, invoice_id, line_item_id, kind, text, x, y, w, h,
                confidence, color, page_number, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            annotation_id,
            invoice_id,
            ann.get('line_item_id'),
            ann.get('kind'),
            ann.get('text'),
            ann.get('x'),
            ann.get('y'),
            ann.get('w'),
            ann.get('h'),
            ann.get('confidence'),
            ann.get('color'),
            1,  # page number - would be determined from processing context
            datetime.datetime.now(datetime.timezone.utc).isoformat()
        ))
        
        annotation_ids.append(annotation_id)
    
    db.commit()
    return annotation_ids
