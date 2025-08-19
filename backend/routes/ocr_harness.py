"""
OCR Harness - Golden File Testing System

Provides endpoints for running OCR tests against golden files to ensure
quality and consistency of the OCR pipeline.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from datetime import datetime

from ..ocr.unified_ocr_engine import UnifiedOCREngine
from ..services.audit import log_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ocr/harness", tags=["ocr-harness"])

# Models
class TestResult(BaseModel):
    test_name: str
    success: bool
    confidence: float
    processing_time: float
    error_message: Optional[str] = None
    expected_text: Optional[str] = None
    actual_text: Optional[str] = None
    diff_score: Optional[float] = None

class SuiteResult(BaseModel):
    suite_name: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    average_confidence: float
    average_processing_time: float
    results: List[TestResult]
    timestamp: str

class GoldenFile(BaseModel):
    filename: str
    expected_text: str
    expected_confidence: float
    category: str

# Constants
GOLDEN_DIR = Path("tests/golden/ocr")
SUITES_DIR = GOLDEN_DIR / "suites"

# Ensure directories exist
GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
SUITES_DIR.mkdir(parents=True, exist_ok=True)

# Initialize OCR engine
ocr_engine = UnifiedOCREngine()

def get_suite_files(suite_name: str) -> List[Path]:
    """Get all test files for a suite."""
    suite_dir = SUITES_DIR / suite_name
    if not suite_dir.exists():
        return []
    
    return list(suite_dir.glob("*.pdf")) + list(suite_dir.glob("*.png")) + list(suite_dir.glob("*.jpg"))

def get_expected_results(suite_name: str) -> Dict[str, GoldenFile]:
    """Get expected results for a suite."""
    manifest_file = SUITES_DIR / suite_name / "manifest.json"
    if not manifest_file.exists():
        return {}
    
    try:
        with open(manifest_file, 'r') as f:
            data = json.load(f)
            return {item["filename"]: GoldenFile(**item) for item in data.get("tests", [])}
    except Exception as e:
        logger.error(f"Failed to load manifest for suite {suite_name}: {e}")
        return {}

def calculate_text_similarity(expected: str, actual: str) -> float:
    """Calculate similarity between expected and actual text."""
    if not expected or not actual:
        return 0.0
    
    # Simple word-based similarity
    expected_words = set(expected.lower().split())
    actual_words = set(actual.lower().split())
    
    if not expected_words:
        return 1.0 if not actual_words else 0.0
    
    intersection = expected_words.intersection(actual_words)
    union = expected_words.union(actual_words)
    
    return len(intersection) / len(union) if union else 0.0

@router.get("/suites")
async def list_suites():
    """List available test suites."""
    try:
        suites = []
        for suite_dir in SUITES_DIR.iterdir():
            if suite_dir.is_dir():
                manifest_file = suite_dir / "manifest.json"
                if manifest_file.exists():
                    with open(manifest_file, 'r') as f:
                        data = json.load(f)
                        suites.append({
                            "name": suite_dir.name,
                            "description": data.get("description", ""),
                            "test_count": len(data.get("tests", [])),
                            "last_updated": data.get("last_updated", "")
                        })
        
        return {"suites": suites}
    except Exception as e:
        logger.error(f"Failed to list suites: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list suites: {str(e)}")

@router.get("/suites/{suite_name}")
async def get_suite_info(suite_name: str):
    """Get detailed information about a test suite."""
    try:
        manifest_file = SUITES_DIR / suite_name / "manifest.json"
        if not manifest_file.exists():
            raise HTTPException(status_code=404, detail=f"Suite '{suite_name}' not found")
        
        with open(manifest_file, 'r') as f:
            data = json.load(f)
        
        return {
            "name": suite_name,
            "description": data.get("description", ""),
            "tests": data.get("tests", []),
            "last_updated": data.get("last_updated", ""),
            "file_count": len(get_suite_files(suite_name))
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get suite info for {suite_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get suite info: {str(e)}")

@router.post("/suites/{suite_name}/run")
async def run_suite(suite_name: str):
    """Run all tests in a suite."""
    try:
        start_time = datetime.now()
        
        # Get test files and expected results
        test_files = get_suite_files(suite_name)
        expected_results = get_expected_results(suite_name)
        
        if not test_files:
            raise HTTPException(status_code=404, detail=f"No test files found for suite '{suite_name}'")
        
        results = []
        total_confidence = 0.0
        total_processing_time = 0.0
        passed_tests = 0
        failed_tests = 0
        
        for test_file in test_files:
            test_name = test_file.name
            expected = expected_results.get(test_name)
            
            try:
                # Process file with OCR engine
                file_start_time = datetime.now()
                
                # Read file
                with open(test_file, 'rb') as f:
                    file_content = f.read()
                
                # Process with OCR
                ocr_results = ocr_engine.process_document(file_content, test_name)
                file_end_time = datetime.now()
                
                processing_time = (file_end_time - file_start_time).total_seconds()
                total_processing_time += processing_time
                
                # Extract text and confidence
                extracted_text = ocr_results.get("raw_text", "") if ocr_results else ""
                confidence = ocr_results.get("overall_confidence", 0.0) if ocr_results else 0.0
                total_confidence += confidence
                
                # Compare with expected results
                success = True
                error_message = None
                diff_score = None
                
                if expected:
                    diff_score = calculate_text_similarity(expected.expected_text, extracted_text)
                    success = confidence >= expected.expected_confidence and diff_score >= 0.8
                
                if success:
                    passed_tests += 1
                else:
                    failed_tests += 1
                    error_message = f"Confidence: {confidence:.2f}, Expected: {expected.expected_confidence if expected else 'N/A'}, Similarity: {diff_score:.2f}"
                
                results.append(TestResult(
                    test_name=test_name,
                    success=success,
                    confidence=confidence,
                    processing_time=processing_time,
                    error_message=error_message,
                    expected_text=expected.expected_text if expected else None,
                    actual_text=extracted_text,
                    diff_score=diff_score
                ))
                
            except Exception as e:
                failed_tests += 1
                logger.error(f"Test {test_name} failed: {e}")
                results.append(TestResult(
                    test_name=test_name,
                    success=False,
                    confidence=0.0,
                    processing_time=0.0,
                    error_message=str(e)
                ))
        
        # Calculate summary
        total_tests = len(results)
        average_confidence = total_confidence / total_tests if total_tests > 0 else 0.0
        average_processing_time = total_processing_time / total_tests if total_tests > 0 else 0.0
        
        suite_result = SuiteResult(
            suite_name=suite_name,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            average_confidence=average_confidence,
            average_processing_time=average_processing_time,
            results=results,
            timestamp=datetime.now().isoformat()
        )
        
        # Log audit event
        log_event("ocr_harness.suite_run", {
            "suite_name": suite_name,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "average_confidence": average_confidence,
            "duration": (datetime.now() - start_time).total_seconds()
        })
        
        return suite_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to run suite {suite_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to run suite: {str(e)}")

@router.post("/suites/{suite_name}/upload")
async def upload_test_file(suite_name: str, file: UploadFile = File(...)):
    """Upload a test file to a suite."""
    try:
        suite_dir = SUITES_DIR / suite_name
        suite_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = suite_dir / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Update manifest
        manifest_file = suite_dir / "manifest.json"
        manifest = {"tests": [], "description": f"Test suite: {suite_name}", "last_updated": datetime.now().isoformat()}
        
        if manifest_file.exists():
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)
        
        # Add new test entry
        test_entry = {
            "filename": file.filename,
            "expected_text": "",  # User needs to fill this
            "expected_confidence": 0.8,
            "category": "uploaded"
        }
        
        manifest["tests"].append(test_entry)
        manifest["last_updated"] = datetime.now().isoformat()
        
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return {
            "message": f"File {file.filename} uploaded to suite {suite_name}",
            "filename": file.filename,
            "manifest_updated": True
        }
        
    except Exception as e:
        logger.error(f"Failed to upload test file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

@router.get("/results")
async def get_recent_results(limit: int = 10):
    """Get recent test results."""
    try:
        results_dir = GOLDEN_DIR / "results"
        results_dir.mkdir(exist_ok=True)
        
        result_files = sorted(results_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
        recent_results = []
        
        for result_file in result_files[:limit]:
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)
                    recent_results.append(data)
            except Exception as e:
                logger.warning(f"Failed to load result file {result_file}: {e}")
        
        return {"results": recent_results}
        
    except Exception as e:
        logger.error(f"Failed to get recent results: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get results: {str(e)}")

@router.post("/seed-core-suite")
async def seed_core_suite():
    """Seed the core test suite with basic test files."""
    try:
        core_dir = SUITES_DIR / "core"
        core_dir.mkdir(parents=True, exist_ok=True)
        
        # Create basic manifest
        manifest = {
            "description": "Core OCR test suite with basic invoice examples",
            "last_updated": datetime.now().isoformat(),
            "tests": [
                {
                    "filename": "sample_invoice_1.pdf",
                    "expected_text": "INVOICE\nSupplier: Test Company\nAmount: $100.00",
                    "expected_confidence": 0.85,
                    "category": "basic"
                },
                {
                    "filename": "sample_invoice_2.pdf", 
                    "expected_text": "INVOICE\nSupplier: Another Company\nAmount: $250.00",
                    "expected_confidence": 0.80,
                    "category": "basic"
                }
            ]
        }
        
        manifest_file = core_dir / "manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return {
            "message": "Core test suite seeded successfully",
            "suite_name": "core",
            "test_count": len(manifest["tests"])
        }
        
    except Exception as e:
        logger.error(f"Failed to seed core suite: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to seed core suite: {str(e)}") 