from __future__ import annotations
from datetime import datetime
from uuid import uuid4
from sqlite3 import connect
import os
import json
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join("data", "owlin.db")


def _get_conn():
	os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
	return connect(DB_PATH)


def ensure_conflict_tables():
	"""Ensure conflict logging tables exist."""
	conn = _get_conn()
	cur = conn.cursor()
	
	# Conflict logs table
	cur.execute("""
	CREATE TABLE IF NOT EXISTS conflict_logs (
		id TEXT PRIMARY KEY,
		table_name TEXT NOT NULL,
		conflict_type TEXT NOT NULL CHECK(conflict_type IN ('schema', 'row', 'cell')),
		detected_at TIMESTAMP NOT NULL,
		details TEXT NOT NULL
	)""")
	
	# Conflict resolutions table
	cur.execute("""
	CREATE TABLE IF NOT EXISTS conflict_resolutions (
		id TEXT PRIMARY KEY,
		conflict_id TEXT NOT NULL,
		action TEXT NOT NULL CHECK(action IN ('applied', 'rolled_back', 'ignored')),
		resolved_by TEXT NOT NULL,
		resolved_at TIMESTAMP NOT NULL,
		notes TEXT NULL
	)""")
	
	# Recovery mode status table
	cur.execute("""
	CREATE TABLE IF NOT EXISTS recovery_mode (
		id TEXT PRIMARY KEY,
		active BOOLEAN NOT NULL DEFAULT FALSE,
		reason TEXT NULL,
		activated_at TIMESTAMP NULL,
		activated_by TEXT NULL
	)""")
	
	# Create indexes
	cur.execute("CREATE INDEX IF NOT EXISTS idx_conflict_logs_table ON conflict_logs(table_name, detected_at)")
	cur.execute("CREATE INDEX IF NOT EXISTS idx_conflict_resolutions_conflict ON conflict_resolutions(conflict_id)")
	
	conn.commit()
	conn.close()


def detect_schema_conflicts() -> List[Dict[str, Any]]:
	"""Detect schema-level conflicts between expected and actual database schema."""
	conn = _get_conn()
	cur = conn.cursor()
	
	conflicts = []
	
	# Expected schema (from our application)
	expected_tables = {
		'invoices': [
			('id', 'TEXT', 'PRIMARY KEY'),
			('supplier_id', 'TEXT', 'NOT NULL'),
			('venue_id', 'TEXT', 'NOT NULL'),
			('invoice_date', 'DATE', 'NOT NULL'),
			('total_amount_pennies', 'INTEGER', 'NOT NULL'),
			('ocr_confidence', 'REAL', 'NULL')
		],
		'delivery_notes': [
			('id', 'TEXT', 'PRIMARY KEY'),
			('supplier_id', 'TEXT', 'NOT NULL'),
			('venue_id', 'TEXT', 'NOT NULL'),
			('date', 'DATE', 'NOT NULL'),
			('expected_date', 'DATE', 'NULL'),
			('status', 'TEXT', 'NULL')
		],
		'flagged_issues': [
			('id', 'TEXT', 'PRIMARY KEY'),
			('supplier_id', 'TEXT', 'NOT NULL'),
			('venue_id', 'TEXT', 'NOT NULL'),
			('type', 'TEXT', 'NOT NULL'),
			('status', 'TEXT', 'NOT NULL'),
			('description', 'TEXT', 'NULL'),
			('created_at', 'TIMESTAMP', 'NOT NULL')
		],
		'escalations': [
			('id', 'TEXT', 'PRIMARY KEY'),
			('supplier_id', 'TEXT', 'NOT NULL'),
			('venue_id', 'TEXT', 'NOT NULL'),
			('level', 'INTEGER', 'NOT NULL'),
			('status', 'TEXT', 'NOT NULL'),
			('title', 'TEXT', 'NOT NULL'),
			('description', 'TEXT', 'NULL'),
			('due_at', 'TIMESTAMP', 'NULL'),
			('created_at', 'TIMESTAMP', 'NOT NULL'),
			('updated_at', 'TIMESTAMP', 'NOT NULL')
		]
	}
	
	# Check each expected table
	for table_name, expected_columns in expected_tables.items():
		# Check if table exists
		cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
		if not cur.fetchone():
			conflicts.append({
				'table_name': table_name,
				'conflict_type': 'schema',
				'issue': 'missing_table',
				'expected': f"Table {table_name} should exist",
				'actual': f"Table {table_name} not found"
			})
			continue
		
		# Check table schema
		cur.execute(f"PRAGMA table_info({table_name})")
		actual_columns = cur.fetchall()
		
		# Compare columns
		expected_col_names = {col[0] for col in expected_columns}
		actual_col_names = {col[1] for col in actual_columns}
		
		missing_cols = expected_col_names - actual_col_names
		extra_cols = actual_col_names - expected_col_names
		
		if missing_cols:
			conflicts.append({
				'table_name': table_name,
				'conflict_type': 'schema',
				'issue': 'missing_columns',
				'expected': f"Columns: {', '.join(expected_col_names)}",
				'actual': f"Missing: {', '.join(missing_cols)}"
			})
		
		if extra_cols:
			conflicts.append({
				'table_name': table_name,
				'conflict_type': 'schema',
				'issue': 'extra_columns',
				'expected': f"Columns: {', '.join(expected_col_names)}",
				'actual': f"Extra: {', '.join(extra_cols)}"
			})
	
	conn.close()
	return conflicts


