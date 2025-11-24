"""
Comprehensive tests for LLM integration with OCR pipeline.

Tests include:
- Local LLM interface testing
- Invoice card generation
- Automation features
- OCR-LLM integration
- Performance benchmarking
- Offline operation validation
"""

import pytest
import json
import logging
import time
from typing import Dict, Any, List
from datetime import date, datetime
from decimal import Decimal

# Import LLM components
from backend.llm.local_llm import LocalLLMInterface, LLMConfig, LLMProvider, LLMDevice
from backend.llm.invoice_card_generator import InvoiceCardGenerator
from backend.llm.automation_features import CreditRequestGenerator, PostCorrectionEngine, AnomalyDetector
from backend.llm.llm_pipeline import LLMPipeline
from backend.llm.ocr_llm_integration import OCRLLMIntegration
from backend.llm.prompt_templates import PromptTemplates, PromptType

# Import OCR components
from backend.normalization import FieldNormalizer
from backend.normalization.types import NormalizedInvoice, NormalizedLineItem


class TestLocalLLMInterface:
    """Test local LLM interface functionality."""
    
    def test_llm_interface_initialization(self):
        """Test LLM interface initialization."""
        config = LLMConfig(
            model_path="mock",
            provider=LLMProvider.MOCK,
            device=LLMDevice.CPU
        )
        
        llm = LocalLLMInterface(config)
        assert llm.is_available()
        assert llm.provider == LLMProvider.MOCK
    
    def test_llm_generation_mock(self):
        """Test LLM text generation with mock provider."""
        config = LLMConfig(
            model_path="mock",
            provider=LLMProvider.MOCK,
            device=LLMDevice.CPU
        )
        
        llm = LocalLLMInterface(config)
        result = llm.generate("Generate an invoice card for ACME Corp")
        
        assert result.success
        assert result.text is not None
        assert result.tokens_generated > 0
        assert result.inference_time > 0
    
    def test_llm_config_serialization(self):
        """Test LLM configuration serialization."""
        config = LLMConfig(
            model_path="test_model.gguf",
            provider=LLMProvider.LLAMA_CPP,
            device=LLMDevice.GPU,
            max_tokens=1024,
            temperature=0.1
        )
        
        config_dict = config.to_dict()
        assert config_dict["model_path"] == "test_model.gguf"
        assert config_dict["provider"] == "llama_cpp"
        assert config_dict["device"] == "gpu"
        assert config_dict["max_tokens"] == 1024
        assert config_dict["temperature"] == 0.1


class TestInvoiceCardGenerator:
    """Test invoice card generation functionality."""
    
    def test_invoice_card_generator_initialization(self):
        """Test invoice card generator initialization."""
        config = LLMConfig(
            model_path="mock",
            provider=LLMProvider.MOCK,
            device=LLMDevice.CPU
        )
        
        llm = LocalLLMInterface(config)
        generator = InvoiceCardGenerator(llm)
        
        assert generator.llm is not None
        assert generator.prompt_templates is not None
    
    def test_invoice_card_generation(self):
        """Test invoice card generation."""
        config = LLMConfig(
            model_path="mock",
            provider=LLMProvider.MOCK,
            device=LLMDevice.CPU
        )
        
        llm = LocalLLMInterface(config)
        generator = InvoiceCardGenerator(llm)
        
        # Test data
        ocr_data = {
            "supplier": "ACME Corporation Ltd",
            "invoice_number": "INV-2024-001",
            "invoice_date": "2024-01-15",
            "currency": "GBP",
            "subtotal": "£100.00",
            "tax_amount": "£20.00",
            "total_amount": "£120.00"
        }
        
        confidence_scores = {
            "supplier": 0.95,
            "invoice_number": 0.90,
            "invoice_date": 0.85,
            "currency": 0.95,
            "subtotal": 0.90,
            "tax_amount": 0.85,
            "total_amount": 0.95
        }
        
        review_candidates = []
        
        result = generator.generate_invoice_card(
            ocr_data=ocr_data,
            confidence_scores=confidence_scores,
            review_candidates=review_candidates
        )
        
        assert result.success
        assert result.invoice_card is not None
        assert result.processing_time > 0
        assert result.invoice_card.supplier_name is not None
    
    def test_invoice_card_schema_validation(self):
        """Test invoice card schema validation."""
        from backend.llm.invoice_card_generator import InvoiceCardSchema
        
        # Valid schema
        valid_card = InvoiceCardSchema(
            supplier_name="ACME Corp",
            total_amount=100.0,
            confidence=0.9
        )
        
        errors = valid_card.validate()
        assert len(errors) == 0
        
        # Invalid schema
        invalid_card = InvoiceCardSchema(
            supplier_name="",  # Missing required field
            total_amount=-10.0,  # Invalid amount
            confidence=0.9
        )
        
        errors = invalid_card.validate()
        assert len(errors) > 0


