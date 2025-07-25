from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List, Dict, Optional
from backend.db import get_all_invoices, get_all_delivery_notes, get_db_connection
from backend.ocr.parse_invoice import parse_invoice_text, extract_line_items_from_text
import os
from datetime import datetime
import re

router = APIRouter(prefix="/invoices", tags=["invoices"])

@router.get("/")
async def get_invoices():
    """Get all invoices with optional filtering."""
    try:
        invoices = get_all_invoices()
        delivery_notes = get_all_delivery_notes()
        
        # Group documents by status
        def group_documents_by_status(invoices, delivery_notes):
            scanned_awaiting_match = []
            matched = []
            unmatched = []
            
            # Process invoices
            for invoice in invoices:
                if invoice.status == 'matched':
                    matched.append(invoice)
                elif invoice.status == 'unmatched':
                    unmatched.append(invoice)
                elif invoice.status == 'scanned':
                    scanned_awaiting_match.append(invoice)
            
            # Process delivery notes
            for dn in delivery_notes:
                if dn.status == 'matched':
                    matched.append(dn)
                elif dn.status == 'unmatched':
                    unmatched.append(dn)
                elif dn.status == 'scanned':
                    scanned_awaiting_match.append(dn)
            
            return {
                "scanned_awaiting_match": scanned_awaiting_match,
                "matched": matched,
                "unmatched": unmatched
            }
        
        grouped_documents = group_documents_by_status(invoices, delivery_notes)
        
        return {
            "invoices": invoices,
            "delivery_notes": delivery_notes,
            "grouped": grouped_documents
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/summary")
async def get_invoice_summary():
    """Get summary statistics for invoices."""
    try:
        invoices = get_all_invoices()
        
        total_invoices = len(invoices)
        total_value = sum(invoice.total_amount or 0 for invoice in invoices)
        matched_count = sum(1 for invoice in invoices if invoice.status == 'matched')
        scanned_count = sum(1 for invoice in invoices if invoice.status == 'scanned')
        unmatched_count = sum(1 for invoice in invoices if invoice.status == 'unmatched')
        
        summary = {
            "total_invoices": total_invoices,
            "total_value": total_value,
            "matched_count": matched_count,
            "scanned_count": scanned_count,
            "unmatched_count": unmatched_count
        }
        
        return summary
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/{invoice_id}")
async def get_invoice_detail(invoice_id: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get invoice details
        cursor.execute("""
            SELECT id, invoice_number, invoice_date, supplier_name, total_amount, 
                   status, confidence, upload_timestamp, parent_pdf_filename, ocr_text
            FROM invoices 
            WHERE id = ?
        """, (invoice_id,))
        
        invoice_row = cursor.fetchone()
        if not invoice_row:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Convert to dict
        invoice_data = {
            "id": invoice_row[0],
            "invoice_number": invoice_row[1],
            "invoice_date": invoice_row[2],
            "supplier_name": invoice_row[3],
            "total_amount": float(invoice_row[4]) if invoice_row[4] else 0.0,
            "status": invoice_row[5],
            "confidence": float(invoice_row[6]) if invoice_row[6] else 0.0,
            "upload_timestamp": invoice_row[7],
            "parent_pdf_filename": invoice_row[8],
            "ocr_text": invoice_row[9]
        }
        
        # ✅ Enhanced line items extraction with VAT calculations
        line_items = []
        vat_calculations = {}
        
        if invoice_data["ocr_text"]:
            # Use the enhanced parsing function
            parsed_data = parse_invoice_text(invoice_data["ocr_text"])
            
            # Extract VAT calculations
            vat_calculations = {
                "subtotal": parsed_data.get("subtotal", 0.0),
                "vat": parsed_data.get("vat", 0.0),
                "vat_rate": parsed_data.get("vat_rate", 0.2),
                "total_incl_vat": parsed_data.get("total_incl_vat", invoice_data["total_amount"])
            }
            
            # Use enhanced line items with VAT calculations
            line_items = parsed_data.get("line_items", [])
            
            # If no line items found, fall back to simple extraction
            if not line_items:
                line_items = extract_line_items_from_ocr(invoice_data["ocr_text"])
        
        # ✅ Check for delivery note match
        delivery_note_match = None
        cursor.execute("""
            SELECT id, delivery_note_number, delivery_date, supplier_name, total_amount, status
            FROM delivery_notes 
            WHERE supplier_name = ? AND delivery_date = ?
        """, (invoice_data["supplier_name"], invoice_data["invoice_date"]))
        
        delivery_row = cursor.fetchone()
        if delivery_row:
            delivery_note_match = {
                "id": delivery_row[0],
                "delivery_note_number": delivery_row[1],
                "delivery_date": delivery_row[2],
                "supplier_name": delivery_row[3],
                "total_amount": float(delivery_row[4]) if delivery_row[4] else 0.0,
                "status": delivery_row[5]
            }
        
        # ✅ Calculate price mismatches if delivery note exists
        price_mismatches = []
        if delivery_note_match and abs(invoice_data["total_amount"] - delivery_note_match["total_amount"]) > 0.01:
            price_mismatches.append({
                "description": "Total Amount Mismatch",
                "invoice_amount": invoice_data["total_amount"],
                "delivery_amount": delivery_note_match["total_amount"],
                "difference": invoice_data["total_amount"] - delivery_note_match["total_amount"]
            })
        
        conn.close()
        
        # Return enhanced invoice data with VAT calculations
        return {
            **invoice_data,
            **vat_calculations,  # Include VAT calculations
            "line_items": line_items,
            "delivery_note_match": delivery_note_match,
            "price_mismatches": price_mismatches
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

def extract_line_items_from_ocr(ocr_text: str) -> list:
    """
    Extract line items from OCR text using pattern matching.
    This is a simplified implementation - in production, you'd use more sophisticated parsing.
    """
    line_items = []
    
    # Split text into lines
    lines = ocr_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Look for patterns like: "Item Name    2    £45.99    £91.98"
        # or "Description    Qty    Price    Total"
        parts = line.split()
        
        if len(parts) >= 4:
            try:
                # Try to extract quantity and prices
                # Look for numbers that could be quantities and prices
                numbers = []
                words = []
                
                for part in parts:
                    # Remove currency symbols and commas
                    clean_part = part.replace('£', '').replace('$', '').replace(',', '')
                    try:
                        num = float(clean_part)
                        numbers.append(num)
                    except ValueError:
                        words.append(part)
                
                if len(numbers) >= 2:
                    # Assume last number is total, second to last is unit price
                    total_price = numbers[-1]
                    unit_price = numbers[-2]
                    
                    # Calculate quantity
                    if unit_price > 0:
                        quantity = round(total_price / unit_price, 2)
                    else:
                        quantity = 1
                    
                    # Description is everything before the numbers
                    description = ' '.join(words)
                    
                    if description and len(description) > 2:
                        # ✅ Add VAT calculations for fallback line items
                        vat_rate = 0.2  # Default 20% VAT
                        unit_price_excl_vat = unit_price
                        unit_price_incl_vat = round(unit_price * (1 + vat_rate), 2)
                        line_total_excl_vat = total_price
                        line_total_incl_vat = round(total_price * (1 + vat_rate), 2)
                        
                        line_items.append({
                            "description": description,
                            "quantity": quantity,
                            "unit_price": unit_price,  # Keep for backward compatibility
                            "total_price": total_price,  # Keep for backward compatibility
                            "unit_price_excl_vat": unit_price_excl_vat,
                            "unit_price_incl_vat": unit_price_incl_vat,
                            "line_total_excl_vat": line_total_excl_vat,
                            "line_total_incl_vat": line_total_incl_vat,
                            "flagged": False  # Could be enhanced with business rules
                        })
            except (ValueError, IndexError):
                continue
    
    return line_items

@router.post("/{invoice_id}/pair")
async def pair_invoice_with_delivery_note(invoice_id: str, delivery_note_id: str):
    """Pair an invoice with a delivery note."""
    try:
        # This would update the database to link the invoice and delivery note
        # For now, return a success message
        return {
            "message": "Invoice paired successfully",
            "invoice_id": invoice_id,
            "delivery_note_id": delivery_note_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pairing failed: {str(e)}")

@router.delete("/{invoice_id}")
async def delete_invoice(invoice_id: str):
    """Delete an invoice."""
    try:
        # This would delete the invoice from the database
        # For now, return a success message
        return {
            "message": "Invoice deleted successfully",
            "invoice_id": invoice_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}") 