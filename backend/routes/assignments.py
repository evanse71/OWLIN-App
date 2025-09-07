from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request
from uuid import UUID

from ..contracts import AssignRoleRequest, UserRoleAssignment
from ..services.permissions import require_permission, assign_role_to_user, remove_role_from_user
from ..services.auth import ensure_auth_tables

router = APIRouter(prefix="/api/assignments", tags=["assignments"])


@router.post("", response_model=UserRoleAssignment)
async def assign_role(payload: AssignRoleRequest, request: Request):
	"""Assign a role to a user at a venue."""
	_ = require_permission("settings.manage_users")(request)
	ensure_auth_tables()
	
	success = assign_role_to_user(
		str(payload.user_id), 
		str(payload.role_id), 
		str(payload.venue_id)
	)
	
	if not success:
		raise HTTPException(400, "Failed to assign role")
	
	return UserRoleAssignment(
		user_id=payload.user_id,
		role_id=payload.role_id,
		venue_id=payload.venue_id
	)


@router.delete("")
async def unassign_role(payload: AssignRoleRequest, request: Request):
	"""Remove a role from a user at a venue."""
	_ = require_permission("settings.manage_users")(request)
	ensure_auth_tables()
	
	success = remove_role_from_user(
		str(payload.user_id), 
		str(payload.role_id), 
		str(payload.venue_id)
	)
	
	if not success:
		raise HTTPException(400, "Failed to remove role")
	
	return {"ok": True, "message": "Role removed successfully"}


@router.get("/user/{user_id}")
async def get_user_assignments(user_id: str, request: Request):
	"""Get all role assignments for a user."""
	_ = require_permission("settings.manage_users")(request)
	ensure_auth_tables()
	
	from sqlite3 import connect
	import os
	
	db_path = os.path.join("data", "owlin.db")
	conn = connect(db_path)
	cur = conn.cursor()
	
	cur.execute("""
		SELECT ur.role_id, ur.venue_id, r.name as role_name, v.name as venue_name
		FROM user_roles ur
		JOIN roles r ON r.id = ur.role_id
		JOIN venues v ON v.id = ur.venue_id
		WHERE ur.user_id = ?
	""", (user_id,))
	
	assignments = []
	for row in cur.fetchall():
		assignments.append({
			"role_id": row[0],
			"venue_id": row[1],
			"role_name": row[2],
			"venue_name": row[3]
		})
	
	conn.close()
	return {"assignments": assignments} 