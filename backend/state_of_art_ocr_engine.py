"""
State-of-the-art OCR processing engine with:
- Multi-engine coordination
- Intelligent confidence scoring
- Advanced preprocessing
- Real-time quality assessment
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    import cv2
    import easyocr
    from fuzzywuzzy import fuzz
    OCR_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Some OCR dependencies not available: {e}")
    OCR_AVAILABLE = False

@dataclass
class EngineResult:
    """Result from a single OCR engine"""
    text: str
    confidence: float
    engine_name: str
    processing_time: float
    quality_score: float
    raw_data: Dict[str, Any]

@dataclass
class DocumentResult:
    """Final document processing result"""
    text: str
    confidence: float
    quality_score: float
    engine_contributions: Dict[str, EngineResult]
    processing_time: float
    preprocessing_strategy: str
    error_messages: List[str]

class QualityAssessor:
    """Assesses quality of OCR results"""
    
    def assess(self, fused_results: Dict[str, Any]) -> float:
        """Assess overall quality of OCR results"""
        try:
            quality_factors = []
            
            # Text length factor
            text_length = len(fused_results.get('text', ''))
            if text_length > 100:
                quality_factors.append(0.9)
            elif text_length > 50:
                quality_factors.append(0.7)
            elif text_length > 10:
                quality_factors.append(0.5)
            else:
                quality_factors.append(0.2)
            
            # Confidence factor
            avg_confidence = fused_results.get('avg_confidence', 0.0)
            quality_factors.append(avg_confidence)
            
            # Engine agreement factor
            engine_agreement = fused_results.get('engine_agreement', 0.0)
            quality_factors.append(engine_agreement)
            
            # Business logic factor
            business_score = self._assess_business_logic(fused_results.get('text', ''))
            quality_factors.append(business_score)
            
            return sum(quality_factors) / len(quality_factors)
            
        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")
            return 0.5
    
    def _assess_business_logic(self, text: str) -> float:
        """Assess if text contains business-relevant information"""
        try:
            business_keywords = [
                'invoice', 'total', 'amount', 'date', 'supplier', 'company',
                'limited', 'ltd', 'price', 'quantity', 'item', 'description'
            ]
            
            text_lower = text.lower()
            keyword_matches = sum(1 for keyword in business_keywords if keyword in text_lower)
            
            if keyword_matches >= 5:
                return 0.9
            elif keyword_matches >= 3:
                return 0.7
            elif keyword_matches >= 1:
                return 0.5
            else:
                return 0.2
                
        except Exception as e:
            logger.error(f"Business logic assessment failed: {e}")
            return 0.3

class ConfidenceCalculator:
    """Calculates unified confidence scores"""
    
    def calculate(self, fused_results: Dict[str, Any], quality_score: float) -> float:
        """Calculate unified confidence score"""
        try:
            # Base confidence from engine results
            base_confidence = fused_results.get('avg_confidence', 0.0)
            
            # Quality adjustment
            quality_adjustment = quality_score * 0.3
            
            # Engine agreement bonus
            agreement_bonus = fused_results.get('engine_agreement', 0.0) * 0.2
            
            # Business logic bonus
            business_bonus = self._calculate_business_bonus(fused_results.get('text', ''))
            
            # Calculate final confidence
            final_confidence = (
                base_confidence * 0.5 +
                quality_adjustment +
                agreement_bonus +
                business_bonus
            )
            
            # Ensure proper scale (0-1)
            return min(max(final_confidence, 0.0), 1.0)
            
        except Exception as e:
            logger.error(f"Confidence calculation failed: {e}")
            return 0.5
    
    def _calculate_business_bonus(self, text: str) -> float:
        """Calculate bonus for business-relevant content"""
        try:
            business_patterns = [
                r'\b\d+\.?\d*\s*[£$€]',  # Currency amounts
                r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # Dates
                r'\b[A-Z][A-Za-z\s&]+(?:LIMITED|LTD|CO|COMPANY)\b',  # Company names
                r'\b(?:INVOICE|TOTAL|AMOUNT|SUPPLIER)\b',  # Business keywords
            ]
            
            import re
            matches = 0
            for pattern in business_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    matches += 1
            
            return min(matches * 0.1, 0.3)  # Max 0.3 bonus
            
        except Exception as e:
            logger.error(f"Business bonus calculation failed: {e}")
            return 0.0

class AdvancedPreprocessor:
    """Advanced image preprocessing with multiple strategies"""
    
    def __init__(self):
        self.strategies = [
            'clahe_denoise',
            'histogram_equalization',
            'gaussian_otsu',
            'adaptive_threshold',
            'original_minimal'
        ]
    
    async def process(self, file_path: str) -> List[np.ndarray]:
        """Process image with multiple preprocessing strategies"""
        try:
            # Load image
            if file_path.lower().endswith('.pdf'):
                return await self._process_pdf(file_path)
            else:
                return await self._process_image(file_path)
                
        except Exception as e:
            logger.error(f"Preprocessing failed: {e}")
            return []
    
    async def _process_image(self, file_path: str) -> List[np.ndarray]:
        """Process single image with multiple strategies"""
        try:
            # Load image
            image = cv2.imread(file_path)
            if image is None:
                logger.error(f"Failed to load image: {file_path}")
                return []
            
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Apply preprocessing strategies
            results = []
            
            # Strategy 1: CLAHE + Denoising
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            enhanced1 = clahe.apply(gray)
            denoised1 = cv2.fastNlMeansDenoising(enhanced1)
            results.append(denoised1)
            
            # Strategy 2: Histogram equalization
            enhanced2 = cv2.equalizeHist(gray)
            denoised2 = cv2.fastNlMeansDenoising(enhanced2)
            results.append(denoised2)
            
            # Strategy 3: Gaussian blur + Otsu threshold
            blurred = cv2.GaussianBlur(gray, (5,5), 0)
            _, binary3 = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            results.append(binary3)
            
            # Strategy 4: Adaptive threshold
            binary4 = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            results.append(binary4)
            
            # Strategy 5: Original with minimal processing
            results.append(gray)
            
            return results
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            return []
    
    async def _process_pdf(self, file_path: str) -> List[np.ndarray]:
        """Process PDF with multiple strategies"""
        try:
            import fitz
            from pdf2image import convert_from_path
            
            # Convert PDF to images
            images = convert_from_path(file_path, dpi=300)
            
            all_results = []
            for image in images:
                # Convert PIL image to numpy array
                img_array = np.array(image)
                
                # Process with image strategies
                image_results = await self._process_image_array(img_array)
                all_results.extend(image_results)
            
            return all_results
            
        except Exception as e:
            logger.error(f"PDF preprocessing failed: {e}")
            return []
    
    async def _process_image_array(self, image: np.ndarray) -> List[np.ndarray]:
        """Process numpy array with multiple strategies"""
        try:
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            else:
                gray = image
            
            results = []
            
            # Strategy 1: CLAHE + Denoising
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            enhanced1 = clahe.apply(gray)
            denoised1 = cv2.fastNlMeansDenoising(enhanced1)
            results.append(denoised1)
            
            # Strategy 2: Histogram equalization
            enhanced2 = cv2.equalizeHist(gray)
            denoised2 = cv2.fastNlMeansDenoising(enhanced2)
            results.append(denoised2)
            
            # Strategy 3: Gaussian blur + Otsu threshold
            blurred = cv2.GaussianBlur(gray, (5,5), 0)
            _, binary3 = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            results.append(binary3)
            
            # Strategy 4: Adaptive threshold
            binary4 = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            results.append(binary4)
            
            # Strategy 5: Original with minimal processing
            results.append(gray)
            
            return results
            
        except Exception as e:
            logger.error(f"Image array preprocessing failed: {e}")
            return []

class StateOfTheArtOCREngine:
    """
    State-of-the-art OCR processing with:
    - Multi-engine coordination
    - Intelligent confidence scoring
    - Advanced preprocessing
    - Real-time quality assessment
    """
    
    def __init__(self):
        self.engines = {
            'easyocr': self._init_easyocr(),
            'tesseract': self._init_tesseract(),
        }
        self.confidence_calculator = ConfidenceCalculator()
        self.preprocessor = AdvancedPreprocessor()
        self.quality_assessor = QualityAssessor()
    
    def _init_easyocr(self):
        """Initialize EasyOCR engine"""
        try:
            if OCR_AVAILABLE:
                reader = easyocr.Reader(['en'], gpu=False)
                logger.info("✅ EasyOCR initialized")
                return reader
            else:
                logger.warning("❌ EasyOCR not available")
                return None
        except Exception as e:
            logger.error(f"EasyOCR initialization failed: {e}")
            return None
    
    def _init_tesseract(self):
        """Initialize Tesseract engine"""
        try:
            if OCR_AVAILABLE:
                # Test Tesseract availability
                pytesseract.get_tesseract_version()
                logger.info("✅ Tesseract initialized")
                return True
            else:
                logger.warning("❌ Tesseract not available")
                return None
        except Exception as e:
            logger.error(f"Tesseract initialization failed: {e}")
            return None
    
    async def process_document(self, file_path: str) -> DocumentResult:
        """Process document with state-of-the-art OCR"""
        start_time = datetime.now()
        error_messages = []
        
        try:
            logger.info(f"🔍 Starting state-of-the-art OCR processing for: {file_path}")
            
            # 1. Advanced preprocessing
            processed_images = await self.preprocessor.process(file_path)
            if not processed_images:
                error_messages.append("Preprocessing failed")
                return self._create_error_result(error_messages, start_time)
            
            logger.info(f"✅ Preprocessing completed: {len(processed_images)} strategies")
            
            # 2. Multi-engine OCR with coordination
            engine_results = {}
            for name, engine in self.engines.items():
                if engine:
                    try:
                        result = await self._run_engine(name, engine, processed_images)
                        if result:
                            engine_results[name] = result
                    except Exception as e:
                        error_msg = f"{name} engine failed: {e}"
                        logger.error(error_msg)
                        error_messages.append(error_msg)
            
            if not engine_results:
                error_messages.append("All OCR engines failed")
                return self._create_error_result(error_messages, start_time)
            
            # 3. Intelligent result fusion
            fused_results = self._fuse_engine_results(engine_results)
            
            # 4. Quality assessment
            quality_score = self.quality_assessor.assess(fused_results)
            
            # 5. Confidence calculation
            confidence = self.confidence_calculator.calculate(fused_results, quality_score)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return DocumentResult(
                text=fused_results['text'],
                confidence=confidence,
                quality_score=quality_score,
                engine_contributions=engine_results,
                processing_time=processing_time,
                preprocessing_strategy=f"multi-strategy-{len(processed_images)}",
                error_messages=error_messages
            )
            
        except Exception as e:
            error_msg = f"OCR processing failed: {e}"
            logger.error(error_msg)
            error_messages.append(error_msg)
            return self._create_error_result(error_messages, start_time)
    
    async def _run_engine(self, name: str, engine, images: List[np.ndarray]) -> EngineResult:
        """Run a single OCR engine"""
        start_time = datetime.now()
        
        try:
            if name == 'easyocr':
                return await self._run_easyocr(engine, images, start_time)
            elif name == 'tesseract':
                return await self._run_tesseract(engine, images, start_time)
            else:
                logger.warning(f"Unknown engine: {name}")
                return None
                
        except Exception as e:
            logger.error(f"{name} engine failed: {e}")
            return None
    
    async def _run_easyocr(self, reader, images: List[np.ndarray], start_time: datetime) -> EngineResult:
        """Run EasyOCR engine"""
        try:
            all_text = ""
            all_confidences = []
            
            for i, image in enumerate(images):
                results = reader.readtext(image)
                
                for (bbox, text, confidence) in results:
                    if text.strip() and confidence > 0.1:  # Filter low confidence
                        all_text += text.strip() + " "
                        all_confidences.append(confidence)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
            
            return EngineResult(
                text=all_text.strip(),
                confidence=avg_confidence,
                engine_name='easyocr',
                processing_time=processing_time,
                quality_score=avg_confidence,
                raw_data={'results': len(all_confidences)}
            )
            
        except Exception as e:
            logger.error(f"EasyOCR processing failed: {e}")
            return None
    
    async def _run_tesseract(self, engine, images: List[np.ndarray], start_time: datetime) -> EngineResult:
        """Run Tesseract engine"""
        try:
            all_text = ""
            all_confidences = []
            
            for i, image in enumerate(images):
                # Get detailed OCR data from Tesseract
                data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                
                for j in range(len(data['text'])):
                    text = data['text'][j].strip()
                    if text:
                        confidence = float(data['conf'][j]) / 100.0
                        if confidence > 0.1:  # Filter low confidence
                            all_text += text + " "
                            all_confidences.append(confidence)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
            
            return EngineResult(
                text=all_text.strip(),
                confidence=avg_confidence,
                engine_name='tesseract',
                processing_time=processing_time,
                quality_score=avg_confidence,
                raw_data={'results': len(all_confidences)}
            )
            
        except Exception as e:
            logger.error(f"Tesseract processing failed: {e}")
            return None
    
    def _fuse_engine_results(self, engine_results: Dict[str, EngineResult]) -> Dict[str, Any]:
        """Intelligently fuse results from multiple engines"""
        try:
            # Collect all texts and confidences
            texts = []
            confidences = []
            
            for name, result in engine_results.items():
                if result.text:
                    texts.append(result.text)
                    confidences.append(result.confidence)
            
            # Calculate average confidence
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Calculate engine agreement
            engine_agreement = self._calculate_engine_agreement(texts)
            
            # Fuse texts (simple concatenation for now)
            fused_text = " ".join(texts)
            
            return {
                'text': fused_text,
                'avg_confidence': avg_confidence,
                'engine_agreement': engine_agreement,
                'num_engines': len(engine_results)
            }
            
        except Exception as e:
            logger.error(f"Engine result fusion failed: {e}")
            return {
                'text': '',
                'avg_confidence': 0.0,
                'engine_agreement': 0.0,
                'num_engines': 0
            }
    
    def _calculate_engine_agreement(self, texts: List[str]) -> float:
        """Calculate agreement between different engines"""
        try:
            if len(texts) < 2:
                return 0.0
            
            # Simple text similarity using fuzzy matching
            agreements = []
            for i in range(len(texts)):
                for j in range(i + 1, len(texts)):
                    similarity = fuzz.ratio(texts[i], texts[j]) / 100.0
                    agreements.append(similarity)
            
            return sum(agreements) / len(agreements) if agreements else 0.0
            
        except Exception as e:
            logger.error(f"Engine agreement calculation failed: {e}")
            return 0.0
    
    def _create_error_result(self, error_messages: List[str], start_time: datetime) -> DocumentResult:
        """Create error result"""
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return DocumentResult(
            text="",
            confidence=0.0,
            quality_score=0.0,
            engine_contributions={},
            processing_time=processing_time,
            preprocessing_strategy="error",
            error_messages=error_messages
        )

# Global instance
state_of_art_ocr_engine = StateOfTheArtOCREngine() 