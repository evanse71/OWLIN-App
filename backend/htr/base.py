# backend/htr/base.py
"""
Base interfaces and data classes for HTR module.

This module defines the core data structures and interfaces used throughout
the HTR system, providing type safety and clear contracts.
"""

from __future__ import annotations
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path

LOGGER = logging.getLogger("owlin.htr.base")


class HTRStatus(Enum):
    """Status of HTR processing."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    NO_OP = "no_op"


class HTRModelType(Enum):
    """Types of HTR models available."""
    KRAKEN = "kraken"
    PYLAIA = "pylaia"
    FALLBACK = "fallback"


@dataclass
class HTRBlock:
    """Represents a handwriting block with OCR results."""
    block_id: str
    bbox: Tuple[int, int, int, int]  # x, y, width, height
    text: str
    confidence: float
    model_used: HTRModelType
    processing_time: float
    source_image_path: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "block_id": self.block_id,
            "bbox": list(self.bbox),
            "text": self.text,
            "confidence": self.confidence,
            "model_used": self.model_used.value,
            "processing_time": self.processing_time,
            "source_image_path": self.source_image_path,
            "metadata": self.metadata
        }
    
    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if this block has high confidence."""
        return self.confidence >= threshold
    
    def needs_review(self, threshold: float = 0.8) -> bool:
        """Check if this block needs human review."""
        return self.confidence < threshold


@dataclass
class HTRResult:
    """Complete HTR processing result for a document."""
    document_id: str
    page_num: int
    blocks: List[HTRBlock]
    status: HTRStatus
    processing_time: float
    model_used: HTRModelType
    total_blocks: int
    high_confidence_blocks: int
    review_candidates: List[HTRBlock] = field(default_factory=list)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "document_id": self.document_id,
            "page_num": self.page_num,
            "blocks": [block.to_dict() for block in self.blocks],
            "status": self.status.value,
            "processing_time": self.processing_time,
            "model_used": self.model_used.value,
            "total_blocks": self.total_blocks,
            "high_confidence_blocks": self.high_confidence_blocks,
            "review_candidates": [block.to_dict() for block in self.review_candidates],
            "error_message": self.error_message,
            "metadata": self.metadata
        }
    
    def get_confidence_stats(self) -> Dict[str, float]:
        """Get confidence statistics."""
        if not self.blocks:
            return {"min": 0.0, "max": 0.0, "avg": 0.0, "median": 0.0}
        
        confidences = [block.confidence for block in self.blocks]
        confidences.sort()
        
        return {
            "min": min(confidences),
            "max": max(confidences),
            "avg": sum(confidences) / len(confidences),
            "median": confidences[len(confidences) // 2]
        }


@dataclass
class HTRConfig:
    """Configuration for HTR processing."""
    enabled: bool = False
    confidence_threshold: float = 0.8
    model_type: HTRModelType = HTRModelType.KRAKEN
    fallback_enabled: bool = True
    save_samples: bool = True
    review_queue_enabled: bool = True
    max_processing_time: float = 30.0  # seconds
    batch_size: int = 10
    
    # Model-specific settings
    kraken_model_path: Optional[str] = None
    pylaia_model_path: Optional[str] = None
    
    # Processing settings
    image_preprocessing: bool = True
    binarization_threshold: float = 0.5
    noise_reduction: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "enabled": self.enabled,
            "confidence_threshold": self.confidence_threshold,
            "model_type": self.model_type.value,
            "fallback_enabled": self.fallback_enabled,
            "save_samples": self.save_samples,
            "review_queue_enabled": self.review_queue_enabled,
            "max_processing_time": self.max_processing_time,
            "batch_size": self.batch_size,
            "kraken_model_path": self.kraken_model_path,
            "pylaia_model_path": self.pylaia_model_path,
            "image_preprocessing": self.image_preprocessing,
            "binarization_threshold": self.binarization_threshold,
            "noise_reduction": self.noise_reduction
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> HTRConfig:
        """Create HTRConfig from dictionary."""
        config = cls()
        
        # Basic settings
        config.enabled = data.get("enabled", False)
        config.confidence_threshold = data.get("confidence_threshold", 0.8)
        config.fallback_enabled = data.get("fallback_enabled", True)
        config.save_samples = data.get("save_samples", True)
        config.review_queue_enabled = data.get("review_queue_enabled", True)
        config.max_processing_time = data.get("max_processing_time", 30.0)
        config.batch_size = data.get("batch_size", 10)
        
        # Model settings
        model_type = data.get("model_type", "kraken")
        config.model_type = HTRModelType(model_type)
        config.kraken_model_path = data.get("kraken_model_path")
        config.pylaia_model_path = data.get("pylaia_model_path")
        
        # Processing settings
        config.image_preprocessing = data.get("image_preprocessing", True)
        config.binarization_threshold = data.get("binarization_threshold", 0.5)
        config.noise_reduction = data.get("noise_reduction", True)
        
        return config


class HTRInterface:
    """Base interface for HTR implementations."""
    
    def __init__(self, config: HTRConfig):
        self.config = config
        self.logger = logging.getLogger(f"owlin.htr.{self.__class__.__name__}")
    
    def is_available(self) -> bool:
        """Check if this HTR implementation is available."""
        raise NotImplementedError
    
    def process_blocks(self, image_path: Union[str, Path], 
                      handwriting_blocks: List[Dict[str, Any]]) -> HTRResult:
        """Process handwriting blocks in an image."""
        raise NotImplementedError
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        raise NotImplementedError
    
    def cleanup(self) -> None:
        """Clean up resources."""
        pass


class HTRSample:
    """Represents a training sample for HTR."""
    
    def __init__(self, sample_id: str, image_path: str, ground_truth: str,
                 confidence: float, model_used: HTRModelType,
                 metadata: Optional[Dict[str, Any]] = None):
        self.sample_id = sample_id
        self.image_path = image_path
        self.ground_truth = ground_truth
        self.confidence = confidence
        self.model_used = model_used
        self.metadata = metadata or {}
        self.created_at = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "sample_id": self.sample_id,
            "image_path": self.image_path,
            "ground_truth": self.ground_truth,
            "confidence": self.confidence,
            "model_used": self.model_used.value,
            "metadata": self.metadata,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> HTRSample:
        """Create HTRSample from dictionary."""
        return cls(
            sample_id=data["sample_id"],
            image_path=data["image_path"],
            ground_truth=data["ground_truth"],
            confidence=data["confidence"],
            model_used=HTRModelType(data["model_used"]),
            metadata=data.get("metadata", {}),
        )
