#!/usr/bin/env python3
"""Check OCR processing status"""
import sqlite3
from datetime import datetime

DB_PATH = "data/owlin.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check document status
    doc_id = "421a8e1f-2c1b-4ce9-929a-ecda8125dfcf"
    cur.execute("SELECT id, status, ocr_stage, ocr_error FROM documents WHERE id = ?", (doc_id,))
    doc = cur.fetchone()
    if doc:
        print(f"Document {doc_id}:")
        print(f"  Status: {doc[1]}")
        print(f"  Stage: {doc[2]}")
        print(f"  Error: {doc[3]}")
    else:
        print(f"Document {doc_id} not found")
    
    # Check recent OCR audit logs
    print("\nRecent OCR audit logs:")
    cur.execute("SELECT ts, actor, action, detail FROM audit_log WHERE action LIKE '%ocr%' ORDER BY ts DESC LIMIT 15")
    rows = cur.fetchall()
    for row in rows:
        detail = row[3][:150] if row[3] else ""
        print(f"  {row[0]}: {row[2]} - {detail}")
    
    conn.close()

if __name__ == "__main__":
    main()
