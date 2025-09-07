# Enhanced OCR pipeline with PDF support and better error handling
import pytesseract
import cv2, numpy as np
from typing import Dict, Any, List
import os
import fitz  # PyMuPDF for PDF processing

def read_image(path: str) -> np.ndarray:
    """Read image file and return numpy array"""
    try:
        data = np.fromfile(path, dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode image")
        return img
    except Exception as e:
        raise ValueError(f"Failed to read image: {str(e)}")

def read_pdf(path: str) -> List[np.ndarray]:
    """Read PDF file and return list of page images"""
    try:
        doc = fitz.open(path)
        images = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
            img_data = pix.tobytes("png")
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is not None:
                images.append(img)
        doc.close()
        return images
    except Exception as e:
        raise ValueError(f"Failed to read PDF: {str(e)}")

def process_image_for_ocr(img: np.ndarray) -> Dict[str, Any]:
    """Process a single image for OCR"""
    try:
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_OTSU | cv2.THRESH_BINARY)[1]
        
        # Run OCR
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT, lang="eng")
        
        # Calculate confidence
        confs = [int(c) for c in data.get("conf", []) if c != '-1']
        avg_conf = int(sum(confs)/len(confs)) if confs else 0
        
        # Extract text blocks (simplified for now)
        items = []
        if "text" in data and len(data["text"]) > 0:
            # Create a simple item from detected text
            text_blocks = [text.strip() for text in data["text"] if text.strip()]
            if text_blocks:
                items.append({
                    "description": " ".join(text_blocks[:3]),  # First 3 text blocks
                    "qty": 1,
                    "unit_price": 0,
                    "total": 0,
                    "confidence": avg_conf
                })
        
        return {"confidence": avg_conf, "items": items}
    except Exception as e:
        print(f"OCR processing error: {str(e)}")
        return {"confidence": 0, "items": []}

def run_ocr(path: str) -> Dict[str, Any]:
    """Main OCR function that handles both images and PDFs"""
    try:
        file_ext = os.path.splitext(path)[1].lower()
        
        if file_ext == '.pdf':
            # Handle PDF
            try:
                images = read_pdf(path)
                if not images:
                    print(f"⚠️ No images extracted from PDF: {path}")
                    return {"confidence": 0, "items": []}
                
                # Process first page for now
                result = process_image_for_ocr(images[0])
                return result
            except Exception as e:
                print(f"PDF processing error: {str(e)}")
                return {"confidence": 0, "items": []}
            
        elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            # Handle image
            try:
                img = read_image(path)
                return process_image_for_ocr(img)
            except Exception as e:
                print(f"Image processing error: {str(e)}")
                return {"confidence": 0, "items": []}
            
        else:
            print(f"⚠️ Unsupported file type: {file_ext}")
            # Return safe default for unsupported files
            return {"confidence": 0, "items": []}
            
    except Exception as e:
        print(f"OCR error for {path}: {str(e)}")
        # Return safe default
        return {"confidence": 0, "items": []} 