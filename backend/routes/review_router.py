# -*- coding: utf-8 -*-
"""
Review Workflow API Router

Provides endpoints for managing documents that need review, including
queue management, review details, quick fixes, approval, and escalation.
"""

import logging
import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel

from backend.app.db import DB_PATH, update_document_status, upsert_invoice

LOGGER = logging.getLogger("owlin.routes.review")

router = APIRouter(prefix="/api/review", tags=["review"])


class QuickFixRequest(BaseModel):
    """Request to apply quick fixes to a document"""
    fixes: Dict[str, Any]  # Field name -> new value
    reason: Optional[str] = None


class ApproveRequest(BaseModel):
    """Request to approve a reviewed document"""
    notes: Optional[str] = None


class EscalateRequest(BaseModel):
    """Request to escalate a document for external review"""
    reason: str
    escalate_to: Optional[str] = None  # "supplier" | "manager" | etc.


@router.get("/queue")
async def get_review_queue(
    priority: Optional[Literal["low", "medium", "high", "critical"]] = Query(None, description="Filter by review priority"),
    band: Optional[Literal["high", "medium", "low", "critical"]] = Query(None, description="Filter by confidence band"),
    reason: Optional[str] = Query(None, description="Filter by review reason"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of documents to return")
) -> Dict[str, Any]:
    """
    Get list of documents needing review, optionally filtered by priority, band, or reason.
    
    Returns documents with needs_review status, sorted by priority and confidence.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Build query with filters
        query = """
            SELECT 
                i.id,
                i.doc_id,
                i.supplier,
                i.date,
                i.value as total,
                i.confidence,
                i.status,
                i.confidence_breakdown,
                d.filename,
                d.uploaded_at,
                d.ocr_error
            FROM invoices i
            JOIN documents d ON i.doc_id = d.id
            WHERE i.status = 'needs_review'
        """
        params = []
        
        # Apply filters
        if priority or band or reason:
            # Parse confidence_breakdown to filter
            if band:
                query += " AND i.confidence_breakdown LIKE ?"
                params.append(f'%"band":"{band}"%')
            
            if reason:
                query += " AND d.ocr_error LIKE ?"
                params.append(f'%"review_reason":"{reason}"%')
        
        query += " ORDER BY "
        
        # Sort by priority (if available in ocr_error) and confidence
        query += """
            CASE 
                WHEN d.ocr_error LIKE '%"review_priority":"critical"%' THEN 1
                WHEN d.ocr_error LIKE '%"review_priority":"high"%' THEN 2
                WHEN d.ocr_error LIKE '%"review_priority":"medium"%' THEN 3
                WHEN d.ocr_error LIKE '%"review_priority":"low"%' THEN 4
                ELSE 5
            END,
            i.confidence ASC
        """
        
        query += f" LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        documents = []
        for row in rows:
            doc = dict(row)
            
            # Parse confidence_breakdown if present
            if doc.get("confidence_breakdown"):
                try:
                    breakdown = json.loads(doc["confidence_breakdown"])
                    doc["confidence_breakdown"] = breakdown
                    doc["confidence_band"] = breakdown.get("band")
                    doc["action_required"] = breakdown.get("action_required")
                except (json.JSONDecodeError, TypeError):
                    pass
            
            # Parse review metadata from ocr_error if present
            if doc.get("ocr_error"):
                try:
                    error_data = json.loads(doc["ocr_error"])
                    if isinstance(error_data, dict):
                        doc["review_reason"] = error_data.get("review_reason")
                        doc["review_priority"] = error_data.get("review_priority")
                        doc["fixable_fields"] = error_data.get("fixable_fields", [])
                        doc["suggested_actions"] = error_data.get("suggested_actions", [])
                except (json.JSONDecodeError, TypeError):
                    # If not JSON, treat as plain error message
                    doc["review_reason"] = "unknown"
                    doc["review_priority"] = "medium"
            
            documents.append(doc)
        
        return {
            "status": "ok",
            "count": len(documents),
            "documents": documents
        }
    
    except Exception as e:
        LOGGER.error(f"Failed to get review queue: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get review queue: {str(e)}")


@router.get("/{doc_id}/details")
async def get_review_details(doc_id: str) -> Dict[str, Any]:
    """
    Get detailed review information for a specific document.
    
    Returns confidence breakdown, review metadata, and remediation hints.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get invoice and document data
        cursor.execute("""
            SELECT 
                i.id,
                i.doc_id,
                i.supplier,
                i.date,
                i.value as total,
                i.confidence,
                i.status,
                i.confidence_breakdown,
                d.filename,
                d.uploaded_at,
                d.ocr_error,
                d.ocr_confidence,
                d.ocr_stage
            FROM invoices i
            JOIN documents d ON i.doc_id = d.id
            WHERE i.id = ? OR i.doc_id = ?
        """, (doc_id, doc_id))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
        
        doc = dict(row)
        
        # Parse confidence_breakdown
        confidence_breakdown = None
        if doc.get("confidence_breakdown"):
            try:
                confidence_breakdown = json.loads(doc["confidence_breakdown"])
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Parse review metadata
        review_metadata = {}
        if doc.get("ocr_error"):
            try:
                error_data = json.loads(doc["ocr_error"])
                if isinstance(error_data, dict):
                    review_metadata = error_data
            except (json.JSONDecodeError, TypeError):
                review_metadata = {
                    "review_reason": "unknown",
                    "review_priority": "medium",
                    "error_message": doc["ocr_error"]
                }
        
        # Get line items count
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM invoice_line_items
            WHERE invoice_id = ? OR doc_id = ?
        """, (doc_id, doc_id))
        line_items_row = cursor.fetchone()
        line_items_count = line_items_row["count"] if line_items_row else 0
        
        conn.close()
        
        return {
            "status": "ok",
            "doc_id": doc_id,
            "document": {
                "id": doc["id"],
                "doc_id": doc["doc_id"],
                "filename": doc["filename"],
                "supplier": doc["supplier"],
                "date": doc["date"],
                "total": doc["total"],
                "confidence": doc["confidence"],
                "status": doc["status"],
                "uploaded_at": doc["uploaded_at"],
                "line_items_count": line_items_count
            },
            "confidence_breakdown": confidence_breakdown,
            "review_metadata": review_metadata,
            "remediation_hints": confidence_breakdown.get("remediation_hints", []) if confidence_breakdown else []
        }
    
    except HTTPException:
        raise
    except Exception as e:
        LOGGER.error(f"Failed to get review details for {doc_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get review details: {str(e)}")


@router.post("/{doc_id}/quick-fix")
async def apply_quick_fix(doc_id: str, request: QuickFixRequest) -> Dict[str, Any]:
    """
    Apply quick fixes to a document (e.g., correct supplier name, fix date).
    
    Updates the invoice with corrected values and may trigger re-validation.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get current invoice data
        cursor.execute("""
            SELECT supplier, date, value, confidence, status
            FROM invoices
            WHERE id = ? OR doc_id = ?
        """, (doc_id, doc_id))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
        
        current_supplier, current_date, current_value, current_confidence, current_status = row
        
        # Apply fixes
        new_supplier = request.fixes.get("supplier", current_supplier)
        new_date = request.fixes.get("date", current_date)
        new_value = request.fixes.get("total", current_value) or request.fixes.get("value", current_value)
        
        # Update invoice
        cursor.execute("""
            UPDATE invoices
            SET supplier = ?, date = ?, value = ?
            WHERE id = ? OR doc_id = ?
        """, (new_supplier, new_date, new_value, doc_id, doc_id))
        
        # Log the fix
        LOGGER.info(
            f"[QUICK_FIX] Applied fixes to {doc_id}: "
            f"supplier={current_supplier}->{new_supplier}, "
            f"date={current_date}->{new_date}, "
            f"value={current_value}->{new_value}, "
            f"reason={request.reason}"
        )
        
        conn.commit()
        conn.close()
        
        return {
            "status": "ok",
            "doc_id": doc_id,
            "message": "Quick fixes applied successfully",
            "applied_fixes": request.fixes
        }
    
    except HTTPException:
        raise
    except Exception as e:
        LOGGER.error(f"Failed to apply quick fix to {doc_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to apply quick fix: {str(e)}")


@router.post("/{doc_id}/approve")
async def approve_document(doc_id: str, request: ApproveRequest) -> Dict[str, Any]:
    """
    Approve a document after review, marking it as ready.
    
    Updates status to 'ready' and clears review flags.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if document exists
        cursor.execute("""
            SELECT id, status, confidence
            FROM invoices
            WHERE id = ? OR doc_id = ?
        """, (doc_id, doc_id))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
        
        invoice_id, current_status, confidence = row
        
        # Update status to ready
        cursor.execute("""
            UPDATE invoices
            SET status = 'ready'
            WHERE id = ?
        """, (invoice_id,))
        
        # Update document status
        update_document_status(doc_id, "ready", "review_approved", confidence=confidence)
        
        # Clear review error
        cursor.execute("""
            UPDATE documents
            SET ocr_error = NULL
            WHERE id = ?
        """, (doc_id,))
        
        conn.commit()
        conn.close()
        
        LOGGER.info(f"[REVIEW_APPROVE] Document {doc_id} approved after review. Notes: {request.notes}")
        
        return {
            "status": "ok",
            "doc_id": doc_id,
            "message": "Document approved successfully",
            "new_status": "ready"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        LOGGER.error(f"Failed to approve document {doc_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to approve document: {str(e)}")


@router.post("/{doc_id}/escalate")
async def escalate_document(doc_id: str, request: EscalateRequest) -> Dict[str, Any]:
    """
    Escalate a document for external review (e.g., to supplier or manager).
    
    Updates status and adds escalation metadata.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if document exists
        cursor.execute("""
            SELECT id, status
            FROM invoices
            WHERE id = ? OR doc_id = ?
        """, (doc_id, doc_id))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
        
        invoice_id, current_status = row
        
        # Create escalation metadata
        escalation_metadata = {
            "escalated": True,
            "escalated_at": datetime.now().isoformat(),
            "escalate_to": request.escalate_to or "manager",
            "reason": request.reason
        }
        
        # Update document with escalation info
        cursor.execute("""
            UPDATE documents
            SET ocr_error = ?, status = 'needs_review'
            WHERE id = ?
        """, (json.dumps(escalation_metadata), doc_id))
        
        # Update invoice status
        cursor.execute("""
            UPDATE invoices
            SET status = 'needs_review'
            WHERE id = ?
        """, (invoice_id,))
        
        conn.commit()
        conn.close()
        
        LOGGER.info(
            f"[REVIEW_ESCALATE] Document {doc_id} escalated to {request.escalate_to}. "
            f"Reason: {request.reason}"
        )
        
        return {
            "status": "ok",
            "doc_id": doc_id,
            "message": "Document escalated successfully",
            "escalation": escalation_metadata
        }
    
    except HTTPException:
        raise
    except Exception as e:
        LOGGER.error(f"Failed to escalate document {doc_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to escalate document: {str(e)}")

