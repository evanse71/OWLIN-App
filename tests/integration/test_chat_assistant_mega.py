"""
Integration Tests for Code Assistant Mega Upgrade

Tests the complete code assistant system including:
- Model registry and selection
- Code context management
- Response validation
- Fallback chains
- Quality metrics
"""

import pytest
import time
from backend.services.chat_service import ChatService
from backend.services.model_registry import ModelRegistry, get_registry
from backend.services.chat_metrics import get_metrics


class TestModelRegistry:
    """Test model registry functionality."""
    
    def test_registry_initialization(self):
        """Test that registry initializes and discovers models."""
        registry = get_registry()
        assert registry is not None
        
        # Should have models if Ollama is running
        models = registry.get_available_models()
        assert isinstance(models, list)
    
    def test_model_selection_debugging(self):
        """Test model selection for debugging questions."""
        registry = get_registry()
        
        # Large context debugging question should prefer qwen or deepseek
        selected_model, effective_context = registry.select_best_model(
            question_type="debugging",
            context_size=128000,
            code_files_count=5,
            preferred_models=["qwen2.5-coder:7b", "deepseek-coder:6.7b", "codellama:7b"]
        )
        
        if selected_model:
            assert "qwen" in selected_model.lower() or "deepseek" in selected_model.lower()
            assert effective_context <= 128000
    
    def test_model_selection_quick_question(self):
        """Test model selection for quick questions."""
        registry = get_registry()
        
        # Quick question should prefer faster models
        selected_model, effective_context = registry.select_best_model(
            question_type="general",
            context_size=16000,
            code_files_count=1,
            preferred_models=["llama3.2:3b", "codellama:7b", "qwen2.5-coder:7b"]
        )
        
        # Should work even if no models available
        assert effective_context <= 16000


class TestCodeContextManagement:
    """Test code context system."""
    
    def test_always_includes_files_for_debugging(self):
        """Test that debugging questions always get files."""
        service = ChatService()
        
        # Simulate debugging question
        message = "why did the upload succeed but the invoice doesn't show supplier name?"
        code_context = service._extract_code_requests(message)
        
        # Auto-include files
        question_analysis = service._classify_question(message)
        if question_analysis.get("type") == "debugging":
            auto_files = service._get_related_files_for_debugging(message, code_context)
            
            # Should include at least 3 files
            assert len(auto_files) >= 3, f"Expected >= 3 files, got {len(auto_files)}"
            assert len(auto_files) <= 10, f"Expected <= 10 files, got {len(auto_files)}"
            
            # Should include upload-related files
            file_names = " ".join(auto_files)
            assert "upload" in file_names.lower() or "invoice" in file_names.lower()
    
    def test_context_budgeting(self):
        """Test that context budgeting limits files appropriately."""
        service = ChatService()
        
        code_context = {
            "files": [
                "backend/main.py",
                "backend/services/ocr_service.py",
                "frontend_clean/src/pages/Invoices.tsx",
                "frontend_clean/src/lib/upload.ts",
                "backend/app/db.py"
            ]
        }
        
        # Small context size should limit files
        optimized = service._optimize_context_budget(
            code_context,
            effective_context_size=16000,
            conversation_history=None
        )
        
        # Should have some files included
        assert "files" in optimized
        assert len(optimized["files"]) > 0


class TestResponseValidation:
    """Test response validation system."""
    
    def test_detects_generic_response(self):
        """Test that generic responses are detected."""
        service = ChatService()
        
        # Generic response example (like the one in the user's conversation)
        generic_response = """
        It seems that the issue is related to the OCR pipeline not returning any results or errors for the uploaded document. Here are some possible causes and solutions:

        1. **Issue 1: Incorrect file format** - The uploaded document may be in an incorrect format
        2. **Issue 2: Poor image quality** - The quality of the uploaded images may be poor
        3. **Issue 3: Insufficient resources** - If you have limited resources available
        
        To troubleshoot these issues, you can try the following steps:
        1. Check the logs for any error messages
        2. Review your configuration settings
        """
        
        is_generic = service._is_generic_response(generic_response)
        assert is_generic, "Expected generic response to be detected"
    
    def test_accepts_code_specific_response(self):
        """Test that code-specific responses are accepted."""
        service = ChatService()
        
        # Code-specific response
        code_response = """
        **Files Analyzed**
        - `frontend_clean/src/lib/upload.ts` (lines 236-248)
        - `backend/main.py` (lines 630-650)
        - `backend/services/ocr_service.py` (lines 274-320)
        
        **Root Cause**
        In upload.ts:236, the polling stops before invoice data is available.
        
        **Fix**
        Update line 236 in upload.ts:
        ```typescript
        const hasData = statusData.parsed || statusData.invoice
        ```
        """
        
        is_generic = service._is_generic_response(code_response)
        assert not is_generic, "Expected code-specific response to be accepted"


