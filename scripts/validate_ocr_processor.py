#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR Processor Validation Script

This script validates the OCR processor functionality on real-world documents
to ensure high-accuracy text extraction with PaddleOCR and fallbacks.

Usage:
    python scripts/validate_ocr_processor.py [--test-dir PATH] [--output-dir PATH]
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

from backend.ocr.ocr_processor import process_document_ocr
from backend.ocr.layout_detector import detect_document_layout
from backend.config import FEATURE_OCR_V2_LAYOUT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
LOGGER = logging.getLogger("ocr_validation")


class OCRValidationSuite:
    """Comprehensive validation suite for OCR processor."""
    
    def __init__(self, test_dir: Path, output_dir: Path):
        self.test_dir = test_dir
        self.output_dir = output_dir
        self.results = []
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def run_validation(self) -> Dict[str, Any]:
        """Run complete OCR validation suite."""
        LOGGER.info("Starting OCR processor validation...")
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
        report_path = self.output_dir / "ocr_validation_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        LOGGER.info(f"OCR validation report saved to: {report_path}")
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
        """Process a single document through OCR validation."""
        LOGGER.info(f"Processing document: {doc_path.name}")
        
        start_time = time.time()
        
        try:
            # Step 1: Layout detection
            LOGGER.info(f"  Step 1: Layout detection for {doc_path.name}")
            layout_result = detect_document_layout(doc_path, page_num=1, save_artifacts=True, artifact_dir=self.output_dir)
            
            if not layout_result.blocks:
                LOGGER.warning(f"  No layout blocks detected for {doc_path.name}")
                return
            
            # Step 2: OCR processing
            LOGGER.info(f"  Step 2: OCR processing for {doc_path.name}")
            layout_blocks = [block.to_dict() for block in layout_result.blocks]
            ocr_result = process_document_ocr(doc_path, layout_blocks, page_num=1, save_artifacts=True, artifact_dir=self.output_dir)
            
            processing_time = time.time() - start_time
            
            # Store result
            doc_result = {
                "document": doc_path.name,
                "path": str(doc_path),
                "page_num": ocr_result.page_num,
                "num_blocks": len(ocr_result.blocks),
                "processing_time": processing_time,
                "method_used": ocr_result.method_used,
                "confidence_avg": ocr_result.confidence_avg,
                "low_confidence_blocks": ocr_result.low_confidence_blocks,
                "blocks": [block.to_dict() for block in ocr_result.blocks],
                "status": "success"
            }
            
            self.results.append(doc_result)
            
            # Log summary
            LOGGER.info(f"  ✓ {len(ocr_result.blocks)} blocks processed")
            LOGGER.info(f"  ✓ Method: {ocr_result.method_used}")
            LOGGER.info(f"  ✓ Confidence: {ocr_result.confidence_avg:.3f}")
            LOGGER.info(f"  ✓ Low confidence blocks: {ocr_result.low_confidence_blocks}")
            LOGGER.info(f"  ✓ Time: {processing_time:.3f}s")
            
            # Log block details
            for i, block in enumerate(ocr_result.blocks):
                LOGGER.info(f"    Block {i+1}: {block.type} - '{block.ocr_text[:50]}...' (conf: {block.confidence:.3f}, method: {block.method_used})")
            
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
        """Generate comprehensive OCR validation report."""
        successful = [r for r in self.results if r["status"] == "success"]
        failed = [r for r in self.results if r["status"] == "error"]
        
        # Calculate statistics
        if successful:
            avg_blocks = sum(r["num_blocks"] for r in successful) / len(successful)
            avg_confidence = sum(r["confidence_avg"] for r in successful) / len(successful)
            avg_time = sum(r["processing_time"] for r in successful) / len(successful)
            total_low_conf = sum(r["low_confidence_blocks"] for r in successful)
            
            # Method usage statistics
            methods = {}
            for r in successful:
                method = r["method_used"]
                methods[method] = methods.get(method, 0) + 1
            
            # Block type statistics
            block_types = {}
            block_methods = {}
            confidence_by_type = {}
            
            for r in successful:
                for block in r["blocks"]:
                    block_type = block["type"]
                    block_method = block["method_used"]
                    
                    block_types[block_type] = block_types.get(block_type, 0) + 1
                    block_methods[block_method] = block_methods.get(block_method, 0) + 1
                    
                    if block_type not in confidence_by_type:
                        confidence_by_type[block_type] = []
                    confidence_by_type[block_type].append(block["confidence"])
            
            # Calculate average confidence by block type
            avg_confidence_by_type = {}
            for block_type, confidences in confidence_by_type.items():
                avg_confidence_by_type[block_type] = sum(confidences) / len(confidences)
        else:
            avg_blocks = 0
            avg_confidence = 0
            avg_time = 0
            total_low_conf = 0
            methods = {}
            block_types = {}
            block_methods = {}
            avg_confidence_by_type = {}
        
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
                "avg_processing_time": avg_time,
                "total_low_confidence_blocks": total_low_conf
            },
            "method_usage": methods,
            "block_type_distribution": block_types,
            "ocr_method_distribution": block_methods,
            "confidence_by_block_type": avg_confidence_by_type,
            "feature_flag_status": {
                "FEATURE_OCR_V2_LAYOUT": FEATURE_OCR_V2_LAYOUT
            },
            "detailed_results": self.results
        }
        
        return report


