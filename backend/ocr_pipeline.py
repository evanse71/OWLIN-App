import cv2
import numpy as np
import pytesseract
from pytesseract import Output
import re
from typing import List, Dict, Any
# Optional pdf2image import for PDF processing
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    convert_from_path = None  # type: ignore
from PIL import Image


def preprocess_image(img: np.ndarray) -> np.ndarray:
    """Preprocess image for OCR."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

    # Deskew using image moments
    coords = np.column_stack(np.where(gray > 0))
    if len(coords) > 0:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        (h, w) = gray.shape[:2]
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        gray = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    # Noise reduction
    denoised = cv2.medianBlur(gray, 3)

    # Adaptive thresholding
    thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    # Sharpen image
    blurred = cv2.GaussianBlur(thresh, (0, 0), 1)
    sharp = cv2.addWeighted(thresh, 1.5, blurred, -0.5, 0)

    return sharp


def run_ocr(img: np.ndarray, lang: str = "eng") -> Dict[str, List[Any]]:
    """Run Tesseract OCR with tuned configuration."""
    config = "--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz£$€.:/-,"
    data = pytesseract.image_to_data(img, output_type=Output.DICT, lang=lang, config=config)
    return data


def extract_line_items(data: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    """Simple line item extraction from OCR data."""
    lines: Dict[int, List[str]] = {}
    for i, text in enumerate(data.get("text", [])):
        if not text.strip():
            continue
        try:
            conf = int(data.get("conf", ["0"])[i])
        except (ValueError, IndexError):
            conf = 0
        if conf < 40:
            continue
        line_num = data.get("line_num", [0])[i]
        lines.setdefault(line_num, []).append(text)

    items: List[Dict[str, Any]] = []
    item_pattern = re.compile(r"(.+?)\s+(\d+)\s+([£$€]?[\d,.]+)")
    for words in lines.values():
        line = " ".join(words)
        m = item_pattern.search(line)
        if m:
            desc, qty, price = m.groups()
            items.append({"description": desc.strip(), "qty": int(qty), "price": price})
    return items


def parse_invoice_image(img: np.ndarray, lang: str = "eng") -> Dict[str, Any]:
    """Process an invoice image and return structured OCR output."""
    processed = preprocess_image(img)
    data = run_ocr(processed, lang=lang)

    text = "\n".join(
        [t for t, c in zip(data.get("text", []), data.get("conf", [])) if t.strip() and int(c) > 0]
    )
    confidences = [int(c) for c in data.get("conf", []) if c.isdigit()]
    avg_conf = float(np.mean(confidences)) if confidences else 0.0

    line_items = extract_line_items(data)

    total_match = re.search(r"([£$€]\s?[\d,.]+)\b", text)
    total = total_match.group(1) if total_match else ""

    result = {
        "text": text,
        "line_items": line_items,
        "total": total,
        "confidence": round(avg_conf / 100, 2),
        "flag_for_review": avg_conf < 80,
    }
    return result


def parse_document(path: str, lang: str = "eng") -> Dict[str, Any]:
    """Parse a PDF or image document and return OCR results."""
    suffix = path.lower().split(".")[-1]
    if suffix == "pdf":
        if not PDF2IMAGE_AVAILABLE or convert_from_path is None:
            raise ImportError("pdf2image is not installed. PDF processing requires pdf2image. Install with: pip install pdf2image")
        images = convert_from_path(path)
        results = [parse_invoice_image(np.array(img.convert("RGB"))) for img in images]
        if not results:
            return {}
        # Combine results
        combined_text = "\n".join(r["text"] for r in results)
        avg_conf = np.mean([r["confidence"] for r in results])
        items: List[Dict[str, Any]] = []
        for r in results:
            items.extend(r["line_items"])
        total = next((r["total"] for r in results if r["total"]), "")
        return {
            "text": combined_text,
            "line_items": items,
            "total": total,
            "confidence": avg_conf,
            "flag_for_review": avg_conf < 0.8,
        }
    else:
        img = np.array(Image.open(path).convert("RGB"))
        return parse_invoice_image(img, lang=lang) 