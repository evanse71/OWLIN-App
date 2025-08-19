"""
Health Check Endpoints

Provides comprehensive health monitoring for the OWLIN system.
"""

import os
import sqlite3
import time
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from datetime import datetime

router = APIRouter(prefix="/health", tags=["health"])

def check_database() -> Dict[str, Any]:
    """Check database connectivity and basic operations."""
    try:
        db_path = Path("data/owlin.db")
        if not db_path.exists():
            return {
                "status": "error",
                "message": "Database file not found",
                "path": str(db_path)
            }
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        
        # Test invoices table
        cursor.execute("SELECT COUNT(*) FROM invoices LIMIT 1")
        invoice_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "status": "healthy",
            "tables": table_count,
            "invoices": invoice_count,
            "path": str(db_path)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def check_file_system() -> Dict[str, Any]:
    """Check file system permissions and directories."""
    try:
        required_dirs = [
            "data",
            "data/uploads",
            "data/debug",
            "tests/golden/ocr",
            "license"
        ]
        
        dir_status = {}
        for dir_path in required_dirs:
            path = Path(dir_path)
            dir_status[dir_path] = {
                "exists": path.exists(),
                "writable": os.access(path, os.W_OK) if path.exists() else False
            }
        
        return {
            "status": "healthy",
            "directories": dir_status
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def check_ocr_engines() -> Dict[str, Any]:
    """Check OCR engine availability."""
    try:
        engines = {}
        
        # Check Tesseract
        try:
            import pytesseract
            version = pytesseract.get_tesseract_version()
            engines["tesseract"] = {
                "status": "available",
                "version": str(version)
            }
        except Exception as e:
            engines["tesseract"] = {
                "status": "unavailable",
                "error": str(e)
            }
        
        # Check PaddleOCR
        try:
            from paddleocr import PaddleOCR
            engines["paddleocr"] = {
                "status": "available",
                "version": "2.6.1.3"
            }
        except Exception as e:
            engines["paddleocr"] = {
                "status": "unavailable",
                "error": str(e)
            }
        
        return {
            "status": "healthy",
            "engines": engines
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def check_license() -> Dict[str, Any]:
    """Check license status."""
    try:
        from services.license_service import check_license_state
        license_state = check_license_state()
        
        return {
            "status": "healthy",
            "license": license_state
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@router.get("/")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "service": "OWLIN API",
        "version": "1.0.0"
    }

@router.get("/detailed")
async def detailed_health_check():
    """Comprehensive health check with all system components."""
    start_time = time.time()
    
    checks = {
        "database": check_database(),
        "file_system": check_file_system(),
        "ocr_engines": check_ocr_engines(),
        "license": check_license()
    }
    
    # Determine overall status
    overall_status = "healthy"
    for check_name, check_result in checks.items():
        if check_result.get("status") == "error":
            overall_status = "degraded"
            break
    
    response_time = time.time() - start_time
    
    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "response_time_ms": round(response_time * 1000, 2),
        "checks": checks
    }

@router.get("/ready")
async def readiness_check():
    """Readiness check for load balancers."""
    try:
        # Check critical dependencies
        db_check = check_database()
        if db_check["status"] != "healthy":
            raise HTTPException(status_code=503, detail="Database not ready")
        
        fs_check = check_file_system()
        if fs_check["status"] != "healthy":
            raise HTTPException(status_code=503, detail="File system not ready")
        
        return {
            "status": "ready",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")

@router.get("/live")
async def liveness_check():
    """Liveness check for Kubernetes."""
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat()
    } 