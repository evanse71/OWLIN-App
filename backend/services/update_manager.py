from __future__ import annotations
import os
import shutil
import zipfile
import tempfile
import subprocess
import hashlib
import json
from pathlib import Path
from datetime import datetime
from uuid import uuid4
from typing import Optional, List, Tuple, Dict
from sqlite3 import connect
import os

try:
	from nacl.signing import VerifyKey
	from nacl.exceptions import BadSignatureError
	PYNACL_AVAILABLE = True
except ImportError:
	PYNACL_AVAILABLE = False
	VerifyKey = None
	BadSignatureError = Exception

# Constants
APP_ROOT = Path(__file__).parent.parent.parent
UPDATES_DIR = APP_ROOT / "updates"
BACKUPS_DIR = APP_ROOT / "backups"
PUBKEY_PATH = APP_ROOT / "backend" / "updates_pubkey_ed25519.hex"
DB_PATH = os.path.join(str(APP_ROOT), "data", "owlin.db")


def _get_conn():
	os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
	return connect(DB_PATH)


def ensure_update_tables():
	"""Ensure update-related tables exist."""
	conn = _get_conn()
	cur = conn.cursor()
	
	# Updates metadata table
	cur.execute("""
	CREATE TABLE IF NOT EXISTS updates_meta (
		id TEXT PRIMARY KEY,
		filename TEXT NOT NULL,
		version TEXT NOT NULL,
		build TEXT NOT NULL,
		created_at TIMESTAMP NOT NULL,
		verified TEXT CHECK (verified IN ('pending','ok','failed')) NOT NULL DEFAULT 'pending',
		reason TEXT NULL,
		checksum_sha256 TEXT NOT NULL,
		applied_at TIMESTAMP NULL,
		result TEXT NULL
	)""")
	
	# Rollback points table
	cur.execute("""
	CREATE TABLE IF NOT EXISTS rollback_points (
		id TEXT PRIMARY KEY,
		created_at TIMESTAMP NOT NULL,
		version_before TEXT NULL,
		backup_zip TEXT NOT NULL
	)""")
	
	# Changelog entries table
	cur.execute("""
	CREATE TABLE IF NOT EXISTS changelog_entries (
		id TEXT PRIMARY KEY,
		version TEXT NOT NULL,
		build TEXT NOT NULL,
		applied_at TIMESTAMP NOT NULL,
		status TEXT CHECK (status IN ('success','rollback','failed')) NOT NULL,
		notes TEXT NULL
	)""")
	
	# Update progress journal table
	cur.execute("""
	CREATE TABLE IF NOT EXISTS update_progress_journal (
		id TEXT PRIMARY KEY,
		job_id TEXT NOT NULL,
		kind TEXT NOT NULL,
		bundle_id TEXT NOT NULL,
		step TEXT NOT NULL,
		percent INTEGER NOT NULL,
		message TEXT,
		occurred_at TEXT NOT NULL
	)""")
	
	# Create indexes
	cur.execute("CREATE INDEX IF NOT EXISTS idx_updates_meta_ver ON updates_meta(version, build)")
	cur.execute("CREATE INDEX IF NOT EXISTS idx_changelog_ver ON changelog_entries(version, applied_at DESC)")
	cur.execute("CREATE INDEX IF NOT EXISTS idx_upj_job ON update_progress_journal(job_id, occurred_at)")
	
	conn.commit()
	conn.close()


def _digest_bundle(zip_path: str) -> bytes:
	"""Create deterministic digest of bundle contents."""
	with zipfile.ZipFile(zip_path, 'r') as z:
		manifest = z.read('manifest.json')
		names = sorted([n for n in z.namelist() if not n.endswith('/') and n != 'signature.sig'])
		catalog = "\n".join(f"{n}:{z.getinfo(n).file_size}" for n in names).encode('utf-8')
	
	h = hashlib.sha256()
	h.update(manifest)
	h.update(catalog)
	return h.digest()


