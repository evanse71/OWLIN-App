"""
Intake Router - Bulletproof Ingestion v3

Main entry point for the bulletproof ingestion system. Orchestrates the entire
pipeline from file upload to canonical entity creation.
"""

import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path
import re

from .page_fingerprints import PageFingerprinter, PageFingerprint
from .page_classifier import PageClassifier, ClassificationResult
from .cross_file_stitcher import CrossFileStitcher, StitchGroup
from .deduper import Deduper, DuplicateGroup
from .canonical_builder import CanonicalBuilder, CanonicalInvoice, CanonicalDocument

logger = logging.getLogger(__name__)

@dataclass
class IntakeResult:
    """Result of the intake process"""
    success: bool
    canonical_invoices: List[CanonicalInvoice]
    canonical_documents: List[CanonicalDocument]
    duplicate_groups: List[DuplicateGroup]
    stitch_groups: List[StitchGroup]
    processing_time: float
    warnings: List[str]
    errors: List[str]
    metadata: Dict[str, Any]

@dataclass
class ProcessingStep:
    """Processing step information"""
    step_name: str
    status: str  # 'pending', 'running', 'completed', 'failed'
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration: Optional[float]
    details: Dict[str, Any]

class IntakeRouter:
    """Main intake router for bulletproof ingestion"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._load_config()
        self.fingerprinter = PageFingerprinter()
        self.classifier = PageClassifier()
        self.stitcher = CrossFileStitcher(self.config)
        self.deduper = Deduper(self.config)
        self.builder = CanonicalBuilder(self.config)
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            config_path = Path("data/config/ingestion_thresholds.json")
            if config_path.exists():
                with open(config_path, 'r') as f:
                    return json.load(f)
            else:
                logger.warning("Config file not found, using defaults")
                return {}
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}
    
    def process_upload(self, files: List[Dict[str, Any]]) -> IntakeResult:
        """
        Process uploaded files through the bulletproof ingestion pipeline
        
        Args:
            files: List of file data with paths, images, and OCR text
            
        Returns:
            IntakeResult object with all processing results
        """
        start_time = datetime.now()
        warnings = []
        errors = []
        
        try:
            logger.info(f"🚀 Starting bulletproof ingestion for {len(files)} files")
            
            # Step 1: Page fingerprinting
            step1 = self._process_step("Page Fingerprinting", lambda: self._fingerprint_pages(files))
            if not step1['success']:
                errors.append(f"Page fingerprinting failed: {step1['error']}")
                return self._create_failure_result(start_time, warnings, errors)
            
            pages = step1['result']
            logger.info(f"✅ Fingerprinted {len(pages)} pages")
            
            # Step 2: Page classification
            step2 = self._process_step("Page Classification", lambda: self._classify_pages(pages))
            if not step2['success']:
                errors.append(f"Page classification failed: {step2['error']}")
                return self._create_failure_result(start_time, warnings, errors)
            
            classified_pages = step2['result']
            logger.info(f"✅ Classified {len(classified_pages)} pages")
            
            # Step 3: Deduplication
            step3 = self._process_step("Deduplication", lambda: self._deduplicate_pages(classified_pages))
            if not step3['success']:
                errors.append(f"Deduplication failed: {step3['error']}")
                return self._create_failure_result(start_time, warnings, errors)
            
            dedup_groups = step3['result']
            logger.info(f"✅ Deduplicated into {len(dedup_groups)} groups")
            
            # Step 4: Cross-file stitching
            step4 = self._process_step("Cross-File Stitching", lambda: self._stitch_segments(classified_pages))
            if not step4['success']:
                errors.append(f"Cross-file stitching failed: {step4['error']}")
                return self._create_failure_result(start_time, warnings, errors)
            
            stitch_groups = step4['result']
            logger.info(f"✅ Created {len(stitch_groups)} stitch groups")
            
            # Step 5: Canonical entity building
            step5 = self._process_step("Canonical Building", lambda: self._build_canonical_entities(stitch_groups, classified_pages))
            if not step5['success']:
                errors.append(f"Canonical building failed: {step5['error']}")
                return self._create_failure_result(start_time, warnings, errors)
            
            canonical_invoices, canonical_documents = step5['result']
            logger.info(f"✅ Built {len(canonical_invoices)} canonical invoices and {len(canonical_documents)} canonical documents")
            
            # Step 6: Validate and finalize
            step6 = self._process_step("Validation", lambda: self._validate_results(canonical_invoices, canonical_documents))
            if not step6['success']:
                warnings.append(f"Validation warnings: {step6['error']}")
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return IntakeResult(
                success=True,
                canonical_invoices=canonical_invoices,
                canonical_documents=canonical_documents,
                duplicate_groups=dedup_groups,
                stitch_groups=stitch_groups,
                processing_time=processing_time,
                warnings=warnings,
                errors=errors,
                metadata={
                    'files_processed': len(files),
                    'pages_processed': len(pages),
                    'duplicates_found': sum(len(group.duplicates) for group in dedup_groups),
                    'stitch_groups_created': len(stitch_groups),
                    'canonical_entities_created': len(canonical_invoices) + len(canonical_documents)
                }
            )
            
        except Exception as e:
            error_msg = f"Intake processing failed: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            return self._create_failure_result(start_time, warnings, errors)
    
    def _process_step(self, step_name: str, step_func) -> Dict[str, Any]:
        """Execute a processing step with error handling"""
        start_time = datetime.now()
        logger.info(f"🔄 Starting {step_name}")
        
        try:
            result = step_func()
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"✅ {step_name} completed in {duration:.2f}s")
            return {
                'success': True,
                'result': result,
                'duration': duration,
                'error': None
            }
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            error_msg = str(e)
            logger.error(f"❌ {step_name} failed after {duration:.2f}s: {error_msg}")
            
            return {
                'success': False,
                'result': None,
                'duration': duration,
                'error': error_msg
            }
    
    def _fingerprint_pages(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fingerprint all pages from files"""
        pages = []
        
        for file_data in files:
            file_id = file_data.get('id', str(uuid.uuid4()))
            file_path = file_data.get('file_path', '')
            images = file_data.get('images', [])
            ocr_texts = file_data.get('ocr_texts', [])
            
            for i, (image, ocr_text) in enumerate(zip(images, ocr_texts)):
                page_id = f"{file_id}_page_{i}"
                
                # Compute fingerprint
                fingerprint = self.fingerprinter.compute_fingerprint(image, ocr_text)
                
                page_data = {
                    'id': page_id,
                    'file_id': file_id,
                    'file_path': file_path,
                    'page_index': i,
                    'image': image,
                    'text': ocr_text,
                    'fingerprint': fingerprint,
                    'upload_time': file_data.get('upload_time', datetime.now())
                }
                pages.append(page_data)
        
        return pages
    
    def _classify_pages(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Classify all pages by document type"""
        classified_pages = []
        
        for page_data in pages:
            fingerprint = page_data.get('fingerprint', None)
            text = page_data.get('text', '')
            
            # Extract image features
            image_features = None
            if fingerprint:
                image_features = {
                    'width': fingerprint.width,
                    'height': fingerprint.height,
                    'aspect_ratio': fingerprint.aspect_ratio
                }
            
            # Classify page
            classification = self.classifier.classify(text, image_features)
            
            # Add classification to page data
            page_data['doc_type'] = classification.doc_type
            page_data['classification_confidence'] = classification.confidence
            page_data['classification_features'] = classification.features
            page_data['classification_logits'] = classification.logits
            page_data['classification_method'] = classification.method
            
            classified_pages.append(page_data)
        
        return classified_pages
    
    def _deduplicate_pages(self, pages: List[Dict[str, Any]]) -> List[DuplicateGroup]:
        """Deduplicate pages"""
        return self.deduper.dedupe_pages(pages)
    
    def _stitch_segments(self, pages: List[Dict[str, Any]]) -> List[StitchGroup]:
        """Create segments and stitch them across files"""
        # Group pages by file first
        file_groups = {}
        for page in pages:
            file_id = page.get('file_id', 'unknown')
            if file_id not in file_groups:
                file_groups[file_id] = []
            file_groups[file_id].append(page)
        
        # Create segments from each file
        all_segments = []
        for file_id, file_pages in file_groups.items():
            segments = self._create_segments_from_pages(file_pages)
            all_segments.extend(segments)
        
        # Stitch segments across files
        return self.stitcher.stitch_segments(all_segments)
    
    def _create_segments_from_pages(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create segments from pages in a single file"""
        if not pages:
            return []
        
        # Sort pages by index
        pages.sort(key=lambda x: x.get('page_index', 0))
        
        segments = []
        current_segment = None
        
        for page in pages:
            # Check if this page starts a new segment
            if self._should_start_new_segment(page, current_segment):
                # Save current segment if exists
                if current_segment:
                    segments.append(current_segment)
                
                # Start new segment
                current_segment = {
                    'id': f"seg_{len(segments)}",
                    'file_id': page.get('file_id'),
                    'doc_type': page.get('doc_type', 'other'),
                    'pages': [page],
                    'page_numbers': [page.get('page_index', 0)],
                    'text': page.get('text', ''),
                    'supplier_guess': self._extract_supplier_guess(page.get('text', '')),
                    'phash': page.get('fingerprint', PageFingerprint("", "", "", "", 0, 0, 0.0, {})).phash,
                    'header_simhash': page.get('fingerprint', PageFingerprint("", "", "", "", 0, 0, 0.0, {})).header_simhash,
                    'footer_simhash': page.get('fingerprint', PageFingerprint("", "", "", "", 0, 0, 0.0, {})).footer_simhash,
                    'upload_time': page.get('upload_time', datetime.now())
                }
            else:
                # Add page to current segment
                if current_segment:
                    current_segment['pages'].append(page)
                    current_segment['page_numbers'].append(page.get('page_index', 0))
                    current_segment['text'] += f"\n--- PAGE {page.get('page_index', 0)} ---\n{page.get('text', '')}"
        
        # Add final segment
        if current_segment:
            segments.append(current_segment)
        
        return segments
    
    def _should_start_new_segment(self, page: Dict[str, Any], current_segment: Optional[Dict[str, Any]]) -> bool:
        """Determine if a page should start a new segment"""
        if not current_segment:
            return True
        
        # Check for document type change
        if page.get('doc_type') != current_segment.get('doc_type'):
            return True
        
        # Check for supplier change
        page_supplier = self._extract_supplier_guess(page.get('text', ''))
        current_supplier = current_segment.get('supplier_guess', '')
        if page_supplier and current_supplier and page_supplier != current_supplier:
            return True
        
        # Check for totals block (end of invoice)
        text_lower = page.get('text', '').lower()
        if any(keyword in text_lower for keyword in ['total', 'amount due', 'grand total', 'final total']):
            return False  # This is likely the end of a segment
        
        return False
    
    def _extract_supplier_guess(self, text: str) -> str:
        """Extract supplier name from text"""
        patterns = [
            r'\b([A-Z][A-Z\s&\.]+(?:LTD|LIMITED|INC|CORP|LLC|CO|COMPANY))\b',
            r'^(?:from|supplier|company):\s*([A-Za-z\s&\.]+)',
            r'\b([A-Z][A-Z\s&\.]{3,20})\s+(?:invoice|delivery|receipt)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0].strip()
        
        return ""
    
    def _build_canonical_entities(self, stitch_groups: List[StitchGroup], pages: List[Dict[str, Any]]) -> Tuple[List[CanonicalInvoice], List[CanonicalDocument]]:
        """Build canonical entities from stitch groups"""
        return self.builder.build_canonical_entities(stitch_groups, pages)
    
    def _validate_results(self, canonical_invoices: List[CanonicalInvoice], canonical_documents: List[CanonicalDocument]) -> bool:
        """Validate the final results"""
        # Basic validation
        for invoice in canonical_invoices:
            if not invoice.supplier_name:
                logger.warning(f"Invoice {invoice.canonical_id} missing supplier name")
            if not invoice.invoice_number:
                logger.warning(f"Invoice {invoice.canonical_id} missing invoice number")
            if invoice.total_amount <= 0:
                logger.warning(f"Invoice {invoice.canonical_id} has invalid total amount")
        
        return True
    
    def _create_failure_result(self, start_time: datetime, warnings: List[str], errors: List[str]) -> IntakeResult:
        """Create a failure result"""
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return IntakeResult(
            success=False,
            canonical_invoices=[],
            canonical_documents=[],
            duplicate_groups=[],
            stitch_groups=[],
            processing_time=processing_time,
            warnings=warnings,
            errors=errors,
            metadata={'error': 'Processing failed'}
        ) 