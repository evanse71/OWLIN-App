"""
OCR-LLM Integration Module

This module provides seamless integration between the OCR pipeline with confidence
routing and the LLM pipeline for advanced interpretation and automation.
"""

from __future__ import annotations
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

# Import OCR pipeline components
from backend.normalization import FieldNormalizer, ConfidenceRoutingResult
from ..normalization.confidence_routing import ReviewCandidate

# Import LLM pipeline components
from .llm_pipeline import LLMPipeline, LLMPipelineResult, LLMPipelineManager
from .local_llm import LLMConfig, LLMProvider, LLMDevice

LOGGER = logging.getLogger("owlin.llm.ocr_llm_integration")


@dataclass
class OCRLLMResult:
    """Complete result of OCR-LLM integration processing."""
    # OCR Results
    normalization_result: Optional[Any] = None  # NormalizationResult
    confidence_routing_result: Optional[ConfidenceRoutingResult] = None
    
    # LLM Results
    llm_pipeline_result: Optional[LLMPipelineResult] = None
    
    # Integration Results
    final_invoice_card: Optional[Dict[str, Any]] = None
    review_queue: List[Dict[str, Any]] = field(default_factory=list)
    automation_artifacts: Dict[str, Any] = field(default_factory=dict)
    
    # Processing Metadata
    total_processing_time: float = 0.0
    success: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "normalization_result": self.normalization_result.to_dict() if self.normalization_result else None,
            "confidence_routing_result": {
                "overall_confidence": self.confidence_routing_result.overall_confidence,
                "auto_accepted_fields": self.confidence_routing_result.auto_accepted_fields,
                "review_candidates": [c.to_dict() for c in self.confidence_routing_result.review_candidates],
                "processing_time": self.confidence_routing_result.processing_time,
                "error_count": self.confidence_routing_result.error_count,
                "warning_count": self.confidence_routing_result.warning_count
            } if self.confidence_routing_result else None,
            "llm_pipeline_result": self.llm_pipeline_result.to_dict() if self.llm_pipeline_result else None,
            "final_invoice_card": self.final_invoice_card,
            "review_queue": self.review_queue,
            "automation_artifacts": self.automation_artifacts,
            "total_processing_time": self.total_processing_time,
            "success": self.success,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata
        }


