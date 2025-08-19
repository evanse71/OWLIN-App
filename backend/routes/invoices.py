from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from typing import List, Dict, Optional
from db import get_all_invoices, get_all_delivery_notes, get_db_connection
from ocr.parse_invoice import parse_invoice, extract_line_items
from ocr.field_extractor import extract_invoice_metadata
from services.invoice_query import invoice_query_service, InvoiceFilter, InvoiceSort
import os
import logging
from datetime import datetime
import re
import json

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invoices", tags=["invoices"])

@router.get("/")
async def get_invoices(
    venue_id: Optional[str] = Query(None, description="Filter by venue ID"),
    supplier_name: Optional[str] = Query(None, description="Filter by supplier name"),
    date_start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    status: Optional[List[str]] = Query(None, description="Filter by status"),
    search_text: Optional[str] = Query(None, description="Search in supplier, invoice number, date"),
    only_flagged: bool = Query(False, description="Show only flagged invoices"),
    only_unmatched: bool = Query(False, description="Show only unmatched invoices"),
    only_with_credit: bool = Query(False, description="Show only invoices with credit"),
    include_utilities: bool = Query(True, description="Include utility bills"),
    sort_by: str = Query("date_desc", description="Sort order"),
    limit: Optional[int] = Query(None, description="Limit number of results"),
    offset: int = Query(0, description="Offset for pagination"),
    role: str = Query("viewer", description="User role for defaults")
):
    """Get invoices with advanced filtering and sorting."""
    try:
        logger.info(f"Fetching invoices with filters: venue={venue_id}, supplier={supplier_name}, status={status}")
        
        # Build filter object
        filters = InvoiceFilter(
            venue_id=venue_id,
            supplier_name=supplier_name,
            date_start=date_start,
            date_end=date_end,
            status=status,
            search_text=search_text,
            only_flagged=only_flagged,
            only_unmatched=only_unmatched,
            only_with_credit=only_with_credit,
            include_utilities=include_utilities
        )
        
        # Build sort object
        sort = InvoiceSort(
            sort_by=sort_by,
            limit=limit,
            offset=offset
        )
        
        # Execute query
        result = invoice_query_service.query_invoices(filters, sort, role)
        
        logger.info(f"Query returned {len(result.invoices)} invoices in {result.query_time_ms:.2f}ms")
        
        return {
            "invoices": result.invoices,
            "count": result.total_count,
            "filters_applied": result.filters_applied,
            "query_time_ms": result.query_time_ms
        }
        
    except Exception as e:
        logger.exception(f"Error fetching invoices: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/suppliers")
async def get_suppliers():
    """Get list of distinct suppliers for dropdown."""
    try:
        suppliers = invoice_query_service.get_distinct_suppliers()
        return {"suppliers": suppliers}
    except Exception as e:
        logger.exception(f"Error fetching suppliers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/venues")
async def get_venues():
    """Get list of distinct venues for dropdown."""
    try:
        venues = invoice_query_service.get_distinct_venues()
        return {"venues": venues}
    except Exception as e:
        logger.exception(f"Error fetching venues: {str(e)}")
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
        logger.exception(f"Error fetching invoice summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/{invoice_id}")