def verify_signature(zip_path: str) -> Tuple[bool, str]:
	"""Verify Ed25519 signature of bundle."""
	if not PYNACL_AVAILABLE:
		return False, "PyNaCl not available"
	
	if not PUBKEY_PATH.exists():
		return False, "Public key not found"
	
	try:
		with open(PUBKEY_PATH, 'r') as f:
			pub_hex = f.read().strip()
		
		vk = VerifyKey(bytes.fromhex(pub_hex))
		
		with zipfile.ZipFile(zip_path, 'r') as z:
			sig = z.read('signature.sig')
		
		digest = _digest_bundle(zip_path)
		vk.verify(digest, sig)
		return True, "ok"
	except BadSignatureError:
		return False, "signature mismatch"
	except Exception as e:
		return False, f"verification error: {str(e)}"


def _space_ok(min_bytes: int = 200 * 1024 * 1024) -> bool:
	"""Check if sufficient disk space is available."""
	try:
		st = os.statvfs(".")
		return st.f_bavail * st.f_frsize >= min_bytes
	except:
		return True  # Assume OK if we can't check


def _create_snapshot() -> Path:
	"""Create atomic rollback snapshot."""
	BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
	
	timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
	out = BACKUPS_DIR / f"rollback_{timestamp}.zip"
	
	with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
		# Backup critical files and directories
		for rel in ["data/owlin.db", "backend", "frontend"]:
			p = APP_ROOT / rel
			if p.is_dir():
				for base, _, files in os.walk(p):
					for f in files:
						fp = Path(base) / f
						z.write(fp, arcname=str(fp.relative_to(APP_ROOT)))
			elif p.exists():
				z.write(p, arcname=str(p.relative_to(APP_ROOT)))
	
	return out


def preflight(zip_path: str) -> Tuple[bool, List[str]]:
	"""Run preflight checks before applying update."""
	reasons = []
	
	# Check disk space
	if not _space_ok():
		reasons.append("Insufficient disk space")
	
	# Verify signature
	ok, why = verify_signature(zip_path)
	if not ok:
		reasons.append(f"Signature: {why}")
	
	# Check if ZIP is valid
	try:
		with zipfile.ZipFile(zip_path, 'r') as z:
			if 'manifest.json' not in z.namelist():
				reasons.append("Missing manifest.json")
			if 'signature.sig' not in z.namelist():
				reasons.append("Missing signature.sig")
	except Exception as e:
		reasons.append(f"Invalid ZIP: {str(e)}")
	
	return len(reasons) == 0, reasons


def emit_progress(job_id: str, kind: str, bundle_id: str, step: str, percent: int, message: str = None):
	"""Emit progress tick to journal."""
	ensure_update_tables()
	conn = _get_conn()
	cur = conn.cursor()
	
	cur.execute("""
		INSERT INTO update_progress_journal (id, job_id, kind, bundle_id, step, percent, message, occurred_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)
	""", (
		str(uuid4()),
		job_id,
		kind,
		bundle_id,
		step,
		percent,
		message,
		datetime.utcnow().isoformat()
	))
	
	conn.commit()
	conn.close()


def get_progress(job_id: str) -> List[Dict]:
	"""Get progress ticks for a job."""
	ensure_update_tables()
	conn = _get_conn()
	cur = conn.cursor()
	
	cur.execute("""
		SELECT job_id, kind, bundle_id, step, percent, message, occurred_at
		FROM update_progress_journal 
		WHERE job_id = ? 
		ORDER BY occurred_at ASC
	""", (job_id,))
	
	ticks = []
	for row in cur.fetchall():
		ticks.append({
			"job_id": row[0],
			"kind": row[1],
			"bundle_id": row[2],
			"step": row[3],
			"percent": row[4],
			"message": row[5],
			"occurred_at": row[6]
		})
	
	conn.close()
	return ticks