class OCRLLMIntegration:
    """Complete integration between OCR pipeline and LLM pipeline."""
    
    def __init__(self, llm_configs: Optional[List[LLMConfig]] = None,
                 confidence_config: Optional[Dict[str, Any]] = None):
        """Initialize the OCR-LLM integration."""
        # Initialize OCR components
        self.field_normalizer = FieldNormalizer(confidence_config)
        
        # Initialize LLM components
        if llm_configs:
            self.llm_pipeline_manager = LLMPipelineManager(llm_configs)
        else:
            # Use default LLM configuration
            default_config = LLMConfig(
                model_path="models/llama-2-7b-chat.Q4_K_M.gguf",
                provider=LLMProvider.LLAMA_CPP,
                device=LLMDevice.AUTO
            )
            self.llm_pipeline_manager = LLMPipelineManager([default_config])
        
        LOGGER.info("OCR-LLM Integration initialized")
    
    def process_document(self, raw_ocr_data: Dict[str, Any],
                        context: Optional[Dict[str, Any]] = None,
                        enable_llm_processing: bool = True,
                        enable_automation: bool = True) -> OCRLLMResult:
        """
        Process a document through the complete OCR-LLM pipeline.
        
        Args:
            raw_ocr_data: Raw OCR extracted data
            context: Additional context information
            enable_llm_processing: Whether to run LLM processing
            enable_automation: Whether to run automation features
            
        Returns:
            OCRLLMResult with complete processing results
        """
        start_time = time.time()
        result = OCRLLMResult()
        
        try:
            LOGGER.info("Starting OCR-LLM document processing")
            
            # Step 1: OCR Processing with Confidence Routing
            LOGGER.info("Step 1: OCR processing with confidence routing")
            normalization_result, confidence_routing_result = self.field_normalizer.normalize_invoice_with_routing(
                raw_ocr_data, context
            )
            
            result.normalization_result = normalization_result
            result.confidence_routing_result = confidence_routing_result
            
            if not normalization_result.is_successful():
                result.errors.append("OCR normalization failed")
                result.total_processing_time = time.time() - start_time
                return result
            
            # Step 2: LLM Processing (if enabled)
            if enable_llm_processing:
                LOGGER.info("Step 2: LLM processing")
                
                # Prepare data for LLM
                llm_input = self._prepare_llm_input(
                    raw_ocr_data, confidence_routing_result, context
                )
                
                # Run LLM pipeline
                llm_result = self.llm_pipeline_manager.process_invoice(
                    ocr_data=llm_input["ocr_data"],
                    confidence_scores=llm_input["confidence_scores"],
                    review_candidates=llm_input["review_candidates"],
                    context=llm_input["context"],
                    enable_automation=enable_automation
                )
                
                result.llm_pipeline_result = llm_result
                
                if not llm_result.success:
                    result.warnings.append("LLM processing failed, using OCR results only")
            
            # Step 3: Integration and Final Processing
            LOGGER.info("Step 3: Integration and final processing")
            
            # Create final invoice card
            result.final_invoice_card = self._create_final_invoice_card(
                normalization_result, confidence_routing_result, result.llm_pipeline_result
            )
            
            # Create review queue
            result.review_queue = self._create_review_queue(confidence_routing_result)
            
            # Collect automation artifacts
            result.automation_artifacts = self._collect_automation_artifacts(result.llm_pipeline_result)
            
            # Calculate total processing time
            result.total_processing_time = time.time() - start_time
            result.success = True
            
            # Add metadata
            result.metadata = {
                "processing_timestamp": datetime.now().isoformat(),
                "ocr_processing_time": confidence_routing_result.processing_time,
                "llm_processing_time": result.llm_pipeline_result.processing_time if result.llm_pipeline_result else 0,
                "total_processing_time": result.total_processing_time,
                "llm_enabled": enable_llm_processing,
                "automation_enabled": enable_automation,
                "pipeline_version": "1.0.0"
            }
            
            LOGGER.info(f"OCR-LLM processing completed in {result.total_processing_time:.3f}s")
            return result
            
        except Exception as e:
            LOGGER.error(f"OCR-LLM processing failed: {e}")
            result.errors.append(f"Processing failed: {e}")
            result.total_processing_time = time.time() - start_time
            return result
    
    def _prepare_llm_input(self, raw_ocr_data: Dict[str, Any],
                          confidence_routing_result: ConfidenceRoutingResult,
                          context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare input data for LLM processing."""
        # Extract confidence scores
        confidence_scores = {}
        for routing_log in confidence_routing_result.routing_log:
            confidence_scores[routing_log.field_name] = routing_log.confidence_metrics.overall_confidence
        
        # Convert review candidates to LLM format
        review_candidates = []
        for candidate in confidence_routing_result.review_candidates:
            review_candidates.append({
                "field_name": candidate.field_name,
                "field_type": candidate.field_type,
                "raw_value": candidate.raw_value,
                "normalized_value": str(candidate.normalized_value) if candidate.normalized_value else None,
                "confidence": candidate.confidence_metrics.overall_confidence,
                "error_details": candidate.error_details,
                "suggestions": candidate.suggestions
            })
        
        # Prepare context
        llm_context = context or {}
        llm_context.update({
            "ocr_confidence": confidence_routing_result.overall_confidence,
            "auto_accepted_fields": confidence_routing_result.auto_accepted_fields,
            "review_candidates_count": len(confidence_routing_result.review_candidates)
        })
        
        return {
            "ocr_data": raw_ocr_data,
            "confidence_scores": confidence_scores,
            "review_candidates": review_candidates,
            "context": llm_context
        }
    
    def _create_final_invoice_card(self, normalization_result, confidence_routing_result,
                                 llm_pipeline_result: Optional[LLMPipelineResult]) -> Dict[str, Any]:
        """Create the final invoice card combining OCR and LLM results."""
        # Start with OCR results
        invoice_card = normalization_result.normalized_invoice.to_dict()
        
        # Add confidence routing information
        invoice_card["confidence_routing"] = {
            "overall_confidence": confidence_routing_result.overall_confidence,
            "auto_accepted_fields": confidence_routing_result.auto_accepted_fields,
            "needs_review": len(confidence_routing_result.review_candidates) > 0
        }
        
        # Enhance with LLM results if available
        if llm_pipeline_result and llm_pipeline_result.invoice_card:
            llm_card = llm_pipeline_result.invoice_card.invoice_card.to_dict()
            
            # Merge LLM enhancements
            for key, value in llm_card.items():
                if key not in ["llm_metadata"] and value is not None:
                    invoice_card[key] = value
            
            # Add LLM metadata
            invoice_card["llm_enhancement"] = {
                "applied": True,
                "model_used": llm_card.get("llm_metadata", {}).get("model_used", "unknown"),
                "confidence_improvement": llm_card.get("confidence", 0) - confidence_routing_result.overall_confidence
            }
        else:
            invoice_card["llm_enhancement"] = {"applied": False}
        
        return invoice_card
    
    def _create_review_queue(self, confidence_routing_result: ConfidenceRoutingResult) -> List[Dict[str, Any]]:
        """Create review queue from confidence routing results."""
        review_queue = []
        
        for candidate in confidence_routing_result.review_candidates:
            review_item = {
                "field_name": candidate.field_name,
                "field_type": candidate.field_type,
                "raw_value": candidate.raw_value,
                "normalized_value": str(candidate.normalized_value) if candidate.normalized_value else None,
                "confidence": candidate.confidence_metrics.overall_confidence,
                "error_details": candidate.error_details,
                "suggestions": candidate.suggestions,
                "priority": "high" if candidate.confidence_metrics.overall_confidence < 0.5 else "medium",
                "requires_human_review": True
            }
            review_queue.append(review_item)
        
        return review_queue
    
    def _collect_automation_artifacts(self, llm_pipeline_result: Optional[LLMPipelineResult]) -> Dict[str, Any]:
        """Collect automation artifacts from LLM processing."""
        artifacts = {}
        
        if llm_pipeline_result:
            if llm_pipeline_result.credit_request:
                artifacts["credit_request"] = llm_pipeline_result.credit_request.to_dict()
            
            if llm_pipeline_result.post_correction:
                artifacts["post_correction"] = llm_pipeline_result.post_correction.to_dict()
            
            if llm_pipeline_result.anomaly_detection:
                artifacts["anomaly_detection"] = llm_pipeline_result.anomaly_detection.to_dict()
        
        return artifacts
    
    def batch_process_documents(self, batch_data: List[Dict[str, Any]],
                               enable_llm_processing: bool = True,
                               enable_automation: bool = True) -> List[OCRLLMResult]:
        """Process multiple documents in batch."""
        results = []
        
        LOGGER.info(f"Starting batch OCR-LLM processing: {len(batch_data)} documents")
        
        for i, data in enumerate(batch_data):
            LOGGER.info(f"Processing batch item {i+1}/{len(batch_data)}")
            
            result = self.process_document(
                raw_ocr_data=data.get("raw_ocr_data", {}),
                context=data.get("context", {}),
                enable_llm_processing=enable_llm_processing,
                enable_automation=enable_automation
            )
            
            results.append(result)
        
        LOGGER.info(f"Batch OCR-LLM processing completed: {len(results)} results")
        return results
    
    def get_integration_stats(self, results: List[OCRLLMResult]) -> Dict[str, Any]:
        """Get statistics from batch processing results."""
        if not results:
            return {}
        
        total_time = sum(r.total_processing_time for r in results)
        successful = sum(1 for r in results if r.success)
        
        # Count automation features used
        credit_requests = sum(1 for r in results if r.automation_artifacts.get("credit_request"))
        post_corrections = sum(1 for r in results if r.automation_artifacts.get("post_correction"))
        anomaly_detections = sum(1 for r in results if r.automation_artifacts.get("anomaly_detection"))
        
        # Count review items
        total_review_items = sum(len(r.review_queue) for r in results)
        
        return {
            "total_documents": len(results),
            "successful_processing": successful,
            "success_rate": successful / len(results),
            "total_processing_time": total_time,
            "average_processing_time": total_time / len(results),
            "credit_requests_generated": credit_requests,
            "post_corrections_applied": post_corrections,
            "anomaly_detections": anomaly_detections,
            "total_review_items": total_review_items,
            "average_review_items_per_document": total_review_items / len(results),
            "automation_usage_rate": (credit_requests + post_corrections) / len(results)
        }
    
    def validate_integration(self) -> Dict[str, Any]:
        """Validate the integration configuration and components."""
        validation_results = {
            "ocr_components": {
                "field_normalizer": self.field_normalizer is not None,
                "confidence_routing": True  # Always available
            },
            "llm_components": self.llm_pipeline_manager.get_available_pipelines(),
            "integration_ready": False
        }
        
        # Check if at least one LLM pipeline is ready
        llm_ready = any(
            pipeline["pipeline_ready"] for pipeline in validation_results["llm_components"]
        )
        
        validation_results["integration_ready"] = (
            all(validation_results["ocr_components"].values()) and llm_ready
        )
        
        return validation_results
    
    def cleanup(self):
        """Clean up integration resources."""
        if hasattr(self.llm_pipeline_manager, 'cleanup'):
            self.llm_pipeline_manager.cleanup()
        LOGGER.info("OCR-LLM Integration cleaned up")



