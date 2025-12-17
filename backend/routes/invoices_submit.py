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
from backend.app.db import append_audit, DB_PATH

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


class DeleteInvoicesRequest(BaseModel):
    """Request model for deleting invoices"""
    invoice_ids: List[str]


@router.post("/batch/delete")
async def delete_invoices(request: DeleteInvoicesRequest):
    """
    Delete invoices that haven't been submitted yet.
    Removes invoices, line items, and associated documents.
    Only allows deletion of invoices with status != 'submitted'.
    This allows users to clear uploaded invoices before submission.
    Handles both scanned and manual invoices (both stored in invoices table).
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[DELETE_INVOICES] Received request to delete {len(request.invoice_ids)} invoices")
    
    try:
        invoice_ids = request.invoice_ids
        if not invoice_ids:
            return {"success": False, "deleted_count": 0, "message": "No invoice IDs provided"}
        
        con = sqlite3.connect(DB_PATH, check_same_thread=False)
        cur = con.cursor()
        
        deleted_count = 0
        skipped_count = 0
        errors = []
        
        for invoice_id in invoice_ids:
            try:
                # Check invoice exists and get its status
                cur.execute("SELECT doc_id, status FROM invoices WHERE id = ?", (invoice_id,))
                invoice_row = cur.fetchone()
                
                if invoice_row:
                    # Invoice exists in invoices table
                    doc_id = invoice_row[0] if invoice_row else None
                    invoice_status = invoice_row[1] if len(invoice_row) > 1 else None
                    
                    # Only delete invoices that haven't been submitted
                    if invoice_status == 'submitted':
                        skipped_count += 1
                        errors.append(f"Invoice {invoice_id} is already submitted and cannot be deleted")
                        continue
                    
                    # Delete invoice line items first (foreign key constraint)
                    cur.execute("DELETE FROM invoice_line_items WHERE invoice_id = ?", (invoice_id,))
                    
                    # Delete invoice
                    cur.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
                    
                    # Delete associated document if exists (using doc_id from invoice or invoice_id as fallback)
                    if doc_id:
                        cur.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
                    else:
                        # If no doc_id in invoice, try using invoice_id as doc_id (some documents use invoice_id as doc_id)
                        cur.execute("DELETE FROM documents WHERE id = ?", (invoice_id,))
                    
                    deleted_count += 1
                else:
                    # Invoice not found in invoices table - might be a document-only entry (e.g., error documents)
                    # Try to delete directly from documents table
                    cur.execute("SELECT status FROM documents WHERE id = ?", (invoice_id,))
                    doc_row = cur.fetchone()
                    
                    if doc_row:
                        doc_status = doc_row[0] if doc_row else None
                        
                        # Only delete documents that haven't been submitted
                        if doc_status == 'submitted':
                            skipped_count += 1
                            errors.append(f"Document {invoice_id} is already submitted and cannot be deleted")
                            continue
                        
                        # Delete document directly
                        cur.execute("DELETE FROM documents WHERE id = ?", (invoice_id,))
                        deleted_count += 1
                    else:
                        errors.append(f"Invoice/Document {invoice_id} not found in invoices or documents table")
                        continue
                
            except Exception as e:
                error_msg = f"Error deleting invoice {invoice_id}: {str(e)}"
                errors.append(error_msg)
                print(error_msg)
                continue
        
        con.commit()
        con.close()
        
        # Log the deletion
        logger.info(f"[DELETE_INVOICES] Deleted {deleted_count} invoices, skipped {skipped_count}")
        append_audit(
            datetime.now().isoformat(), 
            "local", 
            "delete_invoices", 
            f'{{"count": {deleted_count}, "skipped": {skipped_count}, "ids": {invoice_ids}, "errors": {errors}}}'
        )
        
        message = f"Successfully deleted {deleted_count} invoice(s)"
        if skipped_count > 0:
            message += f", skipped {skipped_count} submitted invoice(s)"
        if errors and deleted_count == 0:
            message += f". Errors: {'; '.join(errors[:3])}"  # Show first 3 errors
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "skipped_count": skipped_count,
            "message": message
        }
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[DELETE_INVOICES] Error: {error_msg}", exc_info=True)
        append_audit(datetime.now().isoformat(), "local", "delete_invoices_error", f'{{"error": "{error_msg}"}}')
        raise HTTPException(status_code=500, detail=f"Failed to delete invoices: {error_msg}")


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
        con = sqlite3.connect(DB_PATH, check_same_thread=False)
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