class TestAutomationFeatures:
    """Test automation features functionality."""
    
    def test_credit_request_generator(self):
        """Test credit request generation."""
        config = LLMConfig(
            model_path="mock",
            provider=LLMProvider.MOCK,
            device=LLMDevice.CPU
        )
        
        llm = LocalLLMInterface(config)
        generator = CreditRequestGenerator(llm)
        
        invoice_data = {
            "invoice_number": "INV-2024-001",
            "total_amount": 120.00,
            "supplier_name": "ACME Corp"
        }
        
        anomalies = ["Duplicate charge detected"]
        credit_reasons = ["Services already paid"]
        
        credit_request = generator.generate_credit_request(
            invoice_data=invoice_data,
            anomalies=anomalies,
            credit_reasons=credit_reasons
        )
        
        assert credit_request.subject is not None
        assert credit_request.body is not None
        assert "INV-2024-001" in credit_request.body
        assert credit_request.amount == 120.00
    
    def test_post_correction_engine(self):
        """Test post-correction functionality."""
        config = LLMConfig(
            model_path="mock",
            provider=LLMProvider.MOCK,
            device=LLMDevice.CPU
        )
        
        llm = LocalLLMInterface(config)
        engine = PostCorrectionEngine(llm)
        
        original_data = {
            "supplier": "ACME Corp Ltd",
            "date": "2024-01-1S",  # OCR error
            "amount": "£120.00"
        }
        
        confidence_issues = ["Date format unclear"]
        
        correction = engine.correct_data(
            original_data=original_data,
            confidence_issues=confidence_issues
        )
        
        assert correction.corrected_data is not None
        assert len(correction.corrections) > 0
        assert correction.confidence_improvement >= 0
    
    def test_anomaly_detector(self):
        """Test anomaly detection functionality."""
        config = LLMConfig(
            model_path="mock",
            provider=LLMProvider.MOCK,
            device=LLMDevice.CPU
        )
        
        llm = LocalLLMInterface(config)
        detector = AnomalyDetector(llm)
        
        invoice_data = {
            "supplier_name": "ACME Corp",
            "total_amount": 1000.00,  # Unusually high amount
            "invoice_date": "2024-01-15"
        }
        
        anomaly_detection = detector.detect_anomalies(invoice_data)
        
        assert anomaly_detection.anomalies is not None
        assert anomaly_detection.severity in ["low", "medium", "high"]
        assert len(anomaly_detection.recommendations) >= 0


