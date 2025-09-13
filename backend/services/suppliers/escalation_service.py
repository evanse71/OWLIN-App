from __future__ import annotations
from datetime import datetime, timedelta
from uuid import uuid4
from sqlite3 import connect
import os

from ..services.audit import log_event

DB_PATH = os.path.join("data", "owlin.db")

# SLA thresholds in hours
SLA_HOURS = {1: 48, 2: 24, 3: 8}

# Valid state transitions
VALID_NEXT = {
	"OPEN": {"ACK", "IN_PROGRESS", "WAITING_VENDOR", "RESOLVED", "CLOSED"},
	"ACK": {"IN_PROGRESS", "WAITING_VENDOR", "RESOLVED", "CLOSED"},
	"IN_PROGRESS": {"WAITING_VENDOR", "RESOLVED", "CLOSED"},
	"WAITING_VENDOR": {"IN_PROGRESS", "RESOLVED", "CLOSED"},
	"RESOLVED": {"CLOSED"},
	"CLOSED": set()
}


def _get_conn():
	os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
	return connect(DB_PATH)


def _due_for_level(level: int) -> datetime:
	"""Calculate due date for escalation level."""
	return datetime.utcnow() + timedelta(hours=SLA_HOURS.get(level, 48))


def ensure_escalation_tables():
	"""Ensure escalation tables exist."""
	conn = _get_conn()
	cur = conn.cursor()
	
	# Escalations table
	cur.execute("""
	CREATE TABLE IF NOT EXISTS escalations (
		id TEXT PRIMARY KEY,
		supplier_id TEXT NOT NULL,
		venue_id TEXT NOT NULL,
		opened_by TEXT NOT NULL,
		assigned_to TEXT NULL,
		level INTEGER NOT NULL CHECK(level IN (1,2,3)) DEFAULT 1,
		status TEXT NOT NULL CHECK(status IN ('OPEN','ACK','IN_PROGRESS','WAITING_VENDOR','RESOLVED','CLOSED')) DEFAULT 'OPEN',
		title TEXT NOT NULL,
		description TEXT NULL,
		due_at TIMESTAMP NULL,
		created_at TIMESTAMP NOT NULL,
		updated_at TIMESTAMP NOT NULL
	)""")
	
	# Escalation notes table
	cur.execute("""
	CREATE TABLE IF NOT EXISTS escalation_notes (
		id TEXT PRIMARY KEY,
		escalation_id TEXT NOT NULL,
		author_id TEXT NOT NULL,
		body TEXT NOT NULL,
		created_at TIMESTAMP NOT NULL
	)""")
	
	# Create indexes
	cur.execute("CREATE INDEX IF NOT EXISTS idx_escalations_supplier ON escalations(supplier_id, status, due_at)")
	cur.execute("CREATE INDEX IF NOT EXISTS idx_escalations_venue ON escalations(venue_id, status)")
	cur.execute("CREATE INDEX IF NOT EXISTS idx_escalation_notes_eid ON escalation_notes(escalation_id, created_at)")
	
	conn.commit()
	conn.close()


def create_escalation(supplier_id: str, venue_id: str, opened_by: str, title: str, description: str = None, level: int = 1, assigned_to: str = None) -> dict:
	"""Create a new escalation."""
	ensure_escalation_tables()
	
	conn = _get_conn()
	cur = conn.cursor()
	
	now = datetime.utcnow()
	escalation_id = str(uuid4())
	due_at = _due_for_level(level)
	
	cur.execute("""
		INSERT INTO escalations (id, supplier_id, venue_id, opened_by, assigned_to, level, status, title, description, due_at, created_at, updated_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	""", (
		escalation_id,
		supplier_id,
		venue_id,
		opened_by,
		assigned_to,
		level,
		"OPEN",
		title,
		description,
		due_at.isoformat(),
		now.isoformat(),
		now.isoformat()
	))
	
	conn.commit()
	conn.close()
	
	# Log audit event
	log_event(None, "escalation_created", "supplier", supplier_id, f"L{level} {title}")
	
	return {
		"id": escalation_id,
		"supplier_id": supplier_id,
		"venue_id": venue_id,
		"opened_by": opened_by,
		"assigned_to": assigned_to,
		"level": level,
		"status": "OPEN",
		"title": title,
		"description": description,
		"due_at": due_at.isoformat(),
		"created_at": now.isoformat(),
		"updated_at": now.isoformat()
	}


