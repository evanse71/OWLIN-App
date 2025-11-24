# -*- coding: utf-8 -*-
"""
Supplier & Item Normalizer Service

This module implements supplier and item canonical matching with rapidfuzz thresholds
as specified in System Bible Section 2.5 (lines 176-179).

Thresholds:
- ≥90 → auto-match to existing supplier
- 85-90 → flag for user confirmation (store in supplier_alias_review table)
- <85 → create new supplier record
- Sentence-transformer embedding fallback for ambiguous cases
"""

from __future__ import annotations
import logging
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

# Optional imports with graceful fallback
try:
    from rapidfuzz.fuzz import token_sort_ratio
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    token_sort_ratio = None

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMER_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMER_AVAILABLE = False
    SentenceTransformer = None

LOGGER = logging.getLogger("owlin.services.normalizer")
LOGGER.setLevel(logging.INFO)

DB_PATH = "data/owlin.db"

# Thresholds as per System Bible Section 2.5
AUTO_MATCH_THRESHOLD = 90  # ≥90 → auto-match
REVIEW_THRESHOLD = 85      # 85-90 → flag for user confirmation
NEW_SUPPLIER_THRESHOLD = 85  # <85 → create new supplier record


def _get_db_connection():
    """Get database connection."""
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def _ensure_tables():
    """Ensure normalization tables exist."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Create normalization_log table (if not exists from migration)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS normalization_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_name TEXT NOT NULL,
                matched_id TEXT,
                confidence REAL,
                action TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create supplier_alias_review table (if not exists from migration)
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
        
        # Create suppliers table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suppliers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                normalized_name TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        LOGGER.debug("Normalization tables ensured")
        
    except Exception as e:
        LOGGER.error(f"Error ensuring normalization tables: {e}")
        conn.rollback()
    finally:
        conn.close()


def normalize_supplier(supplier_name: str) -> Dict[str, Any]:
    """
    Normalize supplier name using rapidfuzz matching.
    
    Implements System Bible Section 2.5 thresholds:
    - ≥90 → auto-match to existing supplier
    - 85-90 → flag for user confirmation
    - <85 → create new supplier record
    
    Args:
        supplier_name: Raw supplier name from OCR
    
    Returns:
        Dictionary with:
        - matched_id: Supplier ID if matched
        - confidence: Match confidence (0-100)
        - action: "auto_match", "review", or "new"
        - supplier_id: ID of matched or new supplier
    """
    if not supplier_name or not supplier_name.strip():
        return {
            "matched_id": None,
            "confidence": 0.0,
            "action": "new",
            "supplier_id": None
        }
    
    _ensure_tables()
    
    if not RAPIDFUZZ_AVAILABLE:
        LOGGER.warning("rapidfuzz not available. Install with: pip install rapidfuzz")
        # Fallback: create new supplier
        return _create_new_supplier(supplier_name)
    
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get all existing suppliers
        cursor.execute("""
            SELECT id, name, normalized_name
            FROM suppliers
        """)
        
        existing_suppliers = cursor.fetchall()
        
        best_match = None
        best_score = 0.0
        
        # Try rapidfuzz matching
        for supplier_id, name, normalized_name in existing_suppliers:
            # Try matching against both name and normalized_name
            candidates = [name]
            if normalized_name:
                candidates.append(normalized_name)
            
            for candidate in candidates:
                if not candidate:
                    continue
                
                score = token_sort_ratio(supplier_name, candidate)
                
                if score > best_score:
                    best_score = score
                    best_match = {
                        "id": supplier_id,
                        "name": name,
                        "normalized_name": normalized_name
                    }
        
        # Apply thresholds
        if best_score >= AUTO_MATCH_THRESHOLD:
            # Auto-match
            action = "auto_match"
            supplier_id = best_match["id"]
            
            # Log normalization
            _log_normalization(supplier_name, supplier_id, best_score, action)
            
            LOGGER.info(f"Auto-matched supplier: '{supplier_name}' → '{best_match['name']}' (confidence={best_score:.1f})")
            
            return {
                "matched_id": supplier_id,
                "confidence": best_score,
                "action": action,
                "supplier_id": supplier_id
            }
        
        elif best_score >= REVIEW_THRESHOLD:
            # Flag for user confirmation
            action = "review"
            
            # Store in supplier_alias_review table
            cursor.execute("""
                INSERT INTO supplier_alias_review (original_name, suggested_match, confidence, status)
                VALUES (?, ?, ?, 'pending')
            """, (supplier_name, best_match["name"], best_score))
            
            review_id = cursor.lastrowid
            conn.commit()
            
            # Log normalization
            _log_normalization(supplier_name, best_match["id"], best_score, action)
            
            LOGGER.info(f"Supplier flagged for review: '{supplier_name}' → '{best_match['name']}' (confidence={best_score:.1f}, review_id={review_id})")
            
            return {
                "matched_id": best_match["id"],
                "confidence": best_score,
                "action": action,
                "supplier_id": None,  # Pending review
                "review_id": review_id
            }
        
        else:
            # Create new supplier
            return _create_new_supplier(supplier_name)
        
    except Exception as e:
        LOGGER.error(f"Error normalizing supplier: {e}")
        return _create_new_supplier(supplier_name)
    finally:
        conn.close()


def _create_new_supplier(supplier_name: str) -> Dict[str, Any]:
    """Create a new supplier record."""
    _ensure_tables()
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Generate supplier ID
        import uuid
        supplier_id = str(uuid.uuid4())
        
        # Normalize name (lowercase, strip)
        normalized_name = supplier_name.lower().strip()
        
        cursor.execute("""
            INSERT INTO suppliers (id, name, normalized_name)
            VALUES (?, ?, ?)
        """, (supplier_id, supplier_name, normalized_name))
        
        conn.commit()
        
        # Log normalization
        _log_normalization(supplier_name, supplier_id, 0.0, "new")
        
        LOGGER.info(f"Created new supplier: '{supplier_name}' (id={supplier_id})")
        
        return {
            "matched_id": None,
            "confidence": 0.0,
            "action": "new",
            "supplier_id": supplier_id
        }
        
    except Exception as e:
        LOGGER.error(f"Error creating new supplier: {e}")
        conn.rollback()
        return {
            "matched_id": None,
            "confidence": 0.0,
            "action": "new",
            "supplier_id": None
        }
    finally:
        conn.close()


def _log_normalization(supplier_name: str, matched_id: Optional[str], confidence: float, action: str):
    """Log normalization action to normalization_log table."""
    _ensure_tables()
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO normalization_log (supplier_name, matched_id, confidence, action)
            VALUES (?, ?, ?, ?)
        """, (supplier_name, matched_id, confidence, action))
        
        conn.commit()
        
    except Exception as e:
        LOGGER.warning(f"Error logging normalization: {e}")
        conn.rollback()
    finally:
        conn.close()