class TestModelFallbackChain:
    """Test cascading model fallback."""
    
    def test_fallback_when_model_unavailable(self):
        """Test that system falls back gracefully when models fail."""
        service = ChatService()
        
        # If no models available, should use fallback
        if not service.ollama_available:
            result = service.chat(
                message="Show me the upload code",
                context_size=16000
            )
            
            # Should still return a response
            assert "response" in result
            assert len(result["response"]) > 0


class TestQualityMetrics:
    """Test quality metrics tracking."""
    
    def test_metrics_tracking(self):
        """Test that metrics are tracked correctly."""
        metrics = get_metrics()
        initial_count = metrics.session_stats["total_requests"]
        
        # Make a request
        service = ChatService()
        if service.ollama_available:
            service.chat(message="What is the upload function?", context_size=16000)
            
            # Metrics should be updated
            assert metrics.session_stats["total_requests"] == initial_count + 1
    
    def test_quality_report_generation(self):
        """Test quality report generation."""
        metrics = get_metrics()
        report = metrics.get_quality_report()
        
        assert "overall_health" in report
        assert "quality_checks" in report
        assert "session_stats" in report
        
        # Check thresholds
        checks = report["quality_checks"]
        assert "generic_response_rate" in checks
        assert "code_reference_rate" in checks


class TestEndToEndFlow:
    """Test complete end-to-end flows."""
    
    @pytest.mark.skipif(
        not ChatService().ollama_available,
        reason="Ollama not available"
    )
    def test_debugging_question_flow(self):
        """
        Test the complete flow for a debugging question.
        
        This simulates the user's actual question from the conversation.
        """
        service = ChatService()
        
        start_time = time.time()
        result = service.chat(
            message="why did the file upload successfully but it didn't show the contents of the invoices in the card, with extracting/displaying things like supplier name, items etc",
            context_size=64000
        )
        elapsed = time.time() - start_time
        
        # Should return a response
        assert "response" in result
        response = result["response"]
        
        # Should not be generic
        is_generic = service._is_generic_response(response)
        assert not is_generic, "Response should not be generic"
        
        # Should include code references
        assert "code_references" in result
        assert len(result["code_references"]) > 0 or \
               ("upload.ts" in response.lower() and "invoices.tsx" in response.lower()), \
               "Response should include code file references"
        
        # Should reference specific files
        assert "upload" in response.lower() or "invoice" in response.lower()
        
        # Should complete in reasonable time (< 60s for 64k context)
        assert elapsed < 60.0, f"Request took {elapsed}s, expected < 60s"
        
        print(f"\n✓ Debugging question flow completed in {elapsed:.2f}s")
        print(f"  Model used: {result.get('model_used')}")
        print(f"  Code refs: {len(result.get('code_references', []))}")
        print(f"  Generic: {is_generic}")
    
    @pytest.mark.skipif(
        not ChatService().ollama_available,
        reason="Ollama not available"
    )
    def test_quick_question_flow(self):
        """Test quick question with small context."""
        service = ChatService()
        
        result = service.chat(
            message="What does the health endpoint do?",
            context_size=10000
        )
        
        assert "response" in result
        assert len(result["response"]) > 0
    
    def test_fallback_without_ollama(self):
        """Test that system works without Ollama."""
        service = ChatService()
        service.ollama_available = False
        
        result = service.chat(
            message="Show me the upload code",
            context_size=16000
        )
        
        # Should still return a response with code
        assert "response" in result
        assert len(result["response"]) > 0
        
        # Should show actual code files
        assert "```" in result["response"] or "upload" in result["response"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

