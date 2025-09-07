"""
Test fixtures for document assembly matrix
12-fixture matrix: PDF/JPG/PNG/HEIC × clean/noisy × single/multi-file
"""
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Any

# Test matrix configuration
FORMATS = ['pdf', 'jpg', 'png', 'heic']
QUALITIES = ['clean', 'noisy']
STRUCTURES = ['single', 'multi']

class AssemblyTestMatrix:
    """Generates test fixtures for assembly testing"""
    
    def __init__(self):
        self.fixtures_dir = Path(__file__).parent / "fixtures"
        self.fixtures_dir.mkdir(exist_ok=True)
        
    def generate_test_fixtures(self) -> Dict[str, Any]:
        """Generate all test fixtures for the matrix"""
        fixtures = {}
        
        for format_type in FORMATS:
            for quality in QUALITIES:
                for structure in STRUCTURES:
                    key = f"{format_type}_{quality}_{structure}"
                    fixtures[key] = self._create_fixture(format_type, quality, structure)
        
        return fixtures
    
    def _create_fixture(self, format_type: str, quality: str, structure: str) -> Dict[str, Any]:
        """Create a specific test fixture"""
        fixture = {
            'id': f"{format_type}_{quality}_{structure}",
            'format': format_type,
            'quality': quality,
            'structure': structure,
            'expected_pages': 1 if structure == 'single' else 3,
            'expected_accuracy': 0.99,  # 99% assembly accuracy requirement
            'files': self._generate_test_files(format_type, quality, structure),
            'fingerprint_data': self._generate_fingerprint_data(format_type, quality, structure)
        }
        
        return fixture
    
    def _generate_test_files(self, format_type: str, quality: str, structure: str) -> List[Dict[str, Any]]:
        """Generate test file specifications"""
        files = []
        
        if structure == 'single':
            # Single file test
            files.append({
                'filename': f"test_{format_type}_{quality}_single.{format_type}",
                'size_bytes': 1024 * 100,  # 100KB
                'mime_type': self._get_mime_type(format_type),
                'phash': self._generate_mock_phash(f"single_{format_type}_{quality}"),
                'header_text': f"Test {format_type.upper()} {quality} single file",
                'created_at': "2024-01-01T10:00:00"
            })
        else:
            # Multi-file test (3 pages)
            for page in range(3):
                files.append({
                    'filename': f"test_{format_type}_{quality}_multi_page_{page+1}.{format_type}",
                    'size_bytes': 1024 * 80,  # 80KB per page
                    'mime_type': self._get_mime_type(format_type),
                    'phash': self._generate_mock_phash(f"multi_{format_type}_{quality}_page_{page+1}"),
                    'header_text': f"Test {format_type.upper()} {quality} multi-page {page+1}",
                    'created_at': f"2024-01-01T10:00:{page:02d}"
                })
        
        return files
    
    def _generate_fingerprint_data(self, format_type: str, quality: str, structure: str) -> Dict[str, Any]:
        """Generate fingerprint data for testing"""
        if structure == 'single':
            return {
                'expected_groups': 1,
                'expected_documents': 1,
                'fingerprint_similarity_threshold': 0.8
            }
        else:
            return {
                'expected_groups': 1,  # All pages should group together
                'expected_documents': 1,  # One logical document
                'fingerprint_similarity_threshold': 0.8,
                'time_window_seconds': 60  # Within 60s window
            }
    
    def _get_mime_type(self, format_type: str) -> str:
        """Get MIME type for format"""
        mime_types = {
            'pdf': 'application/pdf',
            'jpg': 'image/jpeg',
            'png': 'image/png',
            'heic': 'image/heic'
        }
        return mime_types.get(format_type, 'application/octet-stream')
    
    def _generate_mock_phash(self, identifier: str) -> str:
        """Generate a mock perceptual hash for testing"""
        import hashlib
        return hashlib.md5(identifier.encode()).hexdigest()[:16]
    
    def create_test_batch(self, batch_id: str, fixture_key: str) -> Dict[str, Any]:
        """Create a test batch using a specific fixture"""
        fixtures = self.generate_test_fixtures()
        fixture = fixtures[fixture_key]
        
        batch = {
            'id': batch_id,
            'fixture': fixture_key,
            'expected_pages': fixture['expected_pages'],
            'expected_accuracy': fixture['expected_accuracy'],
            'files': fixture['files'],
            'fingerprint_data': fixture['fingerprint_data']
        }
        
        return batch
    
    def get_assembly_accuracy_test_cases(self) -> List[Dict[str, Any]]:
        """Get test cases for assembly accuracy testing"""
        test_cases = []
        
        for format_type in FORMATS:
            for quality in QUALITIES:
                for structure in STRUCTURES:
                    fixture_key = f"{format_type}_{quality}_{structure}"
                    test_case = {
                        'name': f"Assembly accuracy: {fixture_key}",
                        'fixture_key': fixture_key,
                        'expected_accuracy': 0.99,
                        'description': f"Test {format_type.upper()} {quality} {structure} file assembly accuracy"
                    }
                    test_cases.append(test_case)
        
        return test_cases

# Test data for OCR confidence gating
OCR_TEST_CASES = [
    {
        'name': 'OCR confidence < 50 - BLOCKED',
        'ocr_avg_conf': 45.0,
        'ocr_min_conf': 42.0,
        'expected_verdict': 'BLOCKED',
        'expected_flags': ['OCR_TOO_LOW'],
        'description': 'Low confidence OCR should be blocked'
    },
    {
        'name': 'OCR confidence 50-69 - WARNED',
        'ocr_avg_conf': 58.0,
        'ocr_min_conf': 55.0,
        'expected_verdict': 'WARNED',
        'expected_flags': ['LOW_CONFIDENCE'],
        'description': 'Medium confidence OCR should be warned'
    },
    {
        'name': 'OCR confidence ≥ 70 - PASSED',
        'ocr_avg_conf': 82.0,
        'ocr_min_conf': 75.0,
        'expected_verdict': 'PASSED',
        'expected_flags': [],
        'description': 'High confidence OCR should pass through'
    }
]

# Test data for document assembly edge cases
ASSEMBLY_EDGE_CASES = [
    {
        'name': 'Mixed format batch',
        'files': [
            {'format': 'pdf', 'quality': 'clean', 'structure': 'single'},
            {'format': 'jpg', 'quality': 'noisy', 'structure': 'single'},
            {'format': 'png', 'quality': 'clean', 'structure': 'single'}
        ],
        'expected_groups': 3,  # Should create 3 separate documents
        'description': 'Mixed formats should not group together'
    },
    {
        'name': 'Time-window grouping',
        'files': [
            {'created_at': '2024-01-01T10:00:00', 'phash': 'hash1'},
            {'created_at': '2024-01-01T10:00:30', 'phash': 'hash1'},  # Same hash, within 60s
            {'created_at': '2024-01-01T10:02:00', 'phash': 'hash1'}   # Same hash, outside 60s
        ],
        'expected_groups': 2,  # First two should group, third separate
        'description': 'Time window should affect grouping'
    }
] 