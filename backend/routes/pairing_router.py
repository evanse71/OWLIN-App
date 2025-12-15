import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel

from backend.app.db import DB_PATH, insert_pairing_event
from backend.models.pairing import PairingResult
from backend.services import pairing_service

LOGGER = logging.getLogger("owlin.routes.pairing")

router = APIRouter(prefix="/api/pairing", tags=["pairing"])


class ConfirmPairingRequest(BaseModel):
    delivery_note_id: str
    actor_type: Literal["user", "system", "llm_suggestion"] = "user"
    user_id: Optional[str] = None


class RejectPairingRequest(BaseModel):
    delivery_note_id: Optional[str] = None
    actor_type: Literal["user", "system", "llm_suggestion"] = "user"
    user_id: Optional[str] = None


class UnpairRequest(BaseModel):
    actor_type: Literal["user", "system", "llm_suggestion"] = "user"
    user_id: Optional[str] = None


class ReassignPairingRequest(BaseModel):
    new_delivery_note_id: str
    actor_type: Literal["user", "system", "llm_suggestion"] = "user"
    user_id: Optional[str] = None


class PairingStatusResponse(BaseModel):
    invoice_id: str
    delivery_note_id: Optional[str]
    pairing_status: Optional[str]
    pairing_confidence: Optional[float]
    pairing_model_version: Optional[str]


class PairingStatsResponse(BaseModel):
    total_invoices: int
    paired_count: int
    unpaired_count: int
    suggested_count: int
    auto_paired_count: int
    manual_paired_count: int
    avg_confidence: Optional[float]
    pairing_rate_7d: float
    pairing_rate_30d: float
    recent_activity: List[Dict[str, Any]]


@router.get("/invoice/{invoice_id}", response_model=PairingResult)
def evaluate_invoice_pairing(
    invoice_id: str,
    mode: Literal["normal", "review"] = Query("normal", description="normal triggers auto/suggest logic; review is read-only"),
):
    try:
        return pairing_service.evaluate_pairing(invoice_id, mode)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.exception("Failed to evaluate pairing for invoice %s", invoice_id)
        raise HTTPException(status_code=500, detail="Failed to evaluate pairing") from exc


@router.post("/invoice/{invoice_id}/confirm", response_model=PairingStatusResponse)
def confirm_pairing(invoice_id: str, payload: ConfirmPairingRequest):
    # Validate delivery note exists and is correct type
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check invoice exists
    invoice_row = cursor.execute(
        "SELECT id, delivery_note_id FROM invoices WHERE id = ?",
        (invoice_id,),
    ).fetchone()
    if not invoice_row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    
    # Check if invoice is already paired to a different delivery note
    current_dn_id = invoice_row[1]
    if current_dn_id and current_dn_id != payload.delivery_note_id:
        conn.close()
        raise HTTPException(
            status_code=409,
            detail=f"Invoice is already paired to delivery note {current_dn_id}. Unpair first or use reassign endpoint."
        )
    
    # Check delivery note exists and is correct type
    dn_row = cursor.execute(
        "SELECT id, doc_type, invoice_id FROM documents WHERE id = ?",
        (payload.delivery_note_id,),
    ).fetchone()
    if not dn_row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Delivery note {payload.delivery_note_id} not found")
    
    if dn_row[1] and dn_row[1] != "delivery_note":
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"Document {payload.delivery_note_id} is not a delivery note (type: {dn_row[1]})"
        )
    
    # Check if delivery note is already paired to another invoice
    if dn_row[2] and dn_row[2] != invoice_id:
        conn.close()
        raise HTTPException(
            status_code=409,
            detail=f"Delivery note is already paired to invoice {dn_row[2]}"
        )
    
    conn.close()
    
    return _manual_pair(
        invoice_id=invoice_id,
        delivery_note_id=payload.delivery_note_id,
        action="confirmed_manual",
        actor_type=payload.actor_type,
        user_id=payload.user_id,
    )


@router.post("/invoice/{invoice_id}/reject", response_model=PairingStatusResponse)
def reject_pairing(invoice_id: str, payload: RejectPairingRequest):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    invoice_row = cursor.execute(
        "SELECT id FROM invoices WHERE id = ?",
        (invoice_id,),
    ).fetchone()
    if not invoice_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Invoice not found")

    cursor.execute(
        """
        UPDATE invoices
        SET pairing_status = 'unpaired', pairing_confidence = NULL, pairing_model_version = NULL
        WHERE id = ?
        """,
        (invoice_id,),
    )
    conn.commit()
    conn.close()

    insert_pairing_event(
        invoice_id=invoice_id,
        delivery_note_id=payload.delivery_note_id,
        action="rejected",
        actor_type=payload.actor_type,
        user_id=payload.user_id,
    )

    return _current_pairing_status(invoice_id)


