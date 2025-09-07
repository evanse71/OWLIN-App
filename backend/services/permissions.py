from __future__ import annotations
from fastapi import Depends, HTTPException, status, Request
from sqlite3 import connect
import os
from typing import Optional

from .auth import get_current_user, get_current_venue, ensure_auth_tables

DB_PATH = os.path.join("data", "owlin.db")


def _get_conn():
	os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
	return connect(DB_PATH)


def has_permission(user_id: str, venue_id: str, permission_code: str) -> bool:
	"""Check if user has permission at venue."""
	ensure_auth_tables()
	conn = _get_conn()
	cur = conn.cursor()
	
	cur.execute("""
		SELECT 1 FROM user_roles ur 
		JOIN role_permissions rp ON rp.role_id = ur.role_id 
		WHERE ur.user_id = ? AND ur.venue_id = ? AND rp.permission_code = ? 
		LIMIT 1
	""", (user_id, venue_id, permission_code))
	
	result = cur.fetchone()
	conn.close()
	
	return result is not None


def require_permission(permission_code: str):
	"""FastAPI dependency to require a specific permission."""
	def _dep(request: Request):
		user = get_current_user(request)
		venue = get_current_venue(request)
		
		if not user or not venue:
			raise HTTPException(
				status_code=status.HTTP_401_UNAUTHORIZED, 
				detail="Not authenticated"
			)
		
		if not has_permission(str(user["id"]), str(venue["id"]), permission_code):
			raise HTTPException(
				status_code=status.HTTP_403_FORBIDDEN, 
				detail=f"Insufficient permissions: {permission_code}"
			)
		
		return True
	
	return _dep


def get_user_permissions(user_id: str, venue_id: str) -> list[str]:
	"""Get all permissions for a user at a venue."""
	ensure_auth_tables()
	conn = _get_conn()
	cur = conn.cursor()
	
	cur.execute("""
		SELECT DISTINCT rp.permission_code FROM user_roles ur 
		JOIN role_permissions rp ON rp.role_id = ur.role_id 
		WHERE ur.user_id = ? AND ur.venue_id = ?
	""", (user_id, venue_id))
	
	permissions = [row[0] for row in cur.fetchall()]
	conn.close()
	
	return permissions


def get_role_permissions(role_id: str) -> list[dict]:
	"""Get all permissions for a role."""
	ensure_auth_tables()
	conn = _get_conn()
	cur = conn.cursor()
	
	cur.execute("""
		SELECT p.code, p.description FROM role_permissions rp
		JOIN permissions p ON p.code = rp.permission_code
		WHERE rp.role_id = ?
	""", (role_id,))
	
	permissions = [{"code": row[0], "description": row[1]} for row in cur.fetchall()]
	conn.close()
	
	return permissions


def assign_role_to_user(user_id: str, role_id: str, venue_id: str) -> bool:
	"""Assign a role to a user at a venue."""
	ensure_auth_tables()
	conn = _get_conn()
	cur = conn.cursor()
	
	try:
		cur.execute("""
			INSERT OR REPLACE INTO user_roles (user_id, role_id, venue_id) 
			VALUES (?, ?, ?)
		""", (user_id, role_id, venue_id))
		
		conn.commit()
		conn.close()
		return True
	except Exception:
		conn.close()
		return False


def remove_role_from_user(user_id: str, role_id: str, venue_id: str) -> bool:
	"""Remove a role from a user at a venue."""
	ensure_auth_tables()
	conn = _get_conn()
	cur = conn.cursor()
	
	try:
		cur.execute("""
			DELETE FROM user_roles 
			WHERE user_id = ? AND role_id = ? AND venue_id = ?
		""", (user_id, role_id, venue_id))
		
		conn.commit()
		conn.close()
		return True
	except Exception:
		conn.close()
		return False


def update_role_permissions(role_id: str, permission_codes: list[str]) -> bool:
	"""Update permissions for a role."""
	ensure_auth_tables()
	conn = _get_conn()
	cur = conn.cursor()
	
	try:
		# Remove existing permissions
		cur.execute("DELETE FROM role_permissions WHERE role_id = ?", (role_id,))
		
		# Add new permissions
		for code in permission_codes:
			cur.execute("""
				INSERT INTO role_permissions (role_id, permission_code) 
				VALUES (?, ?)
			""", (role_id, code))
		
		conn.commit()
		conn.close()
		return True
	except Exception:
		conn.close()
		return False 