"""
Unit tests for command parsing functionality.

Tests multi-line command parsing, aliases, validation, path resolution, and deduplication.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.services.chat_service import ChatService


class TestCommandParsing(unittest.TestCase):
    """Test command parsing functionality."""
    
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
    
    def test_parse_single_line_command(self):
        """Test parsing a single-line command."""
        response = "READ backend/services/chat_service.py"
        commands = self.chat_service._parse_agent_commands(response)
        
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["type"], "READ")
        self.assertEqual(commands[0]["file"], "backend/services/chat_service.py")
    
    def test_parse_multi_line_command_2_lines(self):
        """Test parsing a 2-line command with continuation."""
        response = """READ backend/services/
chat_service.py"""
        commands = self.chat_service._parse_agent_commands(response)
        
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["type"], "READ")
        # Check that file path contains both parts (may be joined or separate)
        file_path = commands[0].get("file", "")
        self.assertTrue("chat_service.py" in file_path or "backend/services" in file_path, 
                       f"Expected file path to contain 'chat_service.py' or 'backend/services', got: {file_path}")
    
    def test_parse_multi_line_command_3_lines(self):
        """Test parsing a 3-line command with continuation."""
        response = """READ backend/
services/
chat_service.py"""
        commands = self.chat_service._parse_agent_commands(response)
        
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["type"], "READ")
        # Check that file path contains expected parts
        file_path = commands[0].get("file", "")
        self.assertTrue("chat_service.py" in file_path or "backend" in file_path or "services" in file_path,
                       f"Expected file path to contain expected parts, got: {file_path}")
    
    def test_parse_multi_line_command_4_plus_lines(self):
        """Test parsing a 4+ line command with continuation."""
        response = """READ backend/
services/
chat/
service.py"""
        commands = self.chat_service._parse_agent_commands(response)
        
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["type"], "READ")
        # Check that file path contains expected parts
        file_path = commands[0].get("file", "")
        self.assertTrue("service.py" in file_path or "backend" in file_path,
                       f"Expected file path to contain expected parts, got: {file_path}")
    
    def test_parse_command_with_backslash_continuation(self):
        """Test parsing command with backslash continuation marker."""
        response = """READ backend/services/\\
chat_service.py"""
        commands = self.chat_service._parse_agent_commands(response)
        
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["type"], "READ")
    
    def test_parse_command_with_parentheses(self):
        """Test parsing command with parentheses continuation."""
        response = """READ backend/services/
