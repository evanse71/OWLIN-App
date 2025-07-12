"""
OCR Factory for Owlin App
Provides a unified interface for Tesseract and EasyOCR engines.

Usage:
    from app.ocr_factory import get_ocr_recognizer
    recognizer = get_ocr_recognizer()
    text, confidence = recognizer.recognize(image)
"""
import streamlit as st
import logging
import numpy as np
from typing import Tuple, Optional, Union
from app.easyocr_integration import EasyOcrRecognizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TesseractRecognizer:
    """Tesseract OCR recognizer wrapper."""
    
    def __init__(self):
        """Initialize Tesseract recognizer."""
        try:
            import pytesseract
            from PIL import Image
            self.pytesseract = pytesseract
            self.Image = Image
            self.available = True
            logger.info("Tesseract OCR initialized successfully")
        except ImportError as e:
            logger.error(f"Tesseract not available: {e}")
            self.available = False
        except Exception as e:
            logger.error(f"Failed to initialize Tesseract: {e}")
            self.available = False

    def recognize(self, image: np.ndarray) -> Tuple[str, float]:
        """
        Recognize text from image using Tesseract.
        
        Args:
            image: NumPy array (BGR or grayscale)
            
        Returns:
            Tuple of (recognized_text, confidence_score)
        """
        if not self.available:
            return "", 0.0
            
        try:
            # Convert numpy array to PIL Image
            if len(image.shape) == 3:
                # BGR to RGB
                image_rgb = image[..., ::-1]
                pil_image = self.Image.fromarray(image_rgb)
            else:
                pil_image = self.Image.fromarray(image)
            
            # Run OCR with confidence data
            data = self.pytesseract.image_to_data(pil_image, output_type=self.pytesseract.Output.DICT)
            
            # Extract text and confidence
            text_parts = []
            confidences = []
            
            for i, conf in enumerate(data['conf']):
                if conf > 0:  # Filter out low confidence results
                    text_parts.append(data['text'][i])
                    confidences.append(conf)
            
            recognized_text = ' '.join(text_parts).strip()
            avg_confidence = np.mean(confidences) if confidences else 0.0
            
            logger.info(f"Tesseract OCR completed: {len(recognized_text)} chars, {avg_confidence:.2f} confidence")
            return recognized_text, avg_confidence
            
        except Exception as e:
            logger.error(f"Tesseract OCR failed: {e}")
            return "", 0.0

def get_ocr_recognizer(engine_type: Optional[str] = None) -> Union[TesseractRecognizer, EasyOcrRecognizer]:
    """
    Get OCR recognizer based on engine type.
    
    Args:
        engine_type: 'Tesseract' or 'EasyOCR'. If None, uses session state.
        
    Returns:
        OCR recognizer instance
    """
    if engine_type is None:
        engine_type = st.session_state.get('ocr_engine', 'Tesseract (default)')
    
    if 'Tesseract' in engine_type:
        recognizer = TesseractRecognizer()
        if recognizer.available:
            return recognizer
        else:
            logger.warning("Tesseract not available, falling back to EasyOCR")
            return EasyOcrRecognizer()
    elif 'EasyOCR' in engine_type:
        return EasyOcrRecognizer()
    else:
        logger.warning(f"Unknown OCR engine: {engine_type}, using Tesseract")
        return TesseractRecognizer()

def get_available_ocr_engines() -> list:
    """Get list of available OCR engines."""
    engines = []
    
    # Check Tesseract
    try:
        import pytesseract
        engines.append('Tesseract (default)')
    except ImportError:
        pass
    
    # Check EasyOCR
    try:
        import easyocr
        engines.append('EasyOCR')
    except ImportError:
        pass
    
    return engines

def test_ocr_engines():
    """Test all available OCR engines with a sample image."""
    import cv2
    
    # Create a simple test image
    test_image = np.ones((100, 300), dtype=np.uint8) * 255
    cv2.putText(test_image, "Test OCR", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    available_engines = get_available_ocr_engines()
    results = {}
    
    for engine in available_engines:
        try:
            recognizer = get_ocr_recognizer(engine)
            text, confidence = recognizer.recognize(test_image)
            results[engine] = {
                'text': text,
                'confidence': confidence,
                'status': 'success'
            }
        except Exception as e:
            results[engine] = {
                'text': '',
                'confidence': 0.0,
                'status': f'error: {str(e)}'
            }
    
    return results

if __name__ == "__main__":
    # Test the OCR factory
    print("Available OCR engines:", get_available_ocr_engines())
    print("Test results:", test_ocr_engines()) 