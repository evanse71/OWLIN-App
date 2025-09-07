from __future__ import annotations
from datetime import datetime
from uuid import uuid4
from sqlite3 import connect
import os
import json
import shutil
from typing import Optional, Dict, Any

DB_PATH = os.path.join("data", "owlin.db")


def _get_conn():
	os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
	return connect(DB_PATH)


def ensure_recovery_tables():
	"""Ensure recovery mode tables exist."""
	conn = _get_conn()
	cur = conn.cursor()
	
	# Recovery mode status table
	cur.execute("""
	CREATE TABLE IF NOT EXISTS recovery_mode (
		id TEXT PRIMARY KEY,
		active BOOLEAN NOT NULL DEFAULT FALSE,
		reason TEXT NULL,
		activated_at TIMESTAMP NULL,
		activated_by TEXT NULL
	)""")
	
	# Recovery snapshots table
	cur.execute("""
	CREATE TABLE IF NOT EXISTS recovery_snapshots (
		id TEXT PRIMARY KEY,
		created_at TIMESTAMP NOT NULL,
		created_by TEXT NOT NULL,
		reason TEXT NULL,
		snapshot_path TEXT NOT NULL,
		metadata TEXT NULL
	)""")
	
	conn.commit()
	conn.close()


def activate_recovery_mode(reason: str, activated_by: str) -> Dict[str, Any]:
	"""Activate recovery mode and lock the application."""
	ensure_recovery_tables()
	
	conn = _get_conn()
	cur = conn.cursor()
	
	# Check if already active
	cur.execute("SELECT active FROM recovery_mode WHERE id = 'current'")
	row = cur.fetchone()
	
	if row and row[0]:
		conn.close()
		return {
			"success": False,
			"message": "Recovery mode is already active"
		}
	
	# Create or update recovery mode status
	now = datetime.utcnow().isoformat()
	cur.execute("""
		INSERT OR REPLACE INTO recovery_mode (id, active, reason, activated_at, activated_by)
		VALUES ('current', TRUE, ?, ?, ?)
	""", (reason, now, activated_by))
	
	conn.commit()
	conn.close()
	
	return {
		"success": True,
		"message": "Recovery mode activated",
		"activated_at": now,
		"reason": reason
	}


def deactivate_recovery_mode(deactivated_by: str) -> Dict[str, Any]:
	"""Deactivate recovery mode and unlock the application."""
	ensure_recovery_tables()
	
	conn = _get_conn()
	cur = conn.cursor()
	
	# Check if active
	cur.execute("SELECT active FROM recovery_mode WHERE id = 'current'")
	row = cur.fetchone()
	
	if not row or not row[0]:
		conn.close()
		return {
			"success": False,
			"message": "Recovery mode is not active"
		}
	
	# Deactivate recovery mode
	cur.execute("""
		UPDATE recovery_mode 
		SET active = FALSE 
		WHERE id = 'current'
	""")
	
	conn.commit()
	conn.close()
	
	return {
		"success": True,
		"message": "Recovery mode deactivated"
	}


def get_recovery_status() -> Dict[str, Any]:
	"""Get current recovery mode status."""
	ensure_recovery_tables()
	
	conn = _get_conn()
	cur = conn.cursor()
	
	cur.execute("""
		SELECT active, reason, activated_at, activated_by
		FROM recovery_mode 
		WHERE id = 'current'
	""")
	
	row = cur.fetchone()
	conn.close()
	
	if not row:
		return {
			"active": False,
			"reason": None,
			"activated_at": None,
			"activated_by": None
		}
	
	active, reason, activated_at, activated_by = row
	
	return {
		"active": bool(active),
		"reason": reason,
		"activated_at": activated_at,
		"activated_by": activated_by
	}


def create_snapshot(created_by: str, reason: str = None) -> Dict[str, Any]:
	"""Create a database snapshot for rollback purposes."""
	ensure_recovery_tables()
	
	# Create snapshots directory
	snapshots_dir = os.path.join("data", "snapshots")
	os.makedirs(snapshots_dir, exist_ok=True)
	
	# Generate snapshot filename
	timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
	snapshot_id = str(uuid4())
	snapshot_filename = f"snapshot_{timestamp}_{snapshot_id}.db"
	snapshot_path = os.path.join(snapshots_dir, snapshot_filename)
	
	# Copy current database
	try:
		shutil.copy2(DB_PATH, snapshot_path)
	except Exception as e:
		return {
			"success": False,
			"message": f"Failed to create snapshot: {str(e)}"
		}
	
	# Record snapshot in database
	conn = _get_conn()
	cur = conn.cursor()
	
	now = datetime.utcnow().isoformat()
	metadata = {
		"original_db_size": os.path.getsize(DB_PATH),
		"snapshot_size": os.path.getsize(snapshot_path),
		"tables": get_table_list()
	}
	
	cur.execute("""
		INSERT INTO recovery_snapshots (id, created_at, created_by, reason, snapshot_path, metadata)
		VALUES (?, ?, ?, ?, ?, ?)
	""", (snapshot_id, now, created_by, reason, snapshot_path, json.dumps(metadata)))
	
	conn.commit()
	conn.close()
	
	return {
		"success": True,
		"snapshot_id": snapshot_id,
		"snapshot_path": snapshot_path,
		"created_at": now,
		"size": os.path.getsize(snapshot_path)
	}


