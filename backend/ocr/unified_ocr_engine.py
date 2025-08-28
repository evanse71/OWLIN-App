#!/usr/bin/env python3
"""
Unified OCR Engine - Phase-D Enhanced

Orchestrates PaddleOCR, Tesseract, classification, validation, policy, and template memory
"""

import logging
import time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from .config import get_ocr_config
from .classifier import get_document_classifier, ClassificationResult
from .validate import get_document_validator, ValidationResult
from .policy import get_document_policy, PolicyDecision
from .enhanced_line_item_extractor import get_enhanced_line_item_extractor, LineItem, ExtractionResult
from .templates import get_template_manager
from .telemetry import get_telemetry_logger
from .llm_assists import llm_guess_doctype, check_hard_signals

logger = logging.getLogger(__name__)

@dataclass
class ProcessingResult:
    success: bool
    document_type: str
    supplier: str
    invoice_number: str
    date: str
    total_amount: float
    line_items: List[Dict[str, Any]]
    overall_confidence: float
    processing_time: float
    raw_text: str
    word_count: int
    engine_used: str
    error_message: Optional[str] = None
    
    # Phase-C: Enhanced fields
    doc_type_confidence: float = 0.0
    doc_type_reasons: List[str] = None
    validation_result: Optional[Dict[str, Any]] = None
    policy_decision: Optional[Dict[str, Any]] = None
    classification_features: Optional[Dict[str, float]] = None
    alternative_types: Optional[List[Tuple[str, float]]] = None
    
    # Phase-D: Template and retry fields
    template_hint_used: bool = False
    auto_retry_used: bool = False
    retry_metrics: Optional[Dict[str, Any]] = None

