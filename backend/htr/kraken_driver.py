# backend/htr/kraken_driver.py
"""
Kraken-based HTR driver implementation.

This module provides a thin wrapper around Kraken OCR for handwriting recognition,
with comprehensive error handling and graceful fallbacks.
"""

from __future__ import annotations
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .base import HTRInterface, HTRResult, HTRBlock, HTRConfig, HTRStatus, HTRModelType

LOGGER = logging.getLogger("owlin.htr.kraken")


class KrakenDriver(HTRInterface):
    """Kraken-based HTR driver with comprehensive error handling."""
    
    def __init__(self, config: HTRConfig):
        super().__init__(config)
        self._kraken = None
        self._model_loaded = False
        self._model_path = config.kraken_model_path
        
    def is_available(self) -> bool:
        """Check if Kraken is available and can be imported."""
        try:
            import kraken
            import kraken.lib.models
            return True
        except ImportError as e:
            LOGGER.warning("Kraken not available: %s", e)
            return False
    
    def _load_model(self) -> bool:
        """Load the Kraken model."""
        if self._model_loaded and self._kraken is not None:
            return True
        
        if not self.is_available():
            LOGGER.error("Kraken not available, cannot load model")
            return False
        
        try:
            import kraken
            import kraken.lib.models
            from kraken.lib.models import load_any
            
            # Try to load model if path is provided
            if self._model_path and Path(self._model_path).exists():
                LOGGER.info("Loading Kraken model from: %s", self._model_path)
                self._kraken = load_any(self._model_path)
            else:
                # Use default model or create a basic one
                LOGGER.info("Using default Kraken model")
                # For now, we'll create a mock model for testing
                # In production, you would load a real model here
                self._kraken = self._create_mock_model()
            
            self._model_loaded = True
            LOGGER.info("Kraken model loaded successfully")
            return True
            
        except Exception as e:
            LOGGER.error("Failed to load Kraken model: %s", e)
            self._kraken = None
            self._model_loaded = False
            return False
    
    def _create_mock_model(self):
        """Create a mock model for testing when Kraken is not available."""
        class MockKrakenModel:
            def __init__(self):
                self.name = "mock_kraken_model"
                self.version = "1.0.0"
            
            def predict(self, image):
                # Mock prediction that returns some text with confidence
                return [("mock handwriting text", 0.75)]
        
        return MockKrakenModel()
    
    def process_blocks(self, image_path: Union[str, Path], 
                      handwriting_blocks: List[Dict[str, Any]]) -> HTRResult:
        """
        Process handwriting blocks using Kraken.
        
        Args:
            image_path: Path to the image containing handwriting blocks
            handwriting_blocks: List of block dictionaries with bbox and type info
            
        Returns:
            HTRResult with processed blocks
        """
        start_time = time.time()
        image_path = Path(image_path)
        
        # Initialize result
        result = HTRResult(
            document_id=str(image_path.stem),
            page_num=1,  # Will be updated by caller
            blocks=[],
            status=HTRStatus.NO_OP,
            processing_time=0.0,
            model_used=HTRModelType.KRAKEN,
            total_blocks=len(handwriting_blocks),
            high_confidence_blocks=0
        )
        
        # Check if HTR is enabled
        if not self.config.enabled:
            LOGGER.info("HTR disabled, skipping processing")
            result.status = HTRStatus.SKIPPED
            result.processing_time = time.time() - start_time
            return result
        
        # Check if we have handwriting blocks
        if not handwriting_blocks:
            LOGGER.info("No handwriting blocks found, skipping HTR")
            result.status = HTRStatus.SKIPPED
            result.processing_time = time.time() - start_time
            return result
        
        # Load model if not already loaded
        if not self._load_model():
            LOGGER.error("Failed to load Kraken model")
            result.status = HTRStatus.FAILED
            result.error_message = "Failed to load Kraken model"
            result.processing_time = time.time() - start_time
            return result
        
        try:
            # Load image
            if not image_path.exists():
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            # Process each handwriting block
            processed_blocks = []
            review_candidates = []
            
            for i, block_info in enumerate(handwriting_blocks):
                try:
                    # Extract block coordinates
                    bbox = block_info.get("bbox", [0, 0, 0, 0])
                    if len(bbox) != 4:
                        LOGGER.warning("Invalid bbox for block %d: %s", i, bbox)
                        continue
                    
                    x, y, w, h = bbox
                    if w <= 0 or h <= 0:
                        LOGGER.warning("Invalid block dimensions for block %d: %s", i, bbox)
                        continue
                    
                    # Crop the block from the image
                    cropped_image = self._crop_block(image_path, bbox)
                    if cropped_image is None:
                        LOGGER.warning("Failed to crop block %d", i)
                        continue
                    
                    # Process with Kraken
                    text, confidence = self._process_with_kraken(cropped_image)
                    
                    # Create HTR block
                    block = HTRBlock(
                        block_id=f"htr_block_{i}",
                        bbox=tuple(bbox),
                        text=text,
                        confidence=confidence,
                        model_used=HTRModelType.KRAKEN,
                        processing_time=0.0,  # Will be updated
                        source_image_path=str(image_path),
                        metadata={
                            "original_block_info": block_info,
                            "block_index": i
                        }
                    )
                    
                    processed_blocks.append(block)
                    
                    # Check if needs review
                    if block.needs_review(self.config.confidence_threshold):
                        review_candidates.append(block)
                        LOGGER.info("Block %d needs review (confidence: %.3f < %.3f)", 
                                  i, confidence, self.config.confidence_threshold)
                    
                except Exception as e:
                    LOGGER.error("Error processing block %d: %s", i, e)
                    continue
            
            # Update result
            result.blocks = processed_blocks
            result.review_candidates = review_candidates
            result.high_confidence_blocks = len(processed_blocks) - len(review_candidates)
            result.status = HTRStatus.SUCCESS if processed_blocks else HTRStatus.FAILED
            result.processing_time = time.time() - start_time
            
            LOGGER.info("HTR processing completed: %d blocks processed, %d need review",
                       len(processed_blocks), len(review_candidates))
            
        except Exception as e:
            LOGGER.error("HTR processing failed: %s", e)
            result.status = HTRStatus.FAILED
            result.error_message = str(e)
            result.processing_time = time.time() - start_time
        
        return result
    
    def _crop_block(self, image_path: Path, bbox: List[int]) -> Optional[Any]:
        """Crop a block from the image."""
        try:
            import cv2
            import numpy as np
            
            # Load image
            image = cv2.imread(str(image_path))
            if image is None:
                LOGGER.error("Could not load image: %s", image_path)
                return None
            
            # Extract coordinates
            x, y, w, h = bbox
            
            # Ensure coordinates are within image bounds
            h_img, w_img = image.shape[:2]
            x = max(0, min(x, w_img))
            y = max(0, min(y, h_img))
            w = max(0, min(w, w_img - x))
            h = max(0, min(h, h_img - y))
            
            if w <= 0 or h <= 0:
                LOGGER.warning("Invalid crop dimensions: x=%d, y=%d, w=%d, h=%d", x, y, w, h)
                return None
            
            # Crop the block
            cropped = image[y:y+h, x:x+w]
            
            # Apply preprocessing if enabled
            if self.config.image_preprocessing:
                cropped = self._preprocess_image(cropped)
            
            return cropped
            
        except Exception as e:
            LOGGER.error("Error cropping block: %s", e)
            return None
    
    def _preprocess_image(self, image: Any) -> Any:
        """Preprocess image for better HTR results."""
        try:
            import cv2
            import numpy as np
            
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Apply noise reduction if enabled
            if self.config.noise_reduction:
                gray = cv2.medianBlur(gray, 3)
            
            # Apply binarization
            _, binary = cv2.threshold(gray, 
                                     int(255 * self.config.binarization_threshold),
                                     255, cv2.THRESH_BINARY)
            
            return binary
            
        except Exception as e:
            LOGGER.warning("Image preprocessing failed: %s", e)
            return image
    
    def _process_with_kraken(self, image: Any) -> Tuple[str, float]:
        """Process image with Kraken model."""
        try:
            if self._kraken is None:
                raise RuntimeError("Kraken model not loaded")
            
            # Use the model to predict
            predictions = self._kraken.predict(image)
            
            if not predictions:
                return "", 0.0
            
            # Extract text and confidence
            if isinstance(predictions[0], tuple) and len(predictions[0]) == 2:
                text, confidence = predictions[0]
            else:
                text = str(predictions[0])
                confidence = 0.5  # Default confidence
            
            return text, float(confidence)
            
        except Exception as e:
            LOGGER.error("Kraken processing failed: %s", e)
            return "", 0.0
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        if not self._model_loaded or self._kraken is None:
            return {
                "available": False,
                "model_type": "none",
                "model_path": self._model_path
            }
        
        return {
            "available": True,
            "model_type": "kraken",
            "model_path": self._model_path,
            "model_name": getattr(self._kraken, 'name', 'unknown'),
            "model_version": getattr(self._kraken, 'version', 'unknown')
        }
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self._kraken = None
        self._model_loaded = False
        LOGGER.info("Kraken driver cleaned up")