def create_test_documents(output_dir: Path) -> None:
    """Create synthetic test documents for OCR validation."""
    
    LOGGER.info("Creating synthetic test documents for OCR validation...")
    
    # Create different document types with clear text
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
    """Create a standard invoice with clear text."""
    img = np.ones((800, 600, 3), dtype=np.uint8) * 255
    
    # Header
    cv2.rectangle(img, (50, 50), (550, 150), (0, 0, 0), 2)
    cv2.putText(img, "INVOICE", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 2)
    cv2.putText(img, "Invoice #: 12345", (100, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
    cv2.putText(img, "Date: 2024-01-15", (100, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
    
    # Table
    for i in range(8):
        y = 200 + i * 50
        cv2.line(img, (50, y), (550, y), (0, 0, 0), 1)
        if i == 0:
            cv2.putText(img, "Item Description Quantity Price Total", (60, y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
        else:
            cv2.putText(img, f"Item {i} Description {i} Qty: {i} $10.00 ${i*10}.00", (60, y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    # Footer
    cv2.rectangle(img, (50, 650), (550, 750), (0, 0, 0), 2)
    cv2.putText(img, "SUBTOTAL: $70.00", (100, 680), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 1)
    cv2.putText(img, "TAX: $7.00", (100, 710), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 1)
    cv2.putText(img, "TOTAL: $77.00", (100, 740), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 2)
    
    return img


def _create_table_heavy_invoice() -> np.ndarray:
    """Create an invoice with heavy table content."""
    img = np.ones((1000, 700, 3), dtype=np.uint8) * 255
    
    # Header
    cv2.putText(img, "DETAILED INVOICE", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 2)
    cv2.putText(img, "Invoice #: 67890", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    
    # Large table with many items
    for i in range(15):
        y = 120 + i * 40
        cv2.line(img, (50, y), (650, y), (0, 0, 0), 1)
        if i == 0:
            cv2.putText(img, "Item Code Description Quantity Unit Price Total", (60, y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        else:
            cv2.putText(img, f"ITM{i:03d} Product {i} {i} units $5.00 ${i*5}.00", (60, y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    
    # Footer
    cv2.putText(img, "GRAND TOTAL: $600.00", (50, 800), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)
    
    return img


def _create_thermal_receipt() -> np.ndarray:
    """Create a thermal receipt with clear text."""
    img = np.ones((600, 300, 3), dtype=np.uint8) * 255
    
    # Header
    cv2.putText(img, "STORE RECEIPT", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.putText(img, "Store #123", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    cv2.putText(img, "Date: 2024-01-15", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    
    # Items
    items = [
        "Bread Loaf $2.50",
        "Milk 1L $3.00", 
        "Eggs Dozen $4.00",
        "Butter $2.00",
        "Cheese $5.00"
    ]
    
    for i, item in enumerate(items):
        y = 150 + i * 60
        cv2.putText(img, item, (50, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    
    # Total
    cv2.putText(img, "SUBTOTAL: $16.50", (50, 500), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    cv2.putText(img, "TAX: $1.65", (50, 530), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    cv2.putText(img, "TOTAL: $18.15", (50, 560), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    return img


def _create_delivery_note() -> np.ndarray:
    """Create a delivery note with clear text."""
    img = np.ones((700, 500, 3), dtype=np.uint8) * 255
    
    # Header
    cv2.putText(img, "DELIVERY NOTE", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 2)
    cv2.putText(img, "Delivery #: DEL-001", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    
    # Delivery info
    cv2.putText(img, "Delivered to: 123 Main Street", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    cv2.putText(img, "City: Anytown, ST 12345", (50, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    cv2.putText(img, "Date: 2024-01-15", (50, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    cv2.putText(img, "Time: 14:30", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    
    # Items delivered
    cv2.putText(img, "Items Delivered:", (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 1)
    for i in range(4):
        y = 350 + i * 80
        cv2.putText(img, f"Package {i+1}: Delivered Successfully", (50, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    
    # Signature
    cv2.putText(img, "Signature: ________________", (50, 650), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    
    return img


def _create_handwritten_invoice() -> np.ndarray:
    """Create an invoice with handwritten annotations."""
    img = np.ones((800, 600, 3), dtype=np.uint8) * 255
    
    # Header
    cv2.putText(img, "INVOICE", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 2)
    cv2.putText(img, "Invoice #: 12345", (100, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    
    # Table
    for i in range(6):
        y = 200 + i * 60
        cv2.line(img, (50, y), (550, y), (0, 0, 0), 1)
        if i > 0:
            cv2.putText(img, f"Item {i} $10.00", (60, y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    
    # Handwritten note (simulated with irregular text)
    cv2.putText(img, "Note: Please pay within 30 days", (50, 650), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    cv2.putText(img, "Thank you for your business!", (50, 680), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    
    return img


def main():
    """Main OCR validation script."""
    parser = argparse.ArgumentParser(description="Validate OCR processor functionality")
    parser.add_argument("--test-dir", type=Path, default=Path("tests/fixtures/ocr_validation"),
                       help="Directory containing test documents")
    parser.add_argument("--output-dir", type=Path, default=Path("validation_output/ocr_validation"),
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
    
    validator = OCRValidationSuite(args.test_dir, args.output_dir)
    report = validator.run_validation()
    
    # Print summary
    summary = report["validation_summary"]
    LOGGER.info("=" * 60)
    LOGGER.info("OCR PROCESSOR VALIDATION SUMMARY")
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
        LOGGER.info(f"Low confidence blocks: {metrics['total_low_confidence_blocks']}")
        
        LOGGER.info(f"Method usage: {report['method_usage']}")
        LOGGER.info(f"Block types detected: {report['block_type_distribution']}")
        LOGGER.info(f"OCR methods used: {report['ocr_method_distribution']}")
        LOGGER.info(f"Confidence by block type: {report['confidence_by_block_type']}")
    
    LOGGER.info("=" * 60)


if __name__ == "__main__":
    main()