def validate_bundle(bundle_id: str) -> Dict:
	"""Validate a specific bundle."""
	ensure_update_tables()
	
	conn = _get_conn()
	cur = conn.cursor()
	
	cur.execute("SELECT filename FROM updates_meta WHERE id = ?", (bundle_id,))
	row = cur.fetchone()
	
	if not row:
		return {
			"bundle_id": bundle_id,
			"filename": "",
			"version": "",
			"build": "",
			"signature_ok": False,
			"manifest_ok": False,
			"reason": "Bundle not found",
			"checksum_sha256": None,
			"created_at": None
		}
	
	filename = row[0]
	zip_path = UPDATES_DIR / filename
	
	if not zip_path.exists():
		return {
			"bundle_id": bundle_id,
			"filename": filename,
			"version": "",
			"build": "",
			"signature_ok": False,
			"manifest_ok": False,
			"reason": "Bundle file not found",
			"checksum_sha256": None,
			"created_at": None
		}
	
	# Validate signature
	signature_ok, signature_reason = verify_signature(str(zip_path))
	
	# Validate manifest
	manifest_ok = True
	manifest_reason = None
	version = ""
	build = ""
	created_at = None
	
	try:
		with zipfile.ZipFile(zip_path, 'r') as z:
			if 'manifest.json' in z.namelist():
				manifest = json.loads(z.read('manifest.json').decode('utf-8'))
				version = manifest.get("version", "")
				build = manifest.get("build", "")
				created_at = manifest.get("created_at")
				
				# Check required fields
				if not version:
					manifest_ok = False
					manifest_reason = "Missing version"
				elif not build:
					manifest_ok = False
					manifest_reason = "Missing build"
				elif "steps" not in manifest:
					manifest_ok = False
					manifest_reason = "Missing steps"
			else:
				manifest_ok = False
				manifest_reason = "Missing manifest.json"
	except Exception as e:
		manifest_ok = False
		manifest_reason = f"Invalid manifest: {str(e)}"
	
	# Compute checksum
	checksum = hashlib.sha256(zip_path.read_bytes()).hexdigest()
	
	# Update metadata
	status = "ok" if (signature_ok and manifest_ok) else "failed"
	reason = "; ".join(filter(None, [signature_reason if not signature_ok else None, manifest_reason if not manifest_ok else None]))
	
	cur.execute("""
		UPDATE updates_meta SET verified = ?, reason = ? WHERE id = ?
	""", (status, reason, bundle_id))
	
	conn.commit()
	conn.close()
	
	return {
		"bundle_id": bundle_id,
		"filename": filename,
		"version": version,
		"build": build,
		"signature_ok": signature_ok,
		"manifest_ok": manifest_ok,
		"reason": reason if reason else None,
		"checksum_sha256": checksum,
		"created_at": created_at
	}


def compute_dependencies(bundle_id: str) -> Dict:
	"""Compute dependencies for a bundle."""
	ensure_update_tables()
	
	conn = _get_conn()
	cur = conn.cursor()
	
	cur.execute("SELECT filename FROM updates_meta WHERE id = ?", (bundle_id,))
	row = cur.fetchone()
	
	if not row:
		return {
			"bundle_id": bundle_id,
			"items": [],
			"all_satisfied": False
		}
	
	filename = row[0]
	zip_path = UPDATES_DIR / filename
	
	if not zip_path.exists():
		return {
			"bundle_id": bundle_id,
			"items": [],
			"all_satisfied": False
		}
	
	items = []
	all_satisfied = True
	
	try:
		with zipfile.ZipFile(zip_path, 'r') as z:
			if 'manifest.json' in z.namelist():
				manifest = json.loads(z.read('manifest.json').decode('utf-8'))
				
				# Check app version requirement
				if "requires_app" in manifest:
					required_version = manifest["requires_app"]
					current_version = "1.0.0"  # TODO: Get from actual app version
					
					# Simple version comparison (can be enhanced)
					satisfied = True
					reason = f"current {current_version}"
					
					if required_version.startswith(">="):
						min_version = required_version[3:]
						if current_version < min_version:
							satisfied = False
							reason = f"current {current_version} < required {min_version}"
					
					items.append({
						"id": "app",
						"version": required_version,
						"satisfied": satisfied,
						"reason": reason
					})
					
					if not satisfied:
						all_satisfied = False
				
				# Check schema version requirement
				if "min_schema_version" in manifest:
					required_schema = manifest["min_schema_version"]
					current_schema = 8  # TODO: Get from actual database schema version
					
					satisfied = current_schema >= required_schema
					reason = f"current {current_schema}"
					
					if not satisfied:
						reason = f"current {current_schema} < required {required_schema}"
					
					items.append({
						"id": "schema",
						"version": f">={required_schema}",
						"satisfied": satisfied,
						"reason": reason
					})
					
					if not satisfied:
						all_satisfied = False
	except Exception as e:
		items.append({
			"id": "manifest",
			"version": "unknown",
			"satisfied": False,
			"reason": f"Error reading manifest: {str(e)}"
		})
		all_satisfied = False
	
	conn.close()
	return {
		"bundle_id": bundle_id,
		"items": items,
		"all_satisfied": all_satisfied
	}


