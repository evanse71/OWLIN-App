from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sqlite3
import uuid
from datetime import datetime

router = APIRouter()

class ManualInvoiceRequest(BaseModel):
    supplier: str
    invoice_date: str
    total_value: float
    notes: str = ""

@router.post("/invoices/manual")
def create_manual_invoice(request: ManualInvoiceRequest):
    """Create manual invoice"""
    try:
        conn = sqlite3.connect("data/owlin.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Generate invoice ID
        invoice_id = f"inv_{uuid.uuid4().hex[:8]}"
        document_id = f"doc_{uuid.uuid4().hex[:8]}"
        
        # Insert invoice
        cursor.execute("""
            INSERT INTO invoices 
            (id, document_id, supplier, invoice_date, total_value, status, matched_delivery_note_id)
            VALUES (?, ?, ?, ?, ?, 'manual', NULL)
        """, (invoice_id, document_id, request.supplier, request.invoice_date, request.total_value))
        
        conn.commit()
        conn.close()
        
        return {
            "invoice_id": invoice_id,
            "document_id": document_id,
            "supplier": request.supplier,
            "invoice_date": request.invoice_date,
            "total_value": request.total_value,
            "status": "manual"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
