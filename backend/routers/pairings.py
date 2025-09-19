"""
Document Pairings API Router

This module provides API endpoints for managing document pairings between invoices
and delivery notes, including viewing, creating, and managing pairing relationships.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field
import sqlite3
import json
import datetime

router = APIRouter(prefix="/api/pairings", tags=["pairings"])


class PairingResponse(BaseModel):
    """Response model for pairing data"""
    id: str
    invoice_id: str
    delivery_note_id: str
    score: float = Field(..., ge=0.0, le=1.0)
    pairing_method: str
    supplier_match_score: float = Field(..., ge=0.0, le=1.0)
    date_proximity_score: float = Field(..., ge=0.0, le=1.0)
    line_item_similarity_score: float = Field(..., ge=0.0, le=1.0)
    quantity_match_score: float = Field(..., ge=0.0, le=1.0)
    price_match_score: float = Field(..., ge=0.0, le=1.0)
    total_confidence: float = Field(..., ge=0.0, le=1.0)
    status: str
    created_at: str
    updated_at: str
    # Additional fields from joins
    invoice_supplier: Optional[str] = None
    invoice_date: Optional[str] = None
    invoice_number: Optional[str] = None
    dn_supplier: Optional[str] = None
    dn_date: Optional[str] = None
    dn_number: Optional[str] = None


class PairingCreate(BaseModel):
    """Model for creating new pairings"""
    invoice_id: str
    delivery_note_id: str
    score: float = Field(..., ge=0.0, le=1.0)
    pairing_method: str = Field(default="manual", regex="^(auto|manual|fuzzy|exact)$")
    supplier_match_score: float = Field(default=0.0, ge=0.0, le=1.0)
    date_proximity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    line_item_similarity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    quantity_match_score: float = Field(default=0.0, ge=0.0, le=1.0)
    price_match_score: float = Field(default=0.0, ge=0.0, le=1.0)
    total_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    status: str = Field(default="active", regex="^(active|inactive|disputed|confirmed)$")


class PairingUpdate(BaseModel):
    """Model for updating pairings"""
    score: Optional[float] = Field(None, ge=0.0, le=1.0)
    pairing_method: Optional[str] = Field(None, regex="^(auto|manual|fuzzy|exact)$")
    supplier_match_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    date_proximity_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    line_item_similarity_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    quantity_match_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    price_match_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    total_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    status: Optional[str] = Field(None, regex="^(active|inactive|disputed|confirmed)$")


class AutoPairRequest(BaseModel):
    """Model for auto-pairing request"""
    force_recalculate: bool = Field(default=False, description="Force recalculation of existing pairs")
    min_confidence: float = Field(default=0.6, ge=0.0, le=1.0, description="Minimum confidence threshold")


def get_db_connection():
    """Get database connection"""
    return sqlite3.connect('data/owlin.db')


@router.get("/", response_model=List[PairingResponse])
async def get_pairings(
    invoice_id: Optional[str] = Query(None, description="Filter by invoice ID"),
    delivery_note_id: Optional[str] = Query(None, description="Filter by delivery note ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum score threshold"),
    pairing_method: Optional[str] = Query(None, description="Filter by pairing method"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of pairings to return"),
    offset: int = Query(0, ge=0, description="Number of pairings to skip")
):
    """Get document pairings with optional filtering"""
    db = get_db_connection()
    cursor = db.cursor()
    
    # Build query with joins to get additional information
    query = """
        SELECT 
            dp.*,
            i.supplier_name as invoice_supplier,
            i.invoice_date,
            i.invoice_number,
            d.supplier_name as dn_supplier,
            d.delivery_date as dn_date,
            d.delivery_note_number as dn_number
        FROM doc_pairs dp
        LEFT JOIN invoices i ON dp.invoice_id = i.id
        LEFT JOIN delivery_notes d ON dp.delivery_note_id = d.id
        WHERE 1=1
    """
    params = []
    
    if invoice_id:
        query += " AND dp.invoice_id = ?"
        params.append(invoice_id)
    
    if delivery_note_id:
        query += " AND dp.delivery_note_id = ?"
        params.append(delivery_note_id)
    
    if status:
        query += " AND dp.status = ?"
        params.append(status)
    
    if min_score is not None:
        query += " AND dp.score >= ?"
        params.append(min_score)
    
    if pairing_method:
        query += " AND dp.pairing_method = ?"
        params.append(pairing_method)
    
    query += " ORDER BY dp.score DESC, dp.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    # Get column names
    columns = [description[0] for description in cursor.description]
    
    pairings = []
    for row in rows:
        pairing_dict = dict(zip(columns, row))
        pairings.append(PairingResponse(**pairing_dict))
    
    db.close()
    return pairings


@router.get("/{pairing_id}", response_model=PairingResponse)
async def get_pairing(
    pairing_id: str = Path(..., description="Pairing ID")
):
    """Get a specific pairing by ID"""
    db = get_db_connection()
    cursor = db.cursor()
    
    cursor.execute("""
        SELECT 
            dp.*,
            i.supplier_name as invoice_supplier,
            i.invoice_date,
            i.invoice_number,
            d.supplier_name as dn_supplier,
            d.delivery_date as dn_date,
            d.delivery_note_number as dn_number
        FROM doc_pairs dp
        LEFT JOIN invoices i ON dp.invoice_id = i.id
        LEFT JOIN delivery_notes d ON dp.delivery_note_id = d.id
        WHERE dp.id = ?
    """, (pairing_id,))
    
    row = cursor.fetchone()
    
    if not row:
        db.close()
        raise HTTPException(status_code=404, detail="Pairing not found")
    
    # Get column names
    columns = [description[0] for description in cursor.description]
    pairing_dict = dict(zip(columns, row))
    
    db.close()
    return PairingResponse(**pairing_dict)


@router.post("/", response_model=PairingResponse)
async def create_pairing(pairing: PairingCreate):
    """Create a new document pairing"""
    import uuid
    
    db = get_db_connection()
    cursor = db.cursor()
    
    # Check if pairing already exists
    cursor.execute("""
        SELECT id FROM doc_pairs 
        WHERE invoice_id = ? AND delivery_note_id = ?
    """, (pairing.invoice_id, pairing.delivery_note_id))
    
    if cursor.fetchone():
        db.close()
        raise HTTPException(status_code=409, detail="Pairing already exists")
    
    # Verify invoice and delivery note exist
    cursor.execute("SELECT id FROM invoices WHERE id = ?", (pairing.invoice_id,))
    if not cursor.fetchone():
        db.close()
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    cursor.execute("SELECT id FROM delivery_notes WHERE id = ?", (pairing.delivery_note_id,))
    if not cursor.fetchone():
        db.close()
        raise HTTPException(status_code=404, detail="Delivery note not found")
    
    pairing_id = str(uuid.uuid4())
    
    cursor.execute("""
        INSERT INTO doc_pairs (
            id, invoice_id, delivery_note_id, score, pairing_method,
            supplier_match_score, date_proximity_score, line_item_similarity_score,
            quantity_match_score, price_match_score, total_confidence,
            status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    """, (
        pairing_id,
        pairing.invoice_id,
        pairing.delivery_note_id,
        pairing.score,
        pairing.pairing_method,
        pairing.supplier_match_score,
        pairing.date_proximity_score,
        pairing.line_item_similarity_score,
        pairing.quantity_match_score,
        pairing.price_match_score,
        pairing.total_confidence,
        pairing.status
    ))
    
    db.commit()
    db.close()
    
    # Return the created pairing
    return await get_pairing(pairing_id)


@router.put("/{pairing_id}", response_model=PairingResponse)
async def update_pairing(
    pairing_id: str = Path(..., description="Pairing ID"),
    pairing_update: PairingUpdate = None
):
    """Update an existing pairing"""
    db = get_db_connection()
    cursor = db.cursor()
    
    # Check if pairing exists
    cursor.execute("SELECT id FROM doc_pairs WHERE id = ?", (pairing_id,))
    if not cursor.fetchone():
        db.close()
        raise HTTPException(status_code=404, detail="Pairing not found")
    
    # Build update query
    update_fields = []
    params = []
    
    for field, value in pairing_update.dict(exclude_unset=True).items():
        update_fields.append(f"{field} = ?")
        params.append(value)
    
    if not update_fields:
        db.close()
        raise HTTPException(status_code=400, detail="No fields to update")
    
    update_fields.append("updated_at = datetime('now')")
    params.append(pairing_id)
    
    query = f"UPDATE doc_pairs SET {', '.join(update_fields)} WHERE id = ?"
    cursor.execute(query, params)
    
    db.commit()
    db.close()
    
    # Return the updated pairing
    return await get_pairing(pairing_id)


@router.delete("/{pairing_id}")
async def delete_pairing(
    pairing_id: str = Path(..., description="Pairing ID")
):
    """Delete a pairing"""
    db = get_db_connection()
    cursor = db.cursor()
    
    cursor.execute("DELETE FROM doc_pairs WHERE id = ?", (pairing_id,))
    
    if cursor.rowcount == 0:
        db.close()
        raise HTTPException(status_code=404, detail="Pairing not found")
    
    db.commit()
    db.close()
    
    return {"message": "Pairing deleted successfully"}


@router.post("/auto-pair", response_model=Dict[str, Any])
async def auto_pair_documents(request: AutoPairRequest = Body(...)):
    """Run automatic pairing between invoices and delivery notes"""
    try:
        from ..services.enhanced_pairing import auto_pair_enhanced
        
        db = get_db_connection()
        
        if request.force_recalculate:
            # Remove existing pairs below confidence threshold
            cursor = db.cursor()
            cursor.execute("""
                DELETE FROM doc_pairs 
                WHERE total_confidence < ? AND pairing_method = 'auto'
            """, (request.min_confidence,))
            db.commit()
        
        # Run enhanced pairing
        result = auto_pair_enhanced(db)
        
        # Filter results by confidence threshold
        cursor = db.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM doc_pairs 
            WHERE total_confidence >= ? AND created_at >= datetime('now', '-1 minute')
        """, (request.min_confidence,))
        high_confidence_count = cursor.fetchone()[0]
        
        db.close()
        
        return {
            "success": True,
            "message": "Auto-pairing completed successfully",
            "statistics": result,
            "high_confidence_pairs_created": high_confidence_count,
            "min_confidence_threshold": request.min_confidence
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto-pairing failed: {str(e)}")


@router.get("/invoice/{invoice_id}/candidates", response_model=List[Dict[str, Any]])
async def get_pairing_candidates(
    invoice_id: str = Path(..., description="Invoice ID"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of candidates to return")
):
    """Get potential delivery note candidates for an invoice"""
    db = get_db_connection()
    cursor = db.cursor()
    
    # Get invoice details
    cursor.execute("""
        SELECT supplier_name, invoice_date, total_amount_pennies
        FROM invoices WHERE id = ?
    """, (invoice_id,))
    
    invoice_row = cursor.fetchone()
    if not invoice_row:
        db.close()
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    invoice_supplier, invoice_date, invoice_total = invoice_row
    
    # Find candidate delivery notes
    cursor.execute("""
        SELECT 
            d.id,
            d.supplier_name,
            d.delivery_date,
            d.delivery_note_number,
            d.total_items,
            -- Calculate similarity scores
            CASE 
                WHEN LOWER(d.supplier_name) = LOWER(?) THEN 1.0
                ELSE 0.0
            END as supplier_similarity,
            CASE 
                WHEN ABS(julianday(d.delivery_date) - julianday(?)) <= 30 THEN 
                    1.0 - (ABS(julianday(d.delivery_date) - julianday(?)) / 30.0) * 0.5
                ELSE 0.0
            END as date_similarity
        FROM delivery_notes d
        WHERE d.supplier_name IS NOT NULL
        AND d.delivery_date IS NOT NULL
        AND d.id NOT IN (
            SELECT delivery_note_id FROM doc_pairs 
            WHERE invoice_id = ? AND status = 'active'
        )
        ORDER BY supplier_similarity DESC, date_similarity DESC
        LIMIT ?
    """, (invoice_supplier, invoice_date, invoice_date, invoice_id, limit))
    
    candidates = []
    for row in cursor.fetchall():
        candidates.append({
            "delivery_note_id": row[0],
            "supplier_name": row[1],
            "delivery_date": row[2],
            "delivery_note_number": row[3],
            "total_items": row[4],
            "supplier_similarity": row[5],
            "date_similarity": row[6],
            "overall_score": (row[5] * 0.7) + (row[6] * 0.3)
        })
    
    db.close()
    return candidates


@router.get("/stats/summary")
async def get_pairing_stats():
    """Get pairing statistics"""
    db = get_db_connection()
    cursor = db.cursor()
    
    # Total pairings
    cursor.execute("SELECT COUNT(*) FROM doc_pairs")
    total_pairings = cursor.fetchone()[0]
    
    # Pairings by status
    cursor.execute("""
        SELECT status, COUNT(*) as count
        FROM doc_pairs
        GROUP BY status
        ORDER BY count DESC
    """)
    by_status = dict(cursor.fetchall())
    
    # Pairings by method
    cursor.execute("""
        SELECT pairing_method, COUNT(*) as count
        FROM doc_pairs
        GROUP BY pairing_method
        ORDER BY count DESC
    """)
    by_method = dict(cursor.fetchall())
    
    # Average scores
    cursor.execute("""
        SELECT 
            AVG(score) as avg_score,
            AVG(supplier_match_score) as avg_supplier_score,
            AVG(date_proximity_score) as avg_date_score,
            AVG(line_item_similarity_score) as avg_line_item_score,
            AVG(total_confidence) as avg_confidence
        FROM doc_pairs
    """)
    avg_scores = cursor.fetchone()
    
    # Recent pairings (last 7 days)
    cursor.execute("""
        SELECT COUNT(*) FROM doc_pairs 
        WHERE created_at >= datetime('now', '-7 days')
    """)
    recent = cursor.fetchone()[0]
    
    db.close()
    
    return {
        "total_pairings": total_pairings,
        "by_status": by_status,
        "by_method": by_method,
        "average_scores": {
            "overall": avg_scores[0],
            "supplier_match": avg_scores[1],
            "date_proximity": avg_scores[2],
            "line_item_similarity": avg_scores[3],
            "confidence": avg_scores[4]
        },
        "recent_7_days": recent
    }