@router.post("/invoice/{invoice_id}/unpair", response_model=PairingStatusResponse)
def unpair_invoice(invoice_id: str, payload: UnpairRequest = Body(default_factory=UnpairRequest, embed=False)):
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    invoice_row = cursor.execute(
        "SELECT delivery_note_id FROM invoices WHERE id = ?",
        (invoice_id,),
    ).fetchone()
    if not invoice_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Invoice not found")

    current_dn_id = invoice_row[0]
    if not current_dn_id:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Invoice {invoice_id} is not currently paired to any delivery note")

    cursor.execute(
        """
        UPDATE invoices
        SET delivery_note_id = NULL,
            pairing_status = 'unpaired',
            pairing_confidence = NULL,
            pairing_model_version = NULL,
            paired = 0
        WHERE id = ?
        """,
        (invoice_id,),
    )
    cursor.execute(
        "UPDATE documents SET invoice_id = NULL WHERE id = ?",
        (current_dn_id,),
    )
    conn.commit()
    conn.close()

    insert_pairing_event(
        invoice_id=invoice_id,
        delivery_note_id=current_dn_id,
        action="unpaired",
        actor_type=payload.actor_type,
        user_id=payload.user_id,
        previous_delivery_note_id=current_dn_id,
    )

    return _current_pairing_status(invoice_id)


@router.post("/invoice/{invoice_id}/reassign", response_model=PairingStatusResponse)
def reassign_pairing(invoice_id: str, payload: ReassignPairingRequest):
    # Validate invoice exists
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    invoice_row = cursor.execute(
        "SELECT id FROM invoices WHERE id = ?",
        (invoice_id,),
    ).fetchone()
    if not invoice_row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    
    # Check new delivery note exists and is correct type
    dn_row = cursor.execute(
        "SELECT id, doc_type, invoice_id FROM documents WHERE id = ?",
        (payload.new_delivery_note_id,),
    ).fetchone()
    if not dn_row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Delivery note {payload.new_delivery_note_id} not found")
    
    if dn_row[1] and dn_row[1] != "delivery_note":
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"Document {payload.new_delivery_note_id} is not a delivery note (type: {dn_row[1]})"
        )
    
    # Check if new delivery note is already paired to another invoice
    if dn_row[2] and dn_row[2] != invoice_id:
        conn.close()
        raise HTTPException(
            status_code=409,
            detail=f"Delivery note {payload.new_delivery_note_id} is already paired to invoice {dn_row[2]}"
        )
    
    conn.close()
    
    status = _manual_pair(
        invoice_id=invoice_id,
        delivery_note_id=payload.new_delivery_note_id,
        action="reassigned",
        actor_type=payload.actor_type,
        user_id=payload.user_id,
    )
    return status


def _manual_pair(
    invoice_id: str,
    delivery_note_id: str,
    action: str,
    actor_type: str,
    user_id: Optional[str],
) -> PairingStatusResponse:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")

    invoice_row = cursor.execute(
        """
        SELECT id, delivery_note_id
        FROM invoices
        WHERE id = ?
        """,
        (invoice_id,),
    ).fetchone()
    if not invoice_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Invoice not found")

    dn_row = cursor.execute(
        """
        SELECT id, doc_type, invoice_id
        FROM documents
        WHERE id = ?
        """,
        (delivery_note_id,),
    ).fetchone()
    if not dn_row or (dn_row[1] and dn_row[1] != "delivery_note"):
        conn.close()
        raise HTTPException(status_code=404, detail="Delivery note not found")

    if dn_row[2] and dn_row[2] != invoice_id:
        conn.close()
        raise HTTPException(status_code=409, detail="Delivery note is already paired to another invoice")

    previous_delivery_note_id = invoice_row[1]
    if previous_delivery_note_id and previous_delivery_note_id != delivery_note_id:
        cursor.execute(
            "UPDATE documents SET invoice_id = NULL WHERE id = ?",
            (previous_delivery_note_id,),
        )

    cursor.execute(
        """
        UPDATE invoices
        SET delivery_note_id = ?,
            pairing_status = 'manual_paired',
            pairing_confidence = 1.0,
            pairing_model_version = 'manual_pairing',
            paired = 1
        WHERE id = ?
        """,
        (delivery_note_id, invoice_id),
    )
    cursor.execute(
        "UPDATE documents SET invoice_id = ? WHERE id = ?",
        (invoice_id, delivery_note_id),
    )
    conn.commit()
    conn.close()

    insert_pairing_event(
        invoice_id=invoice_id,
        delivery_note_id=delivery_note_id,
        action=action,
        actor_type=actor_type,
        user_id=user_id,
        previous_delivery_note_id=previous_delivery_note_id,
    )

    return _current_pairing_status(invoice_id)


