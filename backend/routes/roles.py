from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request
from uuid import UUID
from typing import List

from ..contracts import RoleWithPerms, CreateRoleRequest, UpdateRoleRequest, Permission
from ..services.permissions import require_permission, get_role_permissions, update_role_permissions
from ..services.auth import ensure_auth_tables

router = APIRouter(prefix="/api/roles", tags=["roles"])


@router.get("", response_model=List[RoleWithPerms])
async def list_roles(request: Request):
	"""List all roles with their permissions."""
	_ = require_permission("settings.manage_roles")(request)
	ensure_auth_tables()
	
	from sqlite3 import connect
	import os
	
	db_path = os.path.join("data", "owlin.db")
	conn = connect(db_path)
	cur = conn.cursor()
	
	cur.execute("SELECT id, name, description FROM roles ORDER BY name")
	roles = []
	
	for row in cur.fetchall():
		role_id, name, description = row
		permissions = get_role_permissions(role_id)
		
		roles.append(RoleWithPerms(
			id=UUID(role_id),
			name=name,
			description=description,
			permissions=[Permission(code=p["code"], description=p["description"]) for p in permissions]
		))
	
	conn.close()
	return roles


@router.post("", response_model=RoleWithPerms)
async def create_role(payload: CreateRoleRequest, request: Request):
	"""Create a new role."""
	_ = require_permission("settings.manage_roles")(request)
	ensure_auth_tables()
	
	from sqlite3 import connect
	import os
	from uuid import uuid4
	from datetime import datetime
	
	db_path = os.path.join("data", "owlin.db")
	conn = connect(db_path)
	cur = conn.cursor()
	
	role_id = str(uuid4())
	
	cur.execute("""
		INSERT INTO roles (id, name, description, created_at) 
		VALUES (?, ?, ?, ?)
	""", (role_id, payload.name, payload.description, datetime.utcnow().isoformat()))
	
	# Add permissions
	for perm_code in payload.permissions:
		cur.execute("""
			INSERT INTO role_permissions (role_id, permission_code) 
			VALUES (?, ?)
		""", (role_id, perm_code))
	
	conn.commit()
	conn.close()
	
	# Return created role
	permissions = get_role_permissions(role_id)
	return RoleWithPerms(
		id=UUID(role_id),
		name=payload.name,
		description=payload.description,
		permissions=[Permission(code=p["code"], description=p["description"]) for p in permissions]
	)


@router.patch("/{role_id}", response_model=RoleWithPerms)
async def update_role(role_id: str, payload: UpdateRoleRequest, request: Request):
	"""Update a role."""
	_ = require_permission("settings.manage_roles")(request)
	ensure_auth_tables()
	
	from sqlite3 import connect
	import os
	
	db_path = os.path.join("data", "owlin.db")
	conn = connect(db_path)
	cur = conn.cursor()
	
	# Update role details
	cur.execute("""
		UPDATE roles SET name = ?, description = ? WHERE id = ?
	""", (payload.name, payload.description, role_id))
	
	# Update permissions
	update_role_permissions(role_id, payload.permissions)
	
	conn.commit()
	conn.close()
	
	# Return updated role
	permissions = get_role_permissions(role_id)
	return RoleWithPerms(
		id=UUID(role_id),
		name=payload.name,
		description=payload.description,
		permissions=[Permission(code=p["code"], description=p["description"]) for p in permissions]
	)


@router.get("/permissions")
async def list_permissions(request: Request):
	"""List all available permissions."""
	_ = require_permission("settings.manage_roles")(request)
	ensure_auth_tables()
	
	from sqlite3 import connect
	import os
	
	db_path = os.path.join("data", "owlin.db")
	conn = connect(db_path)
	cur = conn.cursor()
	
	cur.execute("SELECT code, description FROM permissions ORDER BY code")
	permissions = [Permission(code=row[0], description=row[1]) for row in cur.fetchall()]
	
	conn.close()
	return permissions 