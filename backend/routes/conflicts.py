from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from uuid import UUID
from typing import List, Optional

from ..contracts import ConflictListItem, ResolveConflictRequest, TableDiff
from ..services.permissions import require_permission
from ..services.auth import get_current_user
from ..services.conflict_detector import list_conflicts, get_conflict, run_conflict_detection
from ..utils.render_table_diff import render_table_diff

router = APIRouter(prefix="/api/conflicts", tags=["conflicts"])


@router.get("", response_model=List[ConflictListItem])
async def list_conflicts_endpoint(
	request: Request,
	limit: int = Query(50, ge=1, le=100, description="Number of conflicts to return"),
	offset: int = Query(0, ge=0, description="Number of conflicts to skip")
):
	"""List conflicts with pagination."""
	user = get_current_user(request)
	if not user:
		raise HTTPException(401, "Not authenticated")
	
	# Check permissions - Admin role required
	_ = require_permission("settings.manage_roles")(request)
	
	conflicts_data = list_conflicts(limit=limit, offset=offset)
	
	# Convert to contract format
	conflicts = []
	for conflict_data in conflicts_data:
		conflicts.append(ConflictListItem(
			id=UUID(conflict_data["id"]),
			table_name=conflict_data["table_name"],
			conflict_type=conflict_data["conflict_type"],
			detected_at=conflict_data["detected_at"],
			resolved=conflict_data["resolved"],
			summary=conflict_data["summary"]
		))
	
	return conflicts


@router.get("/detect")
async def detect_conflicts_endpoint(request: Request):
	"""Run conflict detection and return results."""
	user = get_current_user(request)
	if not user:
		raise HTTPException(401, "Not authenticated")
	
	# Check permissions - Admin role required
	_ = require_permission("settings.manage_roles")(request)
	
	conflicts = run_conflict_detection()
	
	return {
		"conflicts_found": len(conflicts),
		"conflicts": conflicts
	}


@router.get("/{conflict_id}/diff", response_model=TableDiff)
async def get_conflict_diff(
	conflict_id: UUID,
	request: Request
):
	"""Get detailed diff for a specific conflict."""
	user = get_current_user(request)
	if not user:
		raise HTTPException(401, "Not authenticated")
	
	# Check permissions - Admin role required
	_ = require_permission("settings.manage_roles")(request)
	
	conflict_data = get_conflict(str(conflict_id))
	if not conflict_data:
		raise HTTPException(404, "Conflict not found")
	
	# Render the diff
	diff_result = render_table_diff(conflict_data["details"])
	
	return TableDiff(
		table_name=conflict_data["table_name"],
		diff_type=conflict_data["conflict_type"],
		html_diff=diff_result["html_diff"],
		json_diff=diff_result["json_diff"],
		summary=diff_result["summary"]
	)


@router.post("/{conflict_id}/resolve")
async def resolve_conflict(
	conflict_id: UUID,
	payload: ResolveConflictRequest,
	request: Request
):
	"""Resolve a specific conflict."""
	user = get_current_user(request)
	if not user:
		raise HTTPException(401, "Not authenticated")
	
	# Check permissions - Admin role required
	_ = require_permission("settings.manage_roles")(request)
	
	# Get conflict
	conflict_data = get_conflict(str(conflict_id))
	if not conflict_data:
		raise HTTPException(404, "Conflict not found")
	
	# Record resolution
	from ..services.conflict_detector import ensure_conflict_tables
	from sqlite3 import connect
	import os
	from datetime import datetime
	
	ensure_conflict_tables()
	
	db_path = os.path.join("data", "owlin.db")
	conn = connect(db_path)
	cur = conn.cursor()
	
	from uuid import uuid4
	
	cur.execute("""
		INSERT INTO conflict_resolutions (id, conflict_id, action, resolved_by, resolved_at, notes)
		VALUES (?, ?, ?, ?, ?, ?)
	""", (
		str(uuid4()),
		str(conflict_id),
		payload.action,
		str(user["id"]),
		datetime.utcnow().isoformat(),
		payload.notes
	))
	
	conn.commit()
	conn.close()
	
	return {
		"success": True,
		"message": f"Conflict {payload.action}",
		"conflict_id": str(conflict_id),
		"action": payload.action,
		"resolved_by": str(user["id"]),
		"resolved_at": datetime.utcnow().isoformat()
	}


@router.get("/{conflict_id}")
async def get_conflict_details(
	conflict_id: UUID,
	request: Request
):
	"""Get detailed information about a specific conflict."""
	user = get_current_user(request)
	if not user:
		raise HTTPException(401, "Not authenticated")
	
	# Check permissions - Admin role required
	_ = require_permission("settings.manage_roles")(request)
	
	conflict_data = get_conflict(str(conflict_id))
	if not conflict_data:
		raise HTTPException(404, "Conflict not found")
	
	return conflict_data 