# backend/htr/integration.py
"""
HTR integration module for the main OCR pipeline.

This module provides the main HTRProcessor class that integrates handwriting
recognition into the existing OCR pipeline, handling block selection, processing,
and review queue routing.
"""

from __future__ import annotations
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .base import HTRConfig, HTRResult, HTRStatus, HTRModelType
from .kraken_driver import KrakenDriver
from .dataset import HTRSampleStorage

LOGGER = logging.getLogger("owlin.htr.integration")


class HTRProcessor:
    """Main HTR processor that integrates with the OCR pipeline."""
    
    def __init__(self, config: Optional[HTRConfig] = None):
        """Initialize HTR processor with configuration."""
        self.config = config or HTRConfig()
        self.driver = None
        self.sample_storage = None
        self._initialized = False
        
        # Initialize components
        self._initialize_driver()
        self._initialize_sample_storage()
    
    def _initialize_driver(self) -> None:
        """Initialize the HTR driver based on configuration."""
        try:
            if self.config.model_type == HTRModelType.KRAKEN:
                self.driver = KrakenDriver(self.config)
            else:
                LOGGER.warning("Unsupported model type: %s", self.config.model_type)
                self.driver = None
        except Exception as e:
            LOGGER.error("Failed to initialize HTR driver: %s", e)
            self.driver = None
    
    def _initialize_sample_storage(self) -> None:
        """Initialize sample storage for training data."""
        try:
            if self.config.save_samples:
                self.sample_storage = HTRSampleStorage()
            else:
                self.sample_storage = None
        except Exception as e:
            LOGGER.warning("Failed to initialize sample storage: %s", e)
            self.sample_storage = None
    
    def is_available(self) -> bool:
        """Check if HTR processing is available."""
        if not self.config.enabled:
            return False
        
        if self.driver is None:
            return False
        
        return self.driver.is_available()
    
    def process_handwriting_blocks(self, image_path: Union[str, Path], 
                                 layout_blocks: List[Dict[str, Any]], 
                                 page_num: int = 1) -> HTRResult:
        """
        Process handwriting blocks from layout detection results.
        
        Args:
            image_path: Path to the preprocessed image
            layout_blocks: List of layout blocks from layout detection
            page_num: Page number for result tracking
            
        Returns:
            HTRResult with processed handwriting blocks
        """
        start_time = time.time()
        
        # Create base result
        result = HTRResult(
            document_id=str(Path(image_path).stem),
            page_num=page_num,
            blocks=[],
            status=HTRStatus.NO_OP,
            processing_time=0.0,
            model_used=HTRModelType.KRAKEN,
            total_blocks=0,
            high_confidence_blocks=0
        )
        
        # Check if HTR is available
        if not self.is_available():
            LOGGER.info("HTR not available, skipping processing")
            result.status = HTRStatus.SKIPPED
            result.processing_time = time.time() - start_time
            return result
        
        # Filter for handwriting blocks
        handwriting_blocks = self._filter_handwriting_blocks(layout_blocks)
        
        if not handwriting_blocks:
            LOGGER.info("No handwriting blocks found in page %d", page_num)
            result.status = HTRStatus.SKIPPED
            result.processing_time = time.time() - start_time
            return result
        
        LOGGER.info("Found %d handwriting blocks in page %d", len(handwriting_blocks), page_num)
        
        try:
            # Process with HTR driver
            htr_result = self.driver.process_blocks(image_path, handwriting_blocks)
            
            # Update result with HTR processing results
            result.blocks = htr_result.blocks
            result.review_candidates = htr_result.review_candidates
            result.high_confidence_blocks = htr_result.high_confidence_blocks
            result.total_blocks = len(handwriting_blocks)
            result.status = htr_result.status
            result.error_message = htr_result.error_message
            result.processing_time = time.time() - start_time
            
            # Save samples if enabled
            if self.sample_storage and result.blocks:
                self._save_samples(result)
            
            # Log results
            self._log_processing_result(result)
            
        except Exception as e:
            LOGGER.error("HTR processing failed: %s", e)
            result.status = HTRStatus.FAILED
            result.error_message = str(e)
            result.processing_time = time.time() - start_time
        
        return result
    
    def _filter_handwriting_blocks(self, layout_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter layout blocks to find handwriting blocks."""
        handwriting_blocks = []
        
        for block in layout_blocks:
            block_type = block.get("type", "").lower()
            
            # Check if this is a handwriting block
            if self._is_handwriting_block(block_type, block):
                handwriting_blocks.append(block)
                LOGGER.debug("Found handwriting block: type=%s, bbox=%s", 
                           block_type, block.get("bbox"))
        
        return handwriting_blocks
    
    def _is_handwriting_block(self, block_type: str, block: Dict[str, Any]) -> bool:
        """Determine if a block contains handwriting."""
        # Check block type
        handwriting_types = ["handwriting", "hand", "script", "cursive"]
        
        if any(ht in block_type for ht in handwriting_types):
            return True
        
        # Check for handwriting indicators in metadata
        metadata = block.get("metadata", {})
        if metadata.get("is_handwriting", False):
            return True
        
        # Check confidence - low confidence might indicate handwriting
        confidence = block.get("confidence", 1.0)
        if confidence < 0.3:  # Low confidence might be handwriting
            return True
        
        # Check block size - handwriting blocks are often smaller
        bbox = block.get("bbox", [0, 0, 0, 0])
        if len(bbox) == 4:
            x, y, w, h = bbox
            area = w * h
            if area < 10000:  # Small blocks might be handwriting
                return True
        
        return False
    
    def _save_samples(self, result: HTRResult) -> None:
        """Save HTR samples for training data."""
        if not self.sample_storage:
            return
        
        try:
            for block in result.blocks:
                # Create sample
                sample = self.sample_storage.create_sample(
                    image_path=block.source_image_path,
                    ground_truth=block.text,
                    confidence=block.confidence,
                    model_used=block.model_used,
                    metadata={
                        "block_id": block.block_id,
                        "bbox": list(block.bbox),
                        "page_num": result.page_num
                    }
                )
                
                # Save to database
                self.sample_storage.save_sample(sample)
                
        except Exception as e:
            LOGGER.warning("Failed to save HTR samples: %s", e)
    
    def _log_processing_result(self, result: HTRResult) -> None:
        """Log HTR processing results."""
        if result.status == HTRStatus.SUCCESS:
            LOGGER.info(
                "HTR processing completed: %d blocks processed, %d high confidence, %d need review",
                len(result.blocks), result.high_confidence_blocks, len(result.review_candidates)
            )
        elif result.status == HTRStatus.FAILED:
            LOGGER.error("HTR processing failed: %s", result.error_message)
        elif result.status == HTRStatus.SKIPPED:
            LOGGER.info("HTR processing skipped: no handwriting blocks found")
    
    def get_review_candidates(self, result: HTRResult) -> List[Dict[str, Any]]:
        """Get review candidates for the review queue."""
        if not self.config.review_queue_enabled:
            return []
        
        candidates = []
        for block in result.review_candidates:
            candidate = {
                "type": "htr_block",
                "block_id": block.block_id,
                "text": block.text,
                "confidence": block.confidence,
                "threshold": self.config.confidence_threshold,
                "source": "htr_processing",
                "metadata": {
                    "bbox": list(block.bbox),
                    "model_used": block.model_used.value,
                    "processing_time": block.processing_time
                }
            }
            candidates.append(candidate)
        
        return candidates
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get HTR processing statistics."""
        return {
            "enabled": self.config.enabled,
            "available": self.is_available(),
            "model_type": self.config.model_type.value,
            "confidence_threshold": self.config.confidence_threshold,
            "driver_info": self.driver.get_model_info() if self.driver else None,
            "sample_storage_enabled": self.sample_storage is not None
        }
    
    def cleanup(self) -> None:
        """Clean up resources."""
        if self.driver:
            self.driver.cleanup()
        self.driver = None
        self.sample_storage = None
        self._initialized = False
        LOGGER.info("HTR processor cleaned up")


# Global HTR processor instance
_htr_processor = None


def get_htr_processor(config: Optional[HTRConfig] = None) -> HTRProcessor:
    """Get global HTR processor instance."""
    global _htr_processor
    
    if _htr_processor is None:
        _htr_processor = HTRProcessor(config)
    
    return _htr_processor


def initialize_htr(config: Optional[HTRConfig] = None) -> bool:
    """Initialize HTR system with configuration."""
    try:
        processor = get_htr_processor(config)
        return processor.is_available()
    except Exception as e:
        LOGGER.error("Failed to initialize HTR: %s", e)
        return False


def cleanup_htr() -> None:
    """Clean up global HTR processor."""
    global _htr_processor
    
    if _htr_processor:
        _htr_processor.cleanup()
        _htr_processor = None