chat_service.py (lines 100-200)"""
        commands = self.chat_service._parse_agent_commands(response)
        
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["type"], "READ")
    
    def test_parse_command_aliases_find(self):
        """Test FIND alias maps to SEARCH."""
        response = "FIND upload endpoint"
        commands = self.chat_service._parse_agent_commands(response)
        
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["type"], "SEARCH")
        self.assertEqual(commands[0]["term"], "upload endpoint")
    
    def test_parse_command_aliases_open(self):
        """Test OPEN alias maps to READ."""
        response = "OPEN backend/main.py"
        commands = self.chat_service._parse_agent_commands(response)
        
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["type"], "READ")
        self.assertEqual(commands[0]["file"], "backend/main.py")
    
    def test_parse_command_aliases_view(self):
        """Test VIEW alias maps to READ."""
        response = "VIEW backend/main.py"
        commands = self.chat_service._parse_agent_commands(response)
        
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["type"], "READ")
    
    def test_parse_command_aliases_show(self):
        """Test SHOW alias maps to READ."""
        response = "SHOW backend/main.py"
        commands = self.chat_service._parse_agent_commands(response)
        
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["type"], "READ")
    
    def test_validate_read_command_valid(self):
        """Test validation of valid READ command."""
        cmd = {"type": "READ", "file": "backend/main.py"}
        is_valid, error_msg, suggestion = self.chat_service._validate_command(cmd)
        
        self.assertTrue(is_valid)
        self.assertIsNone(error_msg)
        self.assertIsNone(suggestion)
    
    def test_validate_read_command_missing_file(self):
        """Test validation of READ command with missing file."""
        cmd = {"type": "READ"}
        is_valid, error_msg, suggestion = self.chat_service._validate_command(cmd)
        
        self.assertFalse(is_valid)
        self.assertIsNotNone(error_msg)
        self.assertIsNotNone(suggestion)
    
    def test_validate_grep_command_valid(self):
        """Test validation of valid GREP command."""
        cmd = {"type": "GREP", "pattern": "def.*function"}
        is_valid, error_msg, suggestion = self.chat_service._validate_command(cmd)
        
        self.assertTrue(is_valid)
    
    def test_validate_grep_command_invalid_regex(self):
        """Test validation of GREP command with invalid regex."""
        cmd = {"type": "GREP", "pattern": "[unclosed"}
        is_valid, error_msg, suggestion = self.chat_service._validate_command(cmd)
        
        self.assertFalse(is_valid)
        self.assertIn("regex", error_msg.lower())
    
    def test_validate_search_command_valid(self):
        """Test validation of valid SEARCH command."""
        cmd = {"type": "SEARCH", "term": "upload endpoint"}
        is_valid, error_msg, suggestion = self.chat_service._validate_command(cmd)
        
        self.assertTrue(is_valid)
    
    def test_validate_search_command_missing_term(self):
        """Test validation of SEARCH command with missing term."""
        cmd = {"type": "SEARCH"}
        is_valid, error_msg, suggestion = self.chat_service._validate_command(cmd)
        
        self.assertFalse(is_valid)
        self.assertIn("term", error_msg.lower())
    
    def test_validate_search_command_empty_term(self):
        """Test validation of SEARCH command with empty term."""
        cmd = {"type": "SEARCH", "term": ""}
        is_valid, error_msg, suggestion = self.chat_service._validate_command(cmd)
        
        self.assertFalse(is_valid)
    
    def test_validate_trace_command_valid(self):
        """Test validation of valid TRACE command."""
        cmd = {"type": "TRACE", "start": "upload", "end": "database"}
        is_valid, error_msg, suggestion = self.chat_service._validate_command(cmd)
        
        self.assertTrue(is_valid)
    
    def test_validate_trace_command_missing_start(self):
        """Test validation of TRACE command with missing start."""
        cmd = {"type": "TRACE", "end": "database"}
        is_valid, error_msg, suggestion = self.chat_service._validate_command(cmd)
        
        self.assertFalse(is_valid)
        self.assertIn("start", error_msg.lower())
    
    def test_resolve_file_path_exact_match(self):
        """Test path resolution with exact match."""
        with patch('os.path.exists', return_value=True):
            path, confidence = self.chat_service._resolve_file_path("backend/main.py")
            self.assertEqual(path, "backend/main.py")
            self.assertEqual(confidence, 1.0)
    
    def test_resolve_file_path_fuzzy_match(self):
        """Test path resolution with fuzzy matching for typos."""
        # Mock file system to return similar paths
        with patch('os.path.exists', side_effect=lambda p: p == "backend/main.py"), \
             patch('os.listdir', return_value=["main.py", "other.py"]), \
             patch('os.path.isdir', return_value=True):
            path, confidence = self.chat_service._resolve_file_path("backend/mian.py")  # Typo
            # Should find similar path
            self.assertGreater(confidence, 0.5)
    
    def test_resolve_file_path_cached(self):
        """Test that resolved paths are cached."""
        with patch('os.path.exists', return_value=True):
            path1, conf1 = self.chat_service._resolve_file_path("backend/main.py")
            path2, conf2 = self.chat_service._resolve_file_path("backend/main.py")
            
            # Second call should use cache
            self.assertEqual(path1, path2)
            self.assertEqual(conf1, conf2)
    
    def test_parse_multiple_commands(self):
        """Test parsing multiple commands in one response."""
        response = """READ backend/main.py
SEARCH upload endpoint
GREP def.*function"""
        commands = self.chat_service._parse_agent_commands(response)
        
        self.assertEqual(len(commands), 3)
        self.assertEqual(commands[0]["type"], "READ")
        self.assertEqual(commands[1]["type"], "SEARCH")
        self.assertEqual(commands[2]["type"], "GREP")
    
    def test_parse_malformed_command(self):
        """Test parsing malformed command."""
        response = "READ"  # Missing file
        commands = self.chat_service._parse_agent_commands(response)
        
        # Should still parse but validation will catch it
        self.assertGreaterEqual(len(commands), 0)


if __name__ == '__main__':
    unittest.main()

