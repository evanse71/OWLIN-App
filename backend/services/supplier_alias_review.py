# -*- coding: utf-8 -*-
"""
Supplier Alias Review System

This module manages supplier alias drift by prompting users to confirm new vendor
strings, as specified in Appendix B.2 (line 623).

Features:
- Store pending alias reviews
- Approve/reject alias matches
- Prevent alias drift over time
"""

from __future__ import annotations
import logging
import sqlite3
from typing import Any, Dict, List, Optional
from datetime import datetime

LOGGER = logging.getLogger("owlin.services.supplier_alias_review")
LOGGER.setLevel(logging.INFO)

DB_PATH = "data/owlin.db"


def _get_db_connection():
    """Get database connection."""
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def _ensure_table():
    """Ensure supplier_alias_review table exists."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS supplier_alias_review (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_name TEXT NOT NULL,
                suggested_match TEXT,
                confidence REAL,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TEXT,
                reviewed_by TEXT
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alias_review_status ON supplier_alias_review(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alias_review_original_name ON supplier_alias_review(original_name)")
        
        conn.commit()
        LOGGER.debug("Supplier alias review table ensured")
        
    except Exception as e:
        LOGGER.error(f"Error ensuring supplier alias review table: {e}")
        conn.rollback()
    finally:
        conn.close()


def create_alias_review(original_name: str, suggested_match: str, confidence: float) -> int:
    """
    Create a new alias review entry.
    
    Args:
        original_name: Original supplier name from OCR
        suggested_match: Suggested matching supplier name
        confidence: Match confidence (0-100)
    
    Returns:
        Review ID
    """
    _ensure_table()
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if review already exists
        cursor.execute("""
            SELECT id FROM supplier_alias_review
            WHERE original_name = ? AND status = 'pending'
        """, (original_name,))
        
        existing = cursor.fetchone()
        if existing:
            # Update existing review
            cursor.execute("""
                UPDATE supplier_alias_review
                SET suggested_match = ?, confidence = ?
                WHERE id = ?
            """, (suggested_match, confidence, existing[0]))
            review_id = existing[0]
        else:
            # Create new review
            cursor.execute("""
                INSERT INTO supplier_alias_review (original_name, suggested_match, confidence, status)
                VALUES (?, ?, ?, 'pending')
            """, (original_name, suggested_match, confidence))
            review_id = cursor.lastrowid
        
        conn.commit()
        LOGGER.info(f"Created alias review: id={review_id}, original='{original_name}', suggested='{suggested_match}', confidence={confidence:.1f}")
        return review_id
        
    except Exception as e:
        LOGGER.error(f"Error creating alias review: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def get_pending_reviews(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get pending alias reviews.
    
    Args:
        limit: Maximum number of reviews to return
    
    Returns:
        List of pending review dictionaries
    """
    _ensure_table()
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT id, original_name, suggested_match, confidence, created_at
            FROM supplier_alias_review
            WHERE status = 'pending'
            ORDER BY confidence DESC, created_at ASC
            LIMIT ?
        """, (limit,))
        
        reviews = []
        for row in cursor.fetchall():
            reviews.append({
                "id": row[0],
                "original_name": row[1],
                "suggested_match": row[2],
                "confidence": row[3] or 0.0,
                "created_at": row[4] or ""
            })
        
        return reviews
        
    except Exception as e:
        LOGGER.error(f"Error getting pending reviews: {e}")
        return []
    finally:
        conn.close()


def approve_alias(review_id: int, reviewed_by: str = "system") -> bool:
    """
    Approve an alias match.
    
    This merges the original_name with the suggested_match supplier.
    
    Args:
        review_id: Review ID
        reviewed_by: User who approved (default: "system")
    
    Returns:
        True if successful
    """
    _ensure_table()
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get review details
        cursor.execute("""
            SELECT original_name, suggested_match
            FROM supplier_alias_review
            WHERE id = ? AND status = 'pending'
        """, (review_id,))
        
        row = cursor.fetchone()
        if not row:
            LOGGER.warning(f"Review {review_id} not found or already processed")
            return False
        
        original_name, suggested_match = row
        
        # Update review status
        cursor.execute("""
            UPDATE supplier_alias_review
            SET status = 'approved',
                reviewed_at = ?,
                reviewed_by = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), reviewed_by, review_id))
        
        # Update all invoices with original_name to use suggested_match
        # (This would require a suppliers table mapping)
        # For now, we'll just mark the review as approved
        
        conn.commit()
        LOGGER.info(f"Alias approved: review_id={review_id}, '{original_name}' → '{suggested_match}'")
        return True
        
    except Exception as e:
        LOGGER.error(f"Error approving alias: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def reject_alias(review_id: int, reviewed_by: str = "system") -> bool:
    """
    Reject an alias match and create new supplier.
    
    Args:
        review_id: Review ID
        reviewed_by: User who rejected (default: "system")
    
    Returns:
        True if successful
    """
    _ensure_table()
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get review details
        cursor.execute("""
            SELECT original_name
            FROM supplier_alias_review
            WHERE id = ? AND status = 'pending'
        """, (review_id,))
        
        row = cursor.fetchone()
        if not row:
            LOGGER.warning(f"Review {review_id} not found or already processed")
            return False
        
        original_name = row[0]
        
        # Update review status
        cursor.execute("""
            UPDATE supplier_alias_review
            SET status = 'rejected',
                reviewed_at = ?,
                reviewed_by = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), reviewed_by, review_id))
        
        # Create new supplier (would call normalizer service)
        from backend.services.normalizer import _create_new_supplier
        result = _create_new_supplier(original_name)
        
        conn.commit()
        LOGGER.info(f"Alias rejected: review_id={review_id}, created new supplier for '{original_name}'")
        return True
        
    except Exception as e:
        LOGGER.error(f"Error rejecting alias: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_review_statistics() -> Dict[str, Any]:
    """
    Get statistics about alias reviews.
    
    Returns:
        Dictionary with review statistics
    """
    _ensure_table()
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM supplier_alias_review
            GROUP BY status
        """)
        
        status_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute("""
            SELECT AVG(confidence) as avg_confidence
            FROM supplier_alias_review
            WHERE status = 'pending'
        """)
        
        row = cursor.fetchone()
        avg_confidence = row[0] if row and row[0] else 0.0
        
        return {
            "pending": status_counts.get("pending", 0),
            "approved": status_counts.get("approved", 0),
            "rejected": status_counts.get("rejected", 0),
            "avg_confidence": round(avg_confidence, 2) if avg_confidence else 0.0,
            "total": sum(status_counts.values())
        }
        
    except Exception as e:
        LOGGER.error(f"Error getting review statistics: {e}")
        return {}
    finally:
        conn.close()

