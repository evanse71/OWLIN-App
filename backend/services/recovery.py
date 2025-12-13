from __future__ import annotations
import os
import zipfile
import hashlib
import shutil
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from uuid import uuid4
from typing import List, Dict, Optional

from ..contracts import IntegrityReport, BackupEntry, DiffReport
from ..services.audit import log_event


BACKUP_DIR = Path("backups")
DATA_DIR = Path("data")
LICENSE_DIR = Path("license")


def sha256_file(p: Path) -> str:
	h = hashlib.sha256()
	with open(p, "rb") as f:
		for chunk in iter(lambda: f.read(1024 * 1024), b""):
			h.update(chunk)
	return h.hexdigest()


def check_integrity() -> IntegrityReport:
	reasons: List[str] = []
	db_version = None
	last_backup_at = None
	
	# Check license
	license_file = LICENSE_DIR / "license.lic"
	if not license_file.exists():
		reasons.append("License file missing")
	else:
		try:
			with open(license_file, "r") as f:
				lic_data = json.load(f)
			if lic_data.get("expiry", "1970-01-01") < datetime.now().strftime("%Y-%m-%d"):
				reasons.append("License expired")
		except Exception:
			reasons.append("License file corrupted")
	
	# Check database
	db_file = DATA_DIR / "owlin.db"
	if not db_file.exists():
		reasons.append("Database file missing")
	else:
		try:
			conn = sqlite3.connect(db_file)
			cur = conn.cursor()
			
			# PRAGMA integrity check
			cur.execute("PRAGMA integrity_check")
			integrity_result = cur.fetchone()
			if integrity_result and integrity_result[0] != "ok":
				reasons.append(f"Database integrity failed: {integrity_result[0]}")
			
			# Check schema version
			cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'")
			if cur.fetchone():
				cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
				version_row = cur.fetchone()
				if version_row:
					db_version = version_row[0]
			
			# Check last backup
			cur.execute("SELECT created_at FROM backups_meta ORDER BY created_at DESC LIMIT 1")
			backup_row = cur.fetchone()
			if backup_row:
				last_backup_at = datetime.fromisoformat(backup_row[0])
			
			conn.close()
		except Exception as e:
			reasons.append(f"Database error: {str(e)}")
	
	# Check backup age
	if last_backup_at:
		days_since_backup = (datetime.now() - last_backup_at).days
		if days_since_backup > 7:
			reasons.append(f"Last backup was {days_since_backup} days ago")
	
	return IntegrityReport(
		ok=len(reasons) == 0,
		reasons=reasons,
		db_version=db_version,
		last_backup_at=last_backup_at
	)


def list_backups() -> List[BackupEntry]:
	BACKUP_DIR.mkdir(parents=True, exist_ok=True)
	out: List[BackupEntry] = []
	
	for z in sorted(BACKUP_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True):
		try:
			cs = sha256_file(z)
			be = BackupEntry(
				id=uuid4(),
				name=z.name,
				path=str(z),
				created_at=datetime.fromtimestamp(z.stat().st_mtime),
				size_bytes=z.stat().st_size,
				checksum_sha256=cs
			)
			out.append(be)
		except Exception:
			continue
	
	return out


def create_support_pack(out_path: Path) -> Path:
	"""Create support pack with database, audit log, and license."""
	DATA_DIR.mkdir(parents=True, exist_ok=True)
	BACKUP_DIR.mkdir(parents=True, exist_ok=True)
	
	with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
		# Database
		db_file = DATA_DIR / "owlin.db"
		if db_file.exists():
			z.write(db_file, arcname="data/owlin.db")
		
		# Audit log
		audit_file = DATA_DIR / "audit.log"
		if audit_file.exists():
			z.write(audit_file, arcname="data/audit.log")
		
		# License
		license_file = LICENSE_DIR / "license.lic"
		if license_file.exists():
			z.write(license_file, arcname="license/license.lic")
		
		# Metadata
		metadata = {
			"created_at": datetime.now().isoformat(),
			"version": "1.0.0",
			"integrity": check_integrity().dict()
		}
		z.writestr("metadata.json", json.dumps(metadata, indent=2))
	
	return out_path


def restore_dry_run(backup_path: str) -> DiffReport:
	"""Extract backup and generate diff report."""
	from .conflict import generate_diff_report
	
	backup_file = Path(backup_path)
	if not backup_file.exists():
		raise ValueError("Backup file not found")
	
	tmp_extract = Path("tmp_restore_dry_run")
	if tmp_extract.exists():
		shutil.rmtree(tmp_extract)
	tmp_extract.mkdir()
	
	try:
		with zipfile.ZipFile(backup_file, "r") as z:
			z.extractall(tmp_extract)
		
		# Find database in extracted files
		candidate_db = None
		for db_file in tmp_extract.rglob("*.db"):
			if db_file.name == "owlin.db":
				candidate_db = db_file
				break
		
		if not candidate_db:
			raise ValueError("No database found in backup")
		
		current_db = DATA_DIR / "owlin.db"
		if not current_db.exists():
			raise ValueError("Current database not found")
		
		diff_result = generate_diff_report(str(current_db), str(candidate_db))
		return DiffReport(
			backup_id=uuid4(),
			rows=diff_result["rows"],
			summary=diff_result["summary"]
		)
	finally:
		if tmp_extract.exists():
			shutil.rmtree(tmp_extract)


def apply_restore_with_decisions(backup_path: str, decisions: List[Dict]) -> bool:
	"""Apply restore with conflict resolutions."""
	from .conflict import apply_decisions_to_db
	
	backup_file = Path(backup_path)
	if not backup_file.exists():
		raise ValueError("Backup file not found")
	
	tmp_dir = Path("tmp_restore_apply")
	if tmp_dir.exists():
		shutil.rmtree(tmp_dir)
	tmp_dir.mkdir()
	
	try:
		with zipfile.ZipFile(backup_file, "r") as z:
			z.extractall(tmp_dir)
		
		candidate_db = None
		for db_file in tmp_dir.rglob("*.db"):
			if db_file.name == "owlin.db":
				candidate_db = db_file
				break
		
		if not candidate_db:
			raise ValueError("No database found in backup")
		
		current_db = DATA_DIR / "owlin.db"
		if not current_db.exists():
			raise ValueError("Current database not found")
		
		# Create backup of current DB
		backup_old = BACKUP_DIR / f"pre_restore_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"
		with zipfile.ZipFile(backup_old, "w", zipfile.ZIP_DEFLATED) as z:
			z.write(current_db, arcname="owlin.db")
		
		# Apply decisions
		apply_decisions_to_db(str(current_db), str(candidate_db), decisions)
		
		# Log the restore
		try:
			conn = sqlite3.connect(current_db)
			log_event(conn, "restore_applied", "database", "owlin.db", "DB replaced via recovery apply")
			conn.close()
		except Exception:
			pass  # Don't fail restore if logging fails
		
		return True
	finally:
		if tmp_dir.exists():
			shutil.rmtree(tmp_dir) 