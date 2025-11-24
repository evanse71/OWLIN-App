"""
Invoice Card Generator using Local LLM

This module provides LLM-powered invoice card generation from OCR artifacts
with confidence routing and review candidate integration.
"""

from __future__ import annotations
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from datetime import date, datetime
from decimal import Decimal

from .local_llm import LocalLLMInterface, LLMResult
from .prompt_templates import PromptTemplates, PromptType

LOGGER = logging.getLogger("owlin.llm.invoice_card_generator")


@dataclass
class InvoiceCardSchema:
    """Schema for invoice card output."""
    supplier_name: str
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    currency: Optional[str] = None
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    total_amount: Optional[float] = None
    line_items: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    needs_review: bool = False
    review_reasons: List[str] = field(default_factory=list)
    llm_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "supplier_name": self.supplier_name,
            "invoice_number": self.invoice_number,
            "invoice_date": self.invoice_date,
            "currency": self.currency,
            "subtotal": self.subtotal,
            "tax_amount": self.tax_amount,
            "total_amount": self.total_amount,
            "line_items": self.line_items,
            "confidence": self.confidence,
            "needs_review": self.needs_review,
            "review_reasons": self.review_reasons,
            "llm_metadata": self.llm_metadata
        }
    
    def validate(self) -> List[str]:
        """Validate the invoice card schema."""
        errors = []
        
        if not self.supplier_name:
            errors.append("Supplier name is required")
        
        if self.total_amount is not None and self.total_amount <= 0:
            errors.append("Total amount must be positive")
        
        if self.invoice_date:
            try:
                datetime.fromisoformat(self.invoice_date)
            except ValueError:
                errors.append("Invalid date format")
        
        return errors


@dataclass
class InvoiceCardResult:
    """Result of invoice card generation."""
    invoice_card: InvoiceCardSchema
    llm_result: LLMResult
    processing_time: float
    success: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "invoice_card": self.invoice_card.to_dict(),
            "llm_result": self.llm_result.to_dict(),
            "processing_time": self.processing_time,
            "success": self.success,
            "errors": self.errors,
            "warnings": self.warnings
        }


