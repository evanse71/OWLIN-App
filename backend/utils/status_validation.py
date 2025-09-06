"""
Status validation utilities to prevent invalid status values
"""

# Valid status values for different tables
UPLOADED_FILES_STATUSES = {
    'pending', 'processing', 'completed', 'failed', 'timeout', 'reviewed'
}

INVOICES_STATUSES = {
    'pending', 'processing', 'scanned', 'parsed', 'matched', 'failed', 'timeout', 'reviewed'
}

def validate_uploaded_files_status(status: str) -> None:
    """Validate uploaded_files.processing_status value"""
    if status not in UPLOADED_FILES_STATUSES:
        raise ValueError(
            f"Invalid uploaded_files.processing_status: '{status}'. "
            f"Must be one of: {sorted(UPLOADED_FILES_STATUSES)}"
        )

def validate_invoice_status(status: str) -> None:
    """Validate invoices.status value"""
    if status not in INVOICES_STATUSES:
        raise ValueError(
            f"Invalid invoices.status: '{status}'. "
            f"Must be one of: {sorted(INVOICES_STATUSES)}"
        )

def assert_valid_status(table: str, column: str, status: str) -> None:
    """Assert status is valid for the given table/column"""
    if table == 'uploaded_files' and column == 'processing_status':
        validate_uploaded_files_status(status)
    elif table == 'invoices' and column == 'status':
        validate_invoice_status(status)
    else:
        # Unknown table/column combination - skip validation
        pass 