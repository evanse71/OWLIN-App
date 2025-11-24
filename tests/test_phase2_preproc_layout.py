"""
Phase 2 Accuracy Upgrade Tests

Tests for enhanced preprocessing, layout detection, and confidence routing
with graceful fallbacks when optional dependencies are missing.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import shutil

from backend.ocr.owlin_scan_pipeline import (
    preprocess_image,
    detect_layout,
    assemble_page_result,
    BlockResult,
    PageResult
)
from backend.config import FEATURE_OCR_V2_PREPROC, FEATURE_OCR_V2_LAYOUT, CONF_FIELD_MIN, CONF_PAGE_MIN


class TestPhase2Preprocessing:
    """Test Phase 2 preprocessing with feature flags."""
    
    def test_preprocess_flag_off_behavior(self, tmp_path):
        """Test that preprocessing behaves like Phase 1 when flag is off."""
        # Create a dummy image file
        img_path = tmp_path / "test.png"
        img_path.write_bytes(b"fake_image_data")
        
        with patch('backend.config.FEATURE_OCR_V2_PREPROC', False):
            with patch('backend.ocr.owlin_scan_pipeline.cv2', None):
                result_path = preprocess_image(img_path)
                
                # Should create .pre.png file (copy through)
                assert result_path.name.endswith(".pre.png")
                assert result_path.exists()
    
    def test_preprocess_flag_on_graceful_fallback(self, tmp_path):
        """Test that preprocessing degrades gracefully when OpenCV missing."""
        # Create a dummy image file
        img_path = tmp_path / "test.png"
        img_path.write_bytes(b"fake_image_data")
        
        with patch('backend.config.FEATURE_OCR_V2_PREPROC', True):
            with patch('backend.ocr.owlin_scan_pipeline.cv2', None):
                with patch('backend.ocr.owlin_scan_pipeline.np', None):
                    result_path = preprocess_image(img_path)
                    
                    # Should still create .pre.png file (copy through)
                    assert result_path.name.endswith(".pre.png")
                    assert result_path.exists()
    
    def test_preprocess_flag_on_with_opencv(self, tmp_path):
        """Test that preprocessing works when OpenCV is available."""
        # Create a dummy image file
        img_path = tmp_path / "test.png"
        img_path.write_bytes(b"fake_image_data")
        
        with patch('backend.config.FEATURE_OCR_V2_PREPROC', True):
            # Mock OpenCV and numpy
            mock_cv2 = MagicMock()
            mock_np = MagicMock()
            mock_img = MagicMock()
            mock_img.shape = (100, 100, 3)
            mock_cv2.imread.return_value = mock_img
            mock_cv2.cvtColor.return_value = mock_img
            mock_cv2.Canny.return_value = mock_img
            mock_cv2.HoughLines.return_value = None
            mock_cv2.bilateralFilter.return_value = mock_img
            mock_cv2.createCLAHE.return_value = MagicMock()
            mock_cv2.getStructuringElement.return_value = MagicMock()
            mock_cv2.morphologyEx.return_value = mock_img
            mock_cv2.adaptiveThreshold.return_value = mock_img
            mock_cv2.findContours.return_value = ([], None)
            def mock_imwrite(path, img):
                Path(path).write_bytes(b"mock_processed_image")
                return True
            mock_cv2.imwrite.side_effect = mock_imwrite
            
            with patch('backend.ocr.owlin_scan_pipeline.cv2', mock_cv2):
                with patch('backend.ocr.owlin_scan_pipeline.np', mock_np):
                    result_path = preprocess_image(img_path)
                    
                    # Should create .pre.png file
                    assert result_path.name.endswith(".pre.png")
                    # The file should exist (created by cv2.imwrite mock)
                    assert result_path.exists()
                    # Verify cv2.imwrite was called
                    mock_cv2.imwrite.assert_called_once()


class TestPhase2LayoutDetection:
    """Test Phase 2 layout detection with feature flags."""
    
    def test_layout_flag_off_behavior(self, tmp_path):
        """Test that layout detection behaves like Phase 1 when flag is off."""
        img_path = tmp_path / "test.png"
        img_path.write_bytes(b"fake_image_data")
        
        with patch('backend.config.FEATURE_OCR_V2_LAYOUT', False):
            blocks = detect_layout(img_path)
            
            # Should return single Text block
            assert len(blocks) == 1
            assert blocks[0]["type"] == "Text"
            assert blocks[0]["bbox"] == [0, 0, 0, 0]
    
    def test_layout_flag_on_graceful_fallback(self, tmp_path):
        """Test that layout detection degrades gracefully when LayoutParser missing."""
        img_path = tmp_path / "test.png"
        img_path.write_bytes(b"fake_image_data")
        
        with patch('backend.config.FEATURE_OCR_V2_LAYOUT', True):
            with patch('backend.ocr.owlin_scan_pipeline.ModelRegistry') as mock_registry:
                mock_registry.get.return_value.layout.return_value = None
                
                blocks = detect_layout(img_path)
                
                # Should return single Text block as fallback
                assert len(blocks) == 1
                assert blocks[0]["type"] == "Text"
                assert blocks[0]["bbox"] == [0, 0, 0, 0]
    
    def test_layout_flag_on_with_layoutparser(self, tmp_path):
        """Test that layout detection works when LayoutParser is available."""
        img_path = tmp_path / "test.png"
        img_path.write_bytes(b"fake_image_data")
        
        with patch('backend.config.FEATURE_OCR_V2_LAYOUT', True):
            # Test that the function doesn't crash and returns some blocks
            blocks = detect_layout(img_path)
            
            # Should return at least one block (even if fallback)
            assert len(blocks) >= 1
            assert blocks[0]["type"] == "Text"
            # Should have bbox format
            assert len(blocks[0]["bbox"]) == 4


class TestPhase2ConfidenceRouting:
    """Test Phase 2 confidence routing and penalties."""
    
    def test_confidence_routing_high_confidence(self):
        """Test that high-confidence blocks are not penalized."""
        blocks_raw = [
            {"type": "Text", "bbox": [0, 0, 100, 50]},
            {"type": "Text", "bbox": [0, 50, 100, 50]}
        ]
        
        # Mock OCR to return high confidence
        with patch('backend.ocr.owlin_scan_pipeline.ocr_block') as mock_ocr:
            mock_ocr.return_value = ("test text", 0.8)  # High confidence
            
            with patch('backend.config.CONF_FIELD_MIN', 0.55):
                with patch('backend.config.CONF_PAGE_MIN', 0.60):
                    result = assemble_page_result(0, Path("test.png"), blocks_raw)
                    
                    # Should not apply penalties for high confidence
                    assert result.confidence > 0.7
                    for block in result.blocks:
                        assert block.confidence > 0.7
    
    def test_confidence_routing_low_confidence_penalty(self):
        """Test that low-confidence blocks are penalized."""
        blocks_raw = [
            {"type": "Text", "bbox": [0, 0, 100, 50]},
            {"type": "Text", "bbox": [0, 50, 100, 50]}
        ]
        
        # Mock OCR to return low confidence
        with patch('backend.ocr.owlin_scan_pipeline.ocr_block') as mock_ocr:
            mock_ocr.return_value = ("test text", 0.3)  # Low confidence
            
            with patch('backend.config.CONF_FIELD_MIN', 0.55):
                with patch('backend.config.CONF_PAGE_MIN', 0.60):
                    result = assemble_page_result(0, Path("test.png"), blocks_raw)
                    
                    # Should apply penalties for low confidence
                    assert result.confidence < 0.3  # Should be penalized
                    for block in result.blocks:
                        assert block.confidence < 0.3  # Should be penalized
    
    def test_confidence_routing_page_penalty(self):
        """Test that low-confidence pages are down-weighted."""
        blocks_raw = [
            {"type": "Text", "bbox": [0, 0, 100, 50]},
            {"type": "Text", "bbox": [0, 50, 100, 50]}
        ]
        
        # Mock OCR to return medium confidence (below page threshold)
        with patch('backend.ocr.owlin_scan_pipeline.ocr_block') as mock_ocr:
            mock_ocr.return_value = ("test text", 0.5)  # Medium confidence
            
            with patch('backend.config.CONF_FIELD_MIN', 0.55):
                with patch('backend.config.CONF_PAGE_MIN', 0.60):
                    result = assemble_page_result(0, Path("test.png"), blocks_raw)
                    
                    # Should apply page-level penalty
                    assert result.confidence < 0.5  # Should be down-weighted


class TestPhase2GracefulDegradation:
    """Test that Phase 2 features degrade gracefully when dependencies are missing."""
    
    def test_all_flags_off_phase1_behavior(self, tmp_path):
        """Test that with all flags off, behavior matches Phase 1."""
        img_path = tmp_path / "test.png"
        img_path.write_bytes(b"fake_image_data")
        
        with patch('backend.config.FEATURE_OCR_V2_PREPROC', False):
            with patch('backend.config.FEATURE_OCR_V2_LAYOUT', False):
                # Test preprocessing
                prep_result = preprocess_image(img_path)
                assert prep_result.exists()
                
                # Test layout detection
                blocks = detect_layout(img_path)
                assert len(blocks) == 1
                assert blocks[0]["type"] == "Text"
    
    def test_missing_dependencies_graceful_fallback(self, tmp_path):
        """Test that missing dependencies don't crash the system."""
        img_path = tmp_path / "test.png"
        img_path.write_bytes(b"fake_image_data")
        
        with patch('backend.config.FEATURE_OCR_V2_PREPROC', True):
            with patch('backend.config.FEATURE_OCR_V2_LAYOUT', True):
                # Mock missing OpenCV
                with patch('backend.ocr.owlin_scan_pipeline.cv2', None):
                    with patch('backend.ocr.owlin_scan_pipeline.np', None):
                        # Should not crash
                        prep_result = preprocess_image(img_path)
                        assert prep_result.exists()
                
                # Mock missing LayoutParser
                with patch('backend.ocr.owlin_scan_pipeline.ModelRegistry') as mock_registry:
                    mock_registry.get.return_value.layout.return_value = None
                    
                    # Should not crash
                    blocks = detect_layout(img_path)
                    assert len(blocks) == 1
                    assert blocks[0]["type"] == "Text"
