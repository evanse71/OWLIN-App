"""
Manual Invoice & Delivery Note Entry Router

Allows users to manually create invoices and delivery notes without OCR/scanning.
Manual entries are stored in the same tables as scanned documents but marked with source='manual'.
"""
import logging
import sqlite3
import uuid
from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.db import DB_PATH, append_audit, get_line_items_for_invoice
from backend.services import pairing_service
from backend.services.quantity_validator import validate_quantity_match

router = APIRouter(prefix="/api/manual", tags=["manual-entry"])
LOGGER = logging.getLogger("owlin.routes.manual_entry")


# ============================================================================
# Pydantic Schemas
# ============================================================================

class LineItemCreate(BaseModel):
    """Line item for manual invoice/delivery note"""
    description: str = Field(..., min_length=1, description="Item description")
    sku: Optional[str] = Field(None, description="SKU code")
    quantity: float = Field(..., ge=0, description="Quantity")
    unit: Optional[str] = Field(None, description="Unit of measure (e.g., 'kg', 'pcs')")
    unit_price: Optional[float] = Field(None, ge=0, description="Price per unit")
    line_total: Optional[float] = Field(None, ge=0, description="Total for this line (auto-calculated if not provided)")
    weight: Optional[float] = Field(None, ge=0, description="Weight in kg (for delivery notes)")


class ManualInvoiceCreate(BaseModel):
    """Request to create a manual invoice"""
    venue: str = Field(..., description="Venue ID or name")
    supplier: str = Field(..., min_length=1, description="Supplier name")
    invoice_number: str = Field(..., min_length=1, description="Invoice number")
    invoice_date: str = Field(..., description="Invoice date (YYYY-MM-DD)")
    currency: Optional[str] = Field("GBP", description="Currency code")
    subtotal: Optional[float] = Field(None, ge=0, description="Subtotal")
    tax_total: Optional[float] = Field(None, ge=0, description="Tax amount")
    grand_total: Optional[float] = Field(None, ge=0, description="Grand total")
    notes: Optional[str] = Field(None, description="Additional notes")
    line_items: List[LineItemCreate] = Field(..., min_items=1, description="At least one line item required")


class ManualDeliveryNoteCreate(BaseModel):
    """Request to create a manual delivery note"""
    venue: str = Field(..., description="Venue ID or name")
    supplier: str = Field(..., min_length=1, description="Supplier name")
    delivery_note_number: str = Field(..., min_length=1, description="Delivery note number")
    delivery_date: str = Field(..., description="Delivery date (YYYY-MM-DD)")
    supervisor: Optional[str] = Field(None, description="Name of supervisor who took the delivery")
    notes: Optional[str] = Field(None, description="Additional notes")
    line_items: List[LineItemCreate] = Field(..., min_items=1, description="At least one line item required")


class ManualInvoiceResponse(BaseModel):
    """Response after creating manual invoice"""
    id: str
    invoice_number: str
    supplier: str
    date: str
    total_value: float
    status: str
    source: str
    message: str


class ManualDeliveryNoteResponse(BaseModel):
    """Response after creating manual delivery note"""
    id: str
    delivery_note_number: str
    supplier: str
    date: str
    source: str
    message: str


class ManualMatchRequest(BaseModel):
    """Request to match an invoice to a delivery note"""
    invoice_id: str = Field(..., description="Invoice ID (from invoices table)")
    delivery_note_id: str = Field(..., description="Delivery note ID (from documents table)")


class ManualMatchResponse(BaseModel):
    """Response after matching invoice to delivery note"""
    invoice_id: str
    delivery_note_id: str
    status: str
    issues_count: int
    paired: bool
    message: str
    warnings: List[str] = []
    quantity_match_score: float = 1.0


# ============================================================================
# Helper Functions
# ============================================================================

def generate_manual_doc_id() -> str:
    """Generate a unique document ID for manual entries"""
    return f"manual-{uuid.uuid4().hex[:12]}"


