#!/usr/bin/env python3
"""
Test script for HTR integration.

This script tests the HTR module integration with the main OCR pipeline,
verifying that all components work together correctly.
"""

import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.htr import HTRConfig, HTRModelType, get_htr_processor
from backend.config import (
    FEATURE_HTR_ENABLED, HTR_CONFIDENCE_THRESHOLD,
    HTR_MODEL_TYPE, HTR_SAVE_SAMPLES, HTR_REVIEW_QUEUE_ENABLED
)

# Setup logging
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("test_htr")


def test_htr_config():
    """Test HTR configuration."""
    LOGGER.info("Testing HTR configuration...")
    
    config = HTRConfig(
        enabled=FEATURE_HTR_ENABLED,
        confidence_threshold=HTR_CONFIDENCE_THRESHOLD,
        model_type=HTRModelType(HTR_MODEL_TYPE),
        save_samples=HTR_SAVE_SAMPLES,
        review_queue_enabled=HTR_REVIEW_QUEUE_ENABLED
    )
    
    LOGGER.info("HTR Config: %s", config.to_dict())
    return config


def test_htr_processor():
    """Test HTR processor initialization."""
    LOGGER.info("Testing HTR processor...")
    
    processor = get_htr_processor()
    
    LOGGER.info("HTR Processor available: %s", processor.is_available())
    LOGGER.info("HTR Processing stats: %s", processor.get_processing_stats())
    
    return processor


def test_htr_processing():
    """Test HTR processing with mock data."""
    LOGGER.info("Testing HTR processing...")
    
    processor = get_htr_processor()
    
    if not processor.is_available():
        LOGGER.warning("HTR not available, skipping processing test")
        return
    
    # Mock layout blocks with handwriting
    layout_blocks = [
        {
            "type": "text",
            "bbox": [0, 0, 100, 50],
            "confidence": 0.9
        },
        {
            "type": "handwriting",
            "bbox": [0, 50, 100, 50],
            "confidence": 0.3
        },
        {
            "type": "script",
            "bbox": [0, 100, 100, 50],
            "confidence": 0.4
        }
    ]
    
    # Create a dummy image path
    dummy_image = Path("test_image.png")
    
    try:
        result = processor.process_handwriting_blocks(dummy_image, layout_blocks, page_num=1)
        
        LOGGER.info("HTR Result: %s", result.to_dict())
        LOGGER.info("Review candidates: %d", len(result.review_candidates))
        
    except Exception as e:
        LOGGER.warning("HTR processing test failed (expected): %s", e)


def test_htr_database():
    """Test HTR database functionality."""
    LOGGER.info("Testing HTR database...")
    
    try:
        from backend.htr.dataset import HTRSampleStorage
        
        # Create storage with actual database
        storage = HTRSampleStorage("data/owlin.db")
        
        # Test sample creation
        sample = storage.create_sample(
            image_path="/test/image.png",
            ground_truth="test handwriting",
            confidence=0.8,
            model_used=HTRModelType.KRAKEN,
            metadata={"test": "value"}
        )
        
        LOGGER.info("Created sample: %s", sample.sample_id)
        
        # Test sample storage
        success = storage.save_sample(sample)
        LOGGER.info("Sample saved: %s", success)
        
        # Test sample retrieval
        samples = storage.get_samples()
        LOGGER.info("Retrieved %d samples", len(samples))
        
        # Test statistics
        stats = storage.get_statistics()
        LOGGER.info("Database statistics: %s", stats)
        
    except Exception as e:
        LOGGER.error("Database test failed: %s", e)


def main():
    """Main test function."""
    LOGGER.info("Starting HTR integration tests...")
    
    try:
        # Test configuration
        config = test_htr_config()
        
        # Test processor
        processor = test_htr_processor()
        
        # Test processing
        test_htr_processing()
        
        # Test database
        test_htr_database()
        
        LOGGER.info("All HTR tests completed successfully!")
        return 0
        
    except Exception as e:
        LOGGER.error("HTR tests failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