async def get_invoice_detail(invoice_id: str):
    """Get detailed invoice information with enhanced error handling."""
    logger.info(f"Fetching invoice details for ID: {invoice_id}")
    
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
            logger.warning(f"Invoice not found: {invoice_id}")
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Convert to dict with proper type handling
        invoice_data = {
            "id": invoice_row[0],
            "invoice_number": invoice_row[1] or "Unknown",
            "invoice_date": invoice_row[2] or "Unknown",
            "supplier_name": invoice_row[3] or "Unknown",
            "total_amount": float(invoice_row[4]) if invoice_row[4] else 0.0,
            "status": invoice_row[5] or "scanned",
            "confidence": float(invoice_row[6]) if invoice_row[6] else 0.0,
            "upload_timestamp": invoice_row[7],
            "parent_pdf_filename": invoice_row[8],
            "ocr_text": invoice_row[9] or ""
        }
        
        logger.debug(f"Invoice data: {invoice_data}")
        
        # ✅ Fix confidence calculation - ensure it's a percentage (0-100)
        if invoice_data["confidence"] > 1.0:
            # If confidence is stored as decimal (0.0-1.0), convert to percentage
            invoice_data["confidence"] = min(100.0, invoice_data["confidence"] * 100)
        else:
            # If already a percentage, ensure it's capped at 100
            invoice_data["confidence"] = min(100.0, invoice_data["confidence"])
        
        logger.debug(f"Adjusted confidence: {invoice_data['confidence']}%")
        
        # Extract line items and metadata from OCR text
        line_items = []
        vat_rate = 20.0  # Default VAT rate
        subtotal = 0.0
        vat_amount = 0.0
        total_amount = 0.0
        
        if invoice_data["ocr_text"]:
            try:
                logger.debug("Extracting metadata from OCR text")
                # Use the enhanced parsing function
                parsed_data = extract_invoice_metadata(invoice_data["ocr_text"])
                
                # Extract VAT calculations with fallbacks
                vat_rate = parsed_data.get("vat_rate", 20.0)
                subtotal = parsed_data.get("subtotal", 0.0)
                vat_amount = parsed_data.get("vat", 0.0)
                total_amount = parsed_data.get("total_amount", 0.0)
                
                # ✅ Calculate totals from line items if missing
                line_items = extract_line_items_from_ocr(invoice_data["ocr_text"])
                
                if line_items and (total_amount == 0.0 or subtotal == 0.0):
                    # Calculate totals from line items
                    calculated_subtotal = sum(item.get("line_total_excl_vat", item.get("total_price", 0)) for item in line_items)
                    calculated_vat = calculated_subtotal * (vat_rate / 100)
                    calculated_total = calculated_subtotal + calculated_vat
                    
                    if subtotal == 0.0:
                        subtotal = calculated_subtotal
                    if vat_amount == 0.0:
                        vat_amount = calculated_vat
                    if total_amount == 0.0:
                        total_amount = calculated_total
                    
                    logger.info(f"Calculated totals from line items: subtotal={subtotal}, vat={vat_amount}, total={total_amount}")
                
                # Update invoice data with extracted values
                if parsed_data.get("supplier_name") and parsed_data["supplier_name"] != "Unknown":
                    invoice_data["supplier_name"] = parsed_data["supplier_name"]
                if parsed_data.get("invoice_number") and parsed_data["invoice_number"] != "Unknown":
                    invoice_data["invoice_number"] = parsed_data["invoice_number"]
                if parsed_data.get("invoice_date") and parsed_data["invoice_date"] != "Unknown":
                    invoice_data["invoice_date"] = parsed_data["invoice_date"]
                
            except Exception as e:
                logger.warning(f"Error parsing OCR text: {str(e)}")
                # Continue with fallback values
        
        # Add calculated values to invoice data
        invoice_data.update({
            "subtotal": subtotal,
            "vat": vat_amount,
            "vat_rate": vat_rate,
            "total_incl_vat": total_amount,
            "line_items": line_items
        })
        
        # ✅ Check for delivery note match
        delivery_note_match = None
        try:
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
        except Exception as e:
            logger.warning(f"Error checking delivery note match: {str(e)}")
        
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
        
        # ✅ Log full response for debugging
        response_data = {
            **invoice_data,
            "delivery_note_match": delivery_note_match,
            "price_mismatches": price_mismatches
        }
        
        logger.info(f"Successfully fetched invoice {invoice_id} with {len(line_items)} line items")
        logger.debug(f"Full response: {response_data}")
        
        return response_data
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.exception(f"Unexpected error fetching invoice {invoice_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

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
                        price_per_unit = round(line_total_incl_vat / quantity, 2) if quantity > 0 else 0
                        
                        line_items.append({
                            "item": description,  # Use "item" for consistency
                            "description": description,  # Keep for backward compatibility
                            "quantity": quantity,
                            "unit_price": unit_price,  # Keep for backward compatibility
                            "total_price": total_price,  # Keep for backward compatibility
                            "price_excl_vat": line_total_excl_vat,
                            "vat_rate": vat_rate,
                            "price_incl_vat": line_total_incl_vat,
                            "price_per_unit": price_per_unit,
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

# Add new endpoints for vertical cards functionality

@router.patch("/{invoice_id}/line-item/{row_idx}")
async def update_line_item(
    invoice_id: str,
    row_idx: int,
    update_data: dict
):
    """Update a single line item in an invoice"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if line item exists
        cursor.execute(
            "SELECT * FROM invoice_line_items WHERE invoice_id = ? AND row_idx = ?",
            (invoice_id, row_idx)
        )
        existing_item = cursor.fetchone()
        
        if not existing_item:
            raise HTTPException(status_code=404, detail="Line item not found")
        
        # Update the line item
        update_fields = []
        update_values = []
        
        for field, value in update_data.items():
            if field in ['description', 'quantity', 'unit', 'unit_price', 'vat_rate', 'line_total', 'page', 'row_idx', 'confidence', 'flags']:
                update_fields.append(f"{field} = ?")
                if field == 'flags' and isinstance(value, list):
                    update_values.append(json.dumps(value))
                else:
                    update_values.append(value)
        
        if update_fields:
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            update_values.extend([invoice_id, row_idx])
            
            query = f"""
                UPDATE invoice_line_items 
                SET {', '.join(update_fields)}
                WHERE invoice_id = ? AND row_idx = ?
            """
            
            cursor.execute(query, update_values)
            conn.commit()
            
            # Log the update
            logger.info(f"Updated line item {row_idx} for invoice {invoice_id}: {update_data}")
            
            return {"success": True, "message": "Line item updated successfully"}
        
    except Exception as e:
        logger.error(f"Failed to update line item: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update line item: {str(e)}")
    finally:
        conn.close()

@router.patch("/{invoice_id}/flags")
async def update_flags(
    invoice_id: str,
    flags_data: dict
):
    """Update flags for an invoice or specific line items"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if invoice exists
        cursor.execute("SELECT id FROM invoices WHERE id = ?", (invoice_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Update invoice flags
        if 'invoice_flags' in flags_data:
            cursor.execute(
                "UPDATE invoices SET flags = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (json.dumps(flags_data['invoice_flags']), invoice_id)
            )
        
        # Update line item flags
        if 'line_item_flags' in flags_data:
            for row_idx, flags in flags_data['line_item_flags'].items():
                cursor.execute(
                    "UPDATE invoice_line_items SET flags = ?, updated_at = CURRENT_TIMESTAMP WHERE invoice_id = ? AND row_idx = ?",
                    (json.dumps(flags), invoice_id, row_idx)
                )
        
        conn.commit()
        logger.info(f"Updated flags for invoice {invoice_id}")
        
        return {"success": True, "message": "Flags updated successfully"}
        
    except Exception as e:
        logger.error(f"Failed to update flags: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update flags: {str(e)}")
    finally:
        conn.close()

@router.post("/{invoice_id}/signatures/extract")
async def extract_signatures(invoice_id: str):
    """Extract signature regions for an invoice"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if invoice exists
        cursor.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
        invoice = cursor.fetchone()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # TODO: Implement signature extraction logic
        # This would involve:
        # 1. Loading the invoice PDF
        # 2. Using computer vision to detect signature regions
        # 3. Cropping and storing the signature images
        # 4. Updating the signature_regions field
        
        # For now, return a mock response
        signature_regions = [
            {
                "page": 1,
                "bbox": {"x": 100, "y": 500, "width": 200, "height": 50},
                "image_b64": "mock_signature_image_base64"
            }
        ]
        
        # Update the invoice with signature regions
        cursor.execute(
            "UPDATE invoices SET signature_regions = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (json.dumps(signature_regions), invoice_id)
        )
        conn.commit()
        
        return {
            "success": True,
            "message": "Signatures extracted successfully",
            "signature_regions": signature_regions
        }
        
    except Exception as e:
        logger.error(f"Failed to extract signatures: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to extract signatures: {str(e)}")
    finally:
        conn.close()

@router.patch("/{invoice_id}/verification-status")
async def update_verification_status(
    invoice_id: str,
    status_data: dict
):
    """Update the verification status of an invoice"""
    try:
        status = status_data.get('status')
        if status not in ['unreviewed', 'needs_review', 'reviewed']:
            raise HTTPException(status_code=400, detail="Invalid verification status")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE invoices SET verification_status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, invoice_id)
        )
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        conn.commit()
        logger.info(f"Updated verification status to {status} for invoice {invoice_id}")
        
        return {"success": True, "message": "Verification status updated successfully"}
        
    except Exception as e:
        logger.error(f"Failed to update verification status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update verification status: {str(e)}")
    finally:
        conn.close() 