class TestLLMPipeline:
    """Test complete LLM pipeline functionality."""
    
    def test_llm_pipeline_initialization(self):
        """Test LLM pipeline initialization."""
        config = LLMConfig(
            model_path="mock",
            provider=LLMProvider.MOCK,
            device=LLMDevice.CPU
        )
        
        pipeline = LLMPipeline(config)
        assert pipeline.llm_interface is not None
        assert pipeline.invoice_card_generator is not None
        assert pipeline.credit_request_generator is not None
        assert pipeline.post_correction_engine is not None
        assert pipeline.anomaly_detector is not None
    
    def test_llm_pipeline_processing(self):
        """Test complete LLM pipeline processing."""
        config = LLMConfig(
            model_path="mock",
            provider=LLMProvider.MOCK,
            device=LLMDevice.CPU
        )
        
        pipeline = LLMPipeline(config)
        
        # Test data
        ocr_data = {
            "supplier": "ACME Corporation Ltd",
            "invoice_number": "INV-2024-001",
            "invoice_date": "2024-01-15",
            "currency": "GBP",
            "subtotal": "£100.00",
            "tax_amount": "£20.00",
            "total_amount": "£120.00"
        }
        
        confidence_scores = {
            "supplier": 0.95,
            "invoice_number": 0.90,
            "invoice_date": 0.85,
            "currency": 0.95,
            "subtotal": 0.90,
            "tax_amount": 0.85,
            "total_amount": 0.95
        }
        
        review_candidates = []
        
        result = pipeline.process_invoice(
            ocr_data=ocr_data,
            confidence_scores=confidence_scores,
            review_candidates=review_candidates,
            enable_automation=True
        )
        
        assert result.success
        assert result.invoice_card is not None
        assert result.processing_time > 0
    
    def test_llm_pipeline_validation(self):
        """Test LLM pipeline validation."""
        config = LLMConfig(
            model_path="mock",
            provider=LLMProvider.MOCK,
            device=LLMDevice.CPU
        )
        
        pipeline = LLMPipeline(config)
        validation = pipeline.validate_pipeline()
        
        assert validation["llm_available"] is True
        assert validation["pipeline_ready"] is True
        assert len(validation["components_initialized"]) > 0


class TestOCRLLMIntegration:
    """Test OCR-LLM integration functionality."""
    
    def test_ocr_llm_integration_initialization(self):
        """Test OCR-LLM integration initialization."""
        config = LLMConfig(
            model_path="mock",
            provider=LLMProvider.MOCK,
            device=LLMDevice.CPU
        )
        
        integration = OCRLLMIntegration([config])
        assert integration.field_normalizer is not None
        assert integration.llm_pipeline_manager is not None
    
    def test_ocr_llm_document_processing(self):
        """Test complete OCR-LLM document processing."""
        config = LLMConfig(
            model_path="mock",
            provider=LLMProvider.MOCK,
            device=LLMDevice.CPU
        )
        
        integration = OCRLLMIntegration([config])
        
        # Test data
        raw_ocr_data = {
            "supplier": "ACME Corporation Ltd",
            "invoice_number": "INV-2024-001",
            "invoice_date": "2024-01-15",
            "currency": "GBP",
            "subtotal": "£100.00",
            "tax_amount": "£20.00",
            "total_amount": "£120.00",
            "line_items": [
                {
                    "description": "Professional Services",
                    "quantity": "10",
                    "unit": "hours",
                    "unit_price": "£10.00",
                    "line_total": "£100.00"
                }
            ]
        }
        
        context = {
            "invoice_id": "test-001",
            "region": "UK",
            "known_suppliers": ["ACME Corporation Ltd"],
            "default_currency": "GBP"
        }
        
        result = integration.process_document(
            raw_ocr_data=raw_ocr_data,
            context=context,
            enable_llm_processing=True,
            enable_automation=True
        )
        
        assert result.success
        assert result.normalization_result is not None
        assert result.confidence_routing_result is not None
        assert result.final_invoice_card is not None
        assert result.total_processing_time > 0
    
    def test_ocr_llm_integration_validation(self):
        """Test OCR-LLM integration validation."""
        config = LLMConfig(
            model_path="mock",
            provider=LLMProvider.MOCK,
            device=LLMDevice.CPU
        )
        
        integration = OCRLLMIntegration([config])
        validation = integration.validate_integration()
        
        assert validation["ocr_components"]["field_normalizer"] is True
        assert validation["integration_ready"] is True


