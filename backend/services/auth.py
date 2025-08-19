from __future__ import annotations
from fastapi import Request, Depends
from sqlite3 import connect
from uuid import uuid4
from datetime import datetime, timedelta
import os
from typing import Optional

SESSION_TTL_HOURS = 12
DB_PATH = os.path.join("data", "owlin.db")


def _get_conn():
	os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
	return connect(DB_PATH)


def ensure_auth_tables():
	"""Ensure RBAC tables exist."""
	conn = _get_conn()
	cur = conn.cursor()
	
	# Users table
	cur.execute("""
	CREATE TABLE IF NOT EXISTS users (
		id TEXT PRIMARY KEY,
		email TEXT UNIQUE NOT NULL,
		display_name TEXT NOT NULL,
		is_active INTEGER NOT NULL DEFAULT 1,
		created_at TIMESTAMP NOT NULL
	)""")
	
	# Venues table
	cur.execute("""
	CREATE TABLE IF NOT EXISTS venues (
		id TEXT PRIMARY KEY,
		name TEXT NOT NULL,
		code TEXT UNIQUE NOT NULL,
		created_at TIMESTAMP NOT NULL
	)""")
	
	# Roles table
	cur.execute("""
	CREATE TABLE IF NOT EXISTS roles (
		id TEXT PRIMARY KEY,
		name TEXT UNIQUE NOT NULL,
		description TEXT,
		created_at TIMESTAMP NOT NULL
	)""")
	
	# Permissions table
	cur.execute("""
	CREATE TABLE IF NOT EXISTS permissions (
		code TEXT PRIMARY KEY,
		description TEXT NOT NULL
	)""")
	
	# Role permissions junction
	cur.execute("""
	CREATE TABLE IF NOT EXISTS role_permissions (
		role_id TEXT NOT NULL,
		permission_code TEXT NOT NULL,
		PRIMARY KEY (role_id, permission_code),
		FOREIGN KEY (role_id) REFERENCES roles(id),
		FOREIGN KEY (permission_code) REFERENCES permissions(code)
	)""")
	
	# User role assignments
	cur.execute("""
	CREATE TABLE IF NOT EXISTS user_roles (
		user_id TEXT NOT NULL,
		role_id TEXT NOT NULL,
		venue_id TEXT NOT NULL,
		PRIMARY KEY (user_id, role_id, venue_id),
		FOREIGN KEY (user_id) REFERENCES users(id),
		FOREIGN KEY (role_id) REFERENCES roles(id),
		FOREIGN KEY (venue_id) REFERENCES venues(id)
	)""")
	
	# Sessions table
	cur.execute("""
	CREATE TABLE IF NOT EXISTS sessions (
		id TEXT PRIMARY KEY,
		user_id TEXT NOT NULL,
		created_at TIMESTAMP NOT NULL,
		expires_at TIMESTAMP NOT NULL,
		FOREIGN KEY (user_id) REFERENCES users(id)
	)""")
	
	# Seed default data
	_seed_default_data(cur)
	
	conn.commit()
	conn.close()


