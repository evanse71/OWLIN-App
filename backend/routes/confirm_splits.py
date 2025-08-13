from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import uuid
import sqlite3

from database import get_db_connection

router = APIRouter()
logger = logging.getLogger(__name__)

class DocumentMetadata(BaseModel):
    invoice_date: Optional[str] = None
    delivery_date: Optional[str] = None
    total_amount: Optional[float] = None
    invoice_number: Optional[str] = None
    delivery_note_number: Optional[str] = None

class ConfirmedDocument(BaseModel):
    id: str
    type: str
    supplier_name: str
    pages: List[int]
    metadata: DocumentMetadata

class ConfirmSplitsRequest(BaseModel):
    file_name: str
    documents: List[ConfirmedDocument]

@router.post("/upload/confirm-splits")
async def confirm_document_splits(request: ConfirmSplitsRequest):
    """
    Confirm document splits and save to database.
    """
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Process each confirmed document
        for document in request.documents:
            # Generate unique document ID
            document_id = str(uuid.uuid4())
            
            # Insert into uploaded_files table
            cursor.execute("""
                INSERT INTO uploaded_files (
                    id, original_filename, file_path, file_size, 
                    upload_date, document_type_guess, status, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                document_id,
                request.file_name,
                f"processed/{document_id}.pdf",  # Placeholder path
                0,  # File size will be updated later
                datetime.now().isoformat(),
                document.type,
                'pending',
                0.8  # Default confidence for confirmed documents
            ))
            
            # Insert document-specific data based on type
            if document.type == 'invoice':
                await _save_invoice_document(cursor, document_id, document, request.file_name)
            elif document.type == 'delivery_note':
                await _save_delivery_note_document(cursor, document_id, document, request.file_name)
            elif document.type == 'utility':
                await _save_utility_document(cursor, document_id, document, request.file_name)
            elif document.type == 'receipt':
                await _save_receipt_document(cursor, document_id, document, request.file_name)
            
            # Store page information
            await _save_document_pages(cursor, document_id, document.pages)
            
            # Add audit log entry
            await _add_audit_log(cursor, document_id, request.file_name, document)
        
        conn.commit()
        conn.close()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Successfully saved {len(request.documents)} document(s)",
                "document_count": len(request.documents)
            }
        )
        
    except Exception as e:
        logger.error(f"Error confirming document splits: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save documents: {str(e)}"
        )

async def _save_invoice_document(cursor, document_id: str, document: ConfirmedDocument, original_filename: str):
    """Save invoice document to database"""
    try:
        # Parse metadata
        invoice_date = document.metadata.invoice_date
        total_amount = document.metadata.total_amount
        invoice_number = document.metadata.invoice_number
        
        # Insert into invoices table (if it exists, otherwise use a generic approach)
        cursor.execute("""
            INSERT OR REPLACE INTO invoices (
                id, invoice_number, invoice_date, supplier_name, 
                total_amount, status, confidence, upload_timestamp,
                original_filename, page_numbers
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            document_id,
            invoice_number or f"INV-{document_id[:8]}",
            invoice_date or datetime.now().strftime('%Y-%m-%d'),
            document.supplier_name,
            total_amount or 0.0,
            'pending',
            0.8,
            datetime.now().isoformat(),
            original_filename,
            ','.join(map(str, document.pages))
        ))
    except sqlite3.OperationalError:
        # If invoices table doesn't exist, create it
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id TEXT PRIMARY KEY,
                invoice_number TEXT,
                invoice_date TEXT,
                supplier_name TEXT,
                total_amount REAL,
                status TEXT,
                confidence REAL,
                upload_timestamp TEXT,
                original_filename TEXT,
                page_numbers TEXT
            )
        """)
        # Retry the insert
        await _save_invoice_document(cursor, document_id, document, original_filename)

async def _save_delivery_note_document(cursor, document_id: str, document: ConfirmedDocument, original_filename: str):
    """Save delivery note document to database"""
    try:
        delivery_date = document.metadata.delivery_date
        delivery_note_number = document.metadata.delivery_note_number
        
        cursor.execute("""
            INSERT OR REPLACE INTO delivery_notes (
                id, delivery_note_number, delivery_date, supplier_name,
                status, confidence, upload_timestamp, original_filename, page_numbers
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            document_id,
            delivery_note_number or f"DN-{document_id[:8]}",
            delivery_date or datetime.now().strftime('%Y-%m-%d'),
            document.supplier_name,
            'pending',
            0.8,
            datetime.now().isoformat(),
            original_filename,
            ','.join(map(str, document.pages))
        ))
    except sqlite3.OperationalError:
        # Create delivery_notes table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS delivery_notes (
                id TEXT PRIMARY KEY,
                delivery_note_number TEXT,
                delivery_date TEXT,
                supplier_name TEXT,
                status TEXT,
                confidence REAL,
                upload_timestamp TEXT,
                original_filename TEXT,
                page_numbers TEXT
            )
        """)
        await _save_delivery_note_document(cursor, document_id, document, original_filename)

async def _save_utility_document(cursor, document_id: str, document: ConfirmedDocument, original_filename: str):
    """Save utility document to database"""
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO utility_bills (
                id, supplier_name, bill_date, total_amount,
                status, confidence, upload_timestamp, original_filename, page_numbers
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            document_id,
            document.supplier_name,
            document.metadata.invoice_date or datetime.now().strftime('%Y-%m-%d'),
            document.metadata.total_amount or 0.0,
            'pending',
            0.8,
            datetime.now().isoformat(),
            original_filename,
            ','.join(map(str, document.pages))
        ))
    except sqlite3.OperationalError:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS utility_bills (
                id TEXT PRIMARY KEY,
                supplier_name TEXT,
                bill_date TEXT,
                total_amount REAL,
                status TEXT,
                confidence REAL,
                upload_timestamp TEXT,
                original_filename TEXT,
                page_numbers TEXT
            )
        """)
        await _save_utility_document(cursor, document_id, document, original_filename)

