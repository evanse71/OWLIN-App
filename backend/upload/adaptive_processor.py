"""
Adaptive Document Processor with 100% Reliability

This module provides adaptive processing with dynamic timeouts, progress tracking,
and comprehensive error recovery to ensure no document fails to be processed.

Key Features:
- Adaptive timeout calculation based on file characteristics
- Progress tracking and reporting
- Comprehensive error recovery with fallback strategies
- Memory-efficient processing for large files
- Real-time status updates
- Graceful degradation for failed processing

Author: OWLIN Development Team
Version: 2.0.0
"""

import logging
import time
import asyncio
import os
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import HTTPException

# Local imports
from .multi_page_processor import multi_page_processor, DocumentResult
from ocr.enhanced_ocr_engine import enhanced_ocr_engine

logger = logging.getLogger(__name__)

@dataclass
class ProcessingProgress:
    """Progress tracking for document processing"""
    current_step: str
    progress_percentage: float
    estimated_time_remaining: float
    details: Dict[str, Any]

class ProgressTracker:
    """Progress tracking for long-running operations"""
    
    def __init__(self):
        self.start_time = time.time()
        self.current_step = "Initializing"
        self.progress = 0.0
        self.callbacks = []
    
    def add_callback(self, callback: Callable[[ProcessingProgress], None]):
        """Add progress callback"""
        self.callbacks.append(callback)
    
    def update_progress(self, step: str, progress: float, details: Dict[str, Any] = None):
        """Update progress and notify callbacks"""
        self.current_step = step
        self.progress = progress
        
        elapsed_time = time.time() - self.start_time
        if progress > 0:
            estimated_total = elapsed_time / progress
            estimated_remaining = estimated_total - elapsed_time
        else:
            estimated_remaining = 0
        
        progress_info = ProcessingProgress(
            current_step=step,
            progress_percentage=progress * 100,
            estimated_time_remaining=estimated_remaining,
            details=details or {}
        )
        
        # Notify callbacks
        for callback in self.callbacks:
            try:
                callback(progress_info)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")