def rollback_to_snapshot(snapshot_id: str, rolled_back_by: str) -> Dict[str, Any]:
	"""Rollback database to a specific snapshot."""
	ensure_recovery_tables()
	
	conn = _get_conn()
	cur = conn.cursor()
	
	# Get snapshot details
	cur.execute("""
		SELECT snapshot_path, created_at, reason
		FROM recovery_snapshots 
		WHERE id = ?
	""", (snapshot_id,))
	
	row = cur.fetchone()
	if not row:
		conn.close()
		return {
			"success": False,
			"message": "Snapshot not found"
		}
	
	snapshot_path, created_at, reason = row
	conn.close()
	
	# Verify snapshot file exists
	if not os.path.exists(snapshot_path):
		return {
			"success": False,
			"message": "Snapshot file not found"
		}
	
	# Create backup of current database
	backup_path = f"{DB_PATH}.backup.{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
	try:
		shutil.copy2(DB_PATH, backup_path)
	except Exception as e:
		return {
			"success": False,
			"message": f"Failed to create backup: {str(e)}"
		}
	
	# Restore from snapshot
	try:
		shutil.copy2(snapshot_path, DB_PATH)
	except Exception as e:
		# Try to restore from backup
		try:
			shutil.copy2(backup_path, DB_PATH)
		except:
			pass
		
		return {
			"success": False,
			"message": f"Failed to restore snapshot: {str(e)}"
		}
	
	return {
		"success": True,
		"message": "Database rolled back successfully",
		"snapshot_id": snapshot_id,
		"backup_path": backup_path,
		"rolled_back_at": datetime.utcnow().isoformat()
	}


def list_snapshots() -> list[Dict[str, Any]]:
	"""List all available snapshots."""
	ensure_recovery_tables()
	
	conn = _get_conn()
	cur = conn.cursor()
	
	cur.execute("""
		SELECT id, created_at, created_by, reason, snapshot_path, metadata
		FROM recovery_snapshots
		ORDER BY created_at DESC
	""")
	
	snapshots = []
	for row in cur.fetchall():
		snapshot_id, created_at, created_by, reason, snapshot_path, metadata_json = row
		
		# Check if snapshot file still exists
		file_exists = os.path.exists(snapshot_path)
		file_size = os.path.getsize(snapshot_path) if file_exists else 0
		
		metadata = json.loads(metadata_json) if metadata_json else {}
		
		snapshots.append({
			"id": snapshot_id,
			"created_at": created_at,
			"created_by": created_by,
			"reason": reason,
			"snapshot_path": snapshot_path,
			"file_exists": file_exists,
			"file_size": file_size,
			"metadata": metadata
		})
	
	conn.close()
	return snapshots


def get_table_list() -> list[str]:
	"""Get list of tables in the database."""
	conn = _get_conn()
	cur = conn.cursor()
	
	cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
	tables = [row[0] for row in cur.fetchall()]
	
	conn.close()
	return tables


def check_database_integrity() -> Dict[str, Any]:
	"""Check database integrity using SQLite PRAGMA commands."""
	conn = _get_conn()
	cur = conn.cursor()
	
	# Check integrity
	cur.execute("PRAGMA integrity_check")
	integrity_result = cur.fetchone()
	
	# Check foreign keys
	cur.execute("PRAGMA foreign_key_check")
	foreign_key_errors = cur.fetchall()
	
	# Check for corruption
	cur.execute("PRAGMA quick_check")
	quick_check_result = cur.fetchone()
	
	conn.close()
	
	integrity_ok = integrity_result[0] == "ok" if integrity_result else False
	quick_check_ok = quick_check_result[0] == "ok" if quick_check_result else False
	
	return {
		"integrity_check": integrity_ok,
		"quick_check": quick_check_ok,
		"foreign_key_errors": len(foreign_key_errors),
		"overall_healthy": integrity_ok and quick_check_ok and len(foreign_key_errors) == 0,
		"details": {
			"integrity_result": integrity_result[0] if integrity_result else "unknown",
			"quick_check_result": quick_check_result[0] if quick_check_result else "unknown",
			"foreign_key_details": foreign_key_errors
		}
	}


def should_activate_recovery_mode() -> Dict[str, Any]:
	"""Determine if recovery mode should be activated based on system health."""
	# Check database integrity
	integrity = check_database_integrity()
	
	# Check for conflicts
	from .conflict_detector import run_conflict_detection
	conflicts = run_conflict_detection()
	
	# Determine if recovery mode should be activated
	should_activate = False
	reasons = []
	
	if not integrity["overall_healthy"]:
		should_activate = True
		reasons.append("Database integrity issues detected")
	
	if len(conflicts) > 10:  # Threshold for critical conflict count
		should_activate = True
		reasons.append(f"Critical number of conflicts detected: {len(conflicts)}")
	
	# Check for schema conflicts specifically
	schema_conflicts = [c for c in conflicts if c.get('conflict_type') == 'schema']
	if len(schema_conflicts) > 0:
		should_activate = True
		reasons.append(f"Schema conflicts detected: {len(schema_conflicts)}")
	
	return {
		"should_activate": should_activate,
		"reasons": reasons,
		"integrity_check": integrity,
		"conflict_count": len(conflicts),
		"schema_conflict_count": len(schema_conflicts)
	} 