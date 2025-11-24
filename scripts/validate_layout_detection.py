#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Layout Detection Validation Script

This script validates the layout detection functionality on real-world documents
to ensure robust segmentation across different invoice/receipt formats.

Usage:
    python scripts/validate_layout_detection.py [--test-dir PATH] [--output-dir PATH]
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
import time
import numpy as np
import cv2

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.ocr.layout_detector import detect_document_layout
from backend.config import FEATURE_OCR_V2_LAYOUT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
LOGGER = logging.getLogger("layout_validation")


class LayoutValidationSuite:
    """Comprehensive validation suite for layout detection."""
    
    def __init__(self, test_dir: Path, output_dir: Path):
        self.test_dir = test_dir
        self.output_dir = output_dir
        self.results = []
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def run_validation(self) -> Dict[str, Any]:
        """Run complete validation suite."""
        LOGGER.info("Starting layout detection validation...")
        LOGGER.info(f"Test directory: {self.test_dir}")
        LOGGER.info(f"Output directory: {self.output_dir}")
        LOGGER.info(f"Feature flag FEATURE_OCR_V2_LAYOUT: {FEATURE_OCR_V2_LAYOUT}")
        
        # Find test documents
        test_documents = self._find_test_documents()
        LOGGER.info(f"Found {len(test_documents)} test documents")
        
        if not test_documents:
            LOGGER.warning("No test documents found!")
            return {"status": "error", "message": "No test documents found"}
        
        # Process each document
        for doc_path in test_documents:
            self._process_document(doc_path)
        
        # Generate validation report
        report = self._generate_report()
        
        # Save report
        report_path = self.output_dir / "layout_validation_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        LOGGER.info(f"Validation report saved to: {report_path}")
        return report
    
    def _find_test_documents(self) -> List[Path]:
        """Find test documents in the test directory."""
        supported_extensions = {'.png', '.jpg', '.jpeg', '.pdf'}
        documents = []
        
        for ext in supported_extensions:
            documents.extend(self.test_dir.glob(f"*{ext}"))
            documents.extend(self.test_dir.glob(f"*{ext.upper()}"))
        
        return sorted(documents)
    
    def _process_document(self, doc_path: Path):
        """Process a single document through layout detection."""
        LOGGER.info(f"Processing document: {doc_path.name}")
        
        start_time = time.time()
        
        try:
            # Run layout detection
            result = detect_document_layout(
                doc_path, 
                page_num=1, 
                save_artifacts=True, 
                artifact_dir=self.output_dir
            )
            
            processing_time = time.time() - start_time
            
            # Store result
            doc_result = {
                "document": doc_path.name,
                "path": str(doc_path),
                "page_num": result.page_num,
                "num_blocks": len(result.blocks),
                "processing_time": processing_time,
                "method_used": result.method_used,
                "confidence_avg": result.confidence_avg,
                "blocks": [block.to_dict() for block in result.blocks],
                "status": "success"
            }
            
            self.results.append(doc_result)
            
            # Log summary
            LOGGER.info(f"  ✓ {len(result.blocks)} blocks detected")
            LOGGER.info(f"  ✓ Method: {result.method_used}")
            LOGGER.info(f"  ✓ Confidence: {result.confidence_avg:.3f}")
            LOGGER.info(f"  ✓ Time: {processing_time:.3f}s")
            
            # Log block details
            for i, block in enumerate(result.blocks):
                LOGGER.info(f"    Block {i+1}: {block.type} at {block.bbox} (conf: {block.confidence:.3f})")
            
        except Exception as e:
            LOGGER.error(f"  ✗ Error processing {doc_path.name}: {e}")
            
            doc_result = {
                "document": doc_path.name,
                "path": str(doc_path),
                "error": str(e),
                "status": "error"
            }
            
            self.results.append(doc_result)
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        successful = [r for r in self.results if r["status"] == "success"]
        failed = [r for r in self.results if r["status"] == "error"]
        
        # Calculate statistics
        if successful:
            avg_blocks = sum(r["num_blocks"] for r in successful) / len(successful)
            avg_confidence = sum(r["confidence_avg"] for r in successful) / len(successful)
            avg_time = sum(r["processing_time"] for r in successful) / len(successful)
            
            # Method usage statistics
            methods = {}
            for r in successful:
                method = r["method_used"]
                methods[method] = methods.get(method, 0) + 1
            
            # Block type statistics
            block_types = {}
            for r in successful:
                for block in r["blocks"]:
                    block_type = block["type"]
                    block_types[block_type] = block_types.get(block_type, 0) + 1
        else:
            avg_blocks = 0
            avg_confidence = 0
            avg_time = 0
            methods = {}
            block_types = {}
        
        report = {
            "validation_summary": {
                "total_documents": len(self.results),
                "successful": len(successful),
                "failed": len(failed),
                "success_rate": len(successful) / len(self.results) if self.results else 0
            },
            "performance_metrics": {
                "avg_blocks_per_document": avg_blocks,
                "avg_confidence": avg_confidence,
                "avg_processing_time": avg_time
            },
            "method_usage": methods,
            "block_type_distribution": block_types,
            "feature_flag_status": {
                "FEATURE_OCR_V2_LAYOUT": FEATURE_OCR_V2_LAYOUT
            },
            "detailed_results": self.results
        }
        
        return report


