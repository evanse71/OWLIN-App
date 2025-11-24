"""
LLM Pipeline for End-to-End Processing

This module provides a complete LLM pipeline that integrates with the OCR
and confidence routing system to provide advanced interpretation and automation.
"""

from __future__ import annotations
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from .local_llm import LocalLLMInterface, LLMConfig, LLMProvider, LLMDevice
from .invoice_card_generator import InvoiceCardGenerator, InvoiceCardResult
from .automation_features import CreditRequestGenerator, PostCorrectionEngine, AnomalyDetector
from .prompt_templates import PromptTemplates

LOGGER = logging.getLogger("owlin.llm.llm_pipeline")


@dataclass
class LLMPipelineResult:
    """Complete result of LLM pipeline processing."""
    invoice_card: Optional[InvoiceCardResult] = None
    credit_request: Optional[Any] = None  # CreditRequest
    post_correction: Optional[Any] = None  # PostCorrection
    anomaly_detection: Optional[Any] = None  # AnomalyDetection
    processing_time: float = 0.0
    success: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "invoice_card": self.invoice_card.to_dict() if self.invoice_card else None,
            "credit_request": self.credit_request.to_dict() if self.credit_request else None,
            "post_correction": self.post_correction.to_dict() if self.post_correction else None,
            "anomaly_detection": self.anomaly_detection.to_dict() if self.anomaly_detection else None,
            "processing_time": self.processing_time,
            "success": self.success,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata
        }


