"""
EasyOCR integration for Owlin OCR
Provides a simple interface to EasyOCR for invoice OCR tasks.

Usage:
    from app.easyocr_integration import EasyOcrRecognizer
    recognizer = EasyOcrRecognizer()
    text, confidence = recognizer.recognize(image)
"""
import easyocr
import numpy as np
import logging
from typing import Tuple, Union, Any

logger = logging.getLogger(__name__)

class EasyOcrRecognizer:
    def __init__(self, lang_list=None, gpu=False):
        """
        Initialize EasyOCR Reader.
        :param lang_list: List of language codes (default: ["en"])
        :param gpu: Use GPU if available (default: False)
        """
        self.lang_list = lang_list or ["en"]
        try:
            self.reader = easyocr.Reader(self.lang_list, gpu=gpu, verbose=False)
            logger.info("EasyOCR Reader initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR Reader: {e}")
            self.reader = None

    def recognize(self, image: np.ndarray) -> Tuple[str, float]:
        """
        Recognize text from a NumPy image (BGR or grayscale).
        :param image: np.ndarray (BGR or grayscale)
        :return: Tuple of (recognized_text, confidence_score)
        """
        if self.reader is None:
            logger.error("EasyOCR Reader is not initialized.")
            return "", 0.0
            
        try:
            # EasyOCR expects RGB
            if len(image.shape) == 2:
                img_rgb = np.stack([image]*3, axis=-1)
            elif image.shape[2] == 3:
                img_rgb = image[..., ::-1]  # BGR to RGB
            else:
                img_rgb = image
                
            # Run OCR with confidence data
            result = self.reader.readtext(img_rgb, detail=1, paragraph=True)
            
            # Extract text and confidence scores
            text_parts = []
            confidences = []
            
            for detection in result:
                bbox, text, confidence = detection
                # Ensure text is string and confidence is numeric
                if isinstance(text, str) and text.strip() and isinstance(confidence, (int, float)) and confidence > 0:
                    text_parts.append(text)
                    confidences.append(float(confidence))
            
            recognized_text = ' '.join(text_parts).strip()
            avg_confidence = float(np.mean(confidences)) if confidences else 0.0
            
            logger.info(f"EasyOCR completed: {len(recognized_text)} chars, {avg_confidence:.2f} confidence")
            return recognized_text, avg_confidence
            
        except Exception as e:
            logger.error(f"EasyOCR recognition failed: {e}")
            return "", 0.0

# Usage example / test function
def test_easyocr():
    import cv2
    recognizer = EasyOcrRecognizer()
    img = cv2.imread("../tests/mock_invoice.png")
    if img is None:
        print("Test image not found.")
        return
    text, confidence = recognizer.recognize(img)
    print(f"Recognized text:\n{text}")
    print(f"Confidence: {confidence:.2f}")

if __name__ == "__main__":
    test_easyocr() 