class TestPromptTemplates:
    """Test prompt template functionality."""
    
    def test_prompt_templates_initialization(self):
        """Test prompt templates initialization."""
        templates = PromptTemplates()
        assert templates.templates is not None
        assert len(templates.templates) > 0
    
    def test_invoice_card_prompt_formatting(self):
        """Test invoice card prompt formatting."""
        templates = PromptTemplates()
        
        ocr_data = {"supplier": "ACME Corp", "total": "£120.00"}
        confidence_scores = {"supplier": 0.95, "total": 0.90}
        review_candidates = []
        
        prompt = templates.format_invoice_card_prompt(
            ocr_data=ocr_data,
            confidence_scores=confidence_scores,
            review_candidates=review_candidates
        )
        
        assert "ACME Corp" in prompt
        assert "0.95" in prompt
        assert "invoice" in prompt.lower()
    
    def test_credit_request_prompt_formatting(self):
        """Test credit request prompt formatting."""
        templates = PromptTemplates()
        
        invoice_data = {"invoice_number": "INV-001", "amount": 120.00}
        anomalies = ["Duplicate charge"]
        credit_reasons = ["Already paid"]
        
        prompt = templates.format_credit_request_prompt(
            invoice_data=invoice_data,
            anomalies=anomalies,
            credit_reasons=credit_reasons
        )
        
        assert "INV-001" in prompt
        assert "Duplicate charge" in prompt
        assert "credit" in prompt.lower()


class TestPerformanceBenchmarking:
    """Test performance benchmarking functionality."""
    
    def test_llm_inference_timing(self):
        """Test LLM inference timing."""
        config = LLMConfig(
            model_path="mock",
            provider=LLMProvider.MOCK,
            device=LLMDevice.CPU
        )
        
        llm = LocalLLMInterface(config)
        
        # Test multiple generations to get timing
        times = []
        for i in range(5):
            start_time = time.time()
            result = llm.generate(f"Generate invoice card {i}")
            end_time = time.time()
            
            times.append(end_time - start_time)
            assert result.success
        
        # Check that timing is reasonable (mock should be fast)
        average_time = sum(times) / len(times)
        assert average_time < 1.0  # Mock should be very fast
    
    def test_pipeline_processing_timing(self):
        """Test complete pipeline processing timing."""
        config = LLMConfig(
            model_path="mock",
            provider=LLMProvider.MOCK,
            device=LLMDevice.CPU
        )
        
        integration = OCRLLMIntegration([config])
        
        raw_ocr_data = {
            "supplier": "ACME Corporation Ltd",
            "invoice_number": "INV-2024-001",
            "total_amount": "£120.00"
        }
        
        start_time = time.time()
        result = integration.process_document(
            raw_ocr_data=raw_ocr_data,
            enable_llm_processing=True,
            enable_automation=True
        )
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        assert result.success
        assert processing_time > 0
        assert result.total_processing_time > 0
        # Should be reasonable for mock processing
        assert processing_time < 10.0


class TestOfflineOperation:
    """Test offline operation functionality."""
    
    def test_mock_provider_offline(self):
        """Test that mock provider works offline."""
        config = LLMConfig(
            model_path="mock",
            provider=LLMProvider.MOCK,
            device=LLMDevice.CPU
        )
        
        llm = LocalLLMInterface(config)
        assert llm.is_available()
        
        # Test generation without network
        result = llm.generate("Test offline generation")
        assert result.success
        assert result.provider == "mock"
    
    def test_pipeline_offline_operation(self):
        """Test complete pipeline offline operation."""
        config = LLMConfig(
            model_path="mock",
            provider=LLMProvider.MOCK,
            device=LLMDevice.CPU
        )
        
        integration = OCRLLMIntegration([config])
        
        # Test offline processing
        raw_ocr_data = {
            "supplier": "ACME Corporation Ltd",
            "total_amount": "£120.00"
        }
        
        result = integration.process_document(
            raw_ocr_data=raw_ocr_data,
            enable_llm_processing=True,
            enable_automation=True
        )
        
        assert result.success
        assert result.final_invoice_card is not None
        # Should work completely offline with mock provider