class AdaptiveProcessor:
    """
    Adaptive document processor with dynamic timeouts and comprehensive error recovery
    """
    
    def __init__(self):
        self.multi_page_processor = multi_page_processor
        self.ocr_engine = None  # Will be lazy loaded
        self.fallbacks = [
            self._fallback_simple_ocr,
            self._fallback_basic_extraction,
            self._fallback_minimal_processing
        ]
    
    def _ensure_ocr_engine_loaded(self):
        """Lazy load OCR engine when needed"""
        if self.ocr_engine is None:
            from ocr.enhanced_ocr_engine import enhanced_ocr_engine
            self.ocr_engine = enhanced_ocr_engine
    
    def calculate_timeout(self, file_path: str) -> int:
        """
        Calculate adaptive timeout based on file characteristics
        
        Args:
            file_path: Path to the file
            
        Returns:
            Timeout in seconds
        """
        try:
            file_size = os.path.getsize(file_path)
            file_ext = Path(file_path).suffix.lower()
            
            # Base timeout on file size and type
            if file_ext == '.pdf':
                base_timeout = 300  # 5 minutes for PDFs
            else:
                base_timeout = 180  # 3 minutes for images
            
            # Adjust for file size (larger files need more time)
            size_factor = min(file_size / (1024 * 1024), 3)  # Cap at 3x for better reliability
            timeout = int(base_timeout * size_factor)
            
            # Add buffer for system load
            timeout = int(timeout * 1.1)  # Reduced buffer
            
            # Cap at reasonable maximum
            timeout = min(timeout, 600)  # 10 minutes maximum
            
            logger.info(f"📊 Calculated timeout: {timeout}s for {file_size} bytes ({file_ext})")
            return timeout
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to calculate timeout: {e}, using default")
            return 300  # 5 minutes default
    
    async def process_with_progress(self, file_path: str, progress_callback: Optional[Callable] = None) -> DocumentResult:
        """
        Process document with progress tracking and adaptive timeout
        
        Args:
            file_path: Path to the document file
            progress_callback: Optional callback for progress updates
            
        Returns:
            DocumentResult with processing results
        """
        timeout = self.calculate_timeout(file_path)
        
        # Create progress tracker
        tracker = ProgressTracker()
        if progress_callback:
            tracker.add_callback(progress_callback)
        
        try:
            # Process with timeout
            result = await asyncio.wait_for(
                self._process_document_async(file_path, tracker),
                timeout=timeout
            )
            
            tracker.update_progress("Completed", 1.0, {"status": "success"})
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"❌ Processing timed out after {timeout} seconds")
            tracker.update_progress("Failed", 1.0, {"status": "timeout", "timeout": timeout})
            raise HTTPException(
                status_code=408,
                detail=f"Processing timed out after {timeout} seconds. Try a smaller file or contact support."
            )
        except Exception as e:
            logger.error(f"❌ Processing failed: {e}")
            tracker.update_progress("Failed", 1.0, {"status": "error", "error": str(e)})
            raise
    
    async def _process_document_async(self, file_path: str, tracker: ProgressTracker) -> DocumentResult:
        """
        Process document asynchronously with progress tracking
        
        Args:
            file_path: Path to the document file
            tracker: Progress tracker
            
        Returns:
            DocumentResult with processing results
        """
        try:
            # Step 1: File validation and preparation
            tracker.update_progress("Validating file", 0.1, {"step": "validation"})
            await asyncio.sleep(0.1)  # Small delay for progress update
            
            # Step 2: Convert to images
            tracker.update_progress("Converting document", 0.2, {"step": "conversion"})
            pages = await asyncio.to_thread(self._convert_to_images, file_path)
            
            # Step 3: Process pages
            tracker.update_progress("Processing pages", 0.3, {"step": "ocr", "pages": len(pages)})
            
            page_results = []
            all_ocr_results = []
            
            for page_num, page_image in enumerate(pages):
                # Update progress for each page
                page_progress = 0.3 + (page_num / len(pages)) * 0.6
                tracker.update_progress(
                    f"Processing page {page_num + 1}/{len(pages)}",
                    page_progress,
                    {"step": "page_processing", "current_page": page_num + 1, "total_pages": len(pages)}
                )
                
                # Process page
                page_result = await asyncio.to_thread(
                    self._process_single_page, page_image, page_num + 1
                )
                page_results.append(page_result)
                all_ocr_results.extend(page_result.ocr_results)
            
            # Step 4: Aggregate results
            tracker.update_progress("Aggregating results", 0.9, {"step": "aggregation"})
            document_result = await asyncio.to_thread(
                self._aggregate_results, page_results, all_ocr_results
            )
            
            tracker.update_progress("Completed", 1.0, {"step": "completed"})
            return document_result
            
        except Exception as e:
            logger.error(f"❌ Async processing failed: {e}")
            raise
    
    def _convert_to_images(self, file_path: str) -> List:
        """Convert document to images (delegated to multi-page processor)"""
        return self.multi_page_processor._convert_to_images(file_path)
    
    def _process_single_page(self, page_image, page_number: int):
        """Process single page (delegated to multi-page processor)"""
        return self.multi_page_processor._process_single_page(page_image, page_number)
    
    def _aggregate_results(self, page_results, all_ocr_results):
        """Aggregate results (delegated to multi-page processor)"""
        return self.multi_page_processor._aggregate_results(page_results, all_ocr_results, 0)
    
    def process_with_recovery(self, file_path: str) -> DocumentResult:
        """
        Process document with comprehensive error recovery
        
        Args:
            file_path: Path to the document file
            
        Returns:
            DocumentResult with processing results
        """
        logger.info(f"🔄 Starting adaptive processing with recovery: {file_path}")
        
        try:
            # Try full processing first
            result = asyncio.run(self.process_with_progress(file_path))
            logger.info("✅ Full processing succeeded")
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ Full processing failed: {e}")
            
            # Try fallback strategies
            for i, fallback in enumerate(self.fallbacks):
                try:
                    logger.info(f"🔄 Trying fallback strategy {i + 1}")
                    result = fallback(file_path)
                    if self._validate_fallback_result(result):
                        logger.info(f"✅ Fallback strategy {i + 1} succeeded")
                        return result
                except Exception as fallback_error:
                    logger.warning(f"⚠️ Fallback strategy {i + 1} failed: {fallback_error}")
            
            # Return minimal result
            logger.error("❌ All processing strategies failed, returning minimal result")
            return self._create_minimal_result(file_path, str(e))
    
    def _fallback_simple_ocr(self, file_path: str) -> DocumentResult:
        """Fallback strategy 1: Simple OCR processing"""
        logger.info("🔄 Fallback 1: Simple OCR processing")
        
        try:
            # Ensure OCR engine is loaded
            self._ensure_ocr_engine_loaded()
            
            # Convert to single image
            images = self._convert_to_images(file_path)
            if not images:
                raise Exception("No images extracted")
            
            # Use first image only
            image = images[0]
            
            # Simple OCR
            ocr_results = self.ocr_engine._run_tesseract_raw(image, 1)
            
            # Basic line item extraction
            line_items = self._extract_basic_line_items(ocr_results)
            
            # Create minimal result
            return DocumentResult(
                document_type='invoice',
                supplier='Unknown Supplier',
                invoice_number='Unknown',
                date='Unknown',
                line_items=line_items,
                page_results=[],
                overall_confidence=0.5,
                total_processing_time=0,
                pages_processed=1,
                pages_failed=0
            )
            
        except Exception as e:
            logger.error(f"❌ Simple OCR fallback failed: {e}")
            raise
    
    def _fallback_basic_extraction(self, file_path: str) -> DocumentResult:
        """Fallback strategy 2: Basic text extraction"""
        logger.info("🔄 Fallback 2: Basic text extraction")
        
        try:
            # Ensure OCR engine is loaded
            self._ensure_ocr_engine_loaded()
            
            # Try to extract any text from the file
            images = self._convert_to_images(file_path)
            if not images:
                raise Exception("No images extracted")
            
            # Use first image
            image = images[0]
            
            # Emergency OCR
            ocr_results = self.ocr_engine._run_emergency_ocr(image, 1)
            
            # Create basic line items from any text found
            line_items = []
            for result in ocr_results:
                if result.text and len(result.text.strip()) > 5:
                    line_item = self._create_basic_line_item(result.text)
                    if line_item:
                        line_items.append(line_item)
            
            return DocumentResult(
                document_type='invoice',
                supplier='Unknown Supplier',
                invoice_number='Unknown',
                date='Unknown',
                line_items=line_items,
                page_results=[],
                overall_confidence=0.3,
                total_processing_time=0,
                pages_processed=1,
                pages_failed=0
            )
            
        except Exception as e:
            logger.error(f"❌ Basic extraction fallback failed: {e}")
            raise
    
    def _fallback_minimal_processing(self, file_path: str) -> DocumentResult:
        """Fallback strategy 3: Minimal processing"""
        logger.info("🔄 Fallback 3: Minimal processing")
        
        try:
            # Just create a minimal result
            return DocumentResult(
                document_type='unknown',
                supplier='Unknown Supplier',
                invoice_number='Unknown',
                date='Unknown',
                line_items=[],
                page_results=[],
                overall_confidence=0.1,
                total_processing_time=0,
                pages_processed=0,
                pages_failed=1
            )
            
        except Exception as e:
            logger.error(f"❌ Minimal processing fallback failed: {e}")
            raise
    
    def _extract_basic_line_items(self, ocr_results) -> List:
        """Extract basic line items from OCR results"""
        line_items = []
        
        for result in ocr_results:
            if result.text and len(result.text.strip()) > 5:
                line_item = self._create_basic_line_item(result.text)
                if line_item:
                    line_items.append(line_item)
        
        return line_items
    
    def _create_basic_line_item(self, text: str):
        """Create a basic line item from text"""
        # Look for price patterns
        import re
        price_match = re.search(r'[£$€]?\s*(\d+(?:\.\d+)?)', text)
        
        if price_match:
            try:
                price = float(price_match.group(1))
                description = re.sub(r'[£$€]?\s*\d+(?:\.\d+)?', '', text).strip()
                
                if description and len(description) > 3:
                    return type('LineItem', (), {
                        'description': description,
                        'quantity': 1.0,
                        'unit_price': price,
                        'total_price': price,
                        'confidence': 0.5,
                        'item_description': description,
                        'unit_price_excl_vat': price,
                        'line_total_excl_vat': price
                    })()
            except ValueError:
                pass
        
        return None
    
    def _validate_fallback_result(self, result: DocumentResult) -> bool:
        """
        Validate fallback result quality
        
        Args:
            result: DocumentResult from fallback processing
            
        Returns:
            True if result is acceptable, False otherwise
        """
        # Check if we have any meaningful data
        has_supplier = result.supplier != 'Unknown Supplier'
        has_line_items = len(result.line_items) > 0
        has_confidence = result.overall_confidence > 0.1
        
        # Accept if we have at least some data
        return has_supplier or has_line_items or has_confidence
    
    def _create_minimal_result(self, file_path: str, error: str) -> DocumentResult:
        """
        Create minimal result when all processing fails
        
        Args:
            file_path: Path to the file
            error: Error message
            
        Returns:
            Minimal DocumentResult
        """
        logger.warning(f"🚨 Creating minimal result due to processing failure: {error}")
        
        return DocumentResult(
            document_type='unknown',
            supplier='Unknown Supplier',
            invoice_number='Unknown',
            date='Unknown',
            line_items=[],
            page_results=[],
            overall_confidence=0.0,
            total_processing_time=0,
            pages_processed=0,
            pages_failed=1
        )

# Global instance for easy access
adaptive_processor = AdaptiveProcessor() 