import sqlite3
import json
from datetime import datetime

def get_db_connection():
    conn = sqlite3.connect('backend/data/owlin.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_receipts_table():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            uploaded_by TEXT,
            store_name TEXT,
            total_amount REAL,
            purchase_date TEXT,
            items TEXT,
            ocr_confidence INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def insert_receipt(filename, uploaded_by, store_name, total_amount, purchase_date, items, ocr_confidence):
    conn = get_db_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('''
        INSERT INTO receipts (filename, uploaded_by, store_name, total_amount, purchase_date, items, ocr_confidence, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        filename,
        uploaded_by,
        store_name,
        total_amount,
        purchase_date,
        json.dumps(items) if items is not None else None,
        ocr_confidence,
        now,
        now
    ))
    conn.commit()
    receipt_id = c.lastrowid
    conn.close()
    return receipt_id

def update_receipt(receipt_id, **kwargs):
    conn = get_db_connection()
    c = conn.cursor()
    fields = []
    values = []
    for key, value in kwargs.items():
        if key == 'items' and value is not None:
            value = json.dumps(value)
        fields.append(f"{key} = ?")
        values.append(value)
    values.append(datetime.now().isoformat())
    fields.append("updated_at = ?")
    values.append(receipt_id)
    sql = f"UPDATE receipts SET {', '.join(fields)} WHERE id = ?"
    c.execute(sql, values)
    conn.commit()
    conn.close() 