#!/usr/bin/env python3
"""
Simple OWLIN server for testing
"""
import os
import sys
import sqlite3
import uuid
import json
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import fitz
import numpy as np
import cv2

# OCR Engine
try:
    from paddleocr import PaddleOCR
    _PADDLE_OK = True
except Exception:
    _PADDLE_OK = False

import pytesseract

class UnifiedOCREngine:
    _instance = None
    _lock = None

    def __init__(self) -> None:
        self._paddle = None
        self._ready = False

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = UnifiedOCREngine()
        return cls._instance

    def ensure_ready(self) -> None:
        if self._ready:
            return
        if _PADDLE_OK:
            self._paddle = PaddleOCR(use_angle_cls=True, lang="en")
        self._ready = True

    def health(self) -> Dict[str, Any]:
        return {
            "engine": "paddle" if _PADDLE_OK else "tesseract",
            "status": "ok" if (self._ready or _PADDLE_OK) else "degraded",
            "paddle_available": _PADDLE_OK,
            "paddle_loaded": self._ready and _PADDLE_OK
        }

    def run_ocr(self, image_bgr):
        self.ensure_ready()
        if _PADDLE_OK and self._paddle is not None:
            result = self._paddle.ocr(image_bgr, cls=True)
            lines = []
            for page in result:
                for box, (text, conf) in [(it[0], it[1]) for it in page]:
                    lines.append({"text": text, "conf": float(conf), "box": box})
            return {"lines": lines}
        # fallback
        text = pytesseract.image_to_string(image_bgr)
        return {"lines": [{"text": t, "conf": 0.5, "box": None} for t in text.splitlines() if t.strip()]}

# Database setup
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

# Create tables
def setup_db():
    execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id TEXT PRIMARY KEY,
            supplier TEXT,
            invoice_date TEXT,
            status TEXT DEFAULT 'scanned',
            currency TEXT DEFAULT 'GBP',
            document_id TEXT,
            page_no INTEGER DEFAULT 0,
            total_value REAL
        )
    """)
    
    execute("""
        CREATE TABLE IF NOT EXISTS invoice_line_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id TEXT NOT NULL,
            description TEXT,
            quantity REAL DEFAULT 0,
            unit_price REAL DEFAULT 0,
            total REAL DEFAULT 0,
            uom TEXT,
            vat_rate REAL DEFAULT 0,
            source TEXT DEFAULT 'ocr',
            FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
        )
    """)
    
    execute("""
        CREATE TABLE IF NOT EXISTS delivery_notes (
            id TEXT PRIMARY KEY,
            supplier TEXT,
            note_date TEXT,
            status TEXT DEFAULT 'scanned',
            document_id TEXT,
            page_no INTEGER DEFAULT 0,
            total_amount REAL
        )
    """)

# Pydantic models
class InvoiceLineItemIn(BaseModel):
    description: Optional[str] = None
    quantity: float = 0
    unit_price: float = 0
    uom: Optional[str] = None
    vat_rate: float = 0

class InvoiceManualIn(BaseModel):
    supplier: str
    invoice_date: Optional[str] = None
    reference: Optional[str] = None
    currency: Optional[str] = "GBP"
    line_items: Optional[List[InvoiceLineItemIn]] = None

# FastAPI app
app = FastAPI(title="OWLIN Simple Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
@app.get("/api/health/ocr")
def ocr_health():
    return UnifiedOCREngine.instance().health()

@app.post("/api/invoices/manual")
def create_manual(inv: InvoiceManualIn):
    inv_id = uuid_str()
    execute(
        "INSERT INTO invoices (id, supplier, invoice_date, status, currency, document_id, page_no, total_value) VALUES (?,?,?,?,?,?,?,?)",
        (inv_id, inv.supplier, inv.invoice_date, "manual", inv.currency, None, 0, None)
    )
    for li in inv.line_items or []:
        tot = float(li.quantity) * float(li.unit_price)
        execute("INSERT INTO invoice_line_items (invoice_id, description, quantity, unit_price, total, uom, vat_rate, source) VALUES (?,?,?,?,?,?,?,?)",
                   (inv_id, li.description, li.quantity, li.unit_price, tot, li.uom, li.vat_rate, "manual"))
    return {"id": inv_id, "status": "manual"}

@app.get("/api/invoices/{invoice_id}/line-items")
def get_items(invoice_id: str):
    rows = fetch_all("SELECT id, description, quantity, unit_price, total, uom, vat_rate, source FROM invoice_line_items WHERE invoice_id=? ORDER BY id ASC", (invoice_id,))
    return {"items": rows}

@app.get("/api/pairing/suggestions")
def suggest(invoice_id: str):
    inv = fetch_one("SELECT supplier, invoice_date, total_value FROM invoices WHERE id=?", (invoice_id,))
    if not inv: raise HTTPException(404, "invoice not found")
    cands = fetch_all("SELECT id, supplier, note_date, total_amount FROM delivery_notes ORDER BY note_date DESC LIMIT 50")
    out = []
    for c in cands:
        score = 0
        if inv["supplier"] and c["supplier"] and inv["supplier"].lower()==c["supplier"].lower():
            score += 50
        if inv["invoice_date"] and c["note_date"] and inv["invoice_date"]==c["note_date"]:
            score += 30
        if inv["total_value"] and c["total_amount"] and abs(inv["total_value"]-c["total_amount"])<=2.0:
            score += 20
        if score>0:
            out.append({"delivery_note_id": c["id"], "score": score, "reason":"heuristics"})
    out.sort(key=lambda x: x["score"], reverse=True)
    return {"suggestions": out, "total_candidates": len(cands)}

if __name__ == "__main__":
    setup_db()
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8081)