def apply_update(zip_path: str) -> Dict:
	"""Apply update with atomic rollback capability and progress tracking."""
	ensure_update_tables()
	
	# Generate job ID
	job_id = str(uuid4())
	
	# Get bundle ID from filename
	bundle_id = Path(zip_path).stem
	
	# Preflight checks
	emit_progress(job_id, "apply", bundle_id, "preflight", 10, "Running preflight checks")
	ok, reasons = preflight(zip_path)
	if not ok:
		emit_progress(job_id, "apply", bundle_id, "error", 100, f"Preflight failed: {'; '.join(reasons)}")
		return {"ok": False, "reasons": reasons, "job_id": job_id}
	
	# Create rollback snapshot
	emit_progress(job_id, "apply", bundle_id, "snapshot", 30, "Creating rollback snapshot")
	snapshot_path = _create_snapshot()
	
	try:
		# Extract bundle
		emit_progress(job_id, "apply", bundle_id, "apply", 50, "Extracting update bundle")
		work = Path(tempfile.mkdtemp(prefix="owlin_update_"))
		with zipfile.ZipFile(zip_path, 'r') as z:
			z.extractall(work)
		
		# Parse manifest
		manifest = json.loads((work / "manifest.json").read_text())
		
		# Execute steps
		emit_progress(job_id, "apply", bundle_id, "apply", 70, "Applying update steps")
		for step in manifest.get("steps", []):
			action = step["action"]
			
			if action == "alembic_upgrade":
				revision = step.get("revision", "head")
				subprocess.check_call(["alembic", "upgrade", revision], cwd=str(APP_ROOT))
			
			elif action == "copy_tree":
				src = work / step["from_path"]
				dst = APP_ROOT / step["to_path"]
				mode = step.get("mode", "merge")
				
				if mode == "replace" and dst.exists():
					shutil.rmtree(dst)
				
				shutil.copytree(src, dst, dirs_exist_ok=True)
			
			elif action == "run_hook":
				hook_path = work / step["path"]
				timeout = step.get("timeout_sec", 120)
				subprocess.check_call(["python", str(hook_path)], timeout=timeout)
		
		# Record success
		emit_progress(job_id, "apply", bundle_id, "finalise", 90, "Finalizing update")
		conn = _get_conn()
		cur = conn.cursor()
		
		changelog_id = str(uuid4())
		cur.execute("""
			INSERT INTO changelog_entries (id, version, build, applied_at, status, notes)
			VALUES (?, ?, ?, ?, ?, ?)
		""", (
			changelog_id,
			manifest.get("version", "unknown"),
			manifest.get("build", "unknown"),
			datetime.utcnow().isoformat(),
			"success",
			manifest.get("description", "")
		))
		
		conn.commit()
		conn.close()
		
		emit_progress(job_id, "apply", bundle_id, "done", 100, "Update completed successfully")
		
		return {
			"ok": True,
			"snapshot": str(snapshot_path),
			"changelog_id": changelog_id,
			"job_id": job_id
		}
		
	except Exception as e:
		# Rollback on failure
		emit_progress(job_id, "apply", bundle_id, "error", 100, f"Update failed: {str(e)}")
		try:
			rollback_to(str(snapshot_path))
		except:
			pass  # Rollback failed, but we tried
		
		# Record failure
		conn = _get_conn()
		cur = conn.cursor()
		
		cur.execute("""
			INSERT INTO changelog_entries (id, version, build, applied_at, status, notes)
			VALUES (?, ?, ?, ?, ?, ?)
		""", (
			str(uuid4()),
			manifest.get("version", "unknown") if 'manifest' in locals() else "unknown",
			manifest.get("build", "unknown") if 'manifest' in locals() else "unknown",
			datetime.utcnow().isoformat(),
			"failed",
			f"Error: {str(e)}"
		))
		
		conn.commit()
		conn.close()
		
		return {"ok": False, "reasons": [str(e)], "job_id": job_id}