def update_escalation(escalation_id: str, status: str = None, level: int = None, assigned_to: str = None, add_note: str = None, author_id: str = None) -> dict:
	"""Update an escalation with state machine validation."""
	ensure_escalation_tables()
	
	conn = _get_conn()
	cur = conn.cursor()
	
	# Get current escalation
	cur.execute("SELECT * FROM escalations WHERE id = ?", (escalation_id,))
	row = cur.fetchone()
	
	if not row:
		conn.close()
		raise ValueError("Escalation not found")
	
	escalation = {
		"id": row[0],
		"supplier_id": row[1],
		"venue_id": row[2],
		"opened_by": row[3],
		"assigned_to": row[4],
		"level": row[5],
		"status": row[6],
		"title": row[7],
		"description": row[8],
		"due_at": row[9],
		"created_at": row[10],
		"updated_at": row[11]
	}
	
	now = datetime.utcnow()
	updates = []
	params = []
	
	# Validate and apply updates
	if level is not None:
		if level not in (1, 2, 3):
			conn.close()
			raise ValueError("Invalid level")
		updates.append("level = ?")
		updates.append("due_at = ?")
		params.extend([level, _due_for_level(level).isoformat()])
		escalation["level"] = level
		escalation["due_at"] = _due_for_level(level).isoformat()
	
	if assigned_to is not None:
		updates.append("assigned_to = ?")
		params.append(assigned_to)
		escalation["assigned_to"] = assigned_to
	
	if status is not None:
		current_status = escalation["status"]
		if status not in VALID_NEXT.get(current_status, set()):
			conn.close()
			raise ValueError(f"Invalid transition {current_status}→{status}")
		
		updates.append("status = ?")
		params.append(status)
		escalation["status"] = status
	
	# Apply updates
	if updates:
		updates.append("updated_at = ?")
		params.append(now.isoformat())
		params.append(escalation_id)
		
		cur.execute(f"UPDATE escalations SET {', '.join(updates)} WHERE id = ?", params)
		escalation["updated_at"] = now.isoformat()
	
	# Add note if provided
	if add_note and author_id:
		note_id = str(uuid4())
		cur.execute("""
			INSERT INTO escalation_notes (id, escalation_id, author_id, body, created_at)
			VALUES (?, ?, ?, ?, ?)
		""", (note_id, escalation_id, author_id, add_note, now.isoformat()))
	
	conn.commit()
	conn.close()
	
	# Log audit event
	log_event(None, "escalation_updated", "supplier", escalation["supplier_id"], f"{escalation['status']}")
	
	return escalation


def get_escalation(escalation_id: str) -> dict:
	"""Get escalation with notes."""
	ensure_escalation_tables()
	
	conn = _get_conn()
	cur = conn.cursor()
	
	# Get escalation
	cur.execute("SELECT * FROM escalations WHERE id = ?", (escalation_id,))
	row = cur.fetchone()
	
	if not row:
		conn.close()
		return None
	
	escalation = {
		"id": row[0],
		"supplier_id": row[1],
		"venue_id": row[2],
		"opened_by": row[3],
		"assigned_to": row[4],
		"level": row[5],
		"status": row[6],
		"title": row[7],
		"description": row[8],
		"due_at": row[9],
		"created_at": row[10],
		"updated_at": row[11],
		"notes": []
	}
	
	# Get notes
	cur.execute("""
		SELECT id, author_id, body, created_at 
		FROM escalation_notes 
		WHERE escalation_id = ? 
		ORDER BY created_at
	""", (escalation_id,))
	
	for note_row in cur.fetchall():
		escalation["notes"].append({
			"id": note_row[0],
			"author_id": note_row[1],
			"body": note_row[2],
			"created_at": note_row[3]
		})
	
	conn.close()
	return escalation


def list_escalations(supplier_id: str = None, venue_id: str = None, status: str = None) -> list[dict]:
	"""List escalations with optional filtering."""
	ensure_escalation_tables()
	
	conn = _get_conn()
	cur = conn.cursor()
	
	query = "SELECT * FROM escalations WHERE 1=1"
	params = []
	
	if supplier_id:
		query += " AND supplier_id = ?"
		params.append(supplier_id)
	
	if venue_id:
		query += " AND venue_id = ?"
		params.append(venue_id)
	
	if status:
		query += " AND status = ?"
		params.append(status)
	
	query += " ORDER BY created_at DESC"
	
	cur.execute(query, params)
	escalations = []
	
	for row in cur.fetchall():
		escalations.append({
			"id": row[0],
			"supplier_id": row[1],
			"venue_id": row[2],
			"opened_by": row[3],
			"assigned_to": row[4],
			"level": row[5],
			"status": row[6],
			"title": row[7],
			"description": row[8],
			"due_at": row[9],
			"created_at": row[10],
			"updated_at": row[11]
		})
	
	conn.close()
	return escalations


def is_overdue(escalation: dict) -> bool:
	"""Check if escalation is overdue."""
	if not escalation.get("due_at"):
		return False
	
	due_at = datetime.fromisoformat(escalation["due_at"])
	return datetime.utcnow() > due_at and escalation["status"] not in ("RESOLVED", "CLOSED") 