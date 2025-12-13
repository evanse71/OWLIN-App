from __future__ import annotations
import shutil, hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from fastapi import UploadFile
from sqlalchemy.orm import Session
from uuid import uuid4
from ..services.audit import log_event

ALLOWED = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def _safe(name: str) -> str:
	return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)[:160]


def _sha256(fp: Path) -> str:
	h = hashlib.sha256()
	with open(fp, "rb") as f:
		for chunk in iter(lambda: f.read(1024 * 1024), b""):
			h.update(chunk)
	return h.hexdigest()


def _store(root: Path, original: str) -> Path:
	root.mkdir(parents=True, exist_ok=True)
	return root / f"{uuid4()}_{_safe(original)}"


def _ensure_tables(session: Session) -> None:
	# uploaded_files
	session.execute(
		"""
		CREATE TABLE IF NOT EXISTS uploaded_files (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			filename TEXT NOT NULL,
			file_type TEXT,
			checksum TEXT,
			status TEXT,
			uploaded_at TEXT
		)
		"""
	)
	# delivery_notes
	session.execute(
		"""
		CREATE TABLE IF NOT EXISTS delivery_notes (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			uploaded_file_id INTEGER,
			supplier_name TEXT,
			note_number TEXT,
			date TEXT,
			status TEXT,
			ocr_confidence INTEGER DEFAULT 0,
			matched_invoice_id TEXT,
			created_at TEXT NOT NULL,
			updated_at TEXT NOT NULL
		)
		"""
	)
	# line_items shared
	session.execute(
		"""
		CREATE TABLE IF NOT EXISTS line_items (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			parent_type TEXT,
			parent_id INTEGER,
			description TEXT,
			qty REAL,
			unit_price_pennies INTEGER DEFAULT 0,
			total_pennies INTEGER DEFAULT 0,
			uom TEXT,
			sku TEXT
		)
		"""
	)
	# audit_log
	session.execute(
		"""
		CREATE TABLE IF NOT EXISTS audit_log (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			event_type TEXT,
			entity_type TEXT,
			entity_id TEXT,
			message TEXT,
			created_at TEXT
		)
		"""
	)
	session.commit()


def ingest_delivery_notes(session: Session, files: List[UploadFile], storage_root: Path = Path("data/uploads")) -> Dict[str, Any]:
	_ensure_tables(session)
	created = []
	for f in files:
		if not f.filename:
			continue
		ext = Path(f.filename).suffix.lower()
		if ext not in ALLOWED:
			continue
		dst = _store(storage_root, f.filename)
		with open(dst, "wb") as out:
			shutil.copyfileobj(f.file, out)
		checksum = _sha256(dst)
		session.execute(
			"""
			INSERT INTO uploaded_files (filename, file_type, checksum, status, uploaded_at)
			VALUES (:filename, :file_type, :checksum, :status, :uploaded_at)
			""",
			{
				"filename": dst.name,
				"file_type": ext,
				"checksum": checksum,
				"status": "pending",
				"uploaded_at": datetime.utcnow().isoformat(),
			},
		)
		uf_id = session.execute("SELECT last_insert_rowid()").scalar()
		log_event(session, "dn_upload_saved", "uploaded_file", str(uf_id), f"Saved DN to {dst}")
		session.execute("UPDATE uploaded_files SET status='scanning' WHERE id = :id", {"id": uf_id})
		session.commit()
		try:
			try:
				from ..ocr.pipeline import run_ocr_pipeline  # type: ignore
			except Exception:
				# Fallback: no OCR available; create empty result
				class _Dummy:
					class H:
						supplier_name = None
						invoice_number = None
						invoice_date_iso = None
					header = None
					line_items = []
					confidence_0_100 = 0
				pass
				def run(path: str):
					return _Dummy()
				run_ocr_pipeline = run  # type: ignore
			ocr = run_ocr_pipeline(str(dst))
			session.execute(
				"""
				INSERT INTO delivery_notes (
					uploaded_file_id, supplier_name, note_number, date, status, ocr_confidence, matched_invoice_id, created_at, updated_at
				) VALUES (:uploaded_file_id, :supplier_name, :note_number, :date, :status, :ocr_confidence, NULL, :created_at, :updated_at)
				""",
				{
					"uploaded_file_id": uf_id,
					"supplier_name": getattr(ocr.header, "supplier_name", None) if getattr(ocr, "header", None) else None,
					"note_number": getattr(ocr.header, "invoice_number", None) if getattr(ocr, "header", None) else None,
					"date": getattr(ocr.header, "invoice_date_iso", None) if getattr(ocr, "header", None) else None,
					"status": "parsed",
					"ocr_confidence": int(getattr(ocr, "confidence_0_100", 0) or 0),
					"created_at": datetime.utcnow().isoformat(),
					"updated_at": datetime.utcnow().isoformat(),
				},
			)
			dn_id = session.execute("SELECT last_insert_rowid()").scalar()
			for li in getattr(ocr, "line_items", []) or []:
				session.execute(
					"""
					INSERT INTO line_items (parent_type, parent_id, description, qty, unit_price_pennies, total_pennies, uom, sku)
					VALUES ('delivery_note', :parent_id, :description, :qty, :unit_price_pennies, :total_pennies, :uom, :sku)
					""",
					{
						"parent_id": dn_id,
						"description": getattr(li, "description", "") or "",
						"qty": float(getattr(li, "qty", 0) or 0),
						"unit_price_pennies": int(getattr(li, "unit_price_pennies", 0) or 0),
						"total_pennies": int(getattr(li, "total_pennies", 0) or 0),
						"uom": getattr(li, "uom", None),
						"sku": getattr(li, "sku", None),
					},
				)
			session.execute("UPDATE uploaded_files SET status='scanned' WHERE id = :id", {"id": uf_id})
			session.commit()
			log_event(session, "dn_ocr_parsed", "delivery_note", str(dn_id), f"conf={int(getattr(ocr, 'confidence_0_100', 0) or 0)}")
			created.append(dn_id)
		except Exception as e:
			session.execute("UPDATE uploaded_files SET status='failed' WHERE id = :id", {"id": uf_id})
			session.commit()
			log_event(session, "dn_ocr_failed", "uploaded_file", str(uf_id), f"{type(e).__name__}: {e}")
	from ..contracts import DeliveryNote as ApiDN, DnLineItem as ApiLi
	out = []
	for dn_id in created:
		row = session.execute(
			"SELECT id, supplier_name, note_number, date, status, ocr_confidence, matched_invoice_id FROM delivery_notes WHERE id = :id",
			{"id": dn_id},
		).fetchone()
		items = session.execute(
			"SELECT id, description, qty, unit_price_pennies, total_pennies, uom, sku FROM line_items WHERE parent_type='delivery_note' AND parent_id = :id",
			{"id": dn_id},
		).fetchall()
		api_items = [ApiLi(id=i[0], description=i[1], qty=float(i[2] or 0), unit_price_pennies=int(i[3] or 0), total_pennies=int(i[4] or 0), uom=i[5], sku=i[6]) for i in items]
		out.append(
			ApiDN(
				id=row[0], supplier_name=row[1], note_number=row[2], date=row[3], status=row[4], ocr_confidence=int(row[5] or 0), matched_invoice_id=row[6], items=api_items
			)
		)
	return {"delivery_notes": out} 