class TestRealWorldScenarios:
    """Test real-world document scenarios."""
    
    def test_high_quality_invoice_processing(self):
        """Test processing of high-quality invoice."""
        config = LLMConfig(
            model_path="mock",
            provider=LLMProvider.MOCK,
            device=LLMDevice.CPU
        )
        
        integration = OCRLLMIntegration([config])
        
        # High-quality invoice data
        raw_ocr_data = {
            "supplier": "ACME Corporation Ltd",
            "invoice_number": "INV-2024-001",
            "invoice_date": "2024-01-15",
            "currency": "GBP",
            "subtotal": "£100.00",
            "tax_amount": "£20.00",
            "total_amount": "£120.00",
            "line_items": [
                {
                    "description": "Professional Services",
                    "quantity": "10",
                    "unit": "hours",
                    "unit_price": "£10.00",
                    "line_total": "£100.00"
                }
            ]
        }
        
        context = {
            "invoice_id": "high-quality-001",
            "region": "UK",
            "known_suppliers": ["ACME Corporation Ltd"],
            "default_currency": "GBP"
        }
        
        result = integration.process_document(
            raw_ocr_data=raw_ocr_data,
            context=context,
            enable_llm_processing=True,
            enable_automation=True
        )
        
        assert result.success
        assert result.final_invoice_card["supplier_name"] == "ACME Corporation Ltd"
        assert result.final_invoice_card["total_amount"] == 120.00
        assert len(result.review_queue) == 0  # High quality should have no review items
    
    def test_poor_quality_invoice_processing(self):
        """Test processing of poor-quality invoice."""
        config = LLMConfig(
            model_path="mock",
            provider=LLMProvider.MOCK,
            device=LLMDevice.CPU
        )
        
        integration = OCRLLMIntegration([config])
        
        # Poor-quality invoice data
        raw_ocr_data = {
            "supplier": "unclear company name",
            "invoice_number": "123?",
            "invoice_date": "sometime in 2024",
            "currency": "?",
            "subtotal": "around 100",
            "tax_amount": "maybe 20",
            "total_amount": "120 or so"
        }
        
        context = {
            "invoice_id": "poor-quality-001",
            "region": "unknown"
        }
        
        result = integration.process_document(
            raw_ocr_data=raw_ocr_data,
            context=context,
            enable_llm_processing=True,
            enable_automation=True
        )
        
        assert result.success
        assert len(result.review_queue) > 0  # Poor quality should have review items
        assert result.confidence_routing_result.overall_confidence < 0.7
    
    def test_perturbed_document_processing(self):
        """Test processing of document with OCR perturbations."""
        config = LLMConfig(
            model_path="mock",
            provider=LLMProvider.MOCK,
            device=LLMDevice.CPU
        )
        
        integration = OCRLLMIntegration([config])
        
        # Perturbed document data
        raw_ocr_data = {
            "supplier": "ACME Corp Ltd",  # Slightly blurred
            "invoice_number": "INV-2024-00I",  # OCR confusion: 1 vs I
            "invoice_date": "2024-01-1S",      # OCR confusion: 5 vs S
            "currency": "GBP",
            "subtotal": "£100.00",
            "tax_amount": "£20.00",
            "total_amount": "£120.00"
        }
        
        context = {
            "invoice_id": "perturbed-001",
            "region": "UK",
            "known_suppliers": ["ACME Corp Ltd"],
            "default_currency": "GBP"
        }
        
        result = integration.process_document(
            raw_ocr_data=raw_ocr_data,
            context=context,
            enable_llm_processing=True,
            enable_automation=True
        )
        
        assert result.success
        # Should detect perturbations and handle appropriately
        assert result.confidence_routing_result.overall_confidence < 0.9


class TestBatchProcessing:
    """Test batch processing functionality."""
    
    def test_batch_document_processing(self):
        """Test batch processing of multiple documents."""
        config = LLMConfig(
            model_path="mock",
            provider=LLMProvider.MOCK,
            device=LLMDevice.CPU
        )
        
        integration = OCRLLMIntegration([config])
        
        # Create batch data
        batch_data = []
        for i in range(5):
            batch_data.append({
                "raw_ocr_data": {
                    "supplier": f"Company {i} Ltd",
                    "invoice_number": f"INV-2024-{i:03d}",
                    "total_amount": f"£{(i+1)*100}.00"
                },
                "context": {
                    "invoice_id": f"batch-{i:03d}",
                    "region": "UK"
                }
            })
        
        results = integration.batch_process_documents(
            batch_data=batch_data,
            enable_llm_processing=True,
            enable_automation=True
        )
        
        assert len(results) == 5
        assert all(result.success for result in results)
        
        # Get statistics
        stats = integration.get_integration_stats(results)
        assert stats["total_documents"] == 5
        assert stats["success_rate"] == 1.0
        assert stats["total_processing_time"] > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
