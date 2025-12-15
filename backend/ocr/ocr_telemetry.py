# -*- coding: utf-8 -*-
"""
OCR Telemetry and Confidence Tracking

Provides structured telemetry collection and reporting for OCR processing,
enabling observability into per-page and per-block confidence metrics.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json
import logging

LOGGER = logging.getLogger("owlin.ocr.telemetry")


@dataclass
class PageTelemetry:
    """Telemetry data for a single page."""
    page_index: int
    engine: str  # "paddleocr", "tesseract", "fallback", "mixed"
    psm: Optional[str] = None  # Tesseract PSM mode if used
    preprocessing: str = "unknown"  # "enhanced", "minimal", "dual_path_chosen", "none"
    confidence: float = 0.0  # 0-1 scale
    word_count: int = 0
    duration_ms: float = 0.0
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "page_index": self.page_index,
            "engine": self.engine,
            "psm": self.psm,
            "preprocessing": self.preprocessing,
            "confidence": self.confidence,
            "word_count": self.word_count,
            "duration_ms": self.duration_ms,
            "errors": self.errors
        }


@dataclass
class BlockTelemetry:
    """Telemetry data for a single block."""
    page_index: int
    block_type: str  # "header", "table", "totals", "body", "footer", "handwriting"
    bbox: List[int]  # [x, y, w, h]
    confidence: float = 0.0  # 0-1 scale
    word_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "page_index": self.page_index,
            "block_type": self.block_type,
            "bbox": self.bbox,
            "confidence": self.confidence,
            "word_count": self.word_count
        }


@dataclass
class OverallTelemetry:
    """Overall document-level telemetry."""
    confidence: float = 0.0  # 0-1 scale
    engine_mix: str = "unknown"  # "paddleocr", "tesseract", "mixed"
    duration_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "confidence": self.confidence,
            "engine_mix": self.engine_mix,
            "duration_ms": self.duration_ms
        }


@dataclass
class OCRTelemetryReport:
    """Complete OCR telemetry report for a document."""
    pages: List[PageTelemetry] = field(default_factory=list)
    blocks: List[BlockTelemetry] = field(default_factory=list)
    overall: OverallTelemetry = field(default_factory=OverallTelemetry)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "pages": [p.to_dict() for p in self.pages],
            "blocks": [b.to_dict() for b in self.blocks],
            "overall": self.overall.to_dict()
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> "OCRTelemetryReport":
        """Deserialize from JSON string."""
        try:
            data = json.loads(json_str)
            report = cls()
            
            # Parse pages
            for page_data in data.get("pages", []):
                report.pages.append(PageTelemetry(
                    page_index=page_data.get("page_index", 0),
                    engine=page_data.get("engine", "unknown"),
                    psm=page_data.get("psm"),
                    preprocessing=page_data.get("preprocessing", "unknown"),
                    confidence=float(page_data.get("confidence", 0.0)),
                    word_count=int(page_data.get("word_count", 0)),
                    duration_ms=float(page_data.get("duration_ms", 0.0)),
                    errors=page_data.get("errors", [])
                ))
            
            # Parse blocks
            for block_data in data.get("blocks", []):
                report.blocks.append(BlockTelemetry(
                    page_index=block_data.get("page_index", 0),
                    block_type=block_data.get("block_type", "body"),
                    bbox=block_data.get("bbox", [0, 0, 0, 0]),
                    confidence=float(block_data.get("confidence", 0.0)),
                    word_count=int(block_data.get("word_count", 0))
                ))
            
            # Parse overall
            overall_data = data.get("overall", {})
            report.overall = OverallTelemetry(
                confidence=float(overall_data.get("confidence", 0.0)),
                engine_mix=overall_data.get("engine_mix", "unknown"),
                duration_ms=float(overall_data.get("duration_ms", 0.0))
            )
            
            return report
        except Exception as e:
            LOGGER.error(f"Failed to parse OCR telemetry report from JSON: {e}")
            return cls()  # Return empty report on error


def count_words(text: str) -> int:
    """Count words in text (simple whitespace-based counting)."""
    if not text or not text.strip():
        return 0
    return len(text.split())


def determine_engine_mix(methods: List[str]) -> str:
    """Determine engine mix from list of methods used."""
    if not methods:
        return "unknown"
    
    unique_methods = set(methods)
    
    if len(unique_methods) == 1:
        method = list(unique_methods)[0]
        if method == "paddleocr":
            return "paddleocr"
        elif method == "tesseract":
            return "tesseract"
        else:
            return "fallback"
    else:
        # Multiple methods used
        if "paddleocr" in unique_methods and "tesseract" in unique_methods:
            return "mixed"
        elif "paddleocr" in unique_methods:
            return "paddleocr"  # Primary method
        elif "tesseract" in unique_methods:
            return "tesseract"  # Primary method
        else:
            return "fallback"


def categorize_block_type(block_type: str) -> str:
    """Categorize block type into standard categories."""
    block_type_lower = block_type.lower()
    
    if "header" in block_type_lower:
        return "header"
    elif "table" in block_type_lower:
        return "table"
    elif "total" in block_type_lower or "vat" in block_type_lower or "footer" in block_type_lower:
        return "totals"
    elif "handwriting" in block_type_lower:
        return "handwriting"
    else:
        return "body"

