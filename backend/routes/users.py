from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request
from uuid import UUID
from typing import List

from ..contracts import User, CreateUserRequest
from ..services.permissions import require_permission
from ..services.auth import ensure_auth_tables

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=List[User])
async def list_users(request: Request):
	"""List all users."""
	_ = require_permission("settings.manage_users")(request)
	ensure_auth_tables()
	
	from sqlite3 import connect
	import os
	
	db_path = os.path.join("data", "owlin.db")
	conn = connect(db_path)
	cur = conn.cursor()
	
	cur.execute("SELECT id, email, display_name, is_active FROM users ORDER BY display_name")
	users = [User(
		id=UUID(row[0]),
		email=row[1],
		display_name=row[2],
		is_active=bool(row[3])
	) for row in cur.fetchall()]
	
	conn.close()
	return users


@router.post("", response_model=User)
async def create_user(payload: CreateUserRequest, request: Request):
	"""Create a new user."""
	_ = require_permission("settings.manage_users")(request)
	ensure_auth_tables()
	
	from sqlite3 import connect
	import os
	from uuid import uuid4
	from datetime import datetime
	
	db_path = os.path.join("data", "owlin.db")
	conn = connect(db_path)
	cur = conn.cursor()
	
	user_id = str(uuid4())
	
	cur.execute("""
		INSERT INTO users (id, email, display_name, is_active, created_at) 
		VALUES (?, ?, ?, ?, ?)
	""", (user_id, payload.email, payload.display_name, 1, datetime.utcnow().isoformat()))
	
	conn.commit()
	conn.close()
	
	return User(
		id=UUID(user_id),
		email=payload.email,
		display_name=payload.display_name,
		is_active=True
	)


@router.get("/venues")
async def list_venues(request: Request):
	"""List all venues."""
	_ = require_permission("settings.manage_users")(request)
	ensure_auth_tables()
	
	from sqlite3 import connect
	import os
	from ..contracts import Venue
	
	db_path = os.path.join("data", "owlin.db")
	conn = connect(db_path)
	cur = conn.cursor()
	
	cur.execute("SELECT id, name, code FROM venues ORDER BY name")
	venues = [Venue(
		id=UUID(row[0]),
		name=row[1],
		code=row[2]
	) for row in cur.fetchall()]
	
	conn.close()
	return venues 