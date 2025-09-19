"""
upload_validator.py
===================

This module contains helper routines that assist with the invoice
upload flow in Owlin.  These routines allow the calling code to
perform basic pre‑upload checks before committing an invoice to the
database.  They operate purely on local data and do not require an
internet connection.

Key features implemented here include:

* **File type validation**: ensures that users only upload files in
  supported formats (PDF and common image types).  An extensible
  mapping from file extension to MIME type allows for future
  expansion.
* **Duplicate detection**: checks whether an invoice number already
  exists in the local SQLite database.  This helps prevent
  inadvertent duplicate uploads.  The function attempts to query
  several plausible invoice tables (``invoices``, ``invoice`` and
  ``invoice_records``) and gracefully handles missing tables.
* **Descriptive naming**: generates a temporary, human‑readable name
  for the invoice using extracted supplier and date information.

These functions are designed to be called from the Streamlit front
end.  They return simple Python objects that can be used to control
user feedback (e.g. disable a save button or show a warning banner).
"""

from __future__ import annotations

import os
import sqlite3
import logging
from typing import Dict, Optional, Tuple, List, Any
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".tiff": "image/tiff",
}

# Database configuration
DEFAULT_DB_PATH = "data/owlin.db"
INVOICE_TABLES = ["invoices", "invoice", "invoice_records", "processed_invoices"]


def is_supported_file(filename: str) -> bool:
    """Return ``True`` if the file has a supported extension.

    Parameters
    ----------
    filename: str
        The name or path of the file to check.

    Returns
    -------
    bool
        ``True`` if the file's extension is among the supported
        formats; ``False`` otherwise.
    """
    _, ext = os.path.splitext(filename.lower())
    return ext in SUPPORTED_EXTENSIONS


def get_file_mime_type(filename: str) -> Optional[str]:
    """Get the MIME type for a supported file.

    Parameters
    ----------
    filename: str
        The name or path of the file to check.

    Returns
    -------
    Optional[str]
        The MIME type if the file is supported, ``None`` otherwise.
    """
    _, ext = os.path.splitext(filename.lower())
    return SUPPORTED_EXTENSIONS.get(ext)


def validate_file_size(file_path: str, max_size_mb: int = 50) -> Tuple[bool, Optional[str]]:
    """Validate that the file size is within acceptable limits.

    Parameters
    ----------
    file_path: str
        The path to the file to check.
    max_size_mb: int
        Maximum file size in megabytes.

    Returns
    -------
    Tuple[bool, Optional[str]]
        A tuple where the first element is ``True`` if the file size
        is acceptable, and the second element is an error message if
        the file is too large.
    """
    try:
        file_size = os.path.getsize(file_path)
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if file_size > max_size_bytes:
            file_size_mb = file_size / (1024 * 1024)
            error_msg = f"File size ({file_size_mb:.1f}MB) exceeds maximum allowed size ({max_size_mb}MB)."
            return False, error_msg
        
        return True, None
    except OSError as e:
        return False, f"Unable to read file size: {str(e)}"


def generate_temp_invoice_name(supplier: Optional[str], date: Optional[str], 
                             invoice_number: Optional[str] = None) -> str:
    """Generate a temporary descriptive name for an uploaded invoice.

    The name uses the format ``Invoice – <Supplier> – <Date>`` or
    ``Invoice – <Supplier> – <Invoice Number>``.  If either supplier
    or date is missing, that component is omitted.

    Parameters
    ----------
    supplier: Optional[str]
        The supplier name extracted from the invoice, if available.
    date: Optional[str]
        The invoice date extracted from the invoice, if available.
    invoice_number: Optional[str]
        The invoice number extracted from the invoice, if available.

    Returns
    -------
    str
        A descriptive name incorporating the supplier and date/number.
    """
    parts = []
    if supplier and supplier.strip() and supplier != "Unknown":
        parts.append(supplier.strip())
    if date and date.strip() and date != "Unknown":
        parts.append(date.strip())
    elif invoice_number and invoice_number.strip() and invoice_number != "Unknown":
        parts.append(f"#{invoice_number.strip()}")
    
    if not parts:
        return "Invoice"
    return "Invoice – " + " – ".join(parts)


