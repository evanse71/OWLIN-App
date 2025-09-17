"""
Delivery Notes API Router
Enhanced with pairing, suggestions, and audit logging
"""
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime

try:
    from ..db import execute, fetch_one, fetch_all, uuid_str
    from ..services.auto_match_engine import get_auto_match_engine
    from ..services.audit import write_audit
    from ..services.recompute import recompute_invoice_totals
except ImportError:
    try:
        from backend.db import execute, fetch_one, fetch_all, uuid_str
        from backend.services.auto_match_engine import get_auto_match_engine
        from backend.services.audit import write_audit
        from backend.services.recompute import recompute_invoice_totals
    except ImportError:
        from db import execute, fetch_one, fetch_all, uuid_str
        from services.auto_match_engine import get_auto_match_engine
        from services.audit import write_audit
        from services.recompute import recompute_invoice_totals

router = APIRouter(prefix="/api/delivery-notes", tags=["delivery-notes"])

class DeliveryNoteResponse(BaseModel):
    id: str
    supplier: str
    note_date: str
    status: str
    total_amount: Optional[float] = None
    matched_invoice_id: Optional[str] = None
    suggested_invoice_id: Optional[str] = None
    suggested_score: Optional[float] = None
    suggested_reason: Optional[str] = None

class PairRequest(BaseModel):
    delivery_note_id: str
    invoice_id: str

class UnpairRequest(BaseModel):
    delivery_note_id: str