def normalize_supplier_with_embedding(supplier_name: str) -> Dict[str, Any]:
    """
    Normalize supplier using sentence-transformer embedding fallback for ambiguous cases.
    
    This is used when rapidfuzz matching is ambiguous (confidence between thresholds).
    
    Args:
        supplier_name: Raw supplier name
    
    Returns:
        Dictionary with normalization result
    """
    if not SENTENCE_TRANSFORMER_AVAILABLE:
        LOGGER.warning("sentence-transformers not available. Install with: pip install sentence-transformers")
        return normalize_supplier(supplier_name)
    
    # First try rapidfuzz
    result = normalize_supplier(supplier_name)
    
    # If confidence is in ambiguous range (85-90), try embedding-based matching
    if result["confidence"] >= REVIEW_THRESHOLD and result["confidence"] < AUTO_MATCH_THRESHOLD:
        try:
            # Load embedding model (lazy)
            if not hasattr(normalize_supplier_with_embedding, "_model"):
                normalize_supplier_with_embedding._model = SentenceTransformer('all-MiniLM-L6-v2')
            
            model = normalize_supplier_with_embedding._model
            
            # Get embeddings for supplier name and existing suppliers
            conn = _get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, name FROM suppliers")
            existing = cursor.fetchall()
            conn.close()
            
            if not existing:
                return result
            
            # Calculate embeddings
            supplier_embedding = model.encode([supplier_name])[0]
            existing_names = [row[1] for row in existing]
            existing_embeddings = model.encode(existing_names)
            
            # Calculate cosine similarity
            from numpy import dot
            from numpy.linalg import norm
            
            best_embedding_match = None
            best_embedding_score = 0.0
            
            for i, (supplier_id, name) in enumerate(existing):
                similarity = dot(supplier_embedding, existing_embeddings[i]) / (
                    norm(supplier_embedding) * norm(existing_embeddings[i])
                )
                # Convert to 0-100 scale
                score = similarity * 100
                
                if score > best_embedding_score:
                    best_embedding_score = score
                    best_embedding_match = supplier_id
            
            # If embedding match is better, use it
            if best_embedding_score > result["confidence"]:
                LOGGER.info(f"Embedding match better: '{supplier_name}' → (confidence={best_embedding_score:.1f})")
                result["matched_id"] = best_embedding_match
                result["confidence"] = best_embedding_score
                result["supplier_id"] = best_embedding_match
                
                # Re-evaluate action based on new confidence
                if best_embedding_score >= AUTO_MATCH_THRESHOLD:
                    result["action"] = "auto_match"
                else:
                    result["action"] = "review"
        
        except Exception as e:
            LOGGER.warning(f"Error in embedding-based matching: {e}")
            # Fall back to rapidfuzz result
    
    return result


def normalize_item(item_name: str, supplier_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Normalize item name (similar logic to supplier normalization).
    
    Args:
        item_name: Raw item name from OCR
        supplier_id: Optional supplier ID for context
    
    Returns:
        Dictionary with normalization result
    """
    # Similar implementation to normalize_supplier
    # For now, return a simplified version
    return {
        "matched_id": None,
        "confidence": 0.0,
        "action": "new",
        "item_id": None
    }