def rollback_to(snapshot_zip: str) -> bool:
	"""Rollback to a previous snapshot."""
	try:
		with zipfile.ZipFile(snapshot_zip, 'r') as z:
			z.extractall(APP_ROOT)
		return True
	except Exception:
		return False


def list_available_updates() -> List[Dict]:
	"""List available update bundles."""
	ensure_update_tables()
	
	updates = []
	UPDATES_DIR.mkdir(exist_ok=True)
	
	for zip_file in UPDATES_DIR.glob("*.zip"):
		try:
			with zipfile.ZipFile(zip_file, 'r') as z:
				if 'manifest.json' in z.namelist():
					manifest = json.loads(z.read('manifest.json').decode('utf-8'))
					
					# Check if we have metadata for this file
					conn = _get_conn()
					cur = conn.cursor()
					
					cur.execute("""
						SELECT id, verified, reason FROM updates_meta 
						WHERE filename = ?
					""", (zip_file.name,))
					
					row = cur.fetchone()
					if row:
						update_id, verified, reason = row
					else:
						# Create new metadata entry
						update_id = str(uuid4())
						cur.execute("""
							INSERT INTO updates_meta (id, filename, version, build, created_at, checksum_sha256)
							VALUES (?, ?, ?, ?, ?, ?)
						""", (
							update_id,
							zip_file.name,
							manifest.get("version", "unknown"),
							manifest.get("build", "unknown"),
							manifest.get("created_at", datetime.utcnow().isoformat()),
							hashlib.sha256(zip_file.read_bytes()).hexdigest()
						))
						verified = "pending"
						reason = None
						conn.commit()
					
					conn.close()
					
					updates.append({
						"id": update_id,
						"filename": zip_file.name,
						"version": manifest.get("version", "unknown"),
						"build": manifest.get("build", "unknown"),
						"created_at": manifest.get("created_at", datetime.utcnow().isoformat()),
						"description": manifest.get("description"),
						"verified": verified,
						"reason": reason
					})
		except Exception as e:
			# Skip invalid bundles
			continue
	
	return updates


def verify_bundle(bundle_id: str) -> Dict:
	"""Verify a specific bundle."""
	ensure_update_tables()
	
	conn = _get_conn()
	cur = conn.cursor()
	
	cur.execute("SELECT filename FROM updates_meta WHERE id = ?", (bundle_id,))
	row = cur.fetchone()
	
	if not row:
		return {"ok": False, "reason": "Bundle not found"}
	
	filename = row[0]
	zip_path = UPDATES_DIR / filename
	
	if not zip_path.exists():
		return {"ok": False, "reason": "Bundle file not found"}
	
	# Run verification
	ok, reasons = preflight(str(zip_path))
	
	# Update metadata
	status = "ok" if ok else "failed"
	reason = "; ".join(reasons) if reasons else None
	
	cur.execute("""
		UPDATE updates_meta SET verified = ?, reason = ? WHERE id = ?
	""", (status, reason, bundle_id))
	
	conn.commit()
	conn.close()
	
	return {
		"ok": ok,
		"verified": status,
		"reason": reason
	}


def get_changelog() -> List[Dict]:
	"""Get changelog entries."""
	ensure_update_tables()
	
	conn = _get_conn()
	cur = conn.cursor()
	
	cur.execute("""
		SELECT id, version, build, applied_at, status, notes 
		FROM changelog_entries 
		ORDER BY applied_at DESC
	""")
	
	entries = []
	for row in cur.fetchall():
		entries.append({
			"id": row[0],
			"version": row[1],
			"build": row[2],
			"applied_at": row[3],
			"status": row[4],
			"notes": row[5]
		})
	
	conn.close()
	return entries
