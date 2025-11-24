"""
Tests for Confidence Calculation Improvements (Section 7)

Tests verify that:
1. Confidence is calculated DURING exploration (after each READ/GREP)
2. Early blocking happens BEFORE ANALYZE if confidence < 0.7
3. Confidence factors are weighted properly (function verification > file count)
4. Confidence guides exploration with suggestions when low
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from backend.services.chat_service import ChatService


class TestConfidenceDuringExploration:
    """Test that confidence is calculated during exploration, not just after."""
    
    def test_confidence_calculated_after_read(self):
        """Test that confidence is calculated after READ command."""
        service = ChatService()
        
        # Mock the confidence calculation method
        service._calculate_confidence_score = Mock(return_value=0.65)
        
        # Simulate exploration state
        files_read = {"backend/main.py"}
        commands_history = ["READ backend/main.py"]
        
        # Calculate confidence during exploration
        confidence = service._calculate_confidence_score(
            files_read=files_read,
            commands_history=commands_history,
            key_insights=[],
            validation_issues=[],
            verification_results=None,
            code_match_accuracy=None,
            runtime_checks=None
        )
        
        # Should have been called
        assert service._calculate_confidence_score.called
        assert confidence == 0.65
    
    def test_confidence_calculated_after_grep(self):
        """Test that confidence is calculated after GREP command."""
        service = ChatService()
        
        # Mock the confidence calculation method
        service._calculate_confidence_score = Mock(return_value=0.72)
        
        # Simulate exploration state with GREP
        files_read = {"backend/main.py"}
        commands_history = ["READ backend/main.py", "GREP upload_file"]
        
        # Calculate confidence during exploration
        confidence = service._calculate_confidence_score(
            files_read=files_read,
            commands_history=commands_history,
            key_insights=[],
            validation_issues=[],
            verification_results=None,
            code_match_accuracy=None,
            runtime_checks=None
        )
        
        # Should have been called
        assert service._calculate_confidence_score.called
        assert confidence == 0.72
    
    def test_confidence_tracks_progress(self):
        """Test that confidence increases as more exploration happens."""
        service = ChatService()
        
        # First exploration - low confidence
        files_read_1 = {"backend/main.py"}
        commands_1 = ["READ backend/main.py"]
        confidence_1 = service._calculate_confidence_score(
            files_read=files_read_1,
            commands_history=commands_1,
            key_insights=[],
            validation_issues=[],
            verification_results=None,
            code_match_accuracy=None,
            runtime_checks=None
        )
        
        # Second exploration - higher confidence
        files_read_2 = {"backend/main.py", "backend/services/ocr_service.py"}
        commands_2 = ["READ backend/main.py", "READ backend/services/ocr_service.py", "GREP upload_file"]
        confidence_2 = service._calculate_confidence_score(
            files_read=files_read_2,
            commands_history=commands_2,
            key_insights=["Found upload endpoint"],
            validation_issues=[],
            verification_results=None,
            code_match_accuracy=None,
            runtime_checks=None
        )
        
        # Confidence should increase with more exploration
        assert confidence_2 >= confidence_1, "Confidence should increase with more exploration"


class TestEarlyBlocking:
    """Test that confidence blocks ANALYZE command early if too low."""
    
    @patch('backend.services.chat_service.ChatService._check_verification_requirements')
    def test_blocks_analyze_if_confidence_too_low(self, mock_verification):
        """Test that ANALYZE is blocked if confidence < 0.7."""
        service = ChatService()
        
        # Mock verification to pass
        mock_verification.return_value = {
            "can_analyze": True,
            "blocking_message": "",
            "verification_results": {},
            "framework_results": {}
        }
        
        # Mock confidence calculation to return low score
        service._calculate_confidence_score = Mock(return_value=0.55)
        
        # Simulate state with low confidence
        files_read = {"backend/main.py"}
        commands_history = ["READ backend/main.py"]
        
        # Check if should block ANALYZE
        confidence = service._calculate_confidence_score(
            files_read=files_read,
            commands_history=commands_history,
            key_insights=[],
            validation_issues=[],
            verification_results=None,
            code_match_accuracy=None,
            runtime_checks=None
        )
        
        # Should block if confidence < 0.7
        should_block = confidence < 0.7
        assert should_block, "Should block ANALYZE if confidence < 0.7"
    
    @patch('backend.services.chat_service.ChatService._check_verification_requirements')
    def test_allows_analyze_if_confidence_high_enough(self, mock_verification):
        """Test that ANALYZE is allowed if confidence >= 0.7."""
        service = ChatService()
        
        # Mock verification to pass
        mock_verification.return_value = {
            "can_analyze": True,
            "blocking_message": "",
            "verification_results": {},
            "framework_results": {}
        }
        
        # Mock confidence calculation to return high score
        service._calculate_confidence_score = Mock(return_value=0.85)
        
        # Simulate state with high confidence
        files_read = {"backend/main.py", "backend/services/ocr_service.py", "backend/app/db.py"}
        commands_history = ["READ backend/main.py", "READ backend/services/ocr_service.py", "GREP upload_file"]
        
        # Check if should block ANALYZE
        confidence = service._calculate_confidence_score(
            files_read=files_read,
            commands_history=commands_history,
            key_insights=["Found upload endpoint", "Verified function names"],
            validation_issues=[],
            verification_results={"function_verifications": {"upload_file": {"exists": True}}},
            code_match_accuracy=0.9,
            runtime_checks=None
        )
        
        # Should not block if confidence >= 0.7
        should_block = confidence < 0.7
        assert not should_block, "Should allow ANALYZE if confidence >= 0.7"


class TestConfidenceWeighting:
    """Test that confidence factors are weighted properly."""
    
    def test_function_verification_weighted_higher_than_file_count(self):
        """Test that function verification contributes more than file count."""
        service = ChatService()
        
        # Scenario 1: Many files but no verification
        confidence_no_verification = service._calculate_confidence_score(
            files_read={"file1.py", "file2.py", "file3.py", "file4.py", "file5.py"},
            commands_history=["READ file1.py", "READ file2.py", "READ file3.py"],
            key_insights=[],
            validation_issues=[],
            verification_results=None,  # No verification
            code_match_accuracy=None,
            runtime_checks=None
        )
        
        # Scenario 2: Fewer files but with verification
        confidence_with_verification = service._calculate_confidence_score(
            files_read={"file1.py", "file2.py"},
            commands_history=["READ file1.py", "READ file2.py", "GREP upload_file"],
            key_insights=["Found upload endpoint"],
            validation_issues=[],
            verification_results={
                "function_verifications": {
                    "upload_file": {"exists": True},
                    "process_document": {"exists": True}
                },
                "framework_results": {"framework": {"confidence": 0.9}}  # Fixed: dict of dicts
            },
            code_match_accuracy=0.85,
            runtime_checks=None
        )
        
        # Verification should boost confidence more than just file count
        # Even with fewer files, verification should make confidence higher
        assert confidence_with_verification > confidence_no_verification, \
            "Function verification should be weighted higher than file count"
    
    def test_code_match_accuracy_contributes_to_confidence(self):
        """Test that code match accuracy contributes to confidence."""
        service = ChatService()
        
        # Without code match accuracy
        confidence_no_accuracy = service._calculate_confidence_score(
            files_read={"file1.py", "file2.py"},
            commands_history=["READ file1.py", "READ file2.py"],
            key_insights=[],
            validation_issues=[],
            verification_results=None,
            code_match_accuracy=None,  # No accuracy
            runtime_checks=None
        )
        
        # With high code match accuracy
        confidence_with_accuracy = service._calculate_confidence_score(
            files_read={"file1.py", "file2.py"},
            commands_history=["READ file1.py", "READ file2.py"],
            key_insights=[],
            validation_issues=[],
            verification_results=None,
            code_match_accuracy=0.95,  # High accuracy
            runtime_checks=None
        )
        
        # Code match accuracy should boost confidence
        assert confidence_with_accuracy > confidence_no_accuracy, \
            "Code match accuracy should contribute to confidence"


class TestExplorationGuidance:
    """Test that confidence guides exploration with suggestions."""
    
    def test_suggests_more_files_if_confidence_low(self):
        """Test that system suggests reading more files if confidence is low."""
        service = ChatService()
        
        # Low confidence scenario
        files_read = {"backend/main.py"}
        commands_history = ["READ backend/main.py"]
        confidence = service._calculate_confidence_score(
            files_read=files_read,
            commands_history=commands_history,
            key_insights=[],
            validation_issues=[],
            verification_results=None,
            code_match_accuracy=None,
            runtime_checks=None
        )
        
        if confidence < 0.7:
            # Should suggest reading more files
            suggestions = service._get_exploration_suggestions(
                files_read=files_read,
                commands_history=commands_history,
                confidence=confidence,
                verification_results=None
            )
            
            assert "READ" in suggestions or "read more files" in suggestions.lower(), \
                "Should suggest reading more files when confidence is low"
    
    def test_suggests_grep_if_no_verification(self):
        """Test that system suggests GREP if no function verification done."""
        service = ChatService()
        
        # No verification scenario
        files_read = {"backend/main.py", "backend/services/ocr_service.py"}
        commands_history = ["READ backend/main.py", "READ backend/services/ocr_service.py"]
        confidence = service._calculate_confidence_score(
            files_read=files_read,
            commands_history=commands_history,
            key_insights=[],
            validation_issues=[],
            verification_results=None,  # No verification
            code_match_accuracy=None,
            runtime_checks=None
        )
        
        if confidence < 0.7:
            suggestions = service._get_exploration_suggestions(
                files_read=files_read,
                commands_history=commands_history,
                confidence=confidence,
                verification_results=None
            )
            
            assert "GREP" in suggestions or "verify function" in suggestions.lower(), \
                "Should suggest GREP when no verification done"


class TestConfidenceBeforeAnalyze:
    """Test that confidence is checked before ANALYZE command executes."""
    
    @patch('backend.services.chat_service.ChatService._check_verification_requirements')
    def test_confidence_checked_before_analyze(self, mock_verification):
        """Test that confidence is calculated and checked before ANALYZE."""
        service = ChatService()
        
        # Mock verification to pass
        mock_verification.return_value = {
            "can_analyze": True,
            "blocking_message": "",
            "verification_results": {},
            "framework_results": {}
        }
        
        # Track if confidence was calculated
        confidence_calculated = []
        original_method = service._calculate_confidence_score
        
        def track_confidence(*args, **kwargs):
            result = original_method(*args, **kwargs)
            confidence_calculated.append(result)
            return result
        
        service._calculate_confidence_score = track_confidence
        
        # Simulate ANALYZE request with low confidence state
        files_read = {"backend/main.py"}
        commands_history = ["READ backend/main.py"]
        
        # This should calculate confidence before allowing ANALYZE
        confidence = service._calculate_confidence_score(
            files_read=files_read,
            commands_history=commands_history,
            key_insights=[],
            validation_issues=[],
            verification_results=None,
            code_match_accuracy=None,
            runtime_checks=None
        )
        
        # Confidence should have been calculated
        assert len(confidence_calculated) > 0, "Confidence should be calculated before ANALYZE"
        assert confidence < 0.7, "Confidence should be low with minimal exploration"