def _current_pairing_status(invoice_id: str) -> PairingStatusResponse:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    row = cursor.execute(
        """
        SELECT delivery_note_id, pairing_status, pairing_confidence, pairing_model_version
        FROM invoices
        WHERE id = ?
        """,
        (invoice_id,),
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return PairingStatusResponse(
        invoice_id=invoice_id,
        delivery_note_id=row[0],
        pairing_status=row[1],
        pairing_confidence=row[2],
        pairing_model_version=row[3],
    )


class BatchReevaluateRequest(BaseModel):
    invoice_ids: Optional[List[str]] = None
    status_filter: Optional[Literal["unpaired", "suggested"]] = None


@router.post("/batch/re-evaluate")
def batch_reevaluate_pairings(request: BatchReevaluateRequest):
    """
    Re-evaluate pairings for multiple invoices.
    Useful after supplier_stats updates or model retraining.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if request.invoice_ids:
        placeholders = ','.join(['?'] * len(request.invoice_ids))
        query = f"SELECT id FROM invoices WHERE id IN ({placeholders})"
        params = request.invoice_ids
    elif request.status_filter:
        query = "SELECT id FROM invoices WHERE pairing_status = ?"
        params = [request.status_filter]
    else:
        query = "SELECT id FROM invoices WHERE pairing_status IN ('unpaired', 'suggested')"
        params = []
    
    cursor.execute(query, params)
    invoice_rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in invoice_rows:
        invoice_id = row[0]
        try:
            result = pairing_service.evaluate_pairing(invoice_id, mode="normal")
            results.append({
                "invoice_id": invoice_id,
                "status": result.status,
                "confidence": result.pairing_confidence
            })
        except Exception as e:
            LOGGER.error(f"Failed to re-evaluate invoice {invoice_id}: {e}")
            results.append({
                "invoice_id": invoice_id,
                "error": str(e)
            })
    
    return {
        "processed": len(results),
        "results": results
    }


@router.get("/stats", response_model=PairingStatsResponse)
def get_pairing_stats():
    """
    Get pairing statistics and metrics.
    Returns aggregated statistics about pairing status, rates, and recent activity.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get invoice counts by status
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN pairing_status = 'unpaired' THEN 1 ELSE 0 END) as unpaired,
            SUM(CASE WHEN pairing_status = 'suggested' THEN 1 ELSE 0 END) as suggested,
            SUM(CASE WHEN pairing_status = 'auto_paired' THEN 1 ELSE 0 END) as auto_paired,
            SUM(CASE WHEN pairing_status = 'manual_paired' THEN 1 ELSE 0 END) as manual_paired,
            SUM(CASE WHEN pairing_status IN ('auto_paired', 'manual_paired') THEN 1 ELSE 0 END) as paired
        FROM invoices
    """)
    counts = cursor.fetchone()
    
    # Get average confidence for paired invoices
    cursor.execute("""
        SELECT AVG(pairing_confidence) as avg_conf
        FROM invoices
        WHERE pairing_status IN ('auto_paired', 'manual_paired')
        AND pairing_confidence IS NOT NULL
    """)
    avg_conf_row = cursor.fetchone()
    avg_confidence = float(avg_conf_row[0]) if avg_conf_row[0] is not None else None
    
    # Calculate pairing rates for last 7 and 30 days
    now = datetime.utcnow()
    seven_days_ago = (now - timedelta(days=7)).isoformat()
    thirty_days_ago = (now - timedelta(days=30)).isoformat()
    
    # Count invoices created in last 7 days
    cursor.execute("""
        SELECT COUNT(*) as total_7d,
               SUM(CASE WHEN pairing_status IN ('auto_paired', 'manual_paired') THEN 1 ELSE 0 END) as paired_7d
        FROM invoices
        WHERE created_at >= ?
    """, (seven_days_ago,))
    rate_7d_row = cursor.fetchone()
    total_7d = rate_7d_row[0] or 0
    paired_7d = rate_7d_row[1] or 0
    pairing_rate_7d = (paired_7d / total_7d * 100) if total_7d > 0 else 0.0
    
    # Count invoices created in last 30 days
    cursor.execute("""
        SELECT COUNT(*) as total_30d,
               SUM(CASE WHEN pairing_status IN ('auto_paired', 'manual_paired') THEN 1 ELSE 0 END) as paired_30d
        FROM invoices
        WHERE created_at >= ?
    """, (thirty_days_ago,))
    rate_30d_row = cursor.fetchone()
    total_30d = rate_30d_row[0] or 0
    paired_30d = rate_30d_row[1] or 0
    pairing_rate_30d = (paired_30d / total_30d * 100) if total_30d > 0 else 0.0
    
    # Get recent pairing activity (last 10 events)
    cursor.execute("""
        SELECT 
            timestamp,
            invoice_id,
            delivery_note_id,
            action,
            actor_type,
            model_version
        FROM pairing_events
        ORDER BY timestamp DESC
        LIMIT 10
    """)
    recent_events = []
    for row in cursor.fetchall():
        recent_events.append({
            "timestamp": row["timestamp"],
            "invoice_id": row["invoice_id"],
            "delivery_note_id": row["delivery_note_id"],
            "action": row["action"],
            "actor_type": row["actor_type"],
            "model_version": row["model_version"],
        })
    
    conn.close()
    
    return PairingStatsResponse(
        total_invoices=counts["total"] or 0,
        paired_count=counts["paired"] or 0,
        unpaired_count=counts["unpaired"] or 0,
        suggested_count=counts["suggested"] or 0,
        auto_paired_count=counts["auto_paired"] or 0,
        manual_paired_count=counts["manual_paired"] or 0,
        avg_confidence=avg_confidence,
        pairing_rate_7d=round(pairing_rate_7d, 2),
        pairing_rate_30d=round(pairing_rate_30d, 2),
        recent_activity=recent_events,
    )