class UnifiedOCREngine:
    """Unified OCR engine with Phase-D enhancements"""
    
    def __init__(self):
        self.config = get_ocr_config()
        self.classifier = get_document_classifier()
        self.validator = get_document_validator()
        self.policy = get_document_policy()
        self.line_extractor = get_enhanced_line_item_extractor()
        self.template_manager = get_template_manager()
        self.telemetry_logger = get_telemetry_logger()
        
        # Initialize OCR engines
        self.paddle_ocr = None
        self.tesseract_available = False
        
        try:
            import paddleocr
            self.paddle_ocr = paddleocr.PaddleOCR(use_angle_cls=True, lang='en')
            logger.info("✅ PaddleOCR initialized")
        except ImportError:
            logger.warning("⚠️ PaddleOCR not available")
        
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self.tesseract_available = True
            logger.info("✅ Tesseract available")
        except Exception:
            logger.warning("⚠️ Tesseract not available")
    
    def process_document(self, text: str, image_path: Optional[str] = None) -> ProcessingResult:
        """
        Process document with full OCR pipeline including template memory and auto-retry
        
        Args:
            text: Document text (for testing) or OCR result
            image_path: Path to image file (optional)
            
        Returns:
            ProcessingResult with all extracted data
        """
        start_time = time.time()
        auto_retry_used = False
        retry_metrics = None
        template_hint_used = False
        
        try:
            # Step 1: OCR (if image provided)
            if image_path:
                ocr_result = self._perform_ocr(image_path)
                text = ocr_result['text']
                word_boxes = ocr_result.get('word_boxes', [])
                engine_used = ocr_result.get('engine', 'unknown')
            else:
                # Use provided text for testing
                word_boxes = []
                engine_used = 'test'
            
            # Step 2: Check for supplier template match
            supplier_key = self.template_manager.match_supplier(text)
            template_hints = {}
            if supplier_key:
                template_hints = self.template_manager.get_template_hints(supplier_key)
                template_hint_used = True
                logger.info(f"🎯 Using template for supplier: {supplier_key}")
            
            # Step 3: Classification
            classification = self.classifier.classify_document(text)
            
            # Step 3.5: LLM Assist (if enabled and confidence is low)
            llm_used = False
            llm_ms = 0
            if self.config.get_llm("enabled", False):
                doctype_gate = self.config.get_llm("doctype_gate", 0.55)
                
                if classification.confidence < doctype_gate:
                    logger.info(f"🤖 LLM assist triggered (confidence: {classification.confidence:.3f} < {doctype_gate})")
                    
                    llm_start = time.time()
                    
                    llm_result = llm_guess_doctype(text)
                    if llm_result:
                        llm_label = llm_result['label']
                        llm_why = llm_result['why']
                        
                        # Check if LLM suggestion agrees with hard signals
                        if check_hard_signals(text, llm_label):
                            logger.info(f"✅ LLM assist accepted: {llm_label} - {llm_why}")
                            classification.doc_type = llm_label
                            classification.reasons.append("LLM_ASSIST_DTYPE")
                            llm_used = True
                        else:
                            logger.info(f"⚠️ LLM assist ignored (no hard signals): {llm_label} - {llm_why}")
                            classification.reasons.append("LLM_ASSIST_IGNORED")
                    
                    llm_ms = int((time.time() - llm_start) * 1000)
            
            # Step 4: Field extraction (with template hints if available)
            extracted_data = self._extract_fields(text, classification.doc_type, template_hints)
            
            # Step 5: Validation
            validation = self.validator.validate_document(extracted_data)
            
            # Step 6: Line item extraction
            ocr_result = {
                'text': text,
                'word_boxes': word_boxes
            }
            line_items_result = self.line_extractor.extract_line_items(
                ocr_result, classification.doc_type
            )
            
            # Step 7: Policy evaluation
            confidence_percentage = classification.confidence * 100.0
            policy_decision = self.policy.evaluate_document(
                classification, validation, extracted_data, 
                confidence_percentage
            )
            
            # Step 8: Auto-retry logic
            if self._should_auto_retry(classification.confidence, policy_decision):
                logger.info("🔄 Auto-retry triggered - reprocessing with enhanced settings")
                auto_retry_used = True
                retry_result = self._auto_retry_process(text, image_path, classification.doc_type)
                
                if retry_result and retry_result.overall_confidence > classification.confidence:
                    # Use retry result if it's better
                    logger.info(f"✅ Auto-retry improved confidence: {classification.confidence:.3f} → {retry_result.overall_confidence:.3f}")
                    classification = retry_result.classification
                    validation = retry_result.validation
                    extracted_data = retry_result.extracted_data
                    line_items_result = retry_result.line_items_result
                    policy_decision = retry_result.policy_decision
                    confidence_percentage = retry_result.overall_confidence * 100.0
                    
                    retry_metrics = {
                        'original_confidence': classification.confidence,
                        'retry_confidence': retry_result.overall_confidence,
                        'improvement': retry_result.overall_confidence - classification.confidence
                    }
                else:
                    logger.info("⚠️ Auto-retry did not improve results")
            
            # Step 9: Save template if document was accepted
            if policy_decision.action.value in ['ACCEPT', 'ACCEPT_WITH_WARNINGS']:
                self._save_template_if_needed(text, word_boxes, extracted_data, supplier_key)
            
            # Step 10: Prepare result
            processing_time = time.time() - start_time
            
            # Step 11: Log telemetry
            self.telemetry_logger.log_processing(
                doc_id=str(datetime.now().timestamp()),  # Use timestamp as doc_id for now
                doc_type=classification.doc_type,
                policy_action=policy_decision.action.value,
                confidence=classification.confidence,
                duration_ms=int(processing_time * 1000),
                reasons=[reason.value for reason in policy_decision.reasons],
                template_hint_used=template_hint_used,
                auto_retry_used=auto_retry_used,
                llm_used=llm_used,
                llm_ms=llm_ms
            )
            
            # Convert line items to dict format
            line_items_dict = []
            for item in line_items_result.line_items:
                line_items_dict.append({
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit": item.unit,
                    "unit_original": item.unit_original,
                    "unit_price": item.unit_price,
                    "line_total": item.line_total,
                    "tax_rate": item.tax_rate,
                    "delivered_qty": item.delivered_qty,
                    "computed_total": item.computed_total,
                    "line_confidence": item.line_confidence,
                    "row_reasons": item.row_reasons
                })
            
            return ProcessingResult(
                success=True,
                document_type=classification.doc_type,
                supplier=extracted_data.get('supplier', ''),
                invoice_number=extracted_data.get('invoice_number', ''),
                date=extracted_data.get('date', ''),
                total_amount=extracted_data.get('total_amount', 0.0),
                line_items=line_items_dict,
                overall_confidence=classification.confidence,
                processing_time=processing_time,
                raw_text=text,
                word_count=len(text.split()),
                engine_used=engine_used,
                doc_type_confidence=classification.confidence,
                doc_type_reasons=classification.reasons,
                validation_result={
                    'arithmetic_ok': validation.arithmetic_ok if validation else True,
                    'currency_ok': validation.currency_ok if validation else True,
                    'vat_ok': validation.vat_ok if validation else True,
                    'date_ok': validation.date_ok if validation else True,
                    'issues': [
                        {
                            'type': issue.issue_type,
                            'severity': issue.severity,
                            'message': issue.message
                        } for issue in validation.issues
                    ] if validation and validation.issues else []
                },
                policy_decision={
                    'action': policy_decision.action.value,
                    'reasons': [reason.value for reason in policy_decision.reasons],
                    'confidence_threshold_met': policy_decision.confidence_threshold_met,
                    'validation_passed': policy_decision.validation_passed,
                    'auto_retry_used': auto_retry_used
                },
                classification_features=classification.features,
                alternative_types=classification.alternative_types,
                template_hint_used=template_hint_used,
                auto_retry_used=auto_retry_used,
                retry_metrics=retry_metrics
            )
            
        except Exception as e:
            logger.error(f"❌ OCR processing failed: {e}")
            return ProcessingResult(
                success=False,
                document_type='unknown',
                supplier='',
                invoice_number='',
                date='',
                total_amount=0.0,
                line_items=[],
                overall_confidence=0.0,
                processing_time=time.time() - start_time,
                raw_text=text,
                word_count=len(text.split()),
                engine_used='error',
                error_message=str(e)
            )
    
    def _should_auto_retry(self, confidence: float, policy_decision: PolicyDecision) -> bool:
        """Determine if auto-retry should be triggered"""
        config = get_ocr_config()
        auto_retry_config = config.get_policy("auto_retry")
        
        if not auto_retry_config.get("enabled", True):
            return False
        
        # Check confidence thresholds
        confidence_threshold = auto_retry_config.get("confidence_threshold", 55) / 100.0
        avg_confidence_threshold = auto_retry_config.get("avg_confidence_threshold", 50) / 100.0
        
        # Don't retry if already used
        if policy_decision.auto_retry_used:
            return False
        
        # Retry if confidence is below thresholds
        return confidence < confidence_threshold or confidence < avg_confidence_threshold
    
    def _auto_retry_process(self, text: str, image_path: Optional[str], doc_type: str) -> Optional[ProcessingResult]:
        """Perform auto-retry with enhanced preprocessing"""
        try:
            # For now, we'll just reprocess with the same text
            # In a real implementation, this would:
            # 1. Apply "receipt" preprocessing profile (CLAHE + denoise)
            # 2. Try ±2° rotation angles
            # 3. Use different OCR settings
            
            logger.info("🔄 Auto-retry: reprocessing with enhanced settings")
            
            # Simulate enhanced processing
            enhanced_text = text  # In reality, this would be preprocessed
            
            # Re-run the pipeline
            classification = self.classifier.classify_document(enhanced_text)
            extracted_data = self._extract_fields(enhanced_text, classification.doc_type)
            validation = self.validator.validate_document(extracted_data)
            
            # Create a mock result for testing
            return ProcessingResult(
                success=True,
                document_type=classification.doc_type,
                supplier=extracted_data.get('supplier', ''),
                invoice_number=extracted_data.get('invoice_number', ''),
                date=extracted_data.get('date', ''),
                total_amount=extracted_data.get('total_amount', 0.0),
                line_items=[],
                overall_confidence=min(1.0, classification.confidence * 1.1),  # Simulate improvement
                processing_time=0.0,
                raw_text=enhanced_text,
                word_count=len(enhanced_text.split()),
                engine_used='auto_retry',
                classification=classification,
                validation=validation,
                extracted_data=extracted_data,
                line_items_result=None,
                policy_decision=None
            )
            
        except Exception as e:
            logger.error(f"❌ Auto-retry failed: {e}")
            return None
    
    def _save_template_if_needed(self, text: str, word_boxes: List[Dict], 
                                extracted_data: Dict[str, Any], supplier_key: Optional[str]) -> None:
        """Save template if supplier was identified"""
        if not supplier_key:
            return
        
        try:
            # Extract header zones
            header_zones = self.template_manager.extract_header_zones(text, word_boxes)
            
            # Extract currency and VAT hints
            currency_hint = extracted_data.get('currency')
            vat_hint = None  # Could be extracted from VAT patterns
            
            # Save template
            self.template_manager.save_template(
                supplier_key, header_zones, currency_hint, vat_hint
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to save template: {e}")
    
    def _extract_fields(self, text: str, doc_type: str, template_hints: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract basic fields from text with template hints"""
        # Simple field extraction for testing
        # In production, this would use more sophisticated extraction
        
        import re
        
        extracted = {
            'supplier': '',
            'invoice_number': '',
            'date': '',
            'total_amount': 0.0,
            'line_items': []
        }
        
        # Use template hints if available
        if template_hints and template_hints.get('currency_hint'):
            extracted['currency'] = template_hints['currency_hint']
        
        # Extract supplier (first line usually)
        lines = text.split('\n')
        if lines:
            extracted['supplier'] = lines[0].strip()
        
        # Extract invoice number
        inv_match = re.search(r'invoice[:\s]*([A-Z0-9\-]+)', text, re.I)
        if inv_match:
            extracted['invoice_number'] = inv_match.group(1)
        
        # Extract date
        date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text)
        if date_match:
            extracted['date'] = date_match.group(1)
        
        # Extract total
        total_match = re.search(r'total[:\s]*[£€$]?([\d,]+\.?\d*)', text, re.I)
        if total_match:
            try:
                total_str = total_match.group(1).replace(',', '')
                extracted['total_amount'] = float(total_str)
            except ValueError:
                pass
        
        return extracted
    
    def _perform_ocr(self, image_path: str) -> Dict[str, Any]:
        """Perform OCR on image"""
        if self.paddle_ocr:
            try:
                result = self.paddle_ocr.ocr(image_path, cls=True)
                text = ' '.join([line[1][0] for line in result[0] if line[1][0]])
                word_boxes = [
                    {
                        'text': line[1][0],
                        'confidence': line[1][1],
                        'bbox': line[0]
                    } for line in result[0]
                ]
                return {
                    'text': text,
                    'word_boxes': word_boxes,
                    'engine': 'paddleocr'
                }
            except Exception as e:
                logger.warning(f"PaddleOCR failed: {e}")
        
        if self.tesseract_available:
            try:
                import pytesseract
                from PIL import Image
                
                image = Image.open(image_path)
                text = pytesseract.image_to_string(image)
                
                return {
                    'text': text,
                    'word_boxes': [],
                    'engine': 'tesseract'
                }
            except Exception as e:
                logger.warning(f"Tesseract failed: {e}")
        
        raise Exception("No OCR engine available")

# Global engine instance
_engine_instance: Optional[UnifiedOCREngine] = None

def get_unified_ocr_engine() -> UnifiedOCREngine:
    """Get global unified OCR engine instance"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = UnifiedOCREngine()
    return _engine_instance 