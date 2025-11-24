"""
Tests for ResponseValidator improvements.

Tests the enhanced validation features:
1. Improved section detection with semantic matching
2. Section content validation
3. Better file path validation (existence check)
4. Code-to-text ratio validation
"""

import pytest
from pathlib import Path
from backend.services.response_validator import ResponseValidator, ValidationResult


class TestSectionDetection:
    """Test improved section detection."""
    
    def test_detects_variations_of_section_names(self):
        """Test that section detection works with variations like 'Code Review' vs 'Code Analysis'."""
        validator = ResponseValidator()
        
        # Response with "Code Review" instead of "Code Analysis"
        response = """
        **Code Review**
        I analyzed the following files...
        
        **Prioritized Diagnosis**
        The issue is...
        
        **Root Cause**
        The problem stems from...
        
        **Fix**
        Change the code to...
        """
        
        result = validator.validate_response(response)
        # Should NOT report "Code Analysis" as missing
        assert "Code Analysis" not in result.missing_sections
    
    def test_detects_section_with_different_phrasing(self):
        """Test detection of sections with semantic variations."""
        validator = ResponseValidator()
        
        # Response with "Analysis of Code" instead of "Code Analysis"
        response = """
        ## Analysis of Code
        Files examined: backend/main.py
        
        **Diagnosis**
        Most likely issue is...
        
        **Root Cause**
        The problem is...
        
        **Solution**
        Modify the code...
        """
        
        result = validator.validate_response(response)
        # Should detect all sections despite variations
        assert len(result.missing_sections) == 0
    
    def test_validates_section_has_content(self):
        """Test that sections must have actual content, not just headers."""
        validator = ResponseValidator()
        
        # Response with empty sections
        response = """
        **Code Analysis**
        
        **Prioritized Diagnosis**
        
        **Root Cause**
        
        **Fix**
        """
        
        result = validator.validate_response(response)
        # Should flag sections with no content
        assert not result.is_valid
        assert any("empty" in issue.lower() or "no content" in issue.lower() 
                  for issue in result.issues)
    
    def test_detects_section_with_minimal_content(self):
        """Test that sections with minimal content are still valid."""
        validator = ResponseValidator()
        
        response = """
        **Code Analysis**
        backend/main.py analyzed
        
        **Prioritized Diagnosis**
        Issue found in code
        
        **Root Cause**
        Bug in code logic
        
        **Fix**
        Fix the bug here
        """
        
        result = validator.validate_response(response)
        # Minimal but valid content should pass
        assert result.is_valid or len(result.missing_sections) == 0


class TestFilePathValidation:
    """Test improved file path validation."""
    
    def test_validates_path_exists(self):
        """Test that file paths are validated for existence."""
        validator = ResponseValidator()
        
        # Response with non-existent path
        response = """
        **Code Analysis**
        backend/nonexistent_file_xyz123.py:10
        
        **Prioritized Diagnosis**
        Issue found
        
        **Root Cause**
        Problem
        
        **Fix**
        Solution
        """
        
        result = validator.validate_response(response)
        # Should flag non-existent paths
        assert any("nonexistent" in issue.lower() or "not found" in issue.lower() 
                  for issue in result.issues)
    
    def test_validates_path_format_correctly(self):
        """Test that file paths must be in correct format."""
        validator = ResponseValidator()
        
        # Response with invalid path format
        response = """
        **Code Analysis**
        invalid/path/format.py:10
        
        **Prioritized Diagnosis**
        Issue
        
        **Root Cause**
        Problem
        
        **Fix**
        Solution
        """
        
        result = validator.validate_response(response)
        # Should flag invalid path format
        assert any("invalid" in issue.lower() or "format" in issue.lower() 
                  for issue in result.issues)
    
    def test_accepts_valid_existing_paths(self):
        """Test that valid existing paths are accepted."""
        validator = ResponseValidator()
        
        # Use a path that should exist (response_validator.py itself)
        response = f"""
        **Code Analysis**
        backend/services/response_validator.py:10
        
        **Prioritized Diagnosis**
        Issue found
        
        **Root Cause**
        Problem identified
        
        **Fix**
        Solution provided
        """
        
        result = validator.validate_response(response)
        # Valid existing path should not be flagged
        file_path_issues = [issue for issue in result.issues 
                           if "path" in issue.lower() or "file" in issue.lower()]
        # Should not have path-related issues for valid paths
        assert len([issue for issue in file_path_issues 
                   if "invalid" in issue.lower() or "not found" in issue.lower()]) == 0


