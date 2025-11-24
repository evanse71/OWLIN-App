#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Table Extraction Validation Script

This script validates the table extraction functionality on real-world documents
to ensure accurate line-item parsing from invoices and receipts.

Usage:
    python scripts/validate_table_extraction.py [--test-dir PATH] [--output-dir PATH]
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

from backend.ocr.table_extractor import extract_table_from_block
from backend.ocr.layout_detector import detect_document_layout
from backend.ocr.ocr_processor import process_document_ocr
from backend.config import FEATURE_OCR_V2_LAYOUT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
LOGGER = logging.getLogger("table_validation")


class TableExtractionValidationSuite:
    """Comprehensive validation suite for table extraction."""
    
    def __init__(self, test_dir: Path, output_dir: Path):
        self.test_dir = test_dir
        self.output_dir = output_dir
        self.results = []
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def run_validation(self) -> Dict[str, Any]:
        """Run complete table extraction validation suite."""
        LOGGER.info("Starting table extraction validation...")
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
        report_path = self.output_dir / "table_extraction_validation_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        LOGGER.info(f"Table extraction validation report saved to: {report_path}")
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
        """Process a single document through table extraction validation."""
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
            
            # Step 3: Table extraction
            LOGGER.info(f"  Step 3: Table extraction for {doc_path.name}")
            
            # Load image for table extraction
            import cv2
            image = cv2.imread(str(doc_path))
            if image is None:
                LOGGER.error(f"  Could not load image: {doc_path}")
                return
            
            table_results = []
            for ocr_block in ocr_result.blocks:
                if ocr_block.type == "table":
                    block_info = {
                        "type": ocr_block.type,
                        "bbox": list(ocr_block.bbox)
                    }
                    
                    table_result = extract_table_from_block(image, block_info, ocr_block.ocr_text)
                    table_results.append(table_result)
                    
                    LOGGER.info(f"    Table block: {len(table_result.line_items)} line items, method={table_result.method_used}, conf={table_result.confidence:.3f}")
            
            processing_time = time.time() - start_time
            
            # Store result
            doc_result = {
                "document": doc_path.name,
                "path": str(doc_path),
                "page_num": 1,
                "num_tables": len(table_results),
                "total_line_items": sum(len(table.line_items) for table in table_results),
                "processing_time": processing_time,
                "table_results": [table.to_dict() for table in table_results],
                "status": "success"
            }
            
            self.results.append(doc_result)
            
            # Log summary
            LOGGER.info(f"  ✓ {len(table_results)} tables processed")
            LOGGER.info(f"  ✓ {sum(len(table.line_items) for table in table_results)} total line items")
            LOGGER.info(f"  ✓ Time: {processing_time:.3f}s")
            
            # Log table details
            for i, table in enumerate(table_results):
                LOGGER.info(f"    Table {i+1}: {len(table.line_items)} line items, method={table.method_used}, conf={table.confidence:.3f}")
                for j, item in enumerate(table.line_items[:3]):  # Show first 3 items
                    LOGGER.info(f"      Item {j+1}: {item.description} | {item.quantity} | {item.unit_price} | {item.total_price}")
                if len(table.line_items) > 3:
                    LOGGER.info(f"      ... and {len(table.line_items) - 3} more items")
            
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
        """Generate comprehensive table extraction validation report."""
        successful = [r for r in self.results if r["status"] == "success"]
        failed = [r for r in self.results if r["status"] == "error"]
        
        # Calculate statistics
        if successful:
            total_tables = sum(r["num_tables"] for r in successful)
            total_line_items = sum(r["total_line_items"] for r in successful)
            avg_processing_time = sum(r["processing_time"] for r in successful) / len(successful)
            
            # Method usage statistics
            methods = {}
            fallback_usage = 0
            structure_aware_usage = 0
            
            for r in successful:
                for table in r["table_results"]:
                    method = table["method_used"]
                    methods[method] = methods.get(method, 0) + 1
                    
                    if table["fallback_used"]:
                        fallback_usage += 1
                    if method == "structure_aware":
                        structure_aware_usage += 1
            
            # Line item quality statistics
            all_line_items = []
            for r in successful:
                for table in r["table_results"]:
                    all_line_items.extend(table["line_items"])
            
            avg_confidence = sum(item["confidence"] for item in all_line_items) / len(all_line_items) if all_line_items else 0.0
            
            # Field completion statistics
            field_stats = {
                "description": sum(1 for item in all_line_items if item["description"]),
                "quantity": sum(1 for item in all_line_items if item["quantity"]),
                "unit_price": sum(1 for item in all_line_items if item["unit_price"]),
                "total_price": sum(1 for item in all_line_items if item["total_price"]),
                "vat": sum(1 for item in all_line_items if item["vat"])
            }
            
            field_completion = {field: count / len(all_line_items) if all_line_items else 0 
                              for field, count in field_stats.items()}
            
        else:
            total_tables = 0
            total_line_items = 0
            avg_processing_time = 0
            methods = {}
            fallback_usage = 0
            structure_aware_usage = 0
            avg_confidence = 0.0
            field_completion = {}
        
        report = {
            "validation_summary": {
                "total_documents": len(self.results),
                "successful": len(successful),
                "failed": len(failed),
                "success_rate": len(successful) / len(self.results) if self.results else 0
            },
            "table_extraction_metrics": {
                "total_tables": total_tables,
                "total_line_items": total_line_items,
                "avg_processing_time": avg_processing_time,
                "avg_confidence": avg_confidence,
                "structure_aware_usage": structure_aware_usage,
                "fallback_usage": fallback_usage
            },
            "method_usage": methods,
            "field_completion_rates": field_completion,
            "feature_flag_status": {
                "FEATURE_OCR_V2_LAYOUT": FEATURE_OCR_V2_LAYOUT
            },
            "detailed_results": self.results
        }
        
        return report


