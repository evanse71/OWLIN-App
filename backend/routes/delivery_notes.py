"""
Delivery Notes API Routes
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
import uuid
from datetime import datetime
import sqlite3

from backend.db_manager_unified import get_db_manager
from backend.services.pairing_service import PairingService

router = APIRouter(prefix="/api/delivery-notes", tags=["delivery-notes"])

class CreateDeliveryNoteRequest(BaseModel):
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    date_iso: str
    asset_ids: Optional[List[str]] = None
    from_invoice_id: Optional[str] = None
    seed_lines: bool = False

class DeliveryNoteResponse(BaseModel):
    dn_id: str
    supplier_name: str
    date_iso: str
    status: str

@router.post("", response_model=DeliveryNoteResponse)
async def create_delivery_note(request: CreateDeliveryNoteRequest):
    """Create delivery note manually"""
    try:
        db = get_db_manager()
        conn = db.get_connection()
        
        # Generate ID
        dn_id = f"dn_{uuid.uuid4().hex[:8]}"
        
        # Resolve supplier
        supplier_name = request.supplier_name
        if request.supplier_id:
            cur = conn.cursor()
            cur.execute("SELECT name FROM suppliers WHERE id = ?", (request.supplier_id,))
            result = cur.fetchone()
            if result:
                supplier_name = result[0]
        
        if not supplier_name:
            raise HTTPException(status_code=400, detail="Supplier name or ID required")
        
        # Create delivery note
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO delivery_notes 
            (id, supplier_name, date_iso, status, created_at)
            VALUES (?, ?, ?, 'pending', ?)
        """, (dn_id, supplier_name, request.date_iso, datetime.utcnow().isoformat()))
        
        # Seed lines from invoice if requested
        if request.from_invoice_id and request.seed_lines:
            await _seed_dn_from_invoice(conn, dn_id, request.from_invoice_id)
        
        # Attach assets if provided
        if request.asset_ids:
            await _attach_assets_to_dn(conn, dn_id, request.asset_ids)
        
        conn.commit()
        
        return DeliveryNoteResponse(
            dn_id=dn_id,
            supplier_name=supplier_name,
            date_iso=request.date_iso,
            status="pending"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create delivery note: {e}")

async def _seed_dn_from_invoice(conn: sqlite3.Connection, dn_id: str, invoice_id: str):
    """Seed delivery note lines from invoice"""
    cur = conn.cursor()
    
    # Copy line items from invoice
    cur.execute("""
        INSERT INTO delivery_note_items 
        (id, dn_id, sku, description, quantity, unit_price, line_total)
        SELECT 
            'dni_' || substr(id, 5), -- Convert invoice item ID to DN item ID
            ?,
            sku,
            description,
            quantity,
            unit_price,
            line_total
        FROM invoice_items 
        WHERE invoice_id = ?
    """, (dn_id, invoice_id))

async def _attach_assets_to_dn(conn: sqlite3.Connection, dn_id: str, asset_ids: List[str]):
    """Attach unassigned assets to delivery note"""
    cur = conn.cursor()
    
    for asset_id in asset_ids:
        # Move asset from unassigned to this DN
        cur.execute("""
            UPDATE ingest_assets 
            SET document_id = ?, document_type = 'delivery_note'
            WHERE id = ? AND document_id IS NULL
        """, (dn_id, asset_id))

@router.get("/{dn_id}")
async def get_delivery_note(dn_id: str):
    """Get delivery note details"""
    try:
        db = get_db_manager()
        conn = db.get_connection()
        cur = conn.cursor()
        
        # Get delivery note
        cur.execute("""
            SELECT id, supplier_name, date_iso, status, created_at
            FROM delivery_notes 
            WHERE id = ?
        """, (dn_id,))
        
        dn = cur.fetchone()
        if not dn:
            raise HTTPException(status_code=404, detail="Delivery note not found")
        
        # Get line items
        cur.execute("""
            SELECT id, sku, description, quantity, unit_price, line_total
            FROM delivery_note_items 
            WHERE dn_id = ?
            ORDER BY id
        """, (dn_id,))
        
        lines = [dict(zip([desc[0] for desc in cur.description], row)) for row in cur.fetchall()]
        
        return {
            "id": dn[0],
            "supplier_name": dn[1],
            "date_iso": dn[2],
            "status": dn[3],
            "created_at": dn[4],
            "lines": lines
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"Failed to get delivery note: {e}")

@router.post("/{dn_id}/pairing/auto")
async def auto_pair_delivery_note(dn_id: str):
    """Automatically pair delivery note with best matching invoice"""
    try:
        pairing_service = PairingService()
        result = await pairing_service.auto_pair_delivery_note(dn_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="No suitable invoice found for pairing")
        
        return result
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"Auto pairing failed: {e}") 