def calculate_line_total(quantity: float, unit_price: Optional[float]) -> Optional[float]:
    """Calculate line total from quantity and unit price"""
    if unit_price is not None and quantity is not None:
        return round(quantity * unit_price, 2)
    return None


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/invoices", response_model=ManualInvoiceResponse)
def create_manual_invoice(data: ManualInvoiceCreate):
    """
    Create a manual invoice entry.
    
    Creates an invoice record in the invoices table with source='manual' and status='ready'.
    Also creates a placeholder document entry and line items.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Generate IDs
        invoice_id = generate_manual_doc_id()
        doc_id = generate_manual_doc_id()
        
        # Calculate grand total if not provided
        grand_total = data.grand_total
        if grand_total is None:
            if data.subtotal is not None and data.tax_total is not None:
                grand_total = data.subtotal + data.tax_total
            elif data.line_items:
                # Sum line totals
                line_totals = []
                for item in data.line_items:
                    line_total = item.line_total
                    if line_total is None:
                        line_total = calculate_line_total(item.quantity, item.unit_price)
                    if line_total is not None:
                        line_totals.append(line_total)
                grand_total = sum(line_totals) if line_totals else 0.0
        
        if grand_total is None:
            grand_total = 0.0
        
        # Create placeholder document entry
        cursor.execute("""
            INSERT INTO documents (id, filename, stored_path, size_bytes, uploaded_at, status, ocr_stage, ocr_confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_id,
            f"Manual Invoice {data.invoice_number}",
            None,  # No file path for manual entries
            0,  # No file size
            datetime.now().isoformat(),
            'completed',
            'manual',
            1.0  # Full confidence for manual entries
        ))
        
        # Create invoice entry
        cursor.execute("""
            INSERT INTO invoices (id, doc_id, supplier, date, value, confidence, status, venue, issues_count, paired, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            invoice_id,
            doc_id,
            data.supplier,
            data.invoice_date,
            grand_total,
            1.0,  # Full confidence for manual entries
            'ready',  # Status for manual entries
            data.venue,
            0,  # No issues initially
            0,  # Not paired initially
            datetime.now().isoformat()
        ))
        
        # Insert line items
        for idx, item in enumerate(data.line_items):
            line_total = item.line_total
            if line_total is None:
                line_total = calculate_line_total(item.quantity, item.unit_price)
            if line_total is None:
                line_total = 0.0
            
            cursor.execute("""
                INSERT INTO invoice_line_items 
                (doc_id, invoice_id, line_number, description, qty, unit_price, total, uom, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_id,
                invoice_id,
                idx + 1,
                item.description,
                item.quantity,
                item.unit_price or 0.0,
                line_total,
                item.unit or '',
                1.0,  # Full confidence for manual entries
                datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()
        
        # Audit log
        append_audit(
            datetime.now().isoformat(),
            "user",
            "manual_invoice_created",
            f'{{"invoice_id": "{invoice_id}", "invoice_number": "{data.invoice_number}", "supplier": "{data.supplier}"}}'
        )

        try:
            pairing_service.evaluate_pairing(invoice_id, mode="normal")
        except Exception as exc:  # pragma: no cover - best-effort hook
            LOGGER.warning("Pairing evaluation after manual invoice creation failed: %s", exc)
        
        return ManualInvoiceResponse(
            id=invoice_id,
            invoice_number=data.invoice_number,
            supplier=data.supplier,
            date=data.invoice_date,
            total_value=grand_total,
            status='ready',
            source='manual',
            message="Manual invoice created successfully"
        )
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating manual invoice: {str(e)}")


@router.put("/invoices/{invoice_id}", response_model=ManualInvoiceResponse)
def update_manual_invoice(invoice_id: str, data: ManualInvoiceCreate):
    """
    Update an existing manual invoice.
    
    Only allows updating invoices that were created manually (source='manual').
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if invoice exists and is manual (check ocr_stage, not source)
        cursor.execute("""
            SELECT i.id, i.doc_id, COALESCE(d.ocr_stage, 'upload') as ocr_stage
            FROM invoices i
            LEFT JOIN documents d ON i.doc_id = d.id
            WHERE i.id = ?
        """, (invoice_id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Manual invoice {invoice_id} not found")
        
        doc_id = row[1]
        ocr_stage = row[2] if row[2] else None
        
        # Only allow updating manual invoices (ocr_stage='manual')
        if ocr_stage != 'manual':
            conn.close()
            raise HTTPException(status_code=403, detail="Only manually created invoices can be edited")
        
        # Update invoice
        cursor.execute("""
            UPDATE invoices
            SET supplier = ?,
                date = ?,
                value = ?,
                venue = ?
            WHERE id = ?
        """, (
            data.supplier,
            data.invoice_date,
            data.grand_total or 0.0,
            data.venue,
            invoice_id
        ))
        
        # Delete existing line items (use correct table name: invoice_line_items)
        cursor.execute("DELETE FROM invoice_line_items WHERE invoice_id = ?", (invoice_id,))
        
        # Insert new line items (use correct table name: invoice_line_items)
        for idx, item in enumerate(data.line_items):
            line_total = item.line_total
            if line_total is None:
                line_total = calculate_line_total(item.quantity, item.unit_price)
            if line_total is None:
                line_total = 0.0
            
            cursor.execute("""
                INSERT INTO invoice_line_items 
                (doc_id, invoice_id, line_number, description, qty, unit_price, total, uom, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_id,
                invoice_id,
                idx + 1,
                item.description,
                item.quantity,
                item.unit_price or 0.0,
                line_total,
                item.unit or '',
                1.0,  # Full confidence for manual entries
                datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()
        
        # Get updated invoice details for response
        cursor.execute("""
            SELECT i.id, i.doc_id, i.supplier, i.date, i.value, i.status
            FROM invoices i
            WHERE i.id = ?
        """, (invoice_id,))
        updated_row = cursor.fetchone()
        
        if not updated_row:
            conn.close()
            raise HTTPException(status_code=500, detail="Failed to retrieve updated invoice")
        
        # Extract invoice number from filename
        cursor.execute("SELECT filename FROM documents WHERE id = ?", (doc_id,))
        filename_row = cursor.fetchone()
        invoice_number = updated_row[0]  # Use invoice ID as fallback
        if filename_row and filename_row[0]:
            filename = filename_row[0]
            if filename.startswith("Manual Invoice "):
                invoice_number = filename.replace("Manual Invoice ", "")
        
        return ManualInvoiceResponse(
            id=updated_row[0],
            invoice_number=invoice_number,
            supplier=updated_row[2] or "Unknown Supplier",
            date=updated_row[3] or "",
            total_value=float(updated_row[4]) if updated_row[4] else 0.0,
            status=updated_row[5] or 'ready',
            source='manual',
            message="Manual invoice updated successfully"
        )
        
    except HTTPException:
        raise
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating manual invoice: {str(e)}")


@router.post("/delivery-notes", response_model=ManualDeliveryNoteResponse)
def create_manual_delivery_note(data: ManualDeliveryNoteCreate):
    """
    Create a manual delivery note entry.
    
    Creates a delivery note record in the documents table with doc_type='delivery_note'.
    Note: Delivery notes are stored in the documents table, not a separate table.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check what columns exist in documents table
        cursor.execute("PRAGMA table_info(documents)")
        columns = [row[1] for row in cursor.fetchall()]
        has_doc_type = 'doc_type' in columns
        has_supplier = 'supplier' in columns
        has_delivery_no = 'delivery_no' in columns
        has_doc_date = 'doc_date' in columns
        has_total = 'total' in columns
        has_venue = 'venue' in columns
        has_notes = 'notes' in columns
        
        # Automatically add missing columns if they don't exist
        if not has_supplier:
            try:
                cursor.execute("ALTER TABLE documents ADD COLUMN supplier TEXT")
                has_supplier = True
                columns.append('supplier')
                print(f"[DEBUG] create_manual_delivery_note: Added missing 'supplier' column to documents table")
            except Exception as e:
                print(f"[WARN] Failed to add 'supplier' column: {e}")
        
        if not has_delivery_no:
            try:
                cursor.execute("ALTER TABLE documents ADD COLUMN delivery_no TEXT")
                has_delivery_no = True
                columns.append('delivery_no')
                print(f"[DEBUG] create_manual_delivery_note: Added missing 'delivery_no' column to documents table")
            except Exception as e:
                print(f"[WARN] Failed to add 'delivery_no' column: {e}")
        
        if not has_doc_date:
            try:
                cursor.execute("ALTER TABLE documents ADD COLUMN doc_date TEXT")
                has_doc_date = True
                columns.append('doc_date')
                print(f"[DEBUG] create_manual_delivery_note: Added missing 'doc_date' column to documents table")
            except Exception as e:
                print(f"[WARN] Failed to add 'doc_date' column: {e}")
        
        if not has_total:
            try:
                cursor.execute("ALTER TABLE documents ADD COLUMN total REAL")
                has_total = True
                columns.append('total')
                print(f"[DEBUG] create_manual_delivery_note: Added missing 'total' column to documents table")
            except Exception as e:
                print(f"[WARN] Failed to add 'total' column: {e}")
        
        if not has_doc_type:
            try:
                cursor.execute("ALTER TABLE documents ADD COLUMN doc_type TEXT DEFAULT 'unknown'")
                has_doc_type = True
                columns.append('doc_type')
                print(f"[DEBUG] create_manual_delivery_note: Added missing 'doc_type' column to documents table")
            except Exception as e:
                print(f"[WARN] Failed to add 'doc_type' column: {e}")
        
        if not has_venue:
            try:
                cursor.execute("ALTER TABLE documents ADD COLUMN venue TEXT")
                has_venue = True
                columns.append('venue')
                print(f"[DEBUG] create_manual_delivery_note: Added missing 'venue' column to documents table")
            except Exception as e:
                print(f"[WARN] Failed to add 'venue' column: {e}")
        
        if not has_notes:
            try:
                cursor.execute("ALTER TABLE documents ADD COLUMN notes TEXT")
                has_notes = True
                columns.append('notes')
                print(f"[DEBUG] create_manual_delivery_note: Added missing 'notes' column to documents table")
            except Exception as e:
                print(f"[WARN] Failed to add 'notes' column: {e}")
        
        # Generate ID
        doc_id = generate_manual_doc_id()
        
        # Build notes string - include supervisor if provided, plus any additional notes
        notes_parts = []
        if data.supervisor and data.supervisor.strip():
            notes_parts.append(f"Supervisor: {data.supervisor.strip()}")
        if data.notes and data.notes.strip():
            notes_parts.append(data.notes.strip())
        final_notes = "\n".join(notes_parts) if notes_parts else None
        
        # Handle supplier - use provided supplier, only default to "Unknown Supplier" if truly empty
        supplier = data.supplier.strip() if data.supplier and data.supplier.strip() else None
        if not supplier:
            supplier = "Unknown Supplier"
        
        # Always track supplier in suppliers table (creates new supplier automatically if needed)
        try:
            # Ensure suppliers table exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS suppliers (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    normalized_name TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Track supplier - this will create a new supplier entry if it doesn't exist
            cursor.execute("""
                INSERT OR IGNORE INTO suppliers (id, name, normalized_name, created_at)
                VALUES (?, ?, ?, ?)
            """, (str(uuid.uuid4()), supplier, supplier.lower().strip(), datetime.now().isoformat()))
            print(f"[DEBUG] create_manual_delivery_note: Tracked supplier '{supplier}' in suppliers table")
        except Exception as e:
            print(f"[WARN] Failed to track supplier '{supplier}': {e}")
        
        # Calculate total from line items if available
        total = 0.0
        if data.line_items:
            line_totals = []
            for item in data.line_items:
                line_total = item.line_total
                if line_total is None:
                    line_total = calculate_line_total(item.quantity, item.unit_price)
                if line_total is not None:
                    line_totals.append(line_total)
            total = sum(line_totals) if line_totals else 0.0
        
        # Insert into documents table
        # Build dynamic INSERT based on available columns (works for both has_doc_type and not)
        insert_cols = ["id", "filename", "stored_path", "size_bytes", "uploaded_at", "status", "ocr_stage", "ocr_confidence"]
        insert_vals = [doc_id, f"Manual Delivery Note {data.delivery_note_number}", None, 0, datetime.now().isoformat(), 'completed', 'manual', 1.0]
        
        # Add sha256 if column exists
        has_sha256 = 'sha256' in columns
        if has_sha256:
            insert_cols.append("sha256")
            insert_vals.append(f"manual-{uuid.uuid4().hex}")
        
        # Add doc_type if column exists
        if has_doc_type:
            insert_cols.append("doc_type")
            insert_vals.append('delivery_note')
        
        # Add optional columns if they exist
        if has_supplier:
            insert_cols.append("supplier")
            insert_vals.append(supplier)
        if has_delivery_no:
            insert_cols.append("delivery_no")
            insert_vals.append(data.delivery_note_number)
        if has_doc_date:
            insert_cols.append("doc_date")
            insert_vals.append(data.delivery_date)
        if has_total:
            insert_cols.append("total")
            insert_vals.append(total)
        if has_venue:
            insert_cols.append("venue")
            insert_vals.append(data.venue)
        if has_notes:
            insert_cols.append("notes")
            insert_vals.append(final_notes)
        
        cols_str = ", ".join(insert_cols)
        placeholders = ", ".join(["?"] * len(insert_vals))
        
        print(f"[DEBUG] create_manual_delivery_note: Inserting with columns: {cols_str}")
        print(f"[DEBUG] create_manual_delivery_note: Data - supplier='{supplier}', delivery_no='{data.delivery_note_number}', date='{data.delivery_date}', venue='{data.venue}'")
        print(f"[DEBUG] create_manual_delivery_note: Available columns: {columns}")
        
        cursor.execute(f"""
            INSERT INTO documents ({cols_str})
            VALUES ({placeholders})
        """, insert_vals)
        
        print(f"[DEBUG] create_manual_delivery_note: Inserted DN with id={doc_id}, supplier={supplier}, delivery_no={data.delivery_note_number}")
        
        # Verify the insert - build SELECT based on available columns
        verify_cols = ["id"]
        if has_supplier:
            verify_cols.append("supplier")
        if has_delivery_no:
            verify_cols.append("delivery_no")
        if has_doc_date:
            verify_cols.append("doc_date")
        if has_venue:
            verify_cols.append("venue")
        
        verify_query = f"SELECT {', '.join(verify_cols)} FROM documents WHERE id = ?"
        cursor.execute(verify_query, (doc_id,))
        verify_row = cursor.fetchone()
        if verify_row:
            verify_dict = {}
            idx = 0
            if 'id' in verify_cols:
                verify_dict['id'] = verify_row[idx]
                idx += 1
            if has_supplier and idx < len(verify_row):
                verify_dict['supplier'] = verify_row[idx]
                idx += 1
            if has_delivery_no and idx < len(verify_row):
                verify_dict['delivery_no'] = verify_row[idx]
                idx += 1
            if has_doc_date and idx < len(verify_row):
                verify_dict['doc_date'] = verify_row[idx]
                idx += 1
            if has_venue and idx < len(verify_row):
                verify_dict['venue'] = verify_row[idx]
            print(f"[DEBUG] create_manual_delivery_note: Verified insert - {verify_dict}")
        else:
            print(f"[DEBUG] create_manual_delivery_note: WARNING - Could not verify insert for doc_id={doc_id}")
        
        
        # Store delivery note line items in invoice_line_items table
        # For delivery notes: doc_id = delivery note ID, invoice_id = NULL
        # Also track products/item names
        for idx, item in enumerate(data.line_items):
            line_total = item.line_total
            if line_total is None:
                line_total = calculate_line_total(item.quantity, item.unit_price)
            if line_total is None:
                line_total = 0.0
            
            # Track product/item name if description is provided (non-blocking, skip on error)
            # This is optional metadata tracking - don't let it slow down DN creation
            if item.description and item.description.strip():
                try:
                    # Use a single query with INSERT OR REPLACE to avoid multiple queries
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS products (
                            id TEXT PRIMARY KEY,
                            name TEXT NOT NULL UNIQUE,
                            normalized_name TEXT,
                            first_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
                            last_seen_at TEXT DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    # Use INSERT OR REPLACE to handle both insert and update in one query
                    normalized_name = item.description.lower().strip()
                    product_id = str(uuid.uuid4())
                    now = datetime.now().isoformat()
                    cursor.execute("""
                        INSERT OR REPLACE INTO products (id, name, normalized_name, first_seen_at, last_seen_at)
                        VALUES (
                            COALESCE((SELECT id FROM products WHERE normalized_name = ?), ?),
                            ?,
                            ?,
                            COALESCE((SELECT first_seen_at FROM products WHERE normalized_name = ?), ?),
                            ?
                        )
                    """, (normalized_name, product_id, item.description.strip(), normalized_name, normalized_name, now, now))
                except Exception as e:
                    # Silently skip product tracking errors - don't block DN creation
                    pass
            
            cursor.execute("""
                INSERT INTO invoice_line_items 
                (doc_id, invoice_id, line_number, description, qty, unit_price, total, uom, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_id,
                None,  # invoice_id is NULL for delivery notes
                idx + 1,
                item.description,
                item.quantity,
                item.unit_price or 0.0,
                line_total,
                item.unit or '',
                1.0,  # Full confidence for manual entries
                datetime.now().isoformat()
            ))
        
        conn.commit()
        # Ensure commit is fully written
        cursor.execute("SELECT 1")
        cursor.fetchone()
        
        # Verify the data was actually saved before closing connection
        cursor.execute("SELECT supplier, delivery_no, doc_date, venue FROM documents WHERE id = ?", (doc_id,))
        verify_after_commit = cursor.fetchone()
        if verify_after_commit:
            print(f"[DEBUG] create_manual_delivery_note: Verified after commit - supplier='{verify_after_commit[0]}', delivery_no='{verify_after_commit[1]}', doc_date='{verify_after_commit[2]}', venue='{verify_after_commit[3] if len(verify_after_commit) > 3 else None}'")
        else:
            print(f"[ERROR] create_manual_delivery_note: WARNING - Could not verify DN {doc_id} after commit!")
        
        conn.close()
        
        print(f"[DEBUG] create_manual_delivery_note: Committed DN {doc_id} to database")
        
        # Audit log
        append_audit(
            datetime.now().isoformat(),
            "user",
            "manual_delivery_note_created",
            f'{{"doc_id": "{doc_id}", "delivery_note_number": "{data.delivery_note_number}", "supplier": "{supplier}"}}'
        )
        
        # Create base response
        base_response = ManualDeliveryNoteResponse(
            id=doc_id,
            delivery_note_number=data.delivery_note_number,
            supplier=supplier,
            date=data.delivery_date,
            source='manual',
            message="Manual delivery note created successfully"
        )
        
        # Convert to dict and add extra fields for frontend compatibility
        response_dict = base_response.model_dump()
        response_dict["deliveryNoteNumber"] = data.delivery_note_number  # Add camelCase variant
        response_dict["noteNumber"] = data.delivery_note_number  # Add alternative field name
        response_dict["venue"] = data.venue  # Include venue in response
        response_dict["supervisor"] = data.supervisor  # Include supervisor in response
        
        return response_dict
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating manual delivery note: {str(e)}")


@router.put("/delivery-notes/{dn_id}", response_model=ManualDeliveryNoteResponse)
def update_manual_delivery_note(dn_id: str, data: ManualDeliveryNoteCreate):
    """
    Update an existing manual delivery note.
    
    Only allows updating delivery notes that were created manually (ocr_stage='manual').
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if delivery note exists and is manual
        cursor.execute("""
            SELECT id, ocr_stage, doc_type
            FROM documents
            WHERE id = ?
        """, (dn_id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Manual delivery note {dn_id} not found")
        
        ocr_stage = row[1] if row[1] else None
        
        # Only allow updating manual delivery notes
        if ocr_stage != 'manual':
            conn.close()
            raise HTTPException(status_code=403, detail="Only manually created delivery notes can be edited")
        
        # Check what columns exist
        cursor.execute("PRAGMA table_info(documents)")
        columns = [row[1] for row in cursor.fetchall()]
        has_supplier = 'supplier' in columns
        has_delivery_no = 'delivery_no' in columns
        has_doc_date = 'doc_date' in columns
        has_total = 'total' in columns
        has_venue = 'venue' in columns
        has_notes = 'notes' in columns
        
        # Build notes string
        notes_parts = []
        if data.supervisor and data.supervisor.strip():
            notes_parts.append(f"Supervisor: {data.supervisor.strip()}")
        if data.notes and data.notes.strip():
            notes_parts.append(data.notes.strip())
        final_notes = "\n".join(notes_parts) if notes_parts else None
        
        # Handle supplier
        supplier = data.supplier.strip() if data.supplier and data.supplier.strip() else None
        if not supplier:
            supplier = "Unknown Supplier"
        
        # Calculate total from line items
        total = 0.0
        if data.line_items:
            line_totals = []
            for item in data.line_items:
                line_total = item.line_total
                if line_total is None:
                    line_total = calculate_line_total(item.quantity, item.unit_price)
                if line_total is not None:
                    line_totals.append(line_total)
            total = sum(line_totals) if line_totals else 0.0
        
        # Build UPDATE statement dynamically
        update_parts = []
        update_vals = []
        
        if has_supplier:
            update_parts.append("supplier = ?")
            update_vals.append(supplier)
        if has_delivery_no:
            update_parts.append("delivery_no = ?")
            update_vals.append(data.delivery_note_number)
        if has_doc_date:
            update_parts.append("doc_date = ?")
            update_vals.append(data.delivery_date)
        if has_total:
            update_parts.append("total = ?")
            update_vals.append(total)
        if has_venue:
            update_parts.append("venue = ?")
            update_vals.append(data.venue)
        if has_notes:
            update_parts.append("notes = ?")
            update_vals.append(final_notes)
        
        update_vals.append(dn_id)
        
        if update_parts:
            cursor.execute(f"""
                UPDATE documents
                SET {', '.join(update_parts)}
                WHERE id = ?
            """, update_vals)
        
        # Delete existing line items (delivery notes don't have a separate line_items table, 
        # but we should handle this if they do in the future)
        # For now, we'll just update the document record
        
        conn.commit()
        conn.close()
        
        return ManualDeliveryNoteResponse(
            delivery_note_id=dn_id,
            source='manual',
            message="Manual delivery note updated successfully"
        )
        
    except HTTPException:
        raise
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating manual delivery note: {str(e)}")


@router.get("/invoices")
def get_manual_invoices(
    venue_id: Optional[str] = Query(None, description="Filter by venue"),
    supplier_id: Optional[str] = Query(None, description="Filter by supplier"),
    from_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    limit: int = Query(50, description="Number of invoices to return"),
    offset: int = Query(0, description="Number of invoices to skip")
):
    """
    Get manual invoices with optional filtering.
    
    Returns invoices where status='ready' (manual entries use this status).
    In a production system, you might add a 'source' column to distinguish manual vs scanned.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Build WHERE clause
        where_parts = ["i.status = 'ready'"]  # Manual entries use status='ready'
        params = []
        
        if venue_id:
            where_parts.append("i.venue = ?")
            params.append(venue_id)
        
        if supplier_id:
            where_parts.append("i.supplier = ?")
            params.append(supplier_id)
        
        if from_date:
            where_parts.append("i.date >= ?")
            params.append(from_date)
        
        if to_date:
            where_parts.append("i.date <= ?")
            params.append(to_date)
        
        where_clause = " AND ".join(where_parts)
        
        # Query invoices
        query = f"""
            SELECT i.id, i.doc_id, i.supplier, i.date, i.value, d.filename,
                   i.status, i.confidence, i.venue, i.issues_count, i.paired
            FROM invoices i
            LEFT JOIN documents d ON i.doc_id = d.id
            WHERE {where_clause}
            ORDER BY i.date DESC, i.id DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM invoices i WHERE {where_clause}"
        cursor.execute(count_query, params[:-2])
        total = cursor.fetchone()[0]
        
        # Transform results
        invoices = []
        for row in rows:
            invoice_id = row[0]
            line_items = get_line_items_for_invoice(invoice_id)
            
            invoices.append({
                "id": invoice_id,
                "doc_id": row[1],
                "id": invoice_id,
                "doc_id": row[1],
                "supplier": row[2] or "Unknown Supplier",
                "invoice_date": row[3] or "",
                "total_value": float(row[4]) if row[4] else 0.0,
                "currency": "GBP",  # Default currency
                "confidence": float(row[7]) if row[7] else 1.0,
                "status": row[6] or "ready",
                "venue": row[8] or "Main Restaurant",
                "issues_count": int(row[9]) if row[9] else 0,
                "paired": bool(row[10]) if row[10] else False,
                "pairing_status": None,  # TODO: populate from invoices table if column exists
                "delivery_note_id": None,  # TODO: populate from invoices table if column exists
                "line_items": line_items
            })
        
        conn.close()
        
        return {
            "invoices": invoices,
            "count": len(invoices),
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching manual invoices: {str(e)}")


@router.get("/invoices/{invoice_id}")
def get_manual_invoice_detail(invoice_id: str):
    """
    Get a specific manual invoice by ID with line items.
    
    Returns invoice details including line items for display in the detail panel.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get invoice details - remove status filter to match list endpoint behavior
        cursor.execute("""
            SELECT i.id, i.doc_id, i.supplier, i.date, i.value, d.filename,
                   i.status, i.confidence, i.venue, i.issues_count, i.paired,
                   COALESCE(d.ocr_stage, 'upload') as ocr_stage
            FROM invoices i
            LEFT JOIN documents d ON i.doc_id = d.id
            WHERE i.id = ?
        """, (invoice_id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Manual invoice {invoice_id} not found")
        
        invoice_id_db = row[0]
        doc_id = row[1]
        
        # Get line items for this invoice
        line_items = get_line_items_for_invoice(invoice_id_db)
        
        # Transform line items to match frontend format
        transformed_line_items = []
        for item in line_items:
            transformed_line_items.append({
                "description": item.get("desc") or item.get("description") or "",
                "qty": item.get("qty") or item.get("quantity") or 0,
                "quantity": item.get("qty") or item.get("quantity") or 0,
                "unit": item.get("uom") or item.get("unit") or "",
                "uom": item.get("uom") or item.get("unit") or "",
                "unit_price": item.get("unit_price") or item.get("price") or 0,
                "price": item.get("unit_price") or item.get("price") or 0,
                "total": item.get("total") or item.get("line_total") or 0,
                "line_total": item.get("total") or item.get("line_total") or 0,
                "line_number": item.get("line_number"),
            })
        
        # Extract invoice number from filename if it follows "Manual Invoice {number}" pattern
        filename = row[5] or f"Manual Invoice {row[0]}"
        invoice_number = filename
        if filename.startswith("Manual Invoice "):
            invoice_number = filename.replace("Manual Invoice ", "")
        
        conn.close()
        
        # Return invoice with line items (canonical field names)
        ocr_stage = row[11] if len(row) > 11 else 'manual'  # Manual invoices should have ocr_stage='manual'
        invoice = {
            "id": row[0],
            "doc_id": row[1],
            "supplier": row[2] or "Unknown Supplier",
            "invoice_date": row[3] or "",
            "invoice_number": invoice_number,  # Include extracted invoice number
            "total_value": float(row[4]) if row[4] else 0.0,
            "currency": "GBP",  # Default currency
            "confidence": float(row[7]) if row[7] else 1.0,
            "status": row[6] or "ready",
            "venue": row[8] or "Main Restaurant",
            "issues_count": int(row[9]) if row[9] else 0,
            "paired": bool(row[10]) if row[10] else False,
            "pairing_status": None,  # TODO: populate from invoices table if column exists
            "delivery_note_id": None,  # TODO: populate from invoices table if column exists
            "ocr_stage": ocr_stage,
            "ocrStage": ocr_stage,
            "source": "manual" if ocr_stage == "manual" else "scanned",
            "line_items": transformed_line_items
        }
        
        return invoice
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching manual invoice: {str(e)}")


@router.get("/delivery-notes")
def get_manual_delivery_notes(
    venue_id: Optional[str] = Query(None, description="Filter by venue"),
    supplier_id: Optional[str] = Query(None, description="Filter by supplier"),
    from_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    limit: int = Query(50, description="Number of delivery notes to return"),
    offset: int = Query(0, description="Number of delivery notes to skip")
):
    """
    Get manual delivery notes with optional filtering.
    
    Returns delivery notes from the documents table where doc_type='delivery_note' and ocr_stage='manual'.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check what columns exist in documents table
        cursor.execute("PRAGMA table_info(documents)")
        columns = [row[1] for row in cursor.fetchall()]
        has_doc_type = 'doc_type' in columns
        has_supplier = 'supplier' in columns
        has_delivery_no = 'delivery_no' in columns
        has_doc_date = 'doc_date' in columns
        has_total = 'total' in columns
        has_venue = 'venue' in columns
        
        # Build WHERE clause - match the insert logic
        # If doc_type column exists, filter by it; otherwise just filter by ocr_stage
        where_parts = ["d.ocr_stage = 'manual'"]
        if has_doc_type:
            where_parts.insert(0, "d.doc_type = 'delivery_note'")
        
        params = []
        
        if supplier_id and has_supplier:
            where_parts.append("d.supplier = ?")
            params.append(supplier_id)
        
        if from_date and has_doc_date:
            where_parts.append("d.doc_date >= ?")
            params.append(from_date)
        
        if to_date and has_doc_date:
            where_parts.append("d.doc_date <= ?")
            params.append(to_date)
        
        where_clause = " AND ".join(where_parts)
        
        # Log the query for debugging
        print(f"[DEBUG] get_manual_delivery_notes: has_doc_type={has_doc_type}, where_clause={where_clause}")
        
        if has_venue:
            query = f"""
                SELECT d.id, d.filename, d.supplier, d.doc_date, d.total, d.delivery_no, d.venue
                FROM documents d
                WHERE {where_clause}
                ORDER BY d.doc_date DESC, d.id DESC
                LIMIT ? OFFSET ?
            """
        else:
            query = f"""
                SELECT d.id, d.filename, d.supplier, d.doc_date, d.total, d.delivery_no, NULL as venue
                FROM documents d
                WHERE {where_clause}
                ORDER BY d.doc_date DESC, d.id DESC
                LIMIT ? OFFSET ?
            """
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Log query results for debugging
        print(f"[DEBUG] get_manual_delivery_notes: Found {len(rows)} delivery notes")
        if len(rows) > 0:
            print(f"[DEBUG] Sample row: {rows[0]}")
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM documents d WHERE {where_clause}"
        cursor.execute(count_query, params[:-2])
        total = cursor.fetchone()[0]
        
        # Transform results
        delivery_notes = []
        for row in rows:
            # Handle different column positions based on what columns exist
            row_id = row[0]
            row_filename = row[1] if len(row) > 1 else None
            row_supplier = row[2] if len(row) > 2 and has_supplier else None
            row_date = row[3] if len(row) > 3 and has_doc_date else None
            row_total = row[4] if len(row) > 4 and has_total else 0.0
            row_delivery_no = row[5] if len(row) > 5 and has_delivery_no else None
            row_venue = row[6] if len(row) > 6 and has_venue else None
            
            delivery_notes.append({
                "id": row_id,
                "filename": row_filename or f"Delivery Note {row_delivery_no or row_id}",
                "supplier": row_supplier or "Unknown Supplier",
                "date": row_date or "",
                "doc_date": row_date or "",
                "total": float(row_total) if row_total else 0.0,
                "delivery_note_number": row_delivery_no or "",
                "delivery_no": row_delivery_no or "",
                "deliveryNo": row_delivery_no or "",
                "noteNumber": row_delivery_no or "",  # Add noteNumber field
                "venue": row_venue,
                "venueId": row_venue,
                "source": "manual"
            })
        
        print(f"[DEBUG] get_manual_delivery_notes: Returning {len(delivery_notes)} delivery notes")
        
        conn.close()
        
        return {
            "delivery_notes": delivery_notes,
            "count": len(delivery_notes),
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching manual delivery notes: {str(e)}")


@router.get("/delivery-notes/{dn_id}")
def get_manual_delivery_note_detail(dn_id: str):
    """
    Get a specific manual delivery note by ID with line items.
    
    Returns delivery note details including line items for display in the detail panel.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check what columns exist in documents table
        cursor.execute("PRAGMA table_info(documents)")
        columns = [row[1] for row in cursor.fetchall()]
        has_doc_type = 'doc_type' in columns
        has_supplier = 'supplier' in columns
        has_delivery_no = 'delivery_no' in columns
        has_doc_date = 'doc_date' in columns
        has_total = 'total' in columns
        has_venue = 'venue' in columns
        
        # Build SELECT based on available columns
        # IMPORTANT: Order must match the order we parse the row
        select_cols = ["d.id", "d.filename"]
        if has_supplier:
            select_cols.append("d.supplier")
        if has_doc_date:
            select_cols.append("d.doc_date")
        if has_delivery_no:
            select_cols.append("d.delivery_no")
        if has_total:
            select_cols.append("d.total")
        if has_venue:
            select_cols.append("d.venue")
        # Always include ocr_stage to determine if manual
        select_cols.append("d.ocr_stage")
        
        print(f"[DEBUG] get_manual_delivery_note_detail: Column checks - has_supplier={has_supplier}, has_delivery_no={has_delivery_no}, has_doc_date={has_doc_date}, has_total={has_total}, has_venue={has_venue}")
        print(f"[DEBUG] get_manual_delivery_note_detail: All columns in documents table: {columns}")
        print(f"[DEBUG] get_manual_delivery_note_detail: SELECT columns: {select_cols}")
        
        # Build WHERE clause - be permissive to find delivery notes
        # Try with doc_type first, then fallback to just id
        where_parts = ["d.id = ?"]
        if has_doc_type:
            where_parts.append("d.doc_type = 'delivery_note'")
        
        query = f"""
            SELECT {', '.join(select_cols)}
            FROM documents d
            WHERE {' AND '.join(where_parts)}
        """
        
        print(f"[DEBUG] get_manual_delivery_note_detail: Executing query: {query}")
        print(f"[DEBUG] get_manual_delivery_note_detail: With params: ({dn_id},)")
        
        cursor.execute(query, (dn_id,))
        row = cursor.fetchone()
        
        # If not found with doc_type filter, try without it (in case doc_type wasn't set)
        if not row and has_doc_type:
            print(f"[DEBUG] get_manual_delivery_note_detail: Not found with doc_type filter, trying with just id")
            query_fallback = f"""
                SELECT {', '.join(select_cols)}
                FROM documents d
                WHERE d.id = ?
            """
            cursor.execute(query_fallback, (dn_id,))
            row = cursor.fetchone()
        
        # If still not found and we have delivery_no column, try looking up by delivery note number
        if not row and has_delivery_no:
            print(f"[DEBUG] get_manual_delivery_note_detail: Not found by id, trying by delivery_no: {dn_id}")
            where_parts_dn = ["d.delivery_no = ?"]
            if has_doc_type:
                where_parts_dn.append("d.doc_type = 'delivery_note'")
            
            query_by_dn = f"""
                SELECT {', '.join(select_cols)}
                FROM documents d
                WHERE {' AND '.join(where_parts_dn)}
            """
            cursor.execute(query_by_dn, (dn_id,))
            row = cursor.fetchone()
            
            # If still not found with doc_type filter, try without it
            if not row and has_doc_type:
                print(f"[DEBUG] get_manual_delivery_note_detail: Not found by delivery_no with doc_type, trying without doc_type")
                query_by_dn_fallback = f"""
                    SELECT {', '.join(select_cols)}
                    FROM documents d
                    WHERE d.delivery_no = ?
                """
                cursor.execute(query_by_dn_fallback, (dn_id,))
                row = cursor.fetchone()
        
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Delivery note {dn_id} not found")
        
        # Debug: Log what we got
        print(f"[DEBUG] get_manual_delivery_note_detail: Query returned row with {len(row)} columns")
        print(f"[DEBUG] get_manual_delivery_note_detail: has_supplier={has_supplier}, has_delivery_no={has_delivery_no}, has_doc_date={has_doc_date}")
        print(f"[DEBUG] get_manual_delivery_note_detail: Row data: {row}")
        
        # Parse row based on available columns
        row_dict = {}
        col_idx = 0
        row_dict['id'] = row[col_idx]
        col_idx += 1
        row_dict['filename'] = row[col_idx] if col_idx < len(row) else None
        col_idx += 1
        
        if has_supplier:
            row_dict['supplier'] = row[col_idx] if col_idx < len(row) and row[col_idx] is not None else None
            print(f"[DEBUG] get_manual_delivery_note_detail: supplier from row[{col_idx}] = {row_dict['supplier']}")
            col_idx += 1
        else:
            row_dict['supplier'] = None
            print(f"[DEBUG] get_manual_delivery_note_detail: supplier column does not exist")
            
        if has_doc_date:
            row_dict['date'] = row[col_idx] if col_idx < len(row) and row[col_idx] is not None else None
            row_dict['doc_date'] = row_dict['date']
            print(f"[DEBUG] get_manual_delivery_note_detail: date from row[{col_idx}] = {row_dict['date']}")
            col_idx += 1
        else:
            row_dict['date'] = None
            row_dict['doc_date'] = None
            print(f"[DEBUG] get_manual_delivery_note_detail: doc_date column does not exist")
            
        if has_delivery_no:
            row_dict['delivery_no'] = row[col_idx] if col_idx < len(row) and row[col_idx] is not None else None
            row_dict['noteNumber'] = row_dict['delivery_no']
            row_dict['note_number'] = row_dict['delivery_no']
            row_dict['deliveryNo'] = row_dict['delivery_no']  # Add alternative field name
            print(f"[DEBUG] get_manual_delivery_note_detail: delivery_no from row[{col_idx}] = {row_dict['delivery_no']}")
            col_idx += 1
        else:
            row_dict['delivery_no'] = None
            row_dict['noteNumber'] = None
            row_dict['note_number'] = None
            row_dict['deliveryNo'] = None
            print(f"[DEBUG] get_manual_delivery_note_detail: delivery_no column does not exist")
            
        if has_total:
            row_dict['total'] = float(row[col_idx]) if col_idx < len(row) and row[col_idx] is not None else 0.0
            col_idx += 1
        else:
            row_dict['total'] = 0.0
            
        if has_venue:
            row_dict['venue'] = row[col_idx] if col_idx < len(row) and row[col_idx] is not None else None
            row_dict['venueId'] = row_dict['venue']
            col_idx += 1
        else:
            row_dict['venue'] = None
            row_dict['venueId'] = None
        
        # Get ocr_stage (always included at the end)
        row_dict['ocrStage'] = row[col_idx] if col_idx < len(row) and row[col_idx] is not None else None
        row_dict['ocr_stage'] = row_dict['ocrStage']
        row_dict['source'] = 'manual' if row_dict['ocrStage'] == 'manual' else 'scanned'
        
        print(f"[DEBUG] get_manual_delivery_note_detail: Final row_dict supplier={row_dict.get('supplier')}, noteNumber={row_dict.get('noteNumber')}, date={row_dict.get('date')}, ocr_stage={row_dict.get('ocrStage')}")
        
        # Get line items for this delivery note (invoice_id=None for delivery notes)
        # Use the actual document ID from the row, not the parameter (which might be a delivery note number)
        actual_doc_id = row_dict['id']
        from backend.app.db import get_line_items_for_doc
        line_items = get_line_items_for_doc(actual_doc_id, invoice_id=None)
        
        # Transform line items to match frontend format
        transformed_line_items = []
        for item in line_items:
            # get_line_items_for_doc returns 'desc', not 'description'
            description = item.get('desc') or item.get('description') or ''
            transformed_line_items.append({
                "description": description,
                "item": description,  # Also include as 'item' for compatibility
                "qty": item.get('qty', item.get('quantity', 0)),
                "quantity": item.get('qty', item.get('quantity', 0)),
                "unit": item.get('uom', item.get('unit', '')),
                "uom": item.get('uom', item.get('unit', '')),
                "unit_price": item.get('unit_price', 0.0),
                "price": item.get('unit_price', 0.0),
                "total": item.get('total', item.get('line_total', 0.0)),
                "line_total": item.get('total', item.get('line_total', 0.0)),
            })
        print(f"[DEBUG] get_manual_delivery_note_detail: Transformed {len(transformed_line_items)} line items")
        for idx, item in enumerate(transformed_line_items):
            print(f"[DEBUG] get_manual_delivery_note_detail: Line item {idx+1}: description='{item.get('description')}', qty={item.get('qty')}, unit='{item.get('unit')}'")
        
        row_dict['lineItems'] = transformed_line_items
        row_dict['line_items'] = transformed_line_items
        
        conn.close()
        
        return row_dict
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching delivery note detail: {str(e)}")


class ValidatePairRequest(BaseModel):
    """Request to validate a pair without creating it"""
    invoice_id: str = Field(..., description="Invoice ID (from invoices table)")
    delivery_note_id: str = Field(..., description="Delivery note ID (from documents table)")


class DiscrepancyDetail(BaseModel):
    """Details about a quantity discrepancy"""
    description: str
    invoice_qty: float
    delivery_qty: float
    difference: float
    severity: Literal["critical", "warning", "info"]


class ValidatePairResponse(BaseModel):
    """Response from pair validation"""
    is_valid: bool
    match_score: float
    discrepancies: List[DiscrepancyDetail] = []
    warnings: List[str] = []


@router.post("/validate-pair", response_model=ValidatePairResponse)
def validate_pair(data: ValidatePairRequest):
    """
    Validate quantity match between invoice and delivery note without creating pair.
    Used by frontend to preview validation results before pairing.
    """
    try:
        # Verify invoice exists
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM invoices WHERE id = ?", (data.invoice_id,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail=f"Invoice {data.invoice_id} not found")
        
        # Verify delivery note exists - try with doc_type filter first, then without
        cursor.execute("PRAGMA table_info(documents)")
        columns = [row[1] for row in cursor.fetchall()]
        has_doc_type = 'doc_type' in columns
        
        if has_doc_type:
            cursor.execute("""
                SELECT id FROM documents
                WHERE id = ? AND doc_type = 'delivery_note'
            """, (data.delivery_note_id,))
        else:
            cursor.execute("SELECT id FROM documents WHERE id = ?", (data.delivery_note_id,))
        
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail=f"Delivery note {data.delivery_note_id} not found")
        
        conn.close()
        
        # Run validation with error handling
        try:
            validation_result = validate_quantity_match(data.invoice_id, data.delivery_note_id)
        except Exception as val_err:
            # If validation fails, return a safe default response
            import logging
            logger = logging.getLogger("owlin.routes.manual_entry")
            logger.warning(f"Quantity validation failed for invoice={data.invoice_id}, delivery={data.delivery_note_id}: {val_err}")
            validation_result = {
                "is_valid": True,  # Allow pairing even if validation fails
                "match_score": 1.0,
                "discrepancies": [],
                "warnings": ["Quantity validation unavailable"]
            }
        
        # Convert discrepancies to Pydantic models with type validation
        discrepancies = []
        for disc in validation_result.get("discrepancies", []):
            try:
                # Validate and convert types safely
                description = str(disc.get("description", ""))
                invoice_qty = float(disc.get("invoice_qty", 0) or 0)
                delivery_qty = float(disc.get("delivery_qty", 0) or 0)
                difference = float(disc.get("difference", 0) or 0)
                severity = disc.get("severity", "info")
                
                # Validate severity is one of the allowed values
                if severity not in ("critical", "warning", "info"):
                    severity = "info"
                
                discrepancies.append(DiscrepancyDetail(
                    description=description,
                    invoice_qty=invoice_qty,
                    delivery_qty=delivery_qty,
                    difference=difference,
                    severity=severity
                ))
            except (ValueError, TypeError) as e:
                # Log but skip invalid discrepancy entries
                import logging
                logger = logging.getLogger("owlin.routes.manual_entry")
                logger.warning(f"Skipping invalid discrepancy entry: {disc}, error: {e}")
                continue
        
        return ValidatePairResponse(
            is_valid=validation_result.get("is_valid", False),
            match_score=validation_result.get("match_score", 0.0),
            discrepancies=discrepancies,
            warnings=validation_result.get("warnings", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger("owlin.routes.manual_entry")
        logger.error(f"Error validating pair (invoice={data.invoice_id}, delivery={data.delivery_note_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error validating pair: {str(e)}")


@router.post("/match", response_model=ManualMatchResponse)
def match_manual_invoice_to_delivery_note(data: ManualMatchRequest):
    """
    Manually link an invoice to a delivery note and trigger mismatch detection.
    
    Creates a pair in the pairs table, updates invoice.paired status,
    runs issue detection, and updates invoice status/issues_count.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get invoice details including doc_id
        cursor.execute("""
            SELECT id, doc_id, supplier, date, value, status, issues_count, paired
            FROM invoices
            WHERE id = ?
        """, (data.invoice_id,))
        
        inv_row = cursor.fetchone()
        if not inv_row:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Invoice {data.invoice_id} not found")
        
        invoice_id = inv_row[0]
        invoice_doc_id = inv_row[1]
        invoice_supplier = inv_row[2]
        invoice_date = inv_row[3]
        invoice_total = inv_row[4] or 0.0
        invoice_status = inv_row[5] or 'ready'
        issues_count = inv_row[6] or 0
        paired = inv_row[7] or 0
        
        # Verify delivery note exists
        cursor.execute("""
            SELECT id, supplier, doc_date, total, delivery_no, doc_type
            FROM documents
            WHERE id = ? AND doc_type = 'delivery_note'
        """, (data.delivery_note_id,))
        
        dn_row = cursor.fetchone()
        if not dn_row:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Delivery note {data.delivery_note_id} not found")
        
        delivery_note_id = dn_row[0]
        dn_supplier = dn_row[1]
        dn_date = dn_row[2]
        dn_total = dn_row[4] or 0.0
        
        # Validate quantity match before creating pair
        validation_result = validate_quantity_match(invoice_id, str(delivery_note_id))
        quantity_match_score = validation_result.get("match_score", 1.0)
        validation_warnings = validation_result.get("warnings", [])
        
        # Check if pairs table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pairs'")
        pairs_table_exists = cursor.fetchone() is not None
        
        # Create or update pair
        if pairs_table_exists:
            # Check if pair already exists
            cursor.execute("""
                SELECT id, status FROM pairs
                WHERE invoice_id = ? AND delivery_id = ?
            """, (invoice_doc_id, delivery_note_id))
            
            existing_pair = cursor.fetchone()
            
            if existing_pair:
                # Update existing pair to accepted
                cursor.execute("""
                    UPDATE pairs
                    SET status = 'accepted', decided_at = datetime('now')
                    WHERE id = ?
                """, (existing_pair[0],))
            else:
                # Create new pair with high confidence (manual match)
                cursor.execute("""
                    INSERT INTO pairs (invoice_id, delivery_id, confidence, status, created_at, decided_at)
                    VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
                """, (invoice_doc_id, delivery_note_id, 1.0, 'accepted'))
        
        # Update invoice paired status
        cursor.execute("""
            UPDATE invoices
            SET paired = 1
            WHERE id = ?
        """, (invoice_id,))
        
        # Run issue detection
        try:
            from backend.services.issue_detector import detect_price_mismatch, detect_short_delivery
            
            # Detect price mismatch
            price_issue = detect_price_mismatch(invoice_id, delivery_note_id)
            
            # Detect short delivery
            short_delivery_issue = detect_short_delivery(invoice_id, delivery_note_id)
            
            # Count issues
            detected_issues = []
            if price_issue:
                detected_issues.append(price_issue)
            if short_delivery_issue:
                detected_issues.append(short_delivery_issue)
            
            issues_count = len(detected_issues)
            
            # Update invoice status based on issues
            if issues_count > 0:
                new_status = 'flagged'
            else:
                new_status = 'matched'
            
            # Update invoice status and issues_count
            cursor.execute("""
                UPDATE invoices
                SET status = ?, issues_count = ?
                WHERE id = ?
            """, (new_status, issues_count, invoice_id))
            
            invoice_status = new_status
            
        except ImportError:
            # Issue detector not available, skip detection
            pass
        except Exception as e:
            # Log but don't fail the match
            print(f"Warning: Issue detection failed: {e}")
        
        conn.commit()
        conn.close()
        
        # Audit log
        append_audit(
            datetime.now().isoformat(),
            "user",
            "manual_invoice_matched",
            f'{{"invoice_id": "{invoice_id}", "delivery_note_id": "{delivery_note_id}", "status": "{invoice_status}", "issues_count": {issues_count}}}'
        )
        
        # Combine validation warnings with issue detection messages
        all_warnings = validation_warnings.copy()
        if issues_count > 0:
            all_warnings.append(f"{issues_count} issue(s) detected after pairing")
        
        message = "Invoice matched to delivery note successfully."
        if all_warnings:
            message = f"Invoice matched to delivery note. {' '.join(all_warnings[:2])}"  # Show first 2 warnings
        elif issues_count > 0:
            message = f"Invoice matched to delivery note. {issues_count} issue(s) detected."
        
        return ManualMatchResponse(
            invoice_id=invoice_id,
            delivery_note_id=str(delivery_note_id),
            status=invoice_status,
            issues_count=issues_count,
            paired=True,
            message=message,
            warnings=all_warnings,
            quantity_match_score=quantity_match_score
        )
        
    except HTTPException:
        raise
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error matching invoice to delivery note: {str(e)}")


class UnpairResponse(BaseModel):
    """Response for unpairing invoice from delivery note"""
    invoice_id: str
    success: bool
    message: str


@router.post("/invoices/{invoice_id}/unpair", response_model=UnpairResponse)
def unpair_invoice_from_delivery_note(invoice_id: str):
    """
    Unpair an invoice from its delivery note.
    
    Removes the pair from the pairs table and updates invoice.paired status to 0.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verify invoice exists
        cursor.execute("""
            SELECT id, doc_id, paired
            FROM invoices
            WHERE id = ?
        """, (invoice_id,))
        
        inv_row = cursor.fetchone()
        if not inv_row:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
        
        invoice_db_id = inv_row[0]
        invoice_doc_id = inv_row[1]
        is_paired = inv_row[2] or 0
        
        if not is_paired:
            conn.close()
            return UnpairResponse(
                invoice_id=invoice_id,
                success=True,
                message="Invoice is not currently paired with any delivery note."
            )
        
        # Check if pairs table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pairs'")
        pairs_table_exists = cursor.fetchone() is not None
        
        if pairs_table_exists:
            # Find and remove/update pairs for this invoice
            cursor.execute("""
                SELECT id, delivery_id, status
                FROM pairs
                WHERE invoice_id = ?
            """, (invoice_doc_id,))
            
            pairs = cursor.fetchall()
            
            if pairs:
                # Delete or mark pairs as rejected
                for pair_id, delivery_id, status in pairs:
                    if status in ('accepted', 'confirmed'):
                        # Delete confirmed pairs
                        cursor.execute("DELETE FROM pairs WHERE id = ?", (pair_id,))
                    else:
                        # Mark suggested pairs as rejected
                        cursor.execute("""
                            UPDATE pairs
                            SET status = 'rejected', decided_at = datetime('now')
                            WHERE id = ?
                        """, (pair_id,))
        
        # Update invoice paired status to 0
        cursor.execute("""
            UPDATE invoices
            SET paired = 0
            WHERE id = ?
        """, (invoice_db_id,))
        
        conn.commit()
        conn.close()
        
        # Audit log
        append_audit(
            datetime.now().isoformat(),
            "user",
            "invoice_unpaired",
            f'{{"invoice_id": "{invoice_id}"}}'
        )
        
        return UnpairResponse(
            invoice_id=invoice_id,
            success=True,
            message="Invoice successfully unpaired from delivery note."
        )
        
    except HTTPException:
        raise
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error unpairing invoice: {str(e)}")
