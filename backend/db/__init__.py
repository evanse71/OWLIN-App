import sqlite3
import os
import uuid
from typing import Optional, List, Dict, Any

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

DB_PATH = "data/owlin.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def execute(sql: str, params: tuple = ()):
    conn = get_connection()
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()

def fetch_one(sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def fetch_all(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def uuid_str() -> str:
    return str(uuid.uuid4())
