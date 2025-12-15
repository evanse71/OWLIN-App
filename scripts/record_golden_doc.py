#!/usr/bin/env python3
"""
Record golden documents for pipeline testing.

Usage:
    python scripts/record_golden_doc.py <doc_id> <filename> <file_size_bytes> <doc_type>
    
Example:
    python scripts/record_golden_doc.py abc-123 invoice.pdf 123456 invoice
"""
import json
import sys
from pathlib import Path
from datetime import datetime

GOLDEN_DOCS_FILE = Path("data/golden_documents.json")

def record_golden_doc(doc_id: str, filename: str, file_size_bytes: int, doc_type: str):
    """Record a golden document for testing."""
    # Load existing records
    if GOLDEN_DOCS_FILE.exists():
        with open(GOLDEN_DOCS_FILE, 'r') as f:
            records = json.load(f)
    else:
        records = []
    
    # Add new record
    record = {
        "doc_id": doc_id,
        "filename": filename,
        "file_size_bytes": file_size_bytes,
        "doc_type": doc_type,  # 'invoice' or 'delivery_note'
        "upload_timestamp": datetime.now().isoformat(),
        "recorded_at": datetime.now().isoformat()
    }
    
    records.append(record)
    
    # Save back
    GOLDEN_DOCS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(GOLDEN_DOCS_FILE, 'w') as f:
        json.dump(records, f, indent=2)
    
    print(f"✅ Recorded golden document: {doc_id} ({filename}, {file_size_bytes} bytes, {doc_type})")
    return record

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(__doc__)
        sys.exit(1)
    
    doc_id = sys.argv[1]
    filename = sys.argv[2]
    file_size_bytes = int(sys.argv[3])
    doc_type = sys.argv[4]
    
    if doc_type not in ['invoice', 'delivery_note']:
        print(f"Error: doc_type must be 'invoice' or 'delivery_note', got '{doc_type}'")
        sys.exit(1)
    
    record_golden_doc(doc_id, filename, file_size_bytes, doc_type)

