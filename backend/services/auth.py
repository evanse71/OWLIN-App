from __future__ import annotations
from fastapi import Request, Depends
import sqlite3
import hashlib
import os
import logging
from typing import Optional, Dict, Any
from db_manager_unified import get_db_manager

logger = logging.getLogger(__name__)

# Get unified database manager
db_manager = get_db_manager()

def _get_conn():
    """Get database connection using unified manager"""
    return db_manager.get_connection()

def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate user with username and password"""
    try:
        with _get_conn() as conn:
            # Hash the password
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            # Check credentials
            cursor = conn.execute("""
                SELECT id, username, role, email, created_at, last_login
                FROM users 
                WHERE username = ? AND password_hash = ? AND active = 1
            """, (username, password_hash))
            
            user = cursor.fetchone()
            if user:
                # Update last login
                conn.execute("""
                    UPDATE users SET last_login = datetime('now') WHERE id = ?
                """, (user['id'],))
                conn.commit()
                
                return dict(user)
            return None
            
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return None

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID"""
    try:
        with _get_conn() as conn:
            cursor = conn.execute("""
                SELECT id, username, role, email, created_at, last_login
                FROM users 
                WHERE id = ? AND active = 1
            """, (user_id,))
            
            user = cursor.fetchone()
            return dict(user) if user else None
            
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None

def create_user(username: str, password: str, email: str, role: str = "user") -> Optional[str]:
    """Create a new user"""
    try:
        with _get_conn() as conn:
            # Check if username already exists
            cursor = conn.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                logger.warning(f"Username already exists: {username}")
                return None
            
            # Hash password
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            # Insert new user
            user_id = f"user_{os.urandom(8).hex()}"
            conn.execute("""
                INSERT INTO users (id, username, password_hash, email, role, created_at, active)
                VALUES (?, ?, ?, ?, ?, datetime('now'), 1)
            """, (user_id, username, password_hash, email, role))
            conn.commit()
            
            logger.info(f"Created user: {username}")
            return user_id
            
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return None

def update_user_role(user_id: str, new_role: str) -> bool:
    """Update user role"""
    try:
        with _get_conn() as conn:
            conn.execute("""
                UPDATE users SET role = ?, updated_at = datetime('now')
                WHERE id = ? AND active = 1
            """, (new_role, user_id))
            conn.commit()
            
            logger.info(f"Updated user role: {user_id} -> {new_role}")
            return True
            
    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        return False 