class TestCodeToTextRatio:
    """Test code-to-text ratio validation."""
    
    def test_flags_responses_with_too_much_code(self):
        """Test that responses with too much code are flagged."""
        validator = ResponseValidator()
        
        # Response that's mostly code
        large_code_block = "\n".join([f"    line{i} = value{i}" for i in range(100)])
        response = f"""
        **Code Analysis**
        Files analyzed
        
        **Prioritized Diagnosis**
        Issue
        
        **Root Cause**
        Problem
        
        **Fix**
        ```python
{large_code_block}
        ```
        """
        
        result = validator.validate_response(response)
        # Should flag too much code
        assert any("ratio" in issue.lower() or "too much code" in issue.lower() 
                  or "text-first" in issue.lower() for issue in result.issues)
    
    def test_accepts_responses_with_appropriate_code_ratio(self):
        """Test that responses with appropriate code-to-text ratio pass."""
        validator = ResponseValidator()
        
        # Response with small code snippets and lots of text
        text_content = "This is a detailed explanation. " * 50
        response = f"""
        **Code Analysis**
        {text_content}
        
        **Prioritized Diagnosis**
        {text_content}
        
        **Root Cause**
        {text_content}
        
        **Fix**
        {text_content}
        
        Here's a small code snippet:
        ```python
        def fix():
            return True
        ```
        """
        
        result = validator.validate_response(response)
        # Should not flag appropriate code ratio
        code_ratio_issues = [issue for issue in result.issues 
                            if "ratio" in issue.lower() or "too much code" in issue.lower()]
        assert len(code_ratio_issues) == 0
    
    def test_validates_total_code_vs_text_not_just_per_block(self):
        """Test that total code vs text is checked, not just per-block."""
        validator = ResponseValidator()
        
        # Multiple small code blocks that together exceed ratio
        small_blocks = "\n".join([
            f"```python\ncode{i} = value{i}\n```" for i in range(20)
        ])
        minimal_text = "Text. "
        response = f"""
        **Code Analysis**
        {minimal_text}
        
        **Prioritized Diagnosis**
        {minimal_text}
        
        **Root Cause**
        {minimal_text}
        
        **Fix**
        {minimal_text}
        
        {small_blocks}
        """
        
        result = validator.validate_response(response)
        # Should flag even though each block is small
        assert any("ratio" in issue.lower() or "too much code" in issue.lower() 
                  for issue in result.issues)


class TestIntegration:
    """Integration tests combining multiple validation aspects."""
    
    def test_comprehensive_validation(self):
        """Test that all validation aspects work together."""
        validator = ResponseValidator()
        
        # Response with multiple issues
        response = """
        **Code Review**  # Variation of Code Analysis
        backend/fake_file.py:10  # Non-existent file
        
        **Diagnosis**  # Variation of Prioritized Diagnosis
        
        **Root Cause**
        Problem
        
        **Fix**
        ```python
        # Large code block
        line1 = value1
        line2 = value2
        line3 = value3
        line4 = value4
        line5 = value5
        line6 = value6
        line7 = value7
        ```
        """
        
        result = validator.validate_response(response)
        # Should catch multiple issues
        assert not result.is_valid
        assert len(result.issues) > 0
    
    def test_perfect_response_passes_all_checks(self):
        """Test that a well-formed response passes all checks."""
        validator = ResponseValidator()
        
        # Perfect response
        response = """
        **Code Analysis**
        I analyzed the following files: backend/services/response_validator.py
        
        **Prioritized Diagnosis**
        The most likely issue is a validation problem in the response structure.
        
        **Root Cause**
        The root cause is that section detection is too strict and doesn't handle variations.
        
        **Fix**
        Update the section detection to use semantic matching:
        ```python
        if section.lower() in response_lower:
            found = True
        ```
        """
        
        result = validator.validate_response(response)
        # Should pass all checks
        assert result.is_valid
        assert len(result.missing_sections) == 0
        assert len(result.code_snippet_issues) == 0