def detect_row_conflicts() -> List[Dict[str, Any]]:
	"""Detect row-level conflicts (orphaned records, missing foreign keys)."""
	conn = _get_conn()
	cur = conn.cursor()
	
	conflicts = []
	
	# Check for orphaned delivery notes (no matching invoice)
	cur.execute("""
		SELECT COUNT(*) FROM delivery_notes dn
		LEFT JOIN invoices i ON dn.supplier_id = i.supplier_id AND dn.venue_id = i.venue_id
		WHERE i.id IS NULL
	""")
	orphaned_deliveries = cur.fetchone()[0]
	
	if orphaned_deliveries > 0:
		conflicts.append({
			'table_name': 'delivery_notes',
			'conflict_type': 'row',
			'issue': 'orphaned_records',
			'count': orphaned_deliveries,
			'description': f"{orphaned_deliveries} delivery notes without matching invoices"
		})
	
	# Check for orphaned escalation notes
	cur.execute("""
		SELECT COUNT(*) FROM escalation_notes en
		LEFT JOIN escalations e ON en.escalation_id = e.id
		WHERE e.id IS NULL
	""")
	orphaned_notes = cur.fetchone()[0]
	
	if orphaned_notes > 0:
		conflicts.append({
			'table_name': 'escalation_notes',
			'conflict_type': 'row',
			'issue': 'orphaned_records',
			'count': orphaned_notes,
			'description': f"{orphaned_notes} escalation notes without parent escalation"
		})
	
	# Check for duplicate primary keys (shouldn't happen but worth checking)
	cur.execute("""
		SELECT table_name FROM (
			SELECT 'invoices' as table_name, id, COUNT(*) as cnt FROM invoices GROUP BY id HAVING cnt > 1
			UNION ALL
			SELECT 'delivery_notes' as table_name, id, COUNT(*) as cnt FROM delivery_notes GROUP BY id HAVING cnt > 1
			UNION ALL
			SELECT 'flagged_issues' as table_name, id, COUNT(*) as cnt FROM flagged_issues GROUP BY id HAVING cnt > 1
			UNION ALL
			SELECT 'escalations' as table_name, id, COUNT(*) as cnt FROM escalations GROUP BY id HAVING cnt > 1
		)
	""")
	duplicate_tables = cur.fetchall()
	
	for table_row in duplicate_tables:
		conflicts.append({
			'table_name': table_row[0],
			'conflict_type': 'row',
			'issue': 'duplicate_primary_keys',
			'description': f"Duplicate primary keys found in {table_row[0]}"
		})
	
	conn.close()
	return conflicts


def detect_cell_conflicts() -> List[Dict[str, Any]]:
	"""Detect cell-level conflicts (invalid data, constraint violations)."""
	conn = _get_conn()
	cur = conn.cursor()
	
	conflicts = []
	
	# Check for invalid escalation levels
	cur.execute("""
		SELECT COUNT(*) FROM escalations 
		WHERE level NOT IN (1, 2, 3)
	""")
	invalid_levels = cur.fetchone()[0]
	
	if invalid_levels > 0:
		conflicts.append({
			'table_name': 'escalations',
			'conflict_type': 'cell',
			'issue': 'invalid_escalation_level',
			'count': invalid_levels,
			'description': f"{invalid_levels} escalations with invalid level (should be 1, 2, or 3)"
		})
	
	# Check for invalid escalation statuses
	cur.execute("""
		SELECT COUNT(*) FROM escalations 
		WHERE status NOT IN ('OPEN', 'ACK', 'IN_PROGRESS', 'WAITING_VENDOR', 'RESOLVED', 'CLOSED')
	""")
	invalid_statuses = cur.fetchone()[0]
	
	if invalid_statuses > 0:
		conflicts.append({
			'table_name': 'escalations',
			'conflict_type': 'cell',
			'issue': 'invalid_escalation_status',
			'count': invalid_statuses,
			'description': f"{invalid_statuses} escalations with invalid status"
		})
	
	# Check for negative amounts
	cur.execute("""
		SELECT COUNT(*) FROM invoices 
		WHERE total_amount_pennies < 0
	""")
	negative_amounts = cur.fetchone()[0]
	
	if negative_amounts > 0:
		conflicts.append({
			'table_name': 'invoices',
			'conflict_type': 'cell',
			'issue': 'negative_amounts',
			'count': negative_amounts,
			'description': f"{negative_amounts} invoices with negative amounts"
		})
	
	# Check for invalid OCR confidence values
	cur.execute("""
		SELECT COUNT(*) FROM invoices 
		WHERE ocr_confidence < 0 OR ocr_confidence > 100
	""")
	invalid_confidence = cur.fetchone()[0]
	
	if invalid_confidence > 0:
		conflicts.append({
			'table_name': 'invoices',
			'conflict_type': 'cell',
			'issue': 'invalid_ocr_confidence',
			'count': invalid_confidence,
			'description': f"{invalid_confidence} invoices with invalid OCR confidence (should be 0-100)"
		})
	
	conn.close()
	return conflicts