@router.get("")
def list_delivery_notes(
    q: Optional[str] = Query(None, description="Search query"),
    supplier: Optional[str] = Query(None, description="Filter by supplier"),
    matched: Optional[bool] = Query(None, description="Filter by matched status"),
    limit: int = Query(100, description="Maximum number of results"),
    offset: int = Query(0, description="Number of results to skip")
):
    """List delivery notes with optional filtering and suggestions"""
    try:
        # Build query with filters
        conditions = []
        params = []
        
        if q:
            conditions.append("(supplier LIKE ? OR note_date LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%"])
        
        if supplier:
            conditions.append("supplier LIKE ?")
            params.append(f"%{supplier}%")
        
        if matched is not None:
            if matched:
                conditions.append("matched_invoice_id IS NOT NULL")
            else:
                conditions.append("matched_invoice_id IS NULL")
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        query = f"""
            SELECT 
                id, supplier, note_date, status, total_amount,
                matched_invoice_id, suggested_invoice_id, 
                suggested_score, suggested_reason
            FROM delivery_notes
            {where_clause}
            ORDER BY note_date DESC
            LIMIT ? OFFSET ?
        """
        
        params.extend([limit, offset])
        rows = fetch_all(query, params)
        
        # Convert to response format
        items = []
        for row in rows:
            items.append({
                "id": row["id"],
                "supplier": row.get("supplier") or "Unknown",
                "note_date": row.get("note_date"),
                "status": row.get("status") or "scanned",
                "total_amount": row.get("total_amount"),
                "matched_invoice_id": row.get("matched_invoice_id"),
                "suggested_invoice_id": row.get("suggested_invoice_id"),
                "suggested_score": row.get("suggested_score"),
                "suggested_reason": row.get("suggested_reason")
            })
        
        return {"items": items, "total": len(items)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list delivery notes: {e}")

@router.get("/{dn_id}")
def get_delivery_note(dn_id: str):
    """Get delivery note details"""
    try:
        row = fetch_one("""
            SELECT 
                id, supplier, note_date, status, total_amount,
                matched_invoice_id, suggested_invoice_id,
                suggested_score, suggested_reason
            FROM delivery_notes 
            WHERE id = ?
        """, (dn_id,))
        
        if not row:
            raise HTTPException(status_code=404, detail="Delivery note not found")
        
        return {
            "id": row["id"],
            "supplier": row.get("supplier") or "Unknown",
            "note_date": row.get("note_date"),
            "status": row.get("status") or "scanned",
            "total_amount": row.get("total_amount"),
            "matched_invoice_id": row.get("matched_invoice_id"),
            "suggested_invoice_id": row.get("suggested_invoice_id"),
            "suggested_score": row.get("suggested_score"),
            "suggested_reason": row.get("suggested_reason")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get delivery note: {e}")

@router.post("/pair")
def pair_delivery_note(request: PairRequest):
    """Pair delivery note with invoice"""
    try:
        # Verify delivery note exists
        dn = fetch_one("SELECT id, supplier, matched_invoice_id FROM delivery_notes WHERE id = ?", (request.delivery_note_id,))
        if not dn:
            raise HTTPException(status_code=404, detail="Delivery note not found")
        
        # Check if already paired
        if dn.get("matched_invoice_id"):
            raise HTTPException(status_code=400, detail="Delivery note already paired")
        
        # Verify invoice exists
        invoice = fetch_one("SELECT id, supplier FROM invoices WHERE id = ?", (request.invoice_id,))
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Update delivery note
        execute("""
            UPDATE delivery_notes 
            SET matched_invoice_id = ?, status = 'matched'
            WHERE id = ?
        """, (request.invoice_id, request.delivery_note_id))
        
        # Recompute invoice totals
        recompute_invoice_totals(request.invoice_id)
        
        # Log audit event
        write_audit(
            actor="system",  # TODO: Get from auth context
            action="PAIR_DN_TO_INVOICE",
            meta={
                "delivery_note_id": request.delivery_note_id,
                "invoice_id": request.invoice_id,
                "supplier": dn.get("supplier")
            },
            resource_type="delivery_note",
            resource_id=request.delivery_note_id
        )
        
        return {"ok": True, "message": "Delivery note paired successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to pair delivery note: {e}")

@router.post("/unpair")
def unpair_delivery_note(request: UnpairRequest):
    """Unpair delivery note from invoice"""
    try:
        # Verify delivery note exists and is paired
        dn = fetch_one("SELECT id, matched_invoice_id FROM delivery_notes WHERE id = ?", (request.delivery_note_id,))
        if not dn:
            raise HTTPException(status_code=404, detail="Delivery note not found")
        
        if not dn.get("matched_invoice_id"):
            raise HTTPException(status_code=400, detail="Delivery note not paired")
        
        invoice_id = dn["matched_invoice_id"]
        
        # Update delivery note
        execute("""
            UPDATE delivery_notes 
            SET matched_invoice_id = NULL, status = 'unmatched'
            WHERE id = ?
        """, (request.delivery_note_id,))
        
        # Recompute invoice totals
        recompute_invoice_totals(invoice_id)
        
        # Log audit event
        write_audit(
            actor="system",  # TODO: Get from auth context
            action="UNPAIR_DN_FROM_INVOICE",
            meta={
                "delivery_note_id": request.delivery_note_id,
                "invoice_id": invoice_id
            },
            resource_type="delivery_note",
            resource_id=request.delivery_note_id
        )
        
        return {"ok": True, "message": "Delivery note unpaired successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unpair delivery note: {e}")

@router.get("/{dn_id}/suggestions")
def get_delivery_note_suggestions(dn_id: str):
    """Get pairing suggestions for delivery note"""
    try:
        # Get delivery note
        dn = fetch_one("""
            SELECT id, supplier, note_date, total_amount
            FROM delivery_notes 
            WHERE id = ?
        """, (dn_id,))
        
        if not dn:
            raise HTTPException(status_code=404, detail="Delivery note not found")
        
        # Get auto-match suggestions
        engine = get_auto_match_engine()
        suggestion = engine.suggest_for_dn(dict(dn))
        
        if suggestion:
            # Update suggestion in database
            execute("""
                UPDATE delivery_notes 
                SET suggested_invoice_id = ?, suggested_score = ?, suggested_reason = ?
                WHERE id = ?
            """, (suggestion.invoice_id, suggestion.score, suggestion.reason, dn_id))
            
            return {
                "suggestions": [{
                    "invoice_id": suggestion.invoice_id,
                    "score": suggestion.score,
                    "reason": suggestion.reason,
                    "confidence": suggestion.confidence
                }]
            }
        else:
            return {"suggestions": []}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {e}")

@router.post("/{dn_id}/suggestions/refresh")
def refresh_suggestions(dn_id: str):
    """Refresh pairing suggestions for delivery note"""
    try:
        # Get delivery note
        dn = fetch_one("""
            SELECT id, supplier, note_date, total_amount
            FROM delivery_notes 
            WHERE id = ?
        """, (dn_id,))
        
        if not dn:
            raise HTTPException(status_code=404, detail="Delivery note not found")
        
        # Clear existing suggestions
        execute("""
            UPDATE delivery_notes 
            SET suggested_invoice_id = NULL, suggested_score = NULL, suggested_reason = NULL
            WHERE id = ?
        """, (dn_id,))
        
        # Get new suggestions
        engine = get_auto_match_engine()
        suggestion = engine.suggest_for_dn(dict(dn))
        
        if suggestion:
            # Update suggestion in database
            execute("""
                UPDATE delivery_notes 
                SET suggested_invoice_id = ?, suggested_score = ?, suggested_reason = ?
                WHERE id = ?
            """, (suggestion.invoice_id, suggestion.score, suggestion.reason, dn_id))
            
            return {
                "suggestions": [{
                    "invoice_id": suggestion.invoice_id,
                    "score": suggestion.score,
                    "reason": suggestion.reason,
                    "confidence": suggestion.confidence
                }]
            }
        else:
            return {"suggestions": []}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh suggestions: {e}")