def check_duplicate_invoice(invoice_number: Optional[str], db_path: str) -> bool:
    """Check whether an invoice number already exists in the database.

    This function attempts to open the SQLite database at ``db_path``
    and search for the provided ``invoice_number`` in one of the
    expected invoice tables.  If the database does not exist or the
    relevant table/column cannot be found, the function returns
    ``False``.  This conservative behaviour ensures that the user is
    not blocked from uploading invoices when the schema is unknown.

    Parameters
    ----------
    invoice_number: Optional[str]
        The invoice number to look up.  If ``None`` or empty, the
        function immediately returns ``False``.
    db_path: str
        The path to the local SQLite database.

    Returns
    -------
    bool
        ``True`` if the invoice number exists in the database;
        ``False`` otherwise or if detection fails.
    """
    if not invoice_number:
        return False
    
    # Ensure database path exists
    if not os.path.exists(db_path):
        logger.debug(f"Database not found at {db_path}")
        return False
    
    invoice_number = invoice_number.strip()
    if not invoice_number:
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # List of candidate table names that may hold invoices
        tables = INVOICE_TABLES
        
        for table in tables:
            try:
                # Determine column names
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1].lower() for row in cursor.fetchall()]
                
                # Look for plausible invoice number columns
                candidate_cols = [c for c in columns if "number" in c or "invoice" in c or "id" in c]
                
                for col in candidate_cols:
                    try:
                        cursor.execute(
                            f"SELECT 1 FROM {table} WHERE {col} = ? LIMIT 1", (invoice_number,)
                        )
                        if cursor.fetchone() is not None:
                            logger.info(f"Duplicate invoice found: {invoice_number} in table {table}")
                            conn.close()
                            return True
                    except sqlite3.Error as e:
                        logger.debug(f"Error querying column {col} in table {table}: {e}")
                        continue
                        
            except sqlite3.Error as e:
                logger.debug(f"Error accessing table {table}: {e}")
                continue  # table doesn't exist or other error
                
        conn.close()
        
    except sqlite3.Error as e:
        logger.warning(f"Database error during duplicate check: {e}")
        # In case the database is corrupted or cannot be opened, we
        # assume no duplicate and allow the upload to proceed.
        return False
    
    return False


def check_duplicate_file_hash(file_path: str, db_path: str) -> Tuple[bool, Optional[str]]:
    """Check whether a file with the same hash already exists in the database.

    This provides an additional layer of duplicate detection based on
    file content rather than just invoice numbers.

    Parameters
    ----------
    file_path: str
        The path to the file to check.
    db_path: str
        The path to the local SQLite database.

    Returns
    -------
    Tuple[bool, Optional[str]]
        A tuple where the first element is ``True`` if a duplicate
        file hash is found, and the second element is the hash value.
    """
    try:
        import hashlib
        
        # Calculate file hash
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        file_hash = hash_md5.hexdigest()
        
        # Check database for existing hash
        if not os.path.exists(db_path):
            return False, None
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check common table names for file_hash column
        tables = INVOICE_TABLES + ["files", "uploads", "documents"]
        
        for table in tables:
            try:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1].lower() for row in cursor.fetchall()]
                
                if "file_hash" in columns or "hash" in columns:
                    col_name = "file_hash" if "file_hash" in columns else "hash"
                    cursor.execute(
                        f"SELECT 1 FROM {table} WHERE {col_name} = ? LIMIT 1", (file_hash,)
                    )
                    if cursor.fetchone() is not None:
                        logger.info(f"Duplicate file hash found: {file_hash} in table {table}")
                        conn.close()
                        return True, file_hash
                        
            except sqlite3.Error:
                continue
        
        conn.close()
        return False, file_hash
        
    except Exception as e:
        logger.warning(f"Error checking file hash: {e}")
        return False, None