class LLMPipeline:
    """Complete LLM pipeline for invoice processing."""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize the LLM pipeline."""
        self.config = config or self._create_default_config()
        self.llm_interface = LocalLLMInterface(self.config)
        
        # Initialize components
        self.invoice_card_generator = InvoiceCardGenerator(self.llm_interface)
        self.credit_request_generator = CreditRequestGenerator(self.llm_interface)
        self.post_correction_engine = PostCorrectionEngine(self.llm_interface)
        self.anomaly_detector = AnomalyDetector(self.llm_interface)
        
        LOGGER.info("LLM Pipeline initialized")
    
    def _create_default_config(self) -> LLMConfig:
        """Create default LLM configuration."""
        return LLMConfig(
            model_path="models/llama-2-7b-chat.Q4_K_M.gguf",  # Default model path
            provider=LLMProvider.LLAMA_CPP,
            device=LLMDevice.AUTO,
            max_tokens=2048,
            temperature=0.0,
            n_threads=4
        )
    
    def process_invoice(self, ocr_data: Dict[str, Any],
                       confidence_scores: Dict[str, float],
                       review_candidates: List[Dict[str, Any]],
                       context: Optional[Dict[str, Any]] = None,
                       enable_automation: bool = True) -> LLMPipelineResult:
        """
        Process an invoice through the complete LLM pipeline.
        
        Args:
            ocr_data: Raw OCR extracted data
            confidence_scores: Confidence scores for each field
            review_candidates: Fields that need human review
            context: Additional context information
            enable_automation: Whether to run automation features
            
        Returns:
            LLMPipelineResult with all processing results
        """
        start_time = time.time()
        result = LLMPipelineResult()
        
        try:
            LOGGER.info("Starting LLM pipeline processing")
            
            # Step 1: Generate invoice card
            LOGGER.info("Step 1: Generating invoice card")
            invoice_card_result = self.invoice_card_generator.generate_invoice_card(
                ocr_data=ocr_data,
                confidence_scores=confidence_scores,
                review_candidates=review_candidates,
                context=context
            )
            result.invoice_card = invoice_card_result
            
            if not invoice_card_result.success:
                result.errors.append("Invoice card generation failed")
                result.processing_time = time.time() - start_time
                return result
            
            # Step 2: Run automation features if enabled
            if enable_automation:
                LOGGER.info("Step 2: Running automation features")
                
                # Detect anomalies
                LOGGER.info("Detecting anomalies")
                anomaly_detection = self.anomaly_detector.detect_anomalies(
                    invoice_data=invoice_card_result.invoice_card.to_dict(),
                    context=context
                )
                result.anomaly_detection = anomaly_detection
                
                # Generate credit request if anomalies found
                if anomaly_detection.anomalies and anomaly_detection.severity in ["medium", "high"]:
                    LOGGER.info("Generating credit request due to anomalies")
                    credit_request = self.credit_request_generator.generate_credit_request(
                        invoice_data=invoice_card_result.invoice_card.to_dict(),
                        anomalies=anomaly_detection.anomalies,
                        credit_reasons=anomaly_detection.recommendations,
                        context=context
                    )
                    result.credit_request = credit_request
                
                # Post-correction for low confidence fields
                if invoice_card_result.invoice_card.needs_review:
                    LOGGER.info("Running post-correction for low confidence fields")
                    post_correction = self.post_correction_engine.correct_data(
                        original_data=ocr_data,
                        confidence_issues=invoice_card_result.invoice_card.review_reasons,
                        context=context
                    )
                    result.post_correction = post_correction
            
            # Calculate processing time
            result.processing_time = time.time() - start_time
            result.success = True
            
            # Add metadata
            result.metadata = {
                "pipeline_version": "1.0.0",
                "processing_timestamp": datetime.now().isoformat(),
                "llm_model": self.llm_interface.get_model_info(),
                "automation_enabled": enable_automation,
                "total_llm_time": sum([
                    result.invoice_card.llm_result.inference_time if result.invoice_card else 0,
                    # Add other LLM times if available
                ])
            }
            
            LOGGER.info(f"LLM pipeline processing completed in {result.processing_time:.3f}s")
            return result
            
        except Exception as e:
            LOGGER.error(f"LLM pipeline processing failed: {e}")
            result.errors.append(f"Pipeline processing failed: {e}")
            result.processing_time = time.time() - start_time
            return result
    
    def batch_process(self, batch_data: List[Dict[str, Any]],
                     enable_automation: bool = True) -> List[LLMPipelineResult]:
        """Process multiple invoices in batch."""
        results = []
        
        LOGGER.info(f"Starting batch processing: {len(batch_data)} documents")
        
        for i, data in enumerate(batch_data):
            LOGGER.info(f"Processing batch item {i+1}/{len(batch_data)}")
            
            result = self.process_invoice(
                ocr_data=data.get("ocr_data", {}),
                confidence_scores=data.get("confidence_scores", {}),
                review_candidates=data.get("review_candidates", []),
                context=data.get("context", {}),
                enable_automation=enable_automation
            )
            
            results.append(result)
        
        LOGGER.info(f"Batch processing completed: {len(results)} results")
        return results
    
    def get_pipeline_stats(self, results: List[LLMPipelineResult]) -> Dict[str, Any]:
        """Get statistics from batch processing results."""
        if not results:
            return {}
        
        total_time = sum(r.processing_time for r in results)
        successful = sum(1 for r in results if r.success)
        
        # Count automation features used
        credit_requests = sum(1 for r in results if r.credit_request)
        post_corrections = sum(1 for r in results if r.post_correction)
        anomaly_detections = sum(1 for r in results if r.anomaly_detection)
        
        return {
            "total_documents": len(results),
            "successful_processing": successful,
            "success_rate": successful / len(results),
            "total_processing_time": total_time,
            "average_processing_time": total_time / len(results),
            "credit_requests_generated": credit_requests,
            "post_corrections_applied": post_corrections,
            "anomaly_detections": anomaly_detections,
            "automation_usage_rate": (credit_requests + post_corrections) / len(results)
        }
    
    def validate_pipeline(self) -> Dict[str, Any]:
        """Validate the pipeline configuration and components."""
        validation_results = {
            "llm_available": self.llm_interface.is_available(),
            "llm_info": self.llm_interface.get_model_info(),
            "components_initialized": {
                "invoice_card_generator": self.invoice_card_generator is not None,
                "credit_request_generator": self.credit_request_generator is not None,
                "post_correction_engine": self.post_correction_engine is not None,
                "anomaly_detector": self.anomaly_detector is not None
            },
            "config": self.config.to_dict()
        }
        
        validation_results["pipeline_ready"] = (
            validation_results["llm_available"] and
            all(validation_results["components_initialized"].values())
        )
        
        return validation_results
    
    def cleanup(self):
        """Clean up pipeline resources."""
        if hasattr(self.llm_interface, 'cleanup'):
            self.llm_interface.cleanup()
        LOGGER.info("LLM Pipeline cleaned up")


class LLMPipelineManager:
    """Manager for multiple LLM pipelines with fallback support."""
    
    def __init__(self, configs: List[LLMConfig]):
        """Initialize with multiple pipeline configurations."""
        self.configs = configs
        self.pipelines = []
        self.active_pipeline = None
        self._initialize_pipelines()
    
    def _initialize_pipelines(self):
        """Initialize all configured pipelines."""
        for config in self.configs:
            try:
                pipeline = LLMPipeline(config)
                if pipeline.validate_pipeline()["pipeline_ready"]:
                    self.pipelines.append(pipeline)
                    if self.active_pipeline is None:
                        self.active_pipeline = pipeline
                    LOGGER.info(f"Pipeline initialized: {config.provider.value}")
                else:
                    LOGGER.warning(f"Pipeline not ready: {config.provider.value}")
            except Exception as e:
                LOGGER.error(f"Failed to initialize pipeline {config.provider.value}: {e}")
        
        if not self.pipelines:
            LOGGER.error("No pipelines available, creating mock pipeline")
            mock_config = LLMConfig(
                model_path="mock",
                provider=LLMProvider.MOCK
            )
            self.active_pipeline = LLMPipeline(mock_config)
            self.pipelines.append(self.active_pipeline)
    
    def process_invoice(self, *args, **kwargs) -> LLMPipelineResult:
        """Process invoice using active pipeline with fallback support."""
        if not self.active_pipeline:
            raise RuntimeError("No pipeline available")
        
        try:
            return self.active_pipeline.process_invoice(*args, **kwargs)
        except Exception as e:
            LOGGER.error(f"Active pipeline failed: {e}")
            # Try fallback pipelines
            for pipeline in self.pipelines:
                if pipeline != self.active_pipeline:
                    try:
                        LOGGER.info(f"Trying fallback pipeline: {pipeline.config.provider.value}")
                        result = pipeline.process_invoice(*args, **kwargs)
                        if result.success:
                            self.active_pipeline = pipeline
                            return result
                    except Exception as fallback_error:
                        LOGGER.error(f"Fallback pipeline failed: {fallback_error}")
                        continue
            
            # All pipelines failed, return error result
            return LLMPipelineResult(
                success=False,
                errors=[f"All pipelines failed: {e}"]
            )
    
    def get_available_pipelines(self) -> List[Dict[str, Any]]:
        """Get information about all available pipelines."""
        return [pipeline.validate_pipeline() for pipeline in self.pipelines]
    
    def cleanup(self):
        """Clean up all pipeline instances."""
        for pipeline in self.pipelines:
            pipeline.cleanup()
        self.pipelines.clear()
        self.active_pipeline = None
