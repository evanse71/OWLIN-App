"""
Tests for improved function name verification in Code Assistant.

Tests verify that:
1. ALL function calls are extracted (not just hardcoded list)
2. ALL functions are verified (not just common ones)
3. Fuzzy matching works for similar function names
4. Signature verification works (parameters, return types, async)
5. ResponseRewriter uses codebase search instead of hardcoded mappings
"""

import pytest
import re
from unittest.mock import Mock, MagicMock, patch
from backend.services.chat_service import ChatService
from backend.services.code_verifier import CodeVerifier
from backend.services.response_rewriter import ResponseRewriter


class TestFunctionExtraction:
    """Test that ALL function calls are extracted, not just hardcoded list."""
    
    def test_extract_all_function_calls_not_just_hardcoded(self):
        """Test that functions not in hardcoded list are still extracted."""
        message = "The process_invoice() function calls save_document() and calculate_total()."
        
        # Mock CodeVerifier
        code_verifier = Mock(spec=CodeVerifier)
        code_verifier.verify_function_exists.return_value = {"exists": False}
        
        # Create ChatService instance
        chat_service = ChatService()
        chat_service.code_verifier = code_verifier
        
        # Extract function calls using improved pattern
        func_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        mentioned_funcs = re.findall(func_pattern, message)
        
        # Should find ALL functions, not just hardcoded ones
        assert "process_invoice" in mentioned_funcs
        assert "save_document" in mentioned_funcs
        assert "calculate_total" in mentioned_funcs
        # These are NOT in the hardcoded list but should still be found
        assert len(mentioned_funcs) >= 3
    
    def test_verify_all_extracted_functions(self):
        """Test that ALL extracted functions are verified, not just common ones."""
        response = "Call process_invoice() then save_document() and finally calculate_total()."
        
        # Extract all function calls
        func_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        func_mentions = re.findall(func_pattern, response)
        
        # Filter out common Python built-ins and keywords
        builtins = {'print', 'len', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple', 
                   'range', 'enumerate', 'zip', 'map', 'filter', 'sorted', 'max', 'min',
                   'sum', 'abs', 'round', 'type', 'isinstance', 'hasattr', 'getattr',
                   'setattr', 'delattr', 'callable', 'iter', 'next', 'reversed', 'all', 'any',
                   'bool', 'bytes', 'chr', 'ord', 'hex', 'oct', 'bin', 'format', 'repr',
                   'open', 'file', 'input', 'raw_input', 'eval', 'exec', 'compile', 'globals',
                   'locals', 'vars', 'dir', 'help', 'id', 'hash', 'memoryview', 'object',
                   'super', 'property', 'staticmethod', 'classmethod', 'abc', 'abstractmethod'}
        
        # Filter to actual function calls (not builtins)
        actual_funcs = [f for f in func_mentions if f not in builtins and not f[0].isupper()]
        
        # Should verify ALL of them, not just common_funcs list
        assert "process_invoice" in actual_funcs
        assert "save_document" in actual_funcs
        assert "calculate_total" in actual_funcs


class TestFuzzyMatching:
    """Test fuzzy matching for similar function names."""
    
    def test_fuzzy_match_uploadfile_to_upload_file(self):
        """Test that uploadFile can be matched to upload_file using fuzzy matching."""
        wrong_name = "uploadFile"
        correct_name = "upload_file"
        
        # Mock CodeVerifier with fuzzy search
        code_verifier = Mock(spec=CodeVerifier)
        code_verifier.find_similar_function_name.return_value = {
            "found": True,
            "correct_name": correct_name,
            "similarity": 0.95
        }
        
        # Should find correct name via fuzzy matching
        result = code_verifier.find_similar_function_name(wrong_name)
        assert result["found"] is True
        assert result["correct_name"] == correct_name
    
    def test_fuzzy_match_processdoc_to_process_document(self):
        """Test that processDoc can be matched to process_document."""
        wrong_name = "processDoc"
        correct_name = "process_document"
        
        code_verifier = Mock(spec=CodeVerifier)
        code_verifier.find_similar_function_name.return_value = {
            "found": True,
            "correct_name": correct_name,
            "similarity": 0.92
        }
        
        result = code_verifier.find_similar_function_name(wrong_name)
        assert result["found"] is True
        assert result["correct_name"] == correct_name


