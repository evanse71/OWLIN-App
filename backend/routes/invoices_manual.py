"""
Manual Invoice Creation API Routes
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import uuid
from datetime import datetime
import sqlite3

from backend.db_manager_unified import get_db_manager

router = APIRouter(prefix="/api/invoices", tags=["invoices-manual"])

class CreateInvoiceRequest(BaseModel):
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    invoice_no: str
    date_iso: str
    currency: str = "GBP"
    asset_ids: Optional[List[str]] = None
    upload_token: Optional[str] = None

class InvoiceResponse(BaseModel):
    invoice_id: str
    supplier_name: str
    invoice_no: str
    date_iso: str
    status: str

class AttachPagesRequest(BaseModel):
    asset_ids: List[str]

class ReorderPagesRequest(BaseModel):
    order: List[str]  # Asset IDs in desired order

@router.post("", response_model=InvoiceResponse)
async def create_invoice_manual(request: CreateInvoiceRequest, background_tasks: BackgroundTasks):
    """Create invoice manually from unassigned assets"""
    try:
        db = get_db_manager()
        conn = db.get_connection()
        
        # Generate invoice ID
        invoice_id = f"inv_{uuid.uuid4().hex[:8]}"
        
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
        
        # Create invoice record
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO invoices 
            (id, supplier_name, invoice_no, date_iso, currency, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
        """, (invoice_id, supplier_name, request.invoice_no, request.date_iso, 
              request.currency, datetime.utcnow().isoformat()))
        
        # Attach assets if provided
        if request.asset_ids:
            await _attach_assets_to_invoice(conn, invoice_id, request.asset_ids)
        
        # Process upload token if provided
        if request.upload_token:
            await _process_upload_token(conn, invoice_id, request.upload_token, background_tasks)
        
        conn.commit()
        
        return InvoiceResponse(
            invoice_id=invoice_id,
            supplier_name=supplier_name,
            invoice_no=request.invoice_no,
            date_iso=request.date_iso,
            status="pending"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create invoice: {e}")

@router.post("/{invoice_id}/attach-pages")
async def attach_pages_to_invoice(invoice_id: str, request: AttachPagesRequest):
    """Attach unassigned assets to invoice as pages"""
    try:
        db = get_db_manager()
        conn = db.get_connection()
        
        # Verify invoice exists
        cur = conn.cursor()
        cur.execute("SELECT id FROM invoices WHERE id = ?", (invoice_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Attach assets
        await _attach_assets_to_invoice(conn, invoice_id, request.asset_ids)
        conn.commit()
        
        return {"attached": len(request.asset_ids)}
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"Failed to attach pages: {e}")

@router.post("/{invoice_id}/detach-pages")
async def detach_pages_from_invoice(invoice_id: str, request: AttachPagesRequest):
    """Detach pages from invoice (return to unassigned)"""
    try:
        db = get_db_manager()
        conn = db.get_connection()
        cur = conn.cursor()
        
        # Detach assets
        for asset_id in request.asset_ids:
            cur.execute("""
                UPDATE ingest_assets 
                SET document_id = NULL, document_type = NULL
                WHERE id = ? AND document_id = ?
            """, (asset_id, invoice_id))
        
        conn.commit()
        
        return {"detached": len(request.asset_ids)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to detach pages: {e}")

@router.post("/{invoice_id}/reorder-pages")
async def reorder_invoice_pages(invoice_id: str, request: ReorderPagesRequest):
    """Reorder pages within invoice"""
    try:
        db = get_db_manager()
        conn = db.get_connection()
        cur = conn.cursor()
        
        # Update page order
        for new_order, asset_id in enumerate(request.order):
            cur.execute("""
                UPDATE document_pages 
                SET page_order = ?
                WHERE document_id = ? AND asset_id = ?
            """, (new_order, invoice_id, asset_id))
        
        conn.commit()
        
        return {"reordered": len(request.order)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reorder pages: {e}")

@router.post("/{invoice_id}/pairing/auto")
async def auto_pair_invoice(invoice_id: str):
    """Automatically pair invoice with best matching delivery note"""
    try:
        from backend.services.pairing_service import PairingService
        
        pairing_service = PairingService()
        result = await pairing_service.auto_pair_invoice(invoice_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="No suitable delivery note found")
        
        return result
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"Auto pairing failed: {e}")

@router.post("/{invoice_id}/pairing/manual")
async def manual_pair_invoice(invoice_id: str, dn_id: str):
    """Manually pair invoice with specific delivery note"""
    try:
        from backend.services.pairing_service import PairingService
        
        pairing_service = PairingService()
        result = await pairing_service.manual_pair(invoice_id, dn_id)
        
        return {"ok": True, "link_id": result.get("link_id")}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Manual pairing failed: {e}")

async def _attach_assets_to_invoice(conn: sqlite3.Connection, invoice_id: str, asset_ids: List[str]):
    """Attach assets to invoice as pages"""
    cur = conn.cursor()
    
    for i, asset_id in enumerate(asset_ids):
        # Create document page entry
        cur.execute("""
            INSERT OR REPLACE INTO document_pages 
            (document_id, asset_id, page_order)
            VALUES (?, ?, ?)
        """, (invoice_id, asset_id, i))
        
        # Update asset assignment
        cur.execute("""
            UPDATE ingest_assets 
            SET document_id = ?, document_type = 'invoice'
            WHERE id = ?
        """, (invoice_id, asset_id))

async def _process_upload_token(conn: sqlite3.Connection, invoice_id: str, 
                               upload_token: str, background_tasks: BackgroundTasks):
    """Process upload token and trigger OCR pipeline"""
    # This would integrate with the upload pipeline
    # For now, just log the token
    cur = conn.cursor()
    cur.execute("""
        UPDATE invoices 
        SET upload_token = ?, status = 'processing'
        WHERE id = ?
    """, (upload_token, invoice_id))
    
    # Schedule background OCR processing
    # background_tasks.add_task(process_invoice_ocr, invoice_id) 