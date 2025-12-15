"""
Integration tests for error handling functionality.

Tests error categorization, retry logic, aggregation, confidence updates, and circuit breaker.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import time

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from backend.services.chat_service import ChatService
from backend.services.retry_handler import RetryHandler, CircuitBreaker


class TestErrorHandling(unittest.TestCase):
    """Test error handling functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        with patch('backend.services.chat_service.CodeReader'), \
             patch('backend.services.chat_service.CodeExplorer'), \
             patch('backend.services.chat_service.CodeVerifier'), \
             patch('backend.services.chat_service.ResponseValidator'), \
             patch('backend.services.chat_service.RuntimeVerifier'), \
             patch('backend.services.chat_service.ArchitectureAnalyzer'), \
             patch('backend.services.chat_service.ResponseRewriter'), \
             patch('backend.services.chat_service.get_config'), \
             patch('backend.services.chat_service.RetryHandler'), \
             patch('backend.services.chat_service.get_registry'), \
             patch('backend.services.chat_service.ChatService._check_ollama_available', return_value=True):
            self.chat_service = ChatService()
    
    def test_categorize_permanent_error_file_not_found(self):
        """Test categorization of permanent error (file not found)."""
        error = FileNotFoundError("File not found: backend/missing.py")
        cmd = {"type": "READ", "file": "backend/missing.py"}
        
        category, should_retry, context = self.chat_service._categorize_error(error, cmd)
        
        self.assertEqual(category, "permanent")
        self.assertFalse(should_retry)
        self.assertEqual(context["error_type"], "FileNotFoundError")
        self.assertIn("file", context)
    
    def test_categorize_transient_error_timeout(self):
        """Test categorization of transient error (timeout)."""
        error = TimeoutError("Operation timed out")
        cmd = {"type": "SEARCH", "term": "test"}
        
        category, should_retry, context = self.chat_service._categorize_error(error, cmd)
        
        self.assertEqual(category, "transient")
        self.assertTrue(should_retry)
        self.assertEqual(context["error_type"], "TimeoutError")
    
    def test_categorize_transient_error_connection(self):
        """Test categorization of transient error (connection)."""
        error = ConnectionError("Connection refused")
        cmd = {"type": "SEARCH", "term": "test"}
        
        category, should_retry, context = self.chat_service._categorize_error(error, cmd)
        
        self.assertEqual(category, "transient")
        self.assertTrue(should_retry)
    
    def test_categorize_permanent_error_invalid_regex(self):
        """Test categorization of permanent error (invalid regex)."""
        import re
        try:
            re.compile("[unclosed")
        except re.error as error:
            cmd = {"type": "GREP", "pattern": "[unclosed"}
            category, should_retry, context = self.chat_service._categorize_error(error, cmd)
            
            self.assertEqual(category, "permanent")
            self.assertFalse(should_retry)
    
    def test_aggregate_errors_single_error(self):
        """Test aggregation of single error."""
        errors = [{
            "type": "error",
            "command": {"type": "READ", "file": "missing.py"},
            "error": "File not found",
            "error_category": "permanent",
            "error_context": {"error_type": "FileNotFoundError"},
            "suggestions": "Check file path"
        }]
        
        aggregated = self.chat_service._aggregate_errors(errors)
        
        self.assertEqual(aggregated["total"], 1)
        self.assertEqual(len(aggregated["groups"]), 1)
        self.assertIn("permanent", aggregated["summary"].lower())
        self.assertEqual(aggregated["retry_info"]["permanent_errors"], 1)
    
    def test_aggregate_errors_multiple_errors(self):
        """Test aggregation of multiple errors."""
        errors = [
            {
                "type": "error",
                "command": {"type": "READ", "file": "missing1.py"},
                "error": "File not found",
                "error_category": "permanent",
                "error_context": {"error_type": "FileNotFoundError"},
                "suggestions": "Check file path"
            },
            {
                "type": "error",
                "command": {"type": "READ", "file": "missing2.py"},
                "error": "File not found",
                "error_category": "permanent",
                "error_context": {"error_type": "FileNotFoundError"},
                "suggestions": "Check file path"
            },
            {
                "type": "error",
                "command": {"type": "SEARCH", "term": "test"},
                "error": "Timeout",
                "error_category": "transient",
                "error_context": {"error_type": "TimeoutError"},
                "suggestions": "Retry"
            }
        ]
        
        aggregated = self.chat_service._aggregate_errors(errors)
        
        self.assertEqual(aggregated["total"], 3)
        self.assertEqual(aggregated["retry_info"]["permanent_errors"], 2)
        self.assertEqual(aggregated["retry_info"]["transient_errors"], 1)
        self.assertTrue(aggregated["retry_info"]["should_retry"])
    
    def test_confidence_score_with_errors(self):
        """Test confidence score calculation with errors."""
        # Test with no errors
        score_no_errors = self.chat_service._calculate_confidence_score(
            files_read=set(["backend/main.py"]),
            commands_history=["READ backend/main.py"],
            key_insights=["Found main function"],
            validation_issues=[],
            verification_results=None,
            code_match_accuracy=None,
            runtime_checks=None,
            error_count=0,
            permanent_error_count=0
        )
        
        # Test with permanent errors
        score_with_errors = self.chat_service._calculate_confidence_score(
            files_read=set(["backend/main.py"]),
            commands_history=["READ backend/main.py"],
            key_insights=["Found main function"],
            validation_issues=[],
            verification_results=None,
            code_match_accuracy=None,
            runtime_checks=None,
            error_count=2,
            permanent_error_count=1
        )
        
        # Score with errors should be lower
        self.assertLess(score_with_errors, score_no_errors)
    
    def test_confidence_score_permanent_vs_transient(self):
        """Test that permanent errors reduce confidence more than transient."""
        # Test with permanent errors - use more context to get meaningful scores
        # Use fewer errors relative to commands to avoid zero score
        score_permanent = self.chat_service._calculate_confidence_score(
            files_read=set(["backend/main.py", "backend/routes.py", "backend/services.py", "backend/utils.py", "backend/config.py"]),
            commands_history=["READ backend/main.py", "READ backend/routes.py", "SEARCH test", "GREP pattern", "READ backend/utils.py", "READ backend/config.py"],
            key_insights=["Found main function", "Routes configured", "Utils available"],
            validation_issues=[],
            verification_results=None,
            code_match_accuracy=None,
            runtime_checks=None,
            error_count=1,  # Fewer errors
            permanent_error_count=1  # All permanent
        )
        
        # Test with transient errors - same context
        score_transient = self.chat_service._calculate_confidence_score(
            files_read=set(["backend/main.py", "backend/routes.py", "backend/services.py", "backend/utils.py", "backend/config.py"]),
            commands_history=["READ backend/main.py", "READ backend/routes.py", "SEARCH test", "GREP pattern", "READ backend/utils.py", "READ backend/config.py"],
            key_insights=["Found main function", "Routes configured", "Utils available"],
            validation_issues=[],
            verification_results=None,
            code_match_accuracy=None,
            runtime_checks=None,
            error_count=1,  # Same error count
            permanent_error_count=0  # All transient
        )
        
        # Permanent errors should reduce confidence more
        # Both should have positive scores with this context
        self.assertGreater(score_permanent, 0.0, f"Permanent error score should be positive with good context, got: {score_permanent}")
        self.assertGreater(score_transient, 0.0, f"Transient error score should be positive with good context, got: {score_transient}")
        self.assertLess(score_permanent, score_transient, f"Permanent errors should reduce confidence more than transient (permanent: {score_permanent}, transient: {score_transient})")
    
    def test_circuit_breaker_opens_after_threshold(self):
        """Test circuit breaker opens after failure threshold."""
        breaker = CircuitBreaker(failure_threshold=3, timeout=60)
        
        # Record failures up to threshold
        breaker.record_failure()
        breaker.record_failure()
        self.assertTrue(breaker.can_attempt())  # Still closed
        
        breaker.record_failure()
        self.assertFalse(breaker.can_attempt())  # Should be open
    
    def test_circuit_breaker_resets_on_success(self):
        """Test circuit breaker resets on success."""
        breaker = CircuitBreaker(failure_threshold=3, timeout=60)
        
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_success()
        
        self.assertEqual(breaker.failure_count, 0)
        self.assertEqual(breaker.state, "closed")
    
    def test_retry_handler_with_circuit_breaker(self):
        """Test RetryHandler with circuit breaker."""
        handler = RetryHandler(failure_threshold=2, timeout=1)
        
        call_count = [0]
        
        def failing_func():
            call_count[0] += 1
            raise Exception("Test error")
        
        # First attempt should fail
        with self.assertRaises(Exception):
            handler.retry_with_backoff(
                failing_func,
                max_retries=1,
                circuit_breaker_key="test_key"
            )
        
        # Second failure should open circuit
        with self.assertRaises(Exception):
            handler.retry_with_backoff(
                failing_func,
                max_retries=1,
                circuit_breaker_key="test_key"
            )
        
        # Third attempt should be blocked by circuit breaker
        with self.assertRaises(Exception) as context:
            handler.retry_with_backoff(
                failing_func,
                max_retries=1,
                circuit_breaker_key="test_key"
            )
        
        self.assertIn("Circuit breaker", str(context.exception))


if __name__ == '__main__':
    unittest.main()