def validate_upload(
    file_path: str,
    extracted_data: Dict[str, Optional[str]],
    db_path: str = DEFAULT_DB_PATH,
    max_file_size_mb: int = 50,
) -> Tuple[bool, Dict[str, str], Dict[str, Any]]:
    """Run a series of pre‑upload checks on an invoice file.

    The function validates the file format, checks for duplicates in
    the database and generates a temporary name for display.  It
    returns a boolean indicating whether the upload should be allowed,
    along with a dictionary of messages.  The caller can use these
    messages to inform the user via the UI.

    Parameters
    ----------
    file_path: str
        The path to the invoice file being uploaded.
    extracted_data: Dict[str, Optional[str]]
        A dictionary containing key fields extracted from the invoice,
        typically produced by ``extract_invoice_fields``.  Expected keys
        include ``supplier_name``, ``invoice_number`` and ``invoice_date``.
    db_path: str
        The path to the SQLite database.
    max_file_size_mb: int
        Maximum allowed file size in megabytes.

    Returns
    -------
    Tuple[bool, Dict[str, str], Dict[str, Any]]
        A tuple where:
        - First element is ``True`` if the upload is allowed to proceed
        - Second element is a mapping from message type to human readable strings
        - Third element is additional validation data (file hash, etc.)
    """
    messages: Dict[str, str] = {}
    validation_data: Dict[str, Any] = {}
    allowed = True

    logger.info(f"🔄 Starting upload validation for: {file_path}")

    # 1. Check file format
    if not is_supported_file(file_path):
        messages["error"] = f"Unsupported file format for '{os.path.basename(file_path)}'. Supported formats: {', '.join(SUPPORTED_EXTENSIONS.keys())}"
        allowed = False
        logger.warning(f"❌ Unsupported file format: {file_path}")
    else:
        mime_type = get_file_mime_type(file_path)
        validation_data["mime_type"] = mime_type
        logger.info(f"✅ File format validated: {mime_type}")

    # 2. Check file size
    size_valid, size_error = validate_file_size(file_path, max_file_size_mb)
    if not size_valid:
        messages["error"] = size_error
        allowed = False
        logger.warning(f"❌ File size validation failed: {size_error}")
    else:
        file_size = os.path.getsize(file_path)
        validation_data["file_size"] = file_size
        logger.info(f"✅ File size validated: {file_size / (1024*1024):.1f}MB")

    # 3. Check for duplicate invoice number if available
    invoice_number = extracted_data.get("invoice_number") if extracted_data else None
    if invoice_number and invoice_number != "Unknown":
        try:
            duplicate = check_duplicate_invoice(invoice_number, db_path)
            if duplicate:
                messages["warning"] = f"An invoice with number '{invoice_number}' already exists in the database."
                validation_data["duplicate_invoice"] = True
                logger.warning(f"⚠️ Duplicate invoice number found: {invoice_number}")
            else:
                validation_data["duplicate_invoice"] = False
                logger.info(f"✅ Invoice number check passed: {invoice_number}")
        except Exception as e:
            logger.warning(f"⚠️ Error checking for duplicate invoice: {e}")
            validation_data["duplicate_invoice"] = False

    # 4. Check for duplicate file hash
    try:
        duplicate_hash, file_hash = check_duplicate_file_hash(file_path, db_path)
        if duplicate_hash:
            messages["warning"] = "A file with identical content already exists in the database."
            validation_data["duplicate_file"] = True
            logger.warning(f"⚠️ Duplicate file hash found: {file_hash}")
        else:
            validation_data["duplicate_file"] = False
            if file_hash:
                validation_data["file_hash"] = file_hash
            logger.info("✅ File hash check passed")
    except Exception as e:
        logger.warning(f"⚠️ Error checking file hash: {e}")
        validation_data["duplicate_file"] = False

    # 5. Generate a descriptive name
    supplier = extracted_data.get("supplier_name") if extracted_data else None
    date = extracted_data.get("invoice_date") if extracted_data else None
    temp_name = generate_temp_invoice_name(supplier, date, invoice_number)
    messages["name"] = temp_name
    validation_data["suggested_name"] = temp_name

    # 6. Additional validation data
    validation_data["file_path"] = file_path
    validation_data["file_name"] = os.path.basename(file_path)
    validation_data["extracted_data"] = extracted_data

    if allowed:
        logger.info(f"✅ Upload validation completed successfully: {temp_name}")
    else:
        logger.error(f"❌ Upload validation failed: {messages.get('error', 'Unknown error')}")

    return allowed, messages, validation_data


def get_validation_summary(validation_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a summary of validation results for UI display.

    Parameters
    ----------
    validation_data: Dict[str, Any]
        The validation data returned by validate_upload.

    Returns
    -------
    Dict[str, Any]
        A summary suitable for UI display.
    """
    summary = {
        "file_info": {
            "name": validation_data.get("file_name", "Unknown"),
            "size_mb": validation_data.get("file_size", 0) / (1024 * 1024) if validation_data.get("file_size") else 0,
            "mime_type": validation_data.get("mime_type", "Unknown"),
        },
        "extracted_info": {
            "supplier": validation_data.get("extracted_data", {}).get("supplier_name", "Unknown"),
            "invoice_number": validation_data.get("extracted_data", {}).get("invoice_number", "Unknown"),
            "date": validation_data.get("extracted_data", {}).get("invoice_date", "Unknown"),
        },
        "validation_results": {
            "duplicate_invoice": validation_data.get("duplicate_invoice", False),
            "duplicate_file": validation_data.get("duplicate_file", False),
            "suggested_name": validation_data.get("suggested_name", "Invoice"),
        }
    }
    
    return summary


def create_upload_metadata(validation_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create metadata for database storage.

    Parameters
    ----------
    validation_data: Dict[str, Any]
        The validation data returned by validate_upload.

    Returns
    -------
    Dict[str, Any]
        Metadata suitable for database storage.
    """
    metadata = {
        "original_filename": validation_data.get("file_name", ""),
        "file_size": validation_data.get("file_size", 0),
        "mime_type": validation_data.get("mime_type", ""),
        "file_hash": validation_data.get("file_hash", ""),
        "upload_timestamp": None,  # Will be set by database layer
        "extracted_supplier": validation_data.get("extracted_data", {}).get("supplier_name"),
        "extracted_invoice_number": validation_data.get("extracted_data", {}).get("invoice_number"),
        "extracted_date": validation_data.get("extracted_data", {}).get("invoice_date"),
        "suggested_name": validation_data.get("suggested_name", ""),
        "validation_status": "validated",
    }
    
    return metadata 