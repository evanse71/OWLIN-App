"""
Debug Lifecycle Router - Operator visibility into OCR processing
"""
from fastapi import APIRouter, Query
import os
from pathlib import Path

router = APIRouter(prefix="/api/debug", tags=["debug"])

@router.get("/lifecycle")
def get_lifecycle(doc_id: str = Query(..., description="Document ID to trace")):
    """
    Return ordered lifecycle markers for a specific document.
    Searches backend_stdout.log for [OCR_LIFECYCLE] entries matching doc_id.
    """
    log_path = Path("backend_stdout.log")
    
    # Check if log file exists
    if not log_path.exists():
        return {
            "doc_id": doc_id,
            "markers": [],
            "truncated": False,
            "error": "Log file not found"
        }
    
    markers = []
    total_size = 0
    max_size = 2048  # 2KB limit
    
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                # Look for [OCR_LIFECYCLE] markers with matching doc_id
                if "[OCR_LIFECYCLE]" in line and f"doc_id={doc_id}" in line:
                    marker = line.strip()
                    marker_size = len(marker)
                    
                    # Check if adding this marker would exceed limit
                    if total_size + marker_size > max_size:
                        return {
                            "doc_id": doc_id,
                            "markers": markers,
                            "truncated": True,
                            "count": len(markers),
                            "total_size": total_size,
                            "message": f"Truncated at {max_size} bytes"
                        }
                    
                    markers.append(marker)
                    total_size += marker_size
        
        return {
            "doc_id": doc_id,
            "markers": markers,
            "truncated": False,
            "count": len(markers),
            "total_size": total_size
        }
    
    except Exception as e:
        return {
            "doc_id": doc_id,
            "markers": [],
            "truncated": False,
            "error": str(e)
        }