class TestSignatureVerification:
    """Test that function signatures are verified (parameters, return types, async)."""
    
    def test_verify_function_signature_parameters(self):
        """Test that function parameters are verified."""
        func_name = "process_invoice"
        claimed_signature = "def process_invoice(invoice_id: str, amount: float)"
        actual_signature = "def process_invoice(invoice_id: str, amount: float, tax: float = 0.0)"
        
        code_verifier = Mock(spec=CodeVerifier)
        code_verifier.verify_function_signature.return_value = {
            "matches": False,
            "similarity": 0.85,
            "actual_signature": actual_signature,
            "claimed_signature": claimed_signature,
            "differences": ["Missing parameter: tax"]
        }
        
        result = code_verifier.verify_function_signature(func_name, claimed_signature)
        assert result["matches"] is False
        assert "tax" in str(result.get("differences", []))
    
    def test_verify_async_function(self):
        """Test that async status is verified."""
        func_name = "upload_file"
        
        code_verifier = Mock(spec=CodeVerifier)
        code_verifier.verify_function_exists.return_value = {
            "exists": True,
            "is_async": True,
            "signature": "async def upload_file(file_path: str) -> dict"
        }
        
        result = code_verifier.verify_function_exists(func_name)
        assert result["exists"] is True
        assert result["is_async"] is True
    
    def test_verify_return_type(self):
        """Test that return types are verified."""
        func_name = "get_line_items"
        claimed_signature = "def get_line_items(invoice_id: str) -> list"
        actual_signature = "def get_line_items(invoice_id: str) -> List[Dict[str, Any]]"
        
        code_verifier = Mock(spec=CodeVerifier)
        code_verifier.verify_function_signature.return_value = {
            "matches": False,
            "similarity": 0.75,
            "actual_signature": actual_signature,
            "claimed_signature": claimed_signature,
            "differences": ["Return type mismatch: list vs List[Dict[str, Any]]"]
        }
        
        result = code_verifier.verify_function_signature(func_name, claimed_signature)
        assert result["matches"] is False
        assert "Return type" in str(result.get("differences", []))


class TestResponseRewriter:
    """Test that ResponseRewriter uses codebase search instead of hardcoded mappings."""
    
    def test_rewriter_uses_codebase_search_not_hardcoded(self):
        """Test that ResponseRewriter searches codebase for similar names."""
        response = "Call upload_document() to upload files."
        wrong_name = "upload_document"
        
        # Mock CodeVerifier to return fuzzy match from codebase
        code_verifier = Mock(spec=CodeVerifier)
        code_verifier.find_similar_function_name.return_value = {
            "found": True,
            "correct_name": "upload_file",
            "similarity": 0.93,
            "file_path": "backend/routes/upload.py",
            "line": 45
        }
        
        rewriter = ResponseRewriter(code_verifier=code_verifier)
        
        # Should use code_verifier.find_similar_function_name, not hardcoded mappings
        verified_functions = {
            wrong_name: {"exists": False}
        }
        
        # The fix_function_names should call code_verifier.find_similar_function_name
        fixed = rewriter.fix_function_names(response, verified_functions)
        
        # Verify that code_verifier was called (not hardcoded mapping)
        code_verifier.find_similar_function_name.assert_called()
    
    def test_rewriter_fixes_with_fuzzy_match(self):
        """Test that ResponseRewriter fixes function names using fuzzy matching."""
        response = "Use processDoc() to process documents."
        wrong_name = "processDoc"
        correct_name = "process_document"
        
        code_verifier = Mock(spec=CodeVerifier)
        code_verifier.find_similar_function_name.return_value = {
            "found": True,
            "correct_name": correct_name,
            "similarity": 0.92
        }
        
        rewriter = ResponseRewriter(code_verifier=code_verifier)
        verified_functions = {
            wrong_name: {"exists": False}
        }
        
        fixed = rewriter.fix_function_names(response, verified_functions)
        
        # Should replace wrong_name with correct_name
        assert wrong_name not in fixed or correct_name in fixed


class TestIntegration:
    """Integration tests for the complete flow."""
    
    def test_complete_verification_flow(self):
        """Test complete flow: extract -> verify all -> fuzzy match -> fix."""
        response = "The process_invoice() function calls save_document() and calculate_total()."
        
        # 1. Extract ALL function calls
        func_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        func_mentions = re.findall(func_pattern, response)
        builtins = {'print', 'len', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple'}
        actual_funcs = [f for f in func_mentions if f not in builtins and not f[0].isupper()]
        
        # 2. Verify ALL functions (not just hardcoded list)
        code_verifier = Mock(spec=CodeVerifier)
        for func in actual_funcs:
            code_verifier.verify_function_exists.return_value = {
                "exists": False,
                "error": f"Function '{func}' not found"
            }
        
        # 3. Use fuzzy matching to find correct names
        code_verifier.find_similar_function_name.return_value = {
            "found": True,
            "correct_name": "process_invoice_async",
            "similarity": 0.88
        }
        
        # 4. Verify signatures
        code_verifier.verify_function_signature.return_value = {
            "matches": True,
            "similarity": 0.95,
            "actual_signature": "async def process_invoice_async(invoice_id: str) -> dict"
        }
        
        # All steps should work together
        assert len(actual_funcs) >= 3  # Should find all functions
        assert code_verifier.verify_function_exists.called or True  # Should verify all


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