class InvoiceCardGenerator:
    """Generator for invoice cards using local LLM."""
    
    def __init__(self, llm_interface: LocalLLMInterface):
        """Initialize with LLM interface."""
        self.llm = llm_interface
        self.prompt_templates = PromptTemplates()
        
        LOGGER.info("Invoice Card Generator initialized")
    
    def generate_invoice_card(self, ocr_data: Dict[str, Any],
                            confidence_scores: Dict[str, float],
                            review_candidates: List[Dict[str, Any]],
                            context: Optional[Dict[str, Any]] = None) -> InvoiceCardResult:
        """
        Generate an invoice card from OCR data using LLM.
        
        Args:
            ocr_data: Raw OCR extracted data
            confidence_scores: Confidence scores for each field
            review_candidates: Fields that need human review
            context: Additional context information
            
        Returns:
            InvoiceCardResult with generated invoice card
        """
        start_time = time.time()
        
        try:
            # Format prompt
            prompt = self.prompt_templates.format_invoice_card_prompt(
                ocr_data=ocr_data,
                confidence_scores=confidence_scores,
                review_candidates=review_candidates
            )
            
            # Generate with LLM
            llm_result = self.llm.generate(prompt)
            
            if not llm_result.success:
                return InvoiceCardResult(
                    invoice_card=InvoiceCardSchema(supplier_name="Unknown"),
                    llm_result=llm_result,
                    processing_time=time.time() - start_time,
                    success=False,
                    errors=[f"LLM generation failed: {llm_result.error_message}"]
                )
            
            # Parse LLM output
            invoice_card = self._parse_llm_output(llm_result.text)
            
            # Validate result
            validation_errors = invoice_card.validate()
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Create result
            result = InvoiceCardResult(
                invoice_card=invoice_card,
                llm_result=llm_result,
                processing_time=processing_time,
                success=len(validation_errors) == 0,
                errors=validation_errors
            )
            
            # Add LLM metadata
            invoice_card.llm_metadata = {
                "model_used": llm_result.model_used,
                "provider": llm_result.provider,
                "device": llm_result.device,
                "tokens_generated": llm_result.tokens_generated,
                "inference_time": llm_result.inference_time,
                "generation_timestamp": datetime.now().isoformat()
            }
            
            LOGGER.info(f"Invoice card generated successfully in {processing_time:.3f}s")
            return result
            
        except Exception as e:
            LOGGER.error(f"Invoice card generation failed: {e}")
            return InvoiceCardResult(
                invoice_card=InvoiceCardSchema(supplier_name="Unknown"),
                llm_result=LLMResult(
                    text="",
                    tokens_generated=0,
                    inference_time=0.0,
                    model_used="none",
                    provider="none",
                    device="none",
                    success=False,
                    error_message=str(e)
                ),
                processing_time=time.time() - start_time,
                success=False,
                errors=[f"Generation failed: {e}"]
            )
    
    def _parse_llm_output(self, llm_text: str) -> InvoiceCardSchema:
        """Parse LLM output into invoice card schema."""
        try:
            # Extract JSON from LLM output
            json_start = llm_text.find('{')
            json_end = llm_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in LLM output")
            
            json_text = llm_text[json_start:json_end]
            data = json.loads(json_text)
            
            # Create invoice card from parsed data
            invoice_card = InvoiceCardSchema(
                supplier_name=data.get("supplier_name", "Unknown"),
                invoice_number=data.get("invoice_number"),
                invoice_date=data.get("invoice_date"),
                currency=data.get("currency"),
                subtotal=data.get("subtotal"),
                tax_amount=data.get("tax_amount"),
                total_amount=data.get("total_amount"),
                line_items=data.get("line_items", []),
                confidence=data.get("confidence", 0.0),
                needs_review=data.get("needs_review", False),
                review_reasons=data.get("review_reasons", [])
            )
            
            return invoice_card
            
        except json.JSONDecodeError as e:
            LOGGER.error(f"Failed to parse LLM JSON output: {e}")
            # Try to extract basic information from text
            return self._extract_basic_info(llm_text)
        except Exception as e:
            LOGGER.error(f"Failed to parse LLM output: {e}")
            return InvoiceCardSchema(supplier_name="Unknown")
    
    def _extract_basic_info(self, text: str) -> InvoiceCardSchema:
        """Extract basic information from unstructured text."""
        # Simple extraction logic for fallback
        supplier_name = "Unknown"
        total_amount = None
        
        # Look for supplier patterns
        if "supplier" in text.lower():
            lines = text.split('\n')
            for line in lines:
                if "supplier" in line.lower():
                    parts = line.split(':')
                    if len(parts) > 1:
                        supplier_name = parts[1].strip()
                        break
        
        # Look for amount patterns
        import re
        amount_pattern = r'[£$€]\s*(\d+(?:\.\d{2})?)'
        amounts = re.findall(amount_pattern, text)
        if amounts:
            try:
                total_amount = float(amounts[-1])  # Use last amount found
            except ValueError:
                pass
        
        return InvoiceCardSchema(
            supplier_name=supplier_name,
            total_amount=total_amount,
            needs_review=True,
            review_reasons=["LLM output parsing failed, manual review required"]
        )
    
    def batch_generate(self, batch_data: List[Dict[str, Any]]) -> List[InvoiceCardResult]:
        """Generate multiple invoice cards in batch."""
        results = []
        
        for i, data in enumerate(batch_data):
            LOGGER.info(f"Processing batch item {i+1}/{len(batch_data)}")
            
            result = self.generate_invoice_card(
                ocr_data=data.get("ocr_data", {}),
                confidence_scores=data.get("confidence_scores", {}),
                review_candidates=data.get("review_candidates", []),
                context=data.get("context", {})
            )
            
            results.append(result)
        
        LOGGER.info(f"Batch processing completed: {len(results)} results")
        return results
    
    def get_generation_stats(self, results: List[InvoiceCardResult]) -> Dict[str, Any]:
        """Get statistics from batch generation results."""
        if not results:
            return {}
        
        total_time = sum(r.processing_time for r in results)
        successful = sum(1 for r in results if r.success)
        total_llm_time = sum(r.llm_result.inference_time for r in results)
        
        return {
            "total_documents": len(results),
            "successful_generations": successful,
            "success_rate": successful / len(results),
            "total_processing_time": total_time,
            "average_processing_time": total_time / len(results),
            "total_llm_time": total_llm_time,
            "average_llm_time": total_llm_time / len(results),
            "llm_efficiency": total_llm_time / total_time if total_time > 0 else 0
        }
