import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)

def extract_text_from_pdf(filepath: str) -> str:
    """
    Extract text from PDF using OCR with Tesseract.
    
    Args:
        filepath: Path to the PDF file
        
    Returns:
        Extracted text as string
    """
    try:
        doc = fitz.open(filepath)
        full_text = ""

        for page_num, page in enumerate(doc):
            logger.info(f"Processing page {page_num + 1} of {len(doc)}")
            
            # Convert page to high-resolution image
            pix = page.get_pixmap(dpi=300)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # Extract text using Tesseract
            text = pytesseract.image_to_string(img)
            full_text += text + "\n\n"

        doc.close()
        return full_text.strip()
        
    except Exception as e:
        logger.error(f"Error extracting text from PDF {filepath}: {str(e)}")
        raise Exception(f"OCR extraction failed: {str(e)}")

def run_ocr(filepath: str) -> tuple[str, float]:
    """
    Run OCR on a PDF file and return text and confidence score.
    
    Args:
        filepath: Path to the PDF file
        
    Returns:
        Tuple of (extracted_text, confidence_score)
    """
    try:
        # Extract text
        ocr_text = extract_text_from_pdf(filepath)
        
        # Calculate confidence based on text quality
        confidence = calculate_confidence(ocr_text)
        
        logger.info(f"OCR completed for {filepath} with confidence: {confidence}")
        
        return ocr_text, confidence
        
    except Exception as e:
        logger.error(f"OCR failed for {filepath}: {str(e)}")
        return "", 0.0

def calculate_confidence(text: str) -> float:
    """
    Calculate confidence score based on text quality.
    
    Args:
        text: Extracted OCR text
        
    Returns:
        Confidence score between 0.0 and 1.0
    """
    if not text or len(text.strip()) == 0:
        return 0.0
    
    # Basic confidence calculation based on text characteristics
    text_length = len(text.strip())
    word_count = len(text.split())
    
    # Higher confidence for longer, more structured text
    if text_length > 500 and word_count > 50:
        base_confidence = 0.8
    elif text_length > 200 and word_count > 20:
        base_confidence = 0.6
    elif text_length > 100 and word_count > 10:
        base_confidence = 0.4
    else:
        base_confidence = 0.2
    
    # Adjust based on common invoice keywords
    invoice_keywords = ['invoice', 'total', 'amount', 'date', 'supplier', 'payment']
    keyword_matches = sum(1 for keyword in invoice_keywords if keyword.lower() in text.lower())
    
    keyword_bonus = min(keyword_matches * 0.1, 0.2)  # Max 0.2 bonus
    
    final_confidence = min(base_confidence + keyword_bonus, 1.0)
    
    return round(final_confidence, 2) 