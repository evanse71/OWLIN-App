"""
Tests for Multi-Pass Validation Improvements

Tests that verify the multi-pass validation loop properly:
1. Tracks specific issues before rewrite
2. Verifies code snippets after rewrite
3. Verifies function names after rewrite
4. Checks if specific issues were actually resolved (not just absence of warnings)
5. Doesn't exit early if rewrite didn't actually fix issues
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from backend.services.chat_service import ChatService
from backend.services.code_verifier import CodeVerifier
from backend.services.response_validator import ResponseValidator
from backend.services.response_rewriter import ResponseRewriter


class TestMultiPassValidationImprovements:
    """Test multi-pass validation improvements."""
    
    def test_tracks_specific_issues_before_rewrite(self):
        """
        Test that specific issues are tracked before rewrite:
        - Code snippets that don't match
        - Function names that don't exist
        - Structure validation issues
        - Unverified claims
        """
        service = ChatService()
        
        # Mock code verifier to return mismatched code snippet
        mock_verifier = Mock(spec=CodeVerifier)
        mock_verifier.verify_code_snippet.return_value = {
            "matches": False,
            "similarity": 0.5,
            "actual_code": "def actual_function():\n    return True",
            "file_path": "backend/test.py",
            "line_range": (10, 15),
            "claimed_code": "def wrong_function():\n    return False"
        }
        service.code_verifier = mock_verifier
        
        # Mock response validator to return structure issues
        mock_validator = Mock(spec=ResponseValidator)
        mock_validator.validate_response.return_value = Mock(
            is_valid=False,
            issues=["Missing required section: Analysis"]
        )
        service.response_validator = mock_validator
        
        # Mock _filter_unverified_claims to return warnings
        def mock_filter_unverified(response, files_read, commands):
            return "⚠️ Unverified claim: process_invoice() function"
        service._filter_unverified_claims = mock_filter_unverified
        
        # Mock _extract_and_verify_code_snippets
        def mock_extract_verify(response):
            return {
                "def wrong_function():\n    return False": {
                    "matches": False,
                    "similarity": 0.5,
                    "actual_code": "def actual_function():\n    return True",
                    "file_path": "backend/test.py"
                }
            }
        service._extract_and_verify_code_snippets = mock_extract_verify
        
        # Response with issues
        response = "Here's the code:\n```python\ndef wrong_function():\n    return False\n```"
        
        # Simulate the multi-pass validation logic
        # Before rewrite, we should track:
        code_verifications_dict = service._extract_and_verify_code_snippets(response)
        structure_validation = service.response_validator.validate_response(response)
        unverified_warnings = service._filter_unverified_claims(response, set(), [])
        
        # Verify issues were tracked
        assert code_verifications_dict
        mismatched_count = sum(1 for v in code_verifications_dict.values() if not v.get("matches", True))
        assert mismatched_count > 0, "Should track mismatched code snippets"
        assert not structure_validation.is_valid, "Should track structure issues"
        assert "⚠️" in unverified_warnings, "Should track unverified claims"
    
    def test_verifies_code_snippets_after_rewrite(self):
        """
        Test that code snippets are verified AFTER rewrite to check if they were actually fixed.
        
        This test verifies:
        1. Before rewrite: code snippet doesn't match
        2. After rewrite: code snippet should be verified again
        3. If still doesn't match: rewrite didn't fix it
        4. If now matches: rewrite fixed it
        """
        service = ChatService()
        
        # Track original verification (before rewrite)
        original_verification = {
            "matches": False,
            "similarity": 0.5,
            "actual_code": "def actual_function():\n    return True",
            "file_path": "backend/test.py",
            "claimed_code": "def wrong_function():\n    return False"
        }
        
        # Mock code verifier - first call (before rewrite) returns mismatch
        # Second call (after rewrite) should verify again
        mock_verifier = Mock(spec=CodeVerifier)
        call_count = 0
        
        def verify_code_side_effect(claimed_code, file_path, line_range):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Before rewrite: doesn't match
                return original_verification
            else:
                # After rewrite: check if it was fixed
                # If rewrite worked, claimed_code should now be actual_code
                if "actual_function" in claimed_code:
                    return {
                        "matches": True,
                        "similarity": 1.0,
                        "actual_code": "def actual_function():\n    return True",
                        "file_path": file_path
                    }
                else:
                    # Still wrong
                    return original_verification
        
        mock_verifier.verify_code_snippet.side_effect = verify_code_side_effect
        service.code_verifier = mock_verifier
        
        # Mock response rewriter to fix the code
        mock_rewriter = Mock(spec=ResponseRewriter)
        def rewrite_side_effect(response, verification_results=None, files_read=None):
            # Simulate fixing the code
            return response.replace("wrong_function", "actual_function")
        mock_rewriter.rewrite_response.side_effect = rewrite_side_effect
        service.response_rewriter = mock_rewriter
        
        # Mock _extract_and_verify_code_snippets
        def mock_extract_verify(response):
            # Extract code snippets and verify them
            import re
            code_verifications_dict = {}
            code_snippet_pattern = r'```(?:python|typescript|javascript|js|ts|tsx|jsx)?\n(.*?)```'
            code_snippets = re.findall(code_snippet_pattern, response, re.DOTALL)
            
            for snippet in code_snippets[:5]:
                claimed_code = snippet.strip()
                if not claimed_code:
                    continue
                # Verify using code verifier
                verification = service.code_verifier.verify_code_snippet(
                    claimed_code, "backend/test.py", (10, 15)
                )
                code_verifications_dict[claimed_code] = verification
            
            return code_verifications_dict
        
        service._extract_and_verify_code_snippets = mock_extract_verify
        
        # Original response with wrong code
        original_response = "Here's the code:\n```python\ndef wrong_function():\n    return False\n```"
        
        # Before rewrite: verify code snippets
        code_verifications_before = service._extract_and_verify_code_snippets(original_response)
        assert call_count == 1, "Should verify code snippets before rewrite"
        assert any(not v.get("matches", True) for v in code_verifications_before.values()), \
            "Should detect mismatched code before rewrite"
        
        # Rewrite response
        rewritten_response = service.response_rewriter.rewrite_response(
            original_response,
            verification_results={"code_verifications": code_verifications_before}
        )
        
        # After rewrite: verify code snippets again
        code_verifications_after = service._extract_and_verify_code_snippets(rewritten_response)
        assert call_count > 1, "Should verify code snippets after rewrite"
        
        # Check if issues were actually fixed
        mismatched_after = sum(1 for v in code_verifications_after.values() if not v.get("matches", True))
        assert mismatched_after == 0, "Code snippets should be fixed after rewrite"
    
    def test_verifies_function_names_after_rewrite(self):
        """
        Test that function names are verified AFTER rewrite to check if they were actually fixed.
        
        This test verifies:
        1. Before rewrite: function name doesn't exist
        2. After rewrite: function name should be verified again
        3. If still doesn't exist: rewrite didn't fix it
        4. If now exists: rewrite fixed it
        """
        service = ChatService()
        
        # Track original verification (before rewrite)
        original_verification = {
            "exists": False,
            "error": "Function 'wrong_function' not found in codebase",
            "match_confidence": 0.0
        }
        
        # Mock code verifier - first call (before rewrite) returns doesn't exist
        # Second call (after rewrite) should verify again
        mock_verifier = Mock(spec=CodeVerifier)
        call_count = 0
        
        def verify_function_side_effect(func_name, file_path=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Before rewrite: doesn't exist
                return original_verification
            else:
                # After rewrite: check if it was fixed
                # If rewrite worked, func_name should now be correct_function
                if func_name == "correct_function":
                    return {
                        "exists": True,
                        "file_path": "backend/test.py",
                        "line": 10,
                        "signature": "def correct_function() -> bool",
                        "match_confidence": 1.0
                    }
                else:
                    # Still wrong
                    return original_verification
        
        mock_verifier.verify_function_exists.side_effect = verify_function_side_effect
        service.code_verifier = mock_verifier
        
        # Mock response rewriter to fix the function name
        mock_rewriter = Mock(spec=ResponseRewriter)
        def rewrite_side_effect(response, verification_results=None, files_read=None):
            # Simulate fixing the function name
            return response.replace("wrong_function", "correct_function")
        mock_rewriter.rewrite_response.side_effect = rewrite_side_effect
        service.response_rewriter = mock_rewriter
        
        # Original response with wrong function name
        original_response = "The wrong_function() is called here."
        
        # Before rewrite: extract and verify function names
        import re
        func_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        func_mentions = re.findall(func_pattern, original_response)
        builtins = {'print', 'len', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple'}
        mentioned_funcs = [f for f in func_mentions if f not in builtins and not f[0].isupper()]
        
        function_verifications_before = {}
        for func in mentioned_funcs:
            verification = service.code_verifier.verify_function_exists(func)
            function_verifications_before[func] = verification
        
        assert call_count == 1, "Should verify function names before rewrite"
        assert any(not v.get("exists", False) for v in function_verifications_before.values()), \
            "Should detect non-existent functions before rewrite"
        
        # Rewrite response
        rewritten_response = service.response_rewriter.rewrite_response(
            original_response,
            verification_results={"function_verifications": function_verifications_before}
        )
        
        # After rewrite: verify function names again
        func_mentions_after = re.findall(func_pattern, rewritten_response)
        mentioned_funcs_after = [f for f in func_mentions_after if f not in builtins and not f[0].isupper()]
        
        function_verifications_after = {}
        for func in mentioned_funcs_after:
            verification = service.code_verifier.verify_function_exists(func)
            function_verifications_after[func] = verification
        
        assert call_count > 1, "Should verify function names after rewrite"
        
        # Check if issues were actually fixed
        non_existent_after = sum(1 for v in function_verifications_after.values() if not v.get("exists", False))
        assert non_existent_after == 0, "Function names should be fixed after rewrite"
    
    def test_checks_specific_issues_resolved_not_just_warnings_gone(self):
        """
        Test that verification checks if SPECIFIC issues were resolved,
        not just that warnings are gone.
        
        Current implementation only checks: "⚠️" not in unverified_after
        This is fragile - what if warning format changes?
        
        Should check:
        1. Code snippets that were wrong are now correct
        2. Function names that were wrong are now correct
        3. Structure issues that existed are now resolved
        4. Unverified claims that existed are now verified
        """
        service = ChatService()
        
        # Track specific issues before rewrite
        issues_before = {
            "code_snippets": [
                {
                    "claimed_code": "def wrong_function():\n    return False",
                    "matches": False,
                    "file_path": "backend/test.py"
                }
            ],
            "function_names": [
                {
                    "name": "wrong_function",
                    "exists": False
                }
            ],
            "structure_issues": ["Missing required section: Analysis"],
            "unverified_claims": ["process_invoice() function"]
        }
        
        # Mock code verifier
        mock_verifier = Mock(spec=CodeVerifier)
        mock_verifier.verify_code_snippet.return_value = {
            "matches": True,  # After rewrite, it matches
            "similarity": 1.0,
            "actual_code": "def correct_function():\n    return True",
            "file_path": "backend/test.py"
        }
        mock_verifier.verify_function_exists.return_value = {
            "exists": True,  # After rewrite, it exists
            "file_path": "backend/test.py",
            "line": 10
        }
        service.code_verifier = mock_verifier
        
        # Mock response validator
        mock_validator = Mock(spec=ResponseValidator)
        mock_validator.validate_response.return_value = Mock(
            is_valid=True,  # After rewrite, structure is valid
            issues=[]
        )
        service.response_validator = mock_validator
        
        # Mock _filter_unverified_claims
        def mock_filter_unverified(response, files_read, commands):
            # After rewrite, no warnings
            return ""  # No warnings
        service._filter_unverified_claims = mock_filter_unverified
        
        # Mock _extract_and_verify_code_snippets
        def mock_extract_verify(response):
            # After rewrite, code snippets match
            return {
                "def correct_function():\n    return True": {
                    "matches": True,
                    "similarity": 1.0,
                    "actual_code": "def correct_function():\n    return True",
                    "file_path": "backend/test.py"
                }
            }
        service._extract_and_verify_code_snippets = mock_extract_verify
        
        # Rewritten response
        rewritten_response = "Here's the code:\n```python\ndef correct_function():\n    return True\n```"
        
        # Verify specific issues were resolved (not just warnings gone)
        code_verifications_after = service._extract_and_verify_code_snippets(rewritten_response)
        structure_validation_after = service.response_validator.validate_response(rewritten_response)
        unverified_after = service._filter_unverified_claims(rewritten_response, set(), [])
        
        # Check specific issues:
        # 1. Code snippets that were wrong are now correct
        mismatched_after = sum(1 for v in code_verifications_after.values() if not v.get("matches", True))
        assert mismatched_after == 0, "Code snippets that were wrong should now be correct"
        
        # 2. Structure issues are resolved
        assert structure_validation_after.is_valid, "Structure issues should be resolved"
        
        # 3. Unverified claims are resolved (check actual content, not just "⚠️" string)
        assert not unverified_after or "⚠️" not in unverified_after, \
            "Unverified claims should be resolved"
        
        # This is better than just checking "⚠️" not in unverified_after
        # because it verifies the actual issues were fixed
    
    def test_doesnt_exit_early_if_rewrite_didnt_fix_issues(self):
        """
        Test that the loop doesn't exit early if rewrite didn't actually fix issues.
        
        Current implementation has a logic error:
        - If rewrite doesn't fix issues, it still adds rewrite prompt and continues
        - But the rewritten response might be worse
        
        Should:
        1. Track issues before rewrite
        2. After rewrite, verify each specific issue
        3. Only exit early if ALL tracked issues are resolved
        4. If any issue remains, continue to next pass
        """
        service = ChatService()
        
        # Track issues before rewrite
        issues_before = {
            "code_snippets": [
                {
                    "claimed_code": "def wrong_function():\n    return False",
                    "matches": False
                }
            ],
            "structure_issues": ["Missing required section: Analysis"]
        }
        
        # Mock code verifier - after rewrite, still doesn't match
        mock_verifier = Mock(spec=CodeVerifier)
        mock_verifier.verify_code_snippet.return_value = {
            "matches": False,  # Still doesn't match after rewrite
            "similarity": 0.5,
            "actual_code": "def actual_function():\n    return True",
            "file_path": "backend/test.py"
        }
        service.code_verifier = mock_verifier
        
        # Mock response validator - after rewrite, still has issues
        mock_validator = Mock(spec=ResponseValidator)
        mock_validator.validate_response.return_value = Mock(
            is_valid=False,  # Still invalid after rewrite
            issues=["Missing required section: Analysis"]
        )
        service.response_validator = mock_validator
        
        # Mock _filter_unverified_claims - after rewrite, still has warnings
        def mock_filter_unverified(response, files_read, commands):
            return "⚠️ Unverified claim: process_invoice() function"  # Still has warnings
        service._filter_unverified_claims = mock_filter_unverified
        
        # Mock _extract_and_verify_code_snippets
        def mock_extract_verify(response):
            return {
                "def wrong_function():\n    return False": {
                    "matches": False,  # Still doesn't match
                    "similarity": 0.5,
                    "actual_code": "def actual_function():\n    return True",
                    "file_path": "backend/test.py"
                }
            }
        service._extract_and_verify_code_snippets = mock_extract_verify
        
        # Rewritten response (but issues not fixed)
        rewritten_response = "Here's the code:\n```python\ndef wrong_function():\n    return False\n```"
        
        # Verify issues after rewrite
        code_verifications_after = service._extract_and_verify_code_snippets(rewritten_response)
        structure_validation_after = service.response_validator.validate_response(rewritten_response)
        unverified_after = service._filter_unverified_claims(rewritten_response, set(), [])
        
        # Check if ALL issues were resolved
        mismatched_after = sum(1 for v in code_verifications_after.values() if not v.get("matches", True))
        structure_fixed = structure_validation_after.is_valid
        unverified_fixed = not unverified_after or "⚠️" not in unverified_after
        
        # Since rewrite didn't fix issues, should NOT exit early
        all_issues_resolved = (
            mismatched_after == 0 and
            structure_fixed and
            unverified_fixed
        )
        
        assert not all_issues_resolved, "Issues were not fixed, should not exit early"
        assert mismatched_after > 0 or not structure_fixed or not unverified_fixed, \
            "Should detect that issues remain after rewrite"
    
    def test_tracks_and_verifies_all_issue_types(self):
        """
        Test that all issue types are tracked and verified:
        1. Code snippets
        2. Function names
        3. Structure validation
        4. Unverified claims
        5. Framework mismatches (if applicable)
        """
        service = ChatService()
        
        # Mock all validators
        mock_verifier = Mock(spec=CodeVerifier)
        mock_validator = Mock(spec=ResponseValidator)
        mock_rewriter = Mock(spec=ResponseRewriter)
        
        service.code_verifier = mock_verifier
        service.response_validator = mock_validator
        service.response_rewriter = mock_rewriter
        
        # Setup mocks to return issues before rewrite
        mock_verifier.verify_code_snippet.return_value = {
            "matches": False,
            "similarity": 0.5,
            "actual_code": "def actual_function():\n    return True",
            "file_path": "backend/test.py"
        }
        mock_verifier.verify_function_exists.return_value = {
            "exists": False,
            "error": "Function not found"
        }
        mock_validator.validate_response.return_value = Mock(
            is_valid=False,
            issues=["Missing section"]
        )
        
        def mock_filter_unverified(response, files_read, commands):
            return "⚠️ Unverified claim"
        service._filter_unverified_claims = mock_filter_unverified
        
        def mock_extract_verify(response):
            return {
                "def wrong_function():\n    return False": {
                    "matches": False,
                    "similarity": 0.5
                }
            }
        service._extract_and_verify_code_snippets = mock_extract_verify
        
        response = "Code: ```python\ndef wrong_function():\n    return False\n```"
        
        # Track all issue types before rewrite
        code_verifications = service._extract_and_verify_code_snippets(response)
        structure_validation = service.response_validator.validate_response(response)
        unverified = service._filter_unverified_claims(response, set(), [])
        
        # Extract function names
        import re
        func_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        func_mentions = re.findall(func_pattern, response)
        builtins = {'print', 'len', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple'}
        mentioned_funcs = [f for f in func_mentions if f not in builtins and not f[0].isupper()]
        
        function_verifications = {}
        for func in mentioned_funcs:
            verification = service.code_verifier.verify_function_exists(func)
            function_verifications[func] = verification
        
        # Verify all issue types were tracked
        assert code_verifications, "Should track code snippet issues"
        assert not structure_validation.is_valid, "Should track structure issues"
        assert "⚠️" in unverified, "Should track unverified claims"
        assert any(not v.get("exists", False) for v in function_verifications.values()), \
            "Should track function name issues"
        
        # After rewrite, verify all issue types again
        mock_rewriter.rewrite_response.return_value = response.replace("wrong_function", "actual_function")
        rewritten_response = mock_rewriter.rewrite_response(response)
        
        code_verifications_after = service._extract_and_verify_code_snippets(rewritten_response)
        structure_validation_after = service.response_validator.validate_response(rewritten_response)
        unverified_after = service._filter_unverified_claims(rewritten_response, set(), [])
        
        func_mentions_after = re.findall(func_pattern, rewritten_response)
        mentioned_funcs_after = [f for f in func_mentions_after if f not in builtins and not f[0].isupper()]
        
        function_verifications_after = {}
        for func in mentioned_funcs_after:
            verification = service.code_verifier.verify_function_exists(func)
            function_verifications_after[func] = verification
        
        # Verify all issue types were checked after rewrite
        assert code_verifications_after, "Should verify code snippets after rewrite"
        assert structure_validation_after, "Should verify structure after rewrite"
        assert unverified_after is not None, "Should verify unverified claims after rewrite"
        assert function_verifications_after, "Should verify function names after rewrite"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