def create_test_documents(output_dir: Path) -> None:
    """Create synthetic test documents for validation."""
    
    LOGGER.info("Creating synthetic test documents...")
    
    # Create different document types
    documents = [
        ("invoice_standard", _create_standard_invoice()),
        ("invoice_table_heavy", _create_table_heavy_invoice()),
        ("receipt_thermal", _create_thermal_receipt()),
        ("delivery_note", _create_delivery_note()),
        ("invoice_handwritten", _create_handwritten_invoice())
    ]
    
    for name, img in documents:
        output_path = output_dir / f"{name}.png"
        cv2.imwrite(str(output_path), img)
        LOGGER.info(f"Created test document: {output_path}")


def _create_standard_invoice() -> np.ndarray:
    """Create a standard invoice layout."""
    img = np.ones((800, 600, 3), dtype=np.uint8) * 255
    
    # Header
    cv2.rectangle(img, (50, 50), (550, 150), (0, 0, 0), 2)
    cv2.putText(img, "INVOICE", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 2)
    cv2.putText(img, "Invoice #: 12345", (100, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
    
    # Table
    for i in range(8):
        y = 200 + i * 50
        cv2.line(img, (50, y), (550, y), (0, 0, 0), 1)
    
    # Footer
    cv2.rectangle(img, (50, 650), (550, 750), (0, 0, 0), 2)
    cv2.putText(img, "TOTAL: $1,234.56", (100, 700), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 2)
    
    return img


def _create_table_heavy_invoice() -> np.ndarray:
    """Create an invoice with heavy table content."""
    img = np.ones((1000, 700, 3), dtype=np.uint8) * 255
    
    # Header
    cv2.putText(img, "DETAILED INVOICE", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 2)
    
    # Large table
    for i in range(15):
        y = 100 + i * 40
        cv2.line(img, (50, y), (650, y), (0, 0, 0), 1)
    
    # Footer
    cv2.putText(img, "GRAND TOTAL: $5,678.90", (50, 800), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)
    
    return img


def _create_thermal_receipt() -> np.ndarray:
    """Create a thermal receipt layout."""
    img = np.ones((600, 300, 3), dtype=np.uint8) * 255
    
    # Header
    cv2.putText(img, "STORE RECEIPT", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    # Items
    for i in range(6):
        y = 100 + i * 60
        cv2.putText(img, f"Item {i+1}: $10.00", (50, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    
    # Total
    cv2.putText(img, "TOTAL: $60.00", (50, 500), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    return img


def _create_delivery_note() -> np.ndarray:
    """Create a delivery note layout."""
    img = np.ones((700, 500, 3), dtype=np.uint8) * 255
    
    # Header
    cv2.putText(img, "DELIVERY NOTE", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 2)
    
    # Delivery info
    cv2.putText(img, "Delivered to: 123 Main St", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    cv2.putText(img, "Date: 2024-01-15", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    
    # Items
    for i in range(4):
        y = 300 + i * 80
        cv2.putText(img, f"Package {i+1}: Delivered", (50, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    
    return img


def _create_handwritten_invoice() -> np.ndarray:
    """Create an invoice with handwritten annotations."""
    img = np.ones((800, 600, 3), dtype=np.uint8) * 255
    
    # Header
    cv2.putText(img, "INVOICE", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 2)
    
    # Table
    for i in range(6):
        y = 200 + i * 60
        cv2.line(img, (50, y), (550, y), (0, 0, 0), 1)
    
    # Handwritten note (simulated with irregular lines)
    cv2.putText(img, "Note: Please pay within 30 days", (50, 650), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    
    return img


def main():
    """Main validation script."""
    parser = argparse.ArgumentParser(description="Validate layout detection functionality")
    parser.add_argument("--test-dir", type=Path, default=Path("tests/fixtures/layout_detection"),
                       help="Directory containing test documents")
    parser.add_argument("--output-dir", type=Path, default=Path("data/validation/layout_detection"),
                       help="Directory for validation outputs")
    parser.add_argument("--create-test-docs", action="store_true",
                       help="Create synthetic test documents")
    
    args = parser.parse_args()
    
    # Create test documents if requested
    if args.create_test_docs:
        args.test_dir.mkdir(parents=True, exist_ok=True)
        create_test_documents(args.test_dir)
        LOGGER.info("Test documents created successfully")
        return
    
    # Run validation
    if not args.test_dir.exists():
        LOGGER.error(f"Test directory not found: {args.test_dir}")
        LOGGER.info("Use --create-test-docs to create synthetic test documents")
        return
    
    validator = LayoutValidationSuite(args.test_dir, args.output_dir)
    report = validator.run_validation()
    
    # Print summary
    summary = report["validation_summary"]
    LOGGER.info("=" * 60)
    LOGGER.info("LAYOUT DETECTION VALIDATION SUMMARY")
    LOGGER.info("=" * 60)
    LOGGER.info(f"Total documents: {summary['total_documents']}")
    LOGGER.info(f"Successful: {summary['successful']}")
    LOGGER.info(f"Failed: {summary['failed']}")
    LOGGER.info(f"Success rate: {summary['success_rate']:.1%}")
    
    if summary['successful'] > 0:
        metrics = report["performance_metrics"]
        LOGGER.info(f"Average blocks per document: {metrics['avg_blocks_per_document']:.1f}")
        LOGGER.info(f"Average confidence: {metrics['avg_confidence']:.3f}")
        LOGGER.info(f"Average processing time: {metrics['avg_processing_time']:.3f}s")
        
        LOGGER.info(f"Method usage: {report['method_usage']}")
        LOGGER.info(f"Block types detected: {report['block_type_distribution']}")
    
    LOGGER.info("=" * 60)


if __name__ == "__main__":
    main()
