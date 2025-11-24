# backend/routes/invoices_submit.py
"""
Session management and submission routes for invoices.
Handles session clearing and batch submission with audit logging.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime
import sqlite3
from backend.app.db import append_audit

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


class ClearSessionRequest(BaseModel):
    """Request to clear session invoices (client-side only operation)"""
    pass


class SubmitInvoicesRequest(BaseModel):
    """Request to submit (commit) invoices"""
    invoice_ids: List[str]


class SubmitInvoicesResponse(BaseModel):
    """Response after submitting invoices"""
    success: bool
    submitted_count: int
    invoice_ids: List[str]
    message: str


@router.post("/session/clear")
async def clear_session(request: ClearSessionRequest):
    """
    Clear session invoices - this is a client-side operation.
    Server logs the action but doesn't modify database entries.
    Only affects the UI session scope, not persisted invoices.
    """
    try:
        # Log the session clear action
        append_audit(
            datetime.now().isoformat(),
            "local",
            "SESSION_CLEAR",
            '{"action": "clear_session", "note": "Client-side session cleared"}'
        )
        
        return {
            "success": True,
            "message": "Session cleared successfully"
        }
    
    except Exception as e:
        error_msg = str(e)
        append_audit(
            datetime.now().isoformat(),
            "local",
            "SESSION_CLEAR_ERROR",
            f'{{"error": "{error_msg}"}}'
        )
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/submit", response_model=SubmitInvoicesResponse)
async def submit_invoices(request: SubmitInvoicesRequest):
    """
    Submit (commit) invoices - marks them as submitted/immutable.
    Updates status in database and returns updated invoice list.
    """
    try:
        if not request.invoice_ids:
            return SubmitInvoicesResponse(
                success=True,
                submitted_count=0,
                invoice_ids=[],
                message="No invoices to submit"
            )
        
        # Update invoices to submitted status
        con = sqlite3.connect("data/owlin.db", check_same_thread=False)
        cur = con.cursor()
        
        # Update each invoice status to 'submitted'
        placeholders = ','.join('?' * len(request.invoice_ids))
        cur.execute(f"""
            UPDATE invoices 
            SET status = 'submitted'
            WHERE id IN ({placeholders})
        """, request.invoice_ids)
        
        updated_count = cur.rowcount
        con.commit()
        con.close()
        
        # Log the submission
        append_audit(
            datetime.now().isoformat(),
            "local",
            "SESSION_SUBMIT",
            f'{{"count": {updated_count}, "invoice_ids": {request.invoice_ids}}}'
        )
        
        return SubmitInvoicesResponse(
            success=True,
            submitted_count=updated_count,
            invoice_ids=request.invoice_ids,
            message=f"Successfully submitted {updated_count} invoice(s)"
        )
    
    except Exception as e:
        error_msg = str(e)
        append_audit(
            datetime.now().isoformat(),
            "local",
            "SESSION_SUBMIT_ERROR",
            f'{{"error": "{error_msg}", "invoice_ids": {request.invoice_ids}}}'
        )
        raise HTTPException(status_code=500, detail=error_msg)