def run_conflict_detection() -> List[Dict[str, Any]]:
	"""Run all conflict detection checks."""
	ensure_conflict_tables()
	
	all_conflicts = []
	
	# Schema conflicts
	schema_conflicts = detect_schema_conflicts()
	all_conflicts.extend(schema_conflicts)
	
	# Row conflicts
	row_conflicts = detect_row_conflicts()
	all_conflicts.extend(row_conflicts)
	
	# Cell conflicts
	cell_conflicts = detect_cell_conflicts()
	all_conflicts.extend(cell_conflicts)
	
	# Log conflicts to database
	conn = _get_conn()
	cur = conn.cursor()
	
	for conflict in all_conflicts:
		conflict_id = str(uuid4())
		cur.execute("""
			INSERT INTO conflict_logs (id, table_name, conflict_type, detected_at, details)
			VALUES (?, ?, ?, ?, ?)
		""", (
			conflict_id,
			conflict['table_name'],
			conflict['conflict_type'],
			datetime.utcnow().isoformat(),
			json.dumps(conflict)
		))
	
	conn.commit()
	conn.close()
	
	return all_conflicts


def get_conflict_summary(conflict: Dict[str, Any]) -> str:
	"""Generate a human-readable summary of a conflict."""
	conflict_type = conflict.get('conflict_type', 'unknown')
	table_name = conflict.get('table_name', 'unknown')
	issue = conflict.get('issue', 'unknown')
	
	if conflict_type == 'schema':
		if issue == 'missing_table':
			return f"Missing table: {table_name}"
		elif issue == 'missing_columns':
			return f"Missing columns in {table_name}"
		elif issue == 'extra_columns':
			return f"Extra columns in {table_name}"
	elif conflict_type == 'row':
		if issue == 'orphaned_records':
			count = conflict.get('count', 0)
			return f"{count} orphaned records in {table_name}"
		elif issue == 'duplicate_primary_keys':
			return f"Duplicate primary keys in {table_name}"
	elif conflict_type == 'cell':
		count = conflict.get('count', 0)
		if issue == 'invalid_escalation_level':
			return f"{count} invalid escalation levels in {table_name}"
		elif issue == 'invalid_escalation_status':
			return f"{count} invalid escalation statuses in {table_name}"
		elif issue == 'negative_amounts':
			return f"{count} negative amounts in {table_name}"
		elif issue == 'invalid_ocr_confidence':
			return f"{count} invalid OCR confidence values in {table_name}"
	
	return f"Unknown conflict in {table_name}"


def list_conflicts(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
	"""List conflicts with pagination."""
	ensure_conflict_tables()
	
	conn = _get_conn()
	cur = conn.cursor()
	
	cur.execute("""
		SELECT cl.id, cl.table_name, cl.conflict_type, cl.detected_at, cl.details,
		       CASE WHEN cr.id IS NOT NULL THEN 1 ELSE 0 END as resolved
		FROM conflict_logs cl
		LEFT JOIN conflict_resolutions cr ON cl.id = cr.conflict_id
		ORDER BY cl.detected_at DESC
		LIMIT ? OFFSET ?
	""", (limit, offset))
	
	conflicts = []
	for row in cur.fetchall():
		conflict_id, table_name, conflict_type, detected_at, details_json, resolved = row
		details = json.loads(details_json)
		
		conflicts.append({
			'id': conflict_id,
			'table_name': table_name,
			'conflict_type': conflict_type,
			'detected_at': detected_at,
			'resolved': bool(resolved),
			'summary': get_conflict_summary(details),
			'details': details
		})
	
	conn.close()
	return conflicts


def get_conflict(conflict_id: str) -> Optional[Dict[str, Any]]:
	"""Get a specific conflict by ID."""
	ensure_conflict_tables()
	
	conn = _get_conn()
	cur = conn.cursor()
	
	cur.execute("""
		SELECT id, table_name, conflict_type, detected_at, details
		FROM conflict_logs
		WHERE id = ?
	""", (conflict_id,))
	
	row = cur.fetchone()
	conn.close()
	
	if not row:
		return None
	
	conflict_id, table_name, conflict_type, detected_at, details_json = row
	details = json.loads(details_json)
	
	return {
		'id': conflict_id,
		'table_name': table_name,
		'conflict_type': conflict_type,
		'detected_at': detected_at,
		'summary': get_conflict_summary(details),
		'details': details
	} 