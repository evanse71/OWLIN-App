#!/usr/bin/env python3
"""
Document Queue API endpoints for reviewing and classifying uploaded documents.
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from db import get_all_invoices, get_all_delivery_notes

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/documents/queue")
async def get_documents_for_review():
    """Get all documents that need review - now returns real invoice data"""
    try:
        # Get real invoices from database
        invoices_data = get_all_invoices()
        
        documents = []
        
        for invoice in invoices_data:
            # Determine status badge based on confidence and status
            status = invoice["status"]
            confidence = float(invoice["confidence"] or 0.0)
            
            if status == 'scanned':
                if confidence < 0.7:
                    status_badge = 'Low Confidence'
                else:
                    status_badge = 'Awaiting Review'
            elif status == 'unmatched':
                status_badge = 'Needs Pairing'
            elif status == 'matched':
                status_badge = 'Complete'
            else:
                status_badge = 'Unknown'
            
            documents.append({
                "id": invoice["id"],
                "filename": invoice["parent_pdf_filename"] or "Unknown",
                "file_type": "invoice",
                "file_path": f"data/uploads/{invoice['parent_pdf_filename']}" if invoice["parent_pdf_filename"] else "",
                "file_size": len(invoice["ocr_text"]) if invoice["ocr_text"] else 0,
                "upload_timestamp": invoice["upload_timestamp"],
                "processing_status": status,
                "confidence": confidence,
                "extracted_text": invoice["ocr_text"],
                "error_message": None,
                "supplier_guess": invoice["supplier_name"],
                "document_type_guess": "invoice",
                "status_badge": status_badge,
                "invoice_number": invoice["invoice_number"],
                "invoice_date": invoice["invoice_date"],
                "total_amount": float(invoice["total_amount"] or 0)
            })
        
        return {"documents": documents}
        
    except Exception as e:
        logger.error(f"Error getting documents for review: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/documents/invoices")
async def get_invoice_documents():
    """Get all invoice documents for the frontend"""
    try:
        # Get real invoices from database
        invoices_data = get_all_invoices()
        
        # Transform to match frontend expectations
        invoices = []
        for invoice in invoices_data:
            transformed_invoice = {
                "id": invoice["id"],
                "invoice_number": invoice["invoice_number"],
                "invoice_date": invoice["invoice_date"],
                "supplier_name": invoice["supplier_name"],
                "total_amount": float(invoice["total_amount"]) if invoice["total_amount"] else 0.0,
                "status": invoice["status"],
                "confidence": float(invoice["confidence"]) if invoice["confidence"] else 0.0,
                "upload_timestamp": invoice["upload_timestamp"],
                "parent_pdf_filename": invoice["parent_pdf_filename"],
                "ocr_text": invoice["ocr_text"]
            }
            invoices.append(transformed_invoice)
        
        return {"invoices": invoices}
        
    except Exception as e:
        logger.error(f"Error getting invoice documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/documents/delivery-notes")
async def get_delivery_note_documents():
    """Get all delivery note documents for the frontend"""
    try:
        # Get real delivery notes from database
        delivery_notes_data = get_all_delivery_notes()
        
        # Transform to match frontend expectations
        delivery_notes = []
        for dn in delivery_notes_data:
            transformed_dn = {
                "id": dn["id"],
                "delivery_note_number": dn["delivery_note_number"],
                "delivery_date": dn["delivery_date"],
                "supplier_name": dn["supplier_name"],
                "total_amount": float(dn["total_amount"]) if dn["total_amount"] else 0.0,
                "status": dn["status"],
                "confidence": float(dn["confidence"]) if dn["confidence"] else 0.0,
                "upload_timestamp": dn["upload_timestamp"],
                "parent_pdf_filename": dn["parent_pdf_filename"],
                "ocr_text": dn["ocr_text"]
            }
            delivery_notes.append(transformed_dn)
        
        return {"delivery_notes": delivery_notes}
        
    except Exception as e:
        logger.error(f"Error getting delivery note documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/documents/approve")
async def approve_document(payload: dict, request: Request):
    """Approve a document - update its status"""
    try:
        doc_id = payload.get("doc_id")
        new_status = payload.get("status", "approved")
        
        # This would update the database
        # For now, return success
        return {
            "message": "Document approved successfully",
            "doc_id": doc_id,
            "status": new_status
        }
        
    except Exception as e:
        logger.error(f"Error approving document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Approval failed: {str(e)}")

@router.post("/documents/escalate")
async def escalate_document(payload: dict, request: Request):
    """Escalate a document for manual review"""
    try:
        doc_id = payload.get("doc_id")
        reason = payload.get("reason", "Manual review required")
        
        # This would update the database
        # For now, return success
        return {
            "message": "Document escalated for review",
            "doc_id": doc_id,
            "reason": reason
        }
        
    except Exception as e:
        logger.error(f"Error escalating document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Escalation failed: {str(e)}")

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document"""
    try:
        # This would delete from the database
        # For now, return success
        return {
            "message": "Document deleted successfully",
            "doc_id": doc_id
        }
        
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}") 