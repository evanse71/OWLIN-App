from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request
from uuid import UUID
from datetime import datetime

from ..contracts import LoginRequest, SessionInfo, User
from ..services.auth import create_session, get_current_user, ensure_auth_tables
from ..services.permissions import get_user_permissions

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=SessionInfo)
async def login(payload: LoginRequest):
	"""Login with email and create session."""
	ensure_auth_tables()
	
	# Simple email-based login (no password for demo)
	from sqlite3 import connect
	import os
	
	db_path = os.path.join("data", "owlin.db")
	conn = connect(db_path)
	cur = conn.cursor()
	
	cur.execute("SELECT id, email, display_name, is_active FROM users WHERE email = ?", (payload.email,))
	user_row = cur.fetchone()
	conn.close()
	
	if not user_row or not user_row[3]:  # is_active check
		raise HTTPException(401, "Invalid user")
	
	user_id, email, display_name, is_active = user_row
	
	# Create session
	session = create_session(user_id)
	
	return SessionInfo(
		session_id=UUID(session["id"]),
		user=User(
			id=UUID(user_id),
			email=email,
			display_name=display_name,
			is_active=bool(is_active)
		),
		expires_at=session["expires_at"]
	)


@router.get("/me", response_model=User)
async def get_current_user_info(request: Request):
	"""Get current user information."""
	user = get_current_user(request)
	if not user:
		raise HTTPException(401, "Not authenticated")
	
	return User(
		id=UUID(user["id"]),
		email=user["email"],
		display_name=user["display_name"],
		is_active=user["is_active"]
	)


@router.get("/permissions")
async def get_my_permissions(request: Request):
	"""Get current user's permissions at current venue."""
	user = get_current_user(request)
	if not user:
		raise HTTPException(401, "Not authenticated")
	
	from ..services.auth import get_current_venue
	venue = get_current_venue(request)
	if not venue:
		raise HTTPException(400, "No venue selected")
	
	permissions = get_user_permissions(str(user["id"]), str(venue["id"]))
	
	return {
		"user_id": user["id"],
		"venue_id": venue["id"],
		"permissions": permissions
	} 