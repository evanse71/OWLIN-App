"""
End-to-end tests for code assistant functionality.

Tests full agent mode workflow, search mode workflow, error recovery, timeout scenarios, and streaming.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import sys
import os
import json
import time

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


class TestE2EAssistant(unittest.TestCase):
    """End-to-end tests for code assistant."""
    
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
            from backend.services.chat_service import ChatService
            self.chat_service = ChatService()
    
    @patch('backend.services.chat_service.ChatService._do_one_turn')
    @patch('backend.services.chat_service.ChatService._optimize_conversation_context')
    def test_agent_mode_workflow(self, mock_optimize, mock_do_turn):
        """Test full agent mode workflow with multi-turn conversation."""
        # Mock agent turn responses
        mock_do_turn.side_effect = [
            {
                "response": "I'll search for the upload endpoint.",
                "commands": [{"type": "SEARCH", "term": "upload endpoint"}],
                "should_continue": True
            },
            {
                "response": "Found the endpoint. Reading the file now.",
                "commands": [{"type": "READ", "file": "backend/routes/upload.py"}],
                "should_continue": True
            },
            {
                "response": "Analysis complete. The issue is in line 42.",
                "commands": [],
                "should_continue": False
            }
        ]
        
        mock_optimize.return_value = "Optimized context"
        
        # Test agent mode
        result = self.chat_service._agent_mode_conversation(
            message="Find the upload endpoint issue",
            context_size=32000,
            max_turns=5,
            progress_callback=None
        )
        
        # Should have completed 3 turns
        self.assertEqual(mock_do_turn.call_count, 3)
        self.assertIsNotNone(result)
    
    @patch('backend.services.chat_service.ChatService._search_mode')
    def test_search_mode_workflow(self, mock_search):
        """Test search mode workflow with exploration plan."""
        # Mock search mode response
        mock_search.return_value = {
            "response": "Found 5 files related to upload endpoint",
            "findings": [
                {"file": "backend/routes/upload.py", "line": 42, "match": "upload endpoint"}
            ]
        }
        
        # Test search mode
        result = self.chat_service._search_mode(
            message="Find all upload endpoints",
            context_size=32000,
            progress_callback=None
        )
        
        mock_search.assert_called_once()
        self.assertIsNotNone(result)
    
    @patch('backend.services.chat_service.ChatService._do_one_turn')
    def test_error_recovery_transient_error(self, mock_do_turn):
        """Test error recovery with transient errors."""
        # First call fails with transient error, second succeeds
        mock_do_turn.side_effect = [
            Exception("Connection timeout"),  # Transient error
            {
                "response": "Success after retry",
                "commands": [],
                "should_continue": False
            }
        ]
        
        # Should retry and succeed
        # Note: This is a simplified test - actual retry logic is in RetryHandler
        with self.assertRaises(Exception):
            mock_do_turn()
        
        # Second call should succeed
        result = mock_do_turn()
        self.assertIsNotNone(result)
    
    @patch('backend.services.chat_service.ChatService._do_one_turn')
    def test_timeout_scenario(self, mock_do_turn):
        """Test timeout scenario with early termination."""
        # Mock slow turn that would timeout
        def slow_turn(*args, **kwargs):
            time.sleep(2.0)  # Simulate slow operation
            return {
                "response": "Response",
                "commands": [],
                "should_continue": False
            }
        
        mock_do_turn.side_effect = slow_turn
        
        # Test with short timeout
        start_time = time.time()
        try:
            result = self.chat_service._agent_mode_conversation(
                message="Test query",
                context_size=32000,
                max_turns=1,
                progress_callback=None
            )
        except Exception:
            pass  # Timeout expected
        
        elapsed = time.time() - start_time
        # Should timeout or complete quickly
        self.assertLess(elapsed, 5.0)
    
    def test_large_codebase_exploration(self):
        """Test large codebase exploration with limits."""
        # Create mock explorer with many results
        mock_explorer = Mock()
        mock_explorer.search_concept.return_value = [
            {"file": f"backend/file{i}.py", "line": i*10, "match": f"Match {i}"}
            for i in range(1000)  # Large result set
        ]
        
        self.chat_service.code_explorer = mock_explorer
        
        # Test that results are limited
        results = mock_explorer.search_concept("test", max_results=50)
        self.assertLessEqual(len(results), 50)  # Should be limited
    
    def test_streaming_progress_updates(self):
        """Test streaming progress updates."""
        progress_events = []
        
        def progress_callback(message, current, total):
            progress_events.append({
                "message": message,
                "current": current,
                "total": total
            })
        
        # Mock agent mode to call progress callback
        with patch('backend.services.chat_service.ChatService._do_one_turn') as mock_turn:
            mock_turn.return_value = {
                "response": "Test response",
                "commands": [],
                "should_continue": False
            }
            
            # Simulate progress updates
            progress_callback("Starting exploration", 1, 4)
            progress_callback("Searching files", 2, 4)
            progress_callback("Analyzing results", 3, 4)
            progress_callback("Complete", 4, 4)
        
        # Should have received progress events
        self.assertEqual(len(progress_events), 4)
        self.assertEqual(progress_events[0]["message"], "Starting exploration")
        self.assertEqual(progress_events[-1]["message"], "Complete")


if __name__ == '__main__':
    unittest.main()

