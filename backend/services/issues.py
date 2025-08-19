from __future__ import annotations
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from uuid import uuid4

from .audit import log_event


def _ensure_tables(session: Session) -> None:
	# flagged_issues
	session.execute(
		"""
		CREATE TABLE IF NOT EXISTS flagged_issues (
			id TEXT PRIMARY KEY,
			invoice_id TEXT NOT NULL,
			supplier_id TEXT,
			type TEXT NOT NULL,
			description TEXT NOT NULL,
			severity TEXT NOT NULL,
			status TEXT NOT NULL,
			created_at TEXT NOT NULL,
			updated_at TEXT NOT NULL
		)
		"""
	)
	# escalations
	session.execute(
		"""
		CREATE TABLE IF NOT EXISTS escalations (
			id TEXT PRIMARY KEY,
			flagged_issue_id TEXT NOT NULL,
			escalated_by TEXT NOT NULL,
			escalated_to TEXT NOT NULL,
			note TEXT,
			created_at TEXT NOT NULL
		)
		"""
	)
	# audit_logs (plural) for this feature
	session.execute(
		"""
		CREATE TABLE IF NOT EXISTS audit_logs (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			user_id TEXT,
			action TEXT,
			entity_type TEXT,
			entity_id TEXT,
			timestamp TEXT
		)
		"""
	)
	# optional grouping tables
	session.execute(
		"""
		CREATE TABLE IF NOT EXISTS issue_groups (
			id TEXT PRIMARY KEY,
			group_name TEXT NOT NULL,
			created_at TEXT NOT NULL
		)
		"""
	)
	session.execute(
		"""
		CREATE TABLE IF NOT EXISTS issue_group_items (
			group_id TEXT NOT NULL,
			flagged_issue_id TEXT NOT NULL,
			PRIMARY KEY (group_id, flagged_issue_id)
		)
		"""
	)
	session.commit()


def _audit(session: Session, user_id: Optional[str], action: str, entity_type: str, entity_id: str) -> None:
	session.execute(
		"INSERT INTO audit_logs (user_id, action, entity_type, entity_id, timestamp) VALUES (:user_id, :action, :entity_type, :entity_id, :ts)",
		{"user_id": user_id, "action": action, "entity_type": entity_type, "entity_id": entity_id, "ts": datetime.utcnow().isoformat()},
	)
	# also log to existing audit_log table if present via log_event helper (best-effort)
	try:
		log_event(session, action, entity_type, entity_id, f"user_id={user_id}")
	except Exception:
		pass


def create_flagged_issue(session: Session, *, invoice_id: str, supplier_id: Optional[str], issue_type: str, description: str, severity: str, user_id: Optional[str]) -> Dict[str, Any]:
	_ensure_tables(session)
	# prevent duplicates: same invoice_id + type + description open
	existing = session.execute(
		"SELECT id FROM flagged_issues WHERE invoice_id=:inv AND type=:type AND description=:desc AND status IN ('open','escalated')",
		{"inv": invoice_id, "type": issue_type, "desc": description},
	).fetchone()
	if existing:
		return {"id": existing[0], "duplicate": True}
	fid = str(uuid4())
	session.execute(
		"""
		INSERT INTO flagged_issues (id, invoice_id, supplier_id, type, description, severity, status, created_at, updated_at)
		VALUES (:id, :invoice_id, :supplier_id, :type, :description, :severity, 'open', :created_at, :updated_at)
		""",
		{
			"id": fid,
			"invoice_id": invoice_id,
			"supplier_id": supplier_id,
			"type": issue_type,
			"description": description,
			"severity": severity,
			"created_at": datetime.utcnow().isoformat(),
			"updated_at": datetime.utcnow().isoformat(),
		},
	)
	session.commit()
	_audit(session, user_id, "issue_created", "flagged_issue", fid)
	return {"id": fid}


def update_flagged_issue_status(session: Session, *, issue_id: str, status: str, description: Optional[str], role: str, user_id: Optional[str]) -> None:
	_ensure_tables(session)
	# permissions
	if status == "resolved" and role not in ("Finance",):
		raise PermissionError("Forbidden")
	if status == "escalated" and role not in ("GM", "Finance"):
		raise PermissionError("Forbidden")
	set_parts = ["status=:status", "updated_at=:ts"]
	params = {"status": status, "ts": datetime.utcnow().isoformat(), "id": issue_id}
	if description is not None:
		set_parts.append("description=:desc")
		params["desc"] = description
	session.execute(f"UPDATE flagged_issues SET {', '.join(set_parts)} WHERE id=:id", params)
	session.commit()
	_audit(session, user_id, f"issue_{status}", "flagged_issue", issue_id)


def group_issues(session: Session, *, issue_ids: List[str], group_name: str, user_id: Optional[str]) -> str:
	_ensure_tables(session)
	gid = str(uuid4())
	session.execute(
		"INSERT INTO issue_groups (id, group_name, created_at) VALUES (:id, :name, :ts)",
		{"id": gid, "name": group_name, "ts": datetime.utcnow().isoformat()},
	)
	for iid in issue_ids:
		session.execute(
			"INSERT OR IGNORE INTO issue_group_items (group_id, flagged_issue_id) VALUES (:gid, :iid)",
			{"gid": gid, "iid": iid},
		)
	session.commit()
	_audit(session, user_id, "issues_grouped", "issue_group", gid)
	return gid


def escalate_issue(session: Session, *, issue_id: str, to_role: str, note: Optional[str], role: str, user_id: Optional[str]) -> str:
	_ensure_tables(session)
	if role not in ("GM", "Finance"):
		raise PermissionError("Forbidden")
	eid = str(uuid4())
	session.execute(
		"""
		INSERT INTO escalations (id, flagged_issue_id, escalated_by, escalated_to, note, created_at)
		VALUES (:id, :fid, :by, :to, :note, :ts)
		""",
		{"id": eid, "fid": issue_id, "by": user_id or "", "to": to_role, "note": note or "", "ts": datetime.utcnow().isoformat()},
	)
	session.execute(
		"UPDATE flagged_issues SET status='escalated', updated_at=:ts WHERE id=:id",
		{"ts": datetime.utcnow().isoformat(), "id": issue_id},
	)
	session.commit()
	_audit(session, user_id, "issue_escalated", "flagged_issue", issue_id)
	return eid


def list_issues(session: Session, *, status: Optional[str], supplier: Optional[str], date_range: Optional[str], limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
	_ensure_tables(session)
	base = "SELECT id, invoice_id, supplier_id, type, description, severity, status, created_at, updated_at FROM flagged_issues"
	conds = []
	params: Dict[str, Any] = {}
	if status:
		conds.append("status=:status")
		params["status"] = status
	if supplier:
		conds.append("supplier_id=:supplier")
		params["supplier"] = supplier
	if date_range:
		try:
			start, end = [s.strip() for s in date_range.split(",", 1)]
			conds.append("created_at>=:start AND created_at<=:end")
			params["start"] = start
			params["end"] = end
		except Exception:
			pass
	if conds:
		base += " WHERE " + " AND ".join(conds)
	base += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
	params["limit"] = limit
	params["offset"] = offset
	rows = session.execute(base, params).fetchall()
	out = []
	for r in rows:
		out.append({
			"id": r[0],
			"invoice_id": r[1],
			"supplier_id": r[2],
			"type": r[3],
			"description": r[4],
			"severity": r[5],
			"status": r[6],
			"created_at": r[7],
			"updated_at": r[8],
		})
	return out 