def create_test_documents(output_dir: Path) -> None:
    """Create synthetic test documents for table extraction validation."""
    
    LOGGER.info("Creating synthetic test documents for table extraction validation...")
    
    # Create different document types with clear table structures
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
    """Create a standard invoice with clear table structure."""
    img = np.ones((800, 600, 3), dtype=np.uint8) * 255
    
    # Header
    cv2.rectangle(img, (50, 50), (550, 150), (0, 0, 0), 2)
    cv2.putText(img, "INVOICE", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 2)
    cv2.putText(img, "Invoice #: 12345", (100, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
    
    # Table with clear structure
    table_y_start = 200
    table_x_start = 50
    table_width = 500
    table_height = 300
    
    # Draw table lines
    # Horizontal lines
    for i, y in enumerate([0, 50, 100, 150, 200, 250, 300]):
        cv2.line(img, (table_x_start, table_y_start + y), (table_x_start + table_width, table_y_start + y), (0, 0, 0), 2)
    
    # Vertical lines
    for i, x in enumerate([0, 200, 300, 400, 500]):
        cv2.line(img, (table_x_start + x, table_y_start), (table_x_start + x, table_y_start + table_height), (0, 0, 0), 2)
    
    # Add table content
    headers = ["Item", "Description", "Qty", "Unit Price", "Total"]
    for i, header in enumerate(headers):
        x = table_x_start + i * 100 + 10
        y = table_y_start + 30
        cv2.putText(img, header, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    # Add line items
    items = [
        ("1", "Widget A", "5", "$10.00", "$50.00"),
        ("2", "Widget B", "3", "$15.00", "$45.00"),
        ("3", "Widget C", "2", "$20.00", "$40.00"),
        ("4", "Widget D", "1", "$25.00", "$25.00")
    ]
    
    for row, (item, desc, qty, unit, total) in enumerate(items):
        y = table_y_start + 80 + row * 50
        cv2.putText(img, item, (table_x_start + 10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        cv2.putText(img, desc, (table_x_start + 210, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        cv2.putText(img, qty, (table_x_start + 310, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        cv2.putText(img, unit, (table_x_start + 410, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        cv2.putText(img, total, (table_x_start + 510, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    
    # Footer
    cv2.rectangle(img, (50, 650), (550, 750), (0, 0, 0), 2)
    cv2.putText(img, "SUBTOTAL: $160.00", (100, 680), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 1)
    cv2.putText(img, "TAX: $16.00", (100, 710), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 1)
    cv2.putText(img, "TOTAL: $176.00", (100, 740), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 2)
    
    return img


def _create_table_heavy_invoice() -> np.ndarray:
    """Create an invoice with heavy table content."""
    img = np.ones((1000, 700, 3), dtype=np.uint8) * 255
    
    # Header
    cv2.putText(img, "DETAILED INVOICE", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 2)
    cv2.putText(img, "Invoice #: 67890", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    
    # Large table with many items
    table_y_start = 120
    table_x_start = 50
    table_width = 600
    table_height = 600
    
    # Draw table lines
    for y in range(0, table_height + 1, 40):
        cv2.line(img, (table_x_start, table_y_start + y), (table_x_start + table_width, table_y_start + y), (0, 0, 0), 1)
    
    for x in range(0, table_width + 1, 120):
        cv2.line(img, (table_x_start + x, table_y_start), (table_x_start + x, table_y_start + table_height), (0, 0, 0), 1)
    
    # Add headers
    headers = ["Item Code", "Description", "Quantity", "Unit Price", "Total"]
    for i, header in enumerate(headers):
        x = table_x_start + i * 120 + 10
        y = table_y_start + 25
        cv2.putText(img, header, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    
    # Add many line items
    for row in range(15):
        y = table_y_start + 65 + row * 40
        item_code = f"ITM{row+1:03d}"
        desc = f"Product {row+1}"
        qty = str(row + 1)
        unit_price = f"${5 + row}.00"
        total = f"${(5 + row) * (row + 1)}.00"
        
        cv2.putText(img, item_code, (table_x_start + 10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)
        cv2.putText(img, desc, (table_x_start + 130, y), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)
        cv2.putText(img, qty, (table_x_start + 250, y), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)
        cv2.putText(img, unit_price, (table_x_start + 370, y), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)
        cv2.putText(img, total, (table_x_start + 490, y), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)
    
    # Footer
    cv2.putText(img, "GRAND TOTAL: $600.00", (50, 800), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)
    
    return img


def _create_thermal_receipt() -> np.ndarray:
    """Create a thermal receipt with table structure."""
    img = np.ones((600, 300, 3), dtype=np.uint8) * 255
    
    # Header
    cv2.putText(img, "STORE RECEIPT", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.putText(img, "Store #123", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    cv2.putText(img, "Date: 2024-01-15", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    
    # Table structure
    table_y_start = 150
    table_x_start = 50
    table_width = 200
    table_height = 300
    
    # Draw table lines
    for y in range(0, table_height + 1, 50):
        cv2.line(img, (table_x_start, table_y_start + y), (table_x_start + table_width, table_y_start + y), (0, 0, 0), 1)
    
    for x in range(0, table_width + 1, 100):
        cv2.line(img, (table_x_start + x, table_y_start), (table_x_start + x, table_y_start + table_height), (0, 0, 0), 1)
    
    # Add items
    items = [
        ("Bread Loaf", "$2.50"),
        ("Milk 1L", "$3.00"),
        ("Eggs Dozen", "$4.00"),
        ("Butter", "$2.00"),
        ("Cheese", "$5.00")
    ]
    
    for i, (item, price) in enumerate(items):
        y = table_y_start + 30 + i * 50
        cv2.putText(img, item, (table_x_start + 10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        cv2.putText(img, price, (table_x_start + 110, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    # Total
    cv2.putText(img, "SUBTOTAL: $16.50", (50, 500), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    cv2.putText(img, "TAX: $1.65", (50, 530), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    cv2.putText(img, "TOTAL: $18.15", (50, 560), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    return img


def _create_delivery_note() -> np.ndarray:
    """Create a delivery note with table structure."""
    img = np.ones((700, 500, 3), dtype=np.uint8) * 255
    
    # Header
    cv2.putText(img, "DELIVERY NOTE", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 2)
    cv2.putText(img, "Delivery #: DEL-001", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    
    # Delivery info
    cv2.putText(img, "Delivered to: 123 Main Street", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    cv2.putText(img, "City: Anytown, ST 12345", (50, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    cv2.putText(img, "Date: 2024-01-15", (50, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    cv2.putText(img, "Time: 14:30", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    
    # Items delivered table
    cv2.putText(img, "Items Delivered:", (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 1)
    
    # Table structure
    table_y_start = 350
    table_x_start = 50
    table_width = 400
    table_height = 200
    
    # Draw table lines
    for y in range(0, table_height + 1, 50):
        cv2.line(img, (table_x_start, table_y_start + y), (table_x_start + table_width, table_y_start + y), (0, 0, 0), 1)
    
    for x in range(0, table_width + 1, 200):
        cv2.line(img, (table_x_start + x, table_y_start), (table_x_start + x, table_y_start + table_height), (0, 0, 0), 1)
    
    # Add items
    items = [
        ("Package 1", "Delivered"),
        ("Package 2", "Delivered"),
        ("Package 3", "Delivered"),
        ("Package 4", "Delivered")
    ]
    
    for i, (item, status) in enumerate(items):
        y = table_y_start + 30 + i * 50
        cv2.putText(img, item, (table_x_start + 10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
        cv2.putText(img, status, (table_x_start + 210, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    
    # Signature
    cv2.putText(img, "Signature: ________________", (50, 650), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    
    return img


def _create_handwritten_invoice() -> np.ndarray:
    """Create an invoice with handwritten annotations."""
    img = np.ones((800, 600, 3), dtype=np.uint8) * 255
    
    # Header
    cv2.putText(img, "INVOICE", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 2)
    cv2.putText(img, "Invoice #: 12345", (100, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    
    # Table with some irregular structure
    table_y_start = 200
    table_x_start = 50
    table_width = 500
    table_height = 300
    
    # Draw irregular table lines
    cv2.line(img, (table_x_start, table_y_start), (table_x_start + table_width, table_y_start), (0, 0, 0), 2)
    cv2.line(img, (table_x_start, table_y_start + 60), (table_x_start + table_width, table_y_start + 60), (0, 0, 0), 2)
    cv2.line(img, (table_x_start, table_y_start + 120), (table_x_start + table_width, table_y_start + 120), (0, 0, 0), 2)
    cv2.line(img, (table_x_start, table_y_start + 180), (table_x_start + table_width, table_y_start + 180), (0, 0, 0), 2)
    cv2.line(img, (table_x_start, table_y_start + 240), (table_x_start + table_width, table_y_start + 240), (0, 0, 0), 2)
    cv2.line(img, (table_x_start, table_y_start + 300), (table_x_start + table_width, table_y_start + 300), (0, 0, 0), 2)
    
    cv2.line(img, (table_x_start, table_y_start), (table_x_start, table_y_start + 300), (0, 0, 0), 2)
    cv2.line(img, (table_x_start + 200, table_y_start), (table_x_start + 200, table_y_start + 300), (0, 0, 0), 2)
    cv2.line(img, (table_x_start + 350, table_y_start), (table_x_start + 350, table_y_start + 300), (0, 0, 0), 2)
    cv2.line(img, (table_x_start + 500, table_y_start), (table_x_start + 500, table_y_start + 300), (0, 0, 0), 2)
    
    # Add content
    cv2.putText(img, "Item", (table_x_start + 10, table_y_start + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(img, "Description", (table_x_start + 210, table_y_start + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(img, "Price", (table_x_start + 360, table_y_start + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    # Add line items
    items = [
        ("1", "Widget A", "$10.00"),
        ("2", "Widget B", "$15.00"),
        ("3", "Widget C", "$20.00"),
        ("4", "Widget D", "$25.00")
    ]
    
    for row, (item, desc, price) in enumerate(items):
        y = table_y_start + 90 + row * 60
        cv2.putText(img, item, (table_x_start + 10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        cv2.putText(img, desc, (table_x_start + 210, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        cv2.putText(img, price, (table_x_start + 360, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    
    # Handwritten note
    cv2.putText(img, "Note: Please pay within 30 days", (50, 650), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    cv2.putText(img, "Thank you for your business!", (50, 680), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    
    return img


def main():
    """Main table extraction validation script."""
    parser = argparse.ArgumentParser(description="Validate table extraction functionality")
    parser.add_argument("--test-dir", type=Path, default=Path("tests/fixtures/table_extraction"),
                       help="Directory containing test documents")
    parser.add_argument("--output-dir", type=Path, default=Path("validation_output/table_extraction"),
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
    
    validator = TableExtractionValidationSuite(args.test_dir, args.output_dir)
    report = validator.run_validation()
    
    # Print summary
    summary = report["validation_summary"]
    LOGGER.info("=" * 60)
    LOGGER.info("TABLE EXTRACTION VALIDATION SUMMARY")
    LOGGER.info("=" * 60)
    LOGGER.info(f"Total documents: {summary['total_documents']}")
    LOGGER.info(f"Successful: {summary['successful']}")
    LOGGER.info(f"Failed: {summary['failed']}")
    LOGGER.info(f"Success rate: {summary['success_rate']:.1%}")
    
    if summary['successful'] > 0:
        metrics = report["table_extraction_metrics"]
        LOGGER.info(f"Total tables: {metrics['total_tables']}")
        LOGGER.info(f"Total line items: {metrics['total_line_items']}")
        LOGGER.info(f"Average processing time: {metrics['avg_processing_time']:.3f}s")
        LOGGER.info(f"Average confidence: {metrics['avg_confidence']:.3f}")
        LOGGER.info(f"Structure-aware usage: {metrics['structure_aware_usage']}")
        LOGGER.info(f"Fallback usage: {metrics['fallback_usage']}")
        
        LOGGER.info(f"Method usage: {report['method_usage']}")
        LOGGER.info(f"Field completion rates: {report['field_completion_rates']}")
    
    LOGGER.info("=" * 60)


if __name__ == "__main__":
    main()