async def _save_receipt_document(cursor, document_id: str, document: ConfirmedDocument, original_filename: str):
    """Save receipt document to database"""
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO receipts (
                id, supplier_name, receipt_date, total_amount,
                status, confidence, upload_timestamp, original_filename, page_numbers
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            document_id,
            document.supplier_name,
            document.metadata.invoice_date or datetime.now().strftime('%Y-%m-%d'),
            document.metadata.total_amount or 0.0,
            'pending',
            0.8,
            datetime.now().isoformat(),
            original_filename,
            ','.join(map(str, document.pages))
        ))
    except sqlite3.OperationalError:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS receipts (
                id TEXT PRIMARY KEY,
                supplier_name TEXT,
                receipt_date TEXT,
                total_amount REAL,
                status TEXT,
                confidence REAL,
                upload_timestamp TEXT,
                original_filename TEXT,
                page_numbers TEXT
            )
        """)
        await _save_receipt_document(cursor, document_id, document, original_filename)

async def _save_document_pages(cursor, document_id: str, pages: List[int]):
    """Store page information for the document"""
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT,
                page_number INTEGER,
                created_at TEXT
            )
        """)
        
        for page_num in pages:
            cursor.execute("""
                INSERT INTO document_pages (document_id, page_number, created_at)
                VALUES (?, ?, ?)
            """, (document_id, page_num, datetime.now().isoformat()))
    except Exception as e:
        logger.error(f"Error saving document pages: {str(e)}")

async def _add_audit_log(cursor, document_id: str, original_filename: str, document: ConfirmedDocument):
    """Add audit log entry for the document processing"""
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT,
                action TEXT,
                details TEXT,
                timestamp TEXT
            )
        """)
        
        details = f"Document split confirmed: {document.type} from {original_filename}, pages {document.pages}"
        
        cursor.execute("""
            INSERT INTO audit_log (document_id, action, details, timestamp)
            VALUES (?, ?, ?, ?)
        """, (document_id, "document_split_confirmed", details, datetime.now().isoformat()))
    except Exception as e:
        logger.error(f"Error adding audit log: {str(e)}") 