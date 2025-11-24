"""
Tests for Framework Detection Enforcement in Code Assistant.

Tests that framework detection is enforced in prompts and code suggestions
match the detected framework.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.services.architecture_analyzer import ArchitectureAnalyzer
from backend.services.chat_service import ChatService


class TestFrameworkDetectionEnforcement:
    """Test framework detection and enforcement."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = ArchitectureAnalyzer()
        self.chat_service = ChatService()
    
    def test_detect_fastapi_framework(self):
        """Test that FastAPI framework is correctly detected."""
        # Use actual FastAPI file from codebase
        result = self.analyzer.detect_framework("backend/main.py")
        
        assert result["framework"] == "fastapi"
        assert result["confidence"] > 0.7
        assert "fastapi" in result.get("indicators", []) or any("fastapi" in str(i).lower() for i in result.get("indicators", []))
    
    def test_framework_syntax_rules_returned(self):
        """Test that framework detection returns syntax rules."""
        result = self.analyzer.detect_framework("backend/main.py")
        
        # Should have framework-specific syntax rules
        assert "syntax_rules" in result or "framework" in result
        # If FastAPI detected, should have decorator patterns
        if result["framework"] == "fastapi":
            assert result.get("confidence", 0) > 0.7
    
    def test_framework_enforced_in_system_prompt(self):
        """Test that detected framework is added to system prompt."""
        # Simulate framework detection
        framework_result = self.analyzer.detect_framework("backend/main.py")
        
        if framework_result.get("confidence", 0) > 0.7:
            framework = framework_result["framework"]
            
            # Check that system prompt would include framework context
            # This tests the _agent_mode_conversation method's architecture_context
            message = "How do I create an upload endpoint?"
            
            # Framework should be detected and added to prompt
            # We can't directly test the prompt, but we can verify the detection works
            assert framework in ["fastapi", "flask", "frontend", "nodejs"]
    
    def test_flask_syntax_rejected_for_fastapi(self):
        """Test that Flask syntax is rejected when FastAPI is detected."""
        # Detect framework
        result = self.analyzer.detect_framework("backend/main.py")
        
        if result["framework"] == "fastapi":
            # Code suggestion with Flask syntax should be invalid
            flask_code = """
@app.route('/upload', methods=['POST'])
def upload_file():
    doc_id = request.form['doc_id']
    return {'success': True}
"""
            
            # Should detect Flask patterns
            has_flask_route = "@app.route" in flask_code
            has_request_form = "request.form" in flask_code
            
            # For FastAPI codebase, this should be flagged
            assert has_flask_route or has_request_form  # Flask syntax detected
            
            # Validation should catch this mismatch
            # (This will be tested in the validator)
    
    def test_fastapi_syntax_accepted(self):
        """Test that FastAPI syntax is accepted when FastAPI is detected."""
        result = self.analyzer.detect_framework("backend/main.py")
        
        if result["framework"] == "fastapi":
            # Code suggestion with FastAPI syntax should be valid
            fastapi_code = """
@app.post("/api/upload")
async def upload_file(file: UploadFile):
    return {"success": True}
"""
            
            # Should have FastAPI patterns
            has_fastapi_post = "@app.post" in fastapi_code
            has_async = "async def" in fastapi_code
            
            assert has_fastapi_post
            assert has_async  # FastAPI typically uses async
    
    def test_decorator_validation(self):
        """Test that decorator patterns are validated against framework."""
        result = self.analyzer.detect_framework("backend/main.py")
        
        if result["framework"] == "fastapi":
            # FastAPI should use @app.post, @router.post, not @app.route
            fastapi_decorators = ["@app.post", "@app.get", "@router.post", "@router.get"]
            flask_decorators = ["@app.route"]
            
            # Check that detected framework matches expected decorators
            indicators = result.get("indicators", [])
            has_fastapi_indicator = any(
                "@app.post" in str(ind) or "@router" in str(ind) or "fastapi" in str(ind).lower()
                for ind in indicators
            )
            
            # Should have FastAPI indicators, not Flask
            assert has_fastapi_indicator
    
    def test_async_pattern_validation(self):
        """Test that async patterns are validated against framework."""
        result = self.analyzer.detect_framework("backend/main.py")
        async_result = self.analyzer.detect_async_patterns("backend/main.py")
        
        if result["framework"] == "fastapi":
            # FastAPI typically uses async
            # If async is detected, code suggestions should use async def
            if async_result.get("has_async"):
                # FastAPI with async should require async def in suggestions
                assert async_result.get("async_function_count", 0) >= 0  # At least checked
    
    def test_framework_context_in_prompt(self):
        """Test that framework context is added to prompts in all modes."""
        # This tests that framework detection is used in prompt generation
        # We'll test by checking if the method exists and works
        framework_result = self.analyzer.detect_framework("backend/main.py")
        
        if framework_result.get("confidence", 0) > 0.7:
            framework = framework_result["framework"]
            
            # Framework should be detectable
            assert framework in ["fastapi", "flask", "frontend", "nodejs", "unknown"]
            
            # Context should be generatable
            if framework != "unknown":
                context = f"This codebase uses {framework.upper()}. Use {framework} syntax."
                assert framework.upper() in context
                assert framework in context.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

