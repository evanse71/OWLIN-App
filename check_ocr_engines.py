#!/usr/bin/env python3
"""Check which OCR engines are available"""
import sys
import io

# Set UTF-8 output for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

engines = {
    "PaddleOCR": False,
    "Tesseract": False,
    "docTR": False,
    "Calamari": False,
    "PyMuPDF (PDF)": False,
    "OpenCV": False,
    "Pillow-HEIF": False
}

# Check PaddleOCR
try:
    from paddleocr import PaddleOCR
    engines["PaddleOCR"] = True
    print("[OK] PaddleOCR: Available")
except ImportError:
    print("[NO] PaddleOCR: Not installed (pip install paddleocr)")

# Check Tesseract
try:
    import pytesseract
    engines["Tesseract"] = True
    print("[OK] Tesseract: Available")
except ImportError:
    print("[NO] Tesseract: Not installed (pip install pytesseract)")

# Check PyMuPDF
try:
    import fitz
    engines["PyMuPDF (PDF)"] = True
    print("[OK] PyMuPDF: Available")
except ImportError:
    print("[NO] PyMuPDF: Not installed (pip install PyMuPDF)")

# Check OpenCV
try:
    import cv2
    engines["OpenCV"] = True
    print("[OK] OpenCV: Available")
except ImportError:
    print("[NO] OpenCV: Not installed (pip install opencv-python)")

# Check docTR
try:
    from doctr.io import DocumentFile
    from doctr.models import ocr_predictor
    engines["docTR"] = True
    print("[OK] docTR: Available")
except ImportError:
    print("[NO] docTR: Not installed (pip install python-doctr)")

# Check Calamari
try:
    from calamari_ocr import predict
    engines["Calamari"] = True
    print("[OK] Calamari: Available")
except ImportError:
    print("[NO] Calamari: Not installed (pip install calamari-ocr)")

# Check Pillow-HEIF
try:
    from PIL import Image
    import pillow_heif
    engines["Pillow-HEIF"] = True
    print("[OK] Pillow-HEIF: Available")
except ImportError:
    print("[NO] Pillow-HEIF: Not installed (pip install pillow-heif)")

print("\n" + "="*50)
print("Summary:")
for engine, available in engines.items():
    status = "[OK]" if available else "[NO]"
    print(f"{status} {engine}")

if not all(engines.values()):
    print("\n[WARN] Some OCR engines are missing. Install with:")
    print("       pip install paddleocr pytesseract python-doctr calamari-ocr PyMuPDF opencv-python pillow-heif")
    sys.exit(1)
else:
    print("\n[OK] All OCR engines available!")

