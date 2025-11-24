# backend/api/llm_router.py
"""
LLM API Router

Provides endpoints for LLM processing of stored documents with automation features.
"""

from __future__ import annotations
import logging
import sqlite3
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from backend.config import env_bool, env_str
from backend.llm.ocr_llm_integration import OCRLLMIntegration
from backend.llm.local_llm import LLMConfig, LLMProvider, LLMDevice

logger = logging.getLogger("owlin.api.llm")
router = APIRouter(prefix="/api/llm", tags=["llm"])


class LLMRunRequest(BaseModel):
    """Request model for LLM processing."""
    doc_id: str
    enable_automation: bool = True


class LLMRunResponse(BaseModel):
    """Response model for LLM processing."""
    ok: bool
    final_invoice_card: Optional[Dict[str, Any]] = None
    review_queue: List[Dict[str, Any]] = []
    automation_artifacts: Dict[str, Any] = {}
    processing_time: float = 0.0
    error_reason: Optional[str] = None
    metadata: Dict[str, Any] = {}


def _get_document_by_id(doc_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve document information from database."""
    try:
        con = sqlite3.connect("data/owlin.db", check_same_thread=False)
        cur = con.cursor()
        
        # Get document info
        cur.execute("""
            SELECT id, filename, file_path, file_size, created_at
            FROM documents 
            WHERE id = ?
        """, (doc_id,))
        
        row = cur.fetchone()
        if not row:
            con.close()
            return None
        
        # Get OCR data if available
        cur.execute("""
            SELECT supplier, date, value, confidence, status
            FROM invoices 
            WHERE doc_id = ?
        """, (doc_id,))
        
        invoice_row = cur.fetchone()
        
        con.close()
        
        document = {
            "id": row[0],
            "filename": row[1],
            "file_path": row[2],
            "file_size": row[3],
            "created_at": row[4],
            "invoice_data": {
                "supplier": invoice_row[0] if invoice_row else None,
                "date": invoice_row[1] if invoice_row else None,
                "value": invoice_row[2] if invoice_row else None,
                "confidence": invoice_row[3] if invoice_row else None,
                "status": invoice_row[4] if invoice_row else None
            } if invoice_row else None
        }
        
        return document
        
    except Exception as e:
        logger.error(f"Failed to get document {doc_id}: {e}")
        return None


def _get_llm_integration() -> OCRLLMIntegration:
    """Get or create LLM integration instance."""
    # Check if model path is configured
    model_path = env_str("OWLIN_LLM_MODEL", "models/llama-2-7b-chat.Q4_K_M.gguf")
    
    # Create LLM config
    config = LLMConfig(
        model_path=model_path,
        provider=LLMProvider.LLAMA_CPP,
        device=LLMDevice.AUTO
    )
    
    # Create integration
    integration = OCRLLMIntegration([config])
    return integration


def _process_document_with_llm(doc_id: str, enable_automation: bool = True) -> LLMRunResponse:
    """Process document with LLM integration."""
    start_time = time.time()
    
    try:
        # Get document info
        document = _get_document_by_id(doc_id)
        if not document:
            return LLMRunResponse(
                ok=False,
                error_reason=f"Document {doc_id} not found",
                processing_time=time.time() - start_time
            )
        
        # Get LLM integration
        integration = _get_llm_integration()
        
        # Prepare OCR data from document
        raw_ocr_data = {
            "supplier": document["invoice_data"]["supplier"] if document["invoice_data"] else "Unknown",
            "invoice_date": document["invoice_data"]["date"] if document["invoice_data"] else None,
            "total_amount": document["invoice_data"]["value"] if document["invoice_data"] else None,
            "confidence": document["invoice_data"]["confidence"] if document["invoice_data"] else 0.5,
            "filename": document["filename"],
            "file_path": document["file_path"]
        }
        
        # Prepare context
        context = {
            "doc_id": doc_id,
            "filename": document["filename"],
            "file_size": document["file_size"],
            "created_at": document["created_at"]
        }
        
        # Process with LLM integration
        result = integration.process_document(
            raw_ocr_data=raw_ocr_data,
            context=context,
            enable_llm_processing=True,
            enable_automation=enable_automation
        )
        
        # Convert to response format
        response = LLMRunResponse(
            ok=result.success,
            final_invoice_card=result.final_invoice_card,
            review_queue=result.review_queue,
            automation_artifacts=result.automation_artifacts,
            processing_time=time.time() - start_time,
            metadata={
                "total_processing_time": result.total_processing_time,
                "ocr_processing_time": result.confidence_routing_result.processing_time if result.confidence_routing_result else 0,
                "llm_processing_time": result.llm_pipeline_result.processing_time if result.llm_pipeline_result else 0,
                "errors": result.errors,
                "warnings": result.warnings
            }
        )
        
        if not result.success:
            response.error_reason = "; ".join(result.errors) if result.errors else "Unknown error"
        
        return response
        
    except Exception as e:
        logger.error(f"LLM processing failed for document {doc_id}: {e}")
        return LLMRunResponse(
            ok=False,
            error_reason=f"LLM processing failed: {e}",
            processing_time=time.time() - start_time
        )


@router.post("/run", response_model=LLMRunResponse)
async def llm_run(request: LLMRunRequest) -> LLMRunResponse:
    """
    Process a stored document with LLM integration.
    
    Args:
        request: LLM processing request with doc_id and automation flag
        
    Returns:
        LLMRunResponse with processing results
    """
    logger.info(f"LLM processing request for document {request.doc_id}")
    
    try:
        # Process document
        result = _process_document_with_llm(
            doc_id=request.doc_id,
            enable_automation=request.enable_automation
        )
        
        logger.info(f"LLM processing completed for document {request.doc_id}: success={result.ok}, time={result.processing_time:.3f}s")
        
        return result
        
    except Exception as e:
        logger.error(f"LLM endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"LLM processing failed: {e}")


@router.get("/status")
async def llm_status() -> Dict[str, Any]:
    """Get LLM system status and configuration."""
    try:
        # Get LLM integration
        integration = _get_llm_integration()
        
        # Validate integration
        validation = integration.validate_integration()
        
        # Get model path
        model_path = env_str("OWLIN_LLM_MODEL", "models/llama-2-7b-chat.Q4_K_M.gguf")
        
        return {
            "status": "ok",
            "model_path": model_path,
            "integration_ready": validation["integration_ready"],
            "ocr_components": validation["ocr_components"],
            "llm_components": validation["llm_components"],
            "automation_enabled": env_bool("FEATURE_LLM_AUTOMATION", True)
        }
        
    except Exception as e:
        logger.error(f"LLM status check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "integration_ready": False
        }


@router.get("/models")
async def list_models() -> Dict[str, Any]:
    """List available LLM models."""
    try:
        # Get model path from config
        model_path = env_str("OWLIN_LLM_MODEL", "models/llama-2-7b-chat.Q4_K_M.gguf")
        
        # Check if model file exists
        import os
        model_exists = os.path.exists(model_path)
        
        return {
            "models": [
                {
                    "name": "llama-2-7b-chat",
                    "path": model_path,
                    "available": model_exists,
                    "size_mb": os.path.getsize(model_path) / (1024 * 1024) if model_exists else 0
                }
            ],
            "default_model": model_path
        }
        
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        return {
            "models": [],
            "error": str(e)
        }