def _seed_default_data(cur):
	"""Seed default roles, permissions, users, and venues."""
	# Default permissions
	permissions = [
		("invoice.upload", "Upload invoices"),
		("invoice.edit", "Edit invoices"),
		("match.confirm", "Confirm matches"),
		("match.reject", "Reject matches"),
		("issues.resolve", "Resolve issues"),
		("issues.escalate", "Escalate issues"),
		("suppliers.export", "Export supplier data"),
		("settings.manage_users", "Manage users"),
		("settings.manage_roles", "Manage roles"),
		("notes.create", "Create notes"),
		("recovery.restore", "Restore from backup"),
		("forecast.view", "View forecasts"),
		("budgets.manage", "Manage budgets")
	]
	
	for code, desc in permissions:
		cur.execute("INSERT OR IGNORE INTO permissions (code, description) VALUES (?, ?)", (code, desc))
	
	# Default roles
	roles = [
		("00000000-0000-0000-0000-000000000001", "General Manager", "Full system access"),
		("00000000-0000-0000-0000-000000000002", "Finance", "Financial operations"),
		("00000000-0000-0000-0000-000000000003", "Shift Lead", "Operational access")
	]
	
	for role_id, name, desc in roles:
		cur.execute("INSERT OR IGNORE INTO roles (id, name, description, created_at) VALUES (?, ?, ?, ?)", 
				   (role_id, name, desc, datetime.utcnow().isoformat()))
	
	# Default users
	users = [
		("00000000-0000-0000-0000-000000000001", "gm@example.com", "General Manager"),
		("00000000-0000-0000-0000-000000000002", "finance@example.com", "Finance User"),
		("00000000-0000-0000-0000-000000000003", "shiftlead@example.com", "Shift Lead")
	]
	
	for user_id, email, name in users:
		cur.execute("INSERT OR IGNORE INTO users (id, email, display_name, is_active, created_at) VALUES (?, ?, ?, ?, ?)", 
				   (user_id, email, name, 1, datetime.utcnow().isoformat()))
	
	# Default venue
	cur.execute("INSERT OR IGNORE INTO venues (id, name, code, created_at) VALUES (?, ?, ?, ?)", 
			   ("00000000-0000-0000-0000-000000000001", "Main Venue", "MAIN", datetime.utcnow().isoformat()))
	
	# Role permissions
	role_perms = [
		# GM: all permissions
		("00000000-0000-0000-0000-000000000001", "invoice.upload"), ("00000000-0000-0000-0000-000000000001", "invoice.edit"), ("00000000-0000-0000-0000-000000000001", "match.confirm"), ("00000000-0000-0000-0000-000000000001", "match.reject"),
		("00000000-0000-0000-0000-000000000001", "issues.resolve"), ("00000000-0000-0000-0000-000000000001", "issues.escalate"), ("00000000-0000-0000-0000-000000000001", "suppliers.export"), ("00000000-0000-0000-0000-000000000001", "settings.manage_users"),
		("00000000-0000-0000-0000-000000000001", "settings.manage_roles"), ("00000000-0000-0000-0000-000000000001", "notes.create"), ("00000000-0000-0000-0000-000000000001", "recovery.restore"), ("00000000-0000-0000-0000-000000000001", "forecast.view"),
		("00000000-0000-0000-0000-000000000001", "budgets.manage"),
		# Finance: all except role management and recovery
		("00000000-0000-0000-0000-000000000002", "invoice.upload"), ("00000000-0000-0000-0000-000000000002", "invoice.edit"), ("00000000-0000-0000-0000-000000000002", "match.confirm"), ("00000000-0000-0000-0000-000000000002", "match.reject"),
		("00000000-0000-0000-0000-000000000002", "issues.resolve"), ("00000000-0000-0000-0000-000000000002", "issues.escalate"), ("00000000-0000-0000-0000-000000000002", "suppliers.export"), ("00000000-0000-0000-0000-000000000002", "settings.manage_users"),
		("00000000-0000-0000-0000-000000000002", "notes.create"), ("00000000-0000-0000-0000-000000000002", "forecast.view"), ("00000000-0000-0000-0000-000000000002", "budgets.manage"),
		# Shift Lead: limited permissions
		("00000000-0000-0000-0000-000000000003", "notes.create"), ("00000000-0000-0000-0000-000000000003", "forecast.view")
	]
	
	for role_id, perm_code in role_perms:
		cur.execute("INSERT OR IGNORE INTO role_permissions (role_id, permission_code) VALUES (?, ?)", (role_id, perm_code))
	
	# Default user assignments
	assignments = [
		("00000000-0000-0000-0000-000000000001", "00000000-0000-0000-0000-000000000001", "00000000-0000-0000-0000-000000000001"),
		("00000000-0000-0000-0000-000000000002", "00000000-0000-0000-0000-000000000002", "00000000-0000-0000-0000-000000000001"),
		("00000000-0000-0000-0000-000000000003", "00000000-0000-0000-0000-000000000003", "00000000-0000-0000-0000-000000000001")
	]
	
	for user_id, role_id, venue_id in assignments:
		cur.execute("INSERT OR IGNORE INTO user_roles (user_id, role_id, venue_id) VALUES (?, ?, ?)", (user_id, role_id, venue_id))


def create_session(user_id: str) -> dict:
	"""Create a new session for a user."""
	ensure_auth_tables()
	conn = _get_conn()
	cur = conn.cursor()
	
	session_id = str(uuid4())
	created_at = datetime.utcnow()
	expires_at = created_at + timedelta(hours=SESSION_TTL_HOURS)
	
	cur.execute("INSERT INTO sessions (id, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)", 
			   (session_id, user_id, created_at.isoformat(), expires_at.isoformat()))
	
	conn.commit()
	conn.close()
	
	return {
		"id": session_id,
		"user_id": user_id,
		"created_at": created_at,
		"expires_at": expires_at
	}


def get_current_user(request: Request) -> Optional[dict]:
	"""Get current user from session."""
	ensure_auth_tables()
	
	sid = request.headers.get("X-Owlin-Session") or request.cookies.get("owlin_session")
	if not sid:
		return None
	
	conn = _get_conn()
	cur = conn.cursor()
	
	cur.execute("SELECT user_id, expires_at FROM sessions WHERE id = ?", (sid,))
	session_row = cur.fetchone()
	
	if not session_row:
		conn.close()
		return None
	
	user_id, expires_at = session_row
	if datetime.fromisoformat(expires_at) < datetime.utcnow():
		conn.close()
		return None
	
	cur.execute("SELECT id, email, display_name, is_active FROM users WHERE id = ?", (user_id,))
	user_row = cur.fetchone()
	
	conn.close()
	
	if not user_row:
		return None
	
	return {
		"id": user_row[0],
		"email": user_row[1],
		"display_name": user_row[2],
		"is_active": bool(user_row[3])
	}


def get_current_venue(request: Request) -> Optional[dict]:
	"""Get current venue from request."""
	ensure_auth_tables()
	
	vid = request.headers.get("X-Owlin-Venue") or request.cookies.get("owlin_venue")
	if not vid:
		return None
	
	conn = _get_conn()
	cur = conn.cursor()
	
	cur.execute("SELECT id, name, code FROM venues WHERE id = ?", (vid,))
	venue_row = cur.fetchone()
	
	conn.close()
	
	if not venue_row:
		return None
	
	return {
		"id": venue_row[0],
		"name": venue_row[1],
		"code": venue_row[2]
	} 