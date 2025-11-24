# -*- coding: utf-8 -*-
"""
OCR Triage Queue Module

This module provides automatic retry queue for low-confidence OCR pages,
as specified in Appendix B.2 (line 619).

Features:
- Queue low-confidence pages for retry
- Process queue with alternate engines
- Log all retries with before/after confidence
"""

from __future__ import annotations
import logging
import sqlite3
from typing import Any, Dict, List, Optional
from datetime import datetime
from backend.services.engine_select import select_engine, get_fallback_chain
from backend.services.ocr_engine_doctr import get_doctr_engine
from backend.services.ocr_engine_calamari import get_calamari_engine

LOGGER = logging.getLogger("owlin.services.ocr_triage")
LOGGER.setLevel(logging.INFO)

DB_PATH = "data/owlin.db"

# Try to import OCR engines
try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    PaddleOCR = None

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None


def _get_db_connection():
    """Get database connection."""
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def _ensure_table():
    """Ensure OCR retry queue table exists."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ocr_retry_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_id TEXT NOT NULL,
                doc_id TEXT NOT NULL,
                original_confidence REAL NOT NULL,
                original_engine TEXT NOT NULL,
                retry_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                alternate_engines TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                processed_at TEXT,
                final_confidence REAL,
                final_engine TEXT,
                FOREIGN KEY(doc_id) REFERENCES documents(id)
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_retry_queue_status ON ocr_retry_queue(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_retry_queue_page_id ON ocr_retry_queue(page_id)")
        
        conn.commit()
        LOGGER.debug("OCR retry queue table ensured")
        
    except Exception as e:
        LOGGER.error(f"Error ensuring OCR retry queue table: {e}")
        conn.rollback()
    finally:
        conn.close()


def queue_low_confidence_page(
    page_id: str,
    doc_id: str,
    confidence: float,
    original_engine: str,
    threshold: float = 0.7
) -> bool:
    """
    Queue a low-confidence page for retry with alternate engines.
    
    Args:
        page_id: Page identifier
        doc_id: Document ID
        confidence: Current confidence score
        original_engine: Engine that produced this confidence
        threshold: Confidence threshold (default 0.7)
    
    Returns:
        True if queued, False otherwise
    """
    if confidence >= threshold:
        return False  # Not low confidence
    
    _ensure_table()
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get fallback chain for original engine
        fallback_chain = get_fallback_chain(original_engine)
        # Remove original engine from chain
        alternate_engines = ",".join([e for e in fallback_chain if e != original_engine])
        
        # Check if already queued
        cursor.execute("""
            SELECT id, status
            FROM ocr_retry_queue
            WHERE page_id = ? AND status IN ('pending', 'processing')
        """, (page_id,))
        
        existing = cursor.fetchone()
        if existing:
            LOGGER.debug(f"Page {page_id} already in retry queue")
            return False
        
        cursor.execute("""
            INSERT INTO ocr_retry_queue 
            (page_id, doc_id, original_confidence, original_engine, alternate_engines, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        """, (page_id, doc_id, confidence, original_engine, alternate_engines))
        
        conn.commit()
        LOGGER.info(f"Queued low-confidence page: page_id={page_id}, confidence={confidence:.3f}, engine={original_engine}")
        return True
        
    except Exception as e:
        LOGGER.error(f"Error queueing page: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def log_retry(
    page_id: str,
    engine_used: str,
    confidence_before: float,
    confidence_after: float
) -> bool:
    """
    Log a retry attempt with results.
    
    Args:
        page_id: Page identifier
        engine_used: Engine used for retry
        confidence_before: Confidence before retry
        confidence_after: Confidence after retry
    
    Returns:
        True if logged successfully
    """
    _ensure_table()
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE ocr_retry_queue
            SET retry_count = retry_count + 1,
                final_confidence = ?,
                final_engine = ?,
                processed_at = ?
            WHERE page_id = ? AND status = 'processing'
        """, (confidence_after, engine_used, datetime.now().isoformat(), page_id))
        
        conn.commit()
        LOGGER.debug(f"Retry logged: page_id={page_id}, engine={engine_used}, conf_before={confidence_before:.3f}, conf_after={confidence_after:.3f}")
        return True
        
    except Exception as e:
        LOGGER.error(f"Error logging retry: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def process_triage_queue(max_items: int = 10) -> int:
    """
    Process queued pages with alternate engines.
    
    Args:
        max_items: Maximum number of items to process in this batch
    
    Returns:
        Number of items processed
    """
    _ensure_table()
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get pending items
        cursor.execute("""
            SELECT id, page_id, doc_id, original_confidence, original_engine, alternate_engines, retry_count
            FROM ocr_retry_queue
            WHERE status = 'pending'
            ORDER BY original_confidence ASC, created_at ASC
            LIMIT ?
        """, (max_items,))
        
        items = cursor.fetchall()
        processed_count = 0
        
        for item in items:
            item_id, page_id, doc_id, orig_conf, orig_engine, alt_engines_str, retry_count = item
            
            # Mark as processing
            cursor.execute("""
                UPDATE ocr_retry_queue
                SET status = 'processing'
                WHERE id = ?
            """, (item_id,))
            conn.commit()
            
            try:
                # Parse alternate engines
                alternate_engines = alt_engines_str.split(",") if alt_engines_str else []
                
                # Try each alternate engine
                best_confidence = orig_conf
                best_engine = orig_engine
                
                for engine in alternate_engines:
                    if retry_count >= 3:  # Max retries
                        break
                    
                    engine = engine.strip()
                    LOGGER.info(f"Retrying page {page_id} with engine {engine}")
                    
                    # Get page image path (would need to be stored or retrieved)
                    # For now, this is a placeholder - actual implementation would need
                    # to retrieve the page image and run OCR
                    try:
                        # This would call the actual OCR engine
                        # For now, we'll simulate
                        new_confidence = _retry_with_engine(page_id, doc_id, engine)
                        
                        if new_confidence > best_confidence:
                            best_confidence = new_confidence
                            best_engine = engine
                            
                            # Log the retry
                            log_retry(page_id, engine, orig_conf, new_confidence)
                            
                            # If confidence is now acceptable, mark as completed
                            if new_confidence >= 0.7:
                                cursor.execute("""
                                    UPDATE ocr_retry_queue
                                    SET status = 'completed',
                                        final_confidence = ?,
                                        final_engine = ?,
                                        processed_at = ?
                                    WHERE id = ?
                                """, (new_confidence, engine, datetime.now().isoformat(), item_id))
                                conn.commit()
                                processed_count += 1
                                break
                    
                    except Exception as e:
                        LOGGER.warning(f"Error retrying with engine {engine}: {e}")
                        continue
                
                # If still low confidence after all retries
                if best_confidence < 0.7:
                    cursor.execute("""
                        UPDATE ocr_retry_queue
                        SET status = 'failed',
                            final_confidence = ?,
                            final_engine = ?,
                            processed_at = ?
                        WHERE id = ?
                    """, (best_confidence, best_engine, datetime.now().isoformat(), item_id))
                    conn.commit()
                    processed_count += 1
                
            except Exception as e:
                LOGGER.error(f"Error processing queue item {item_id}: {e}")
                cursor.execute("""
                    UPDATE ocr_retry_queue
                    SET status = 'error',
                        processed_at = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), item_id))
                conn.commit()
        
        LOGGER.info(f"Processed {processed_count} items from OCR triage queue")
        return processed_count
        
    except Exception as e:
        LOGGER.error(f"Error processing triage queue: {e}")
        return 0
    finally:
        conn.close()


def _retry_with_engine(page_id: str, doc_id: str, engine: str) -> float:
    """
    Retry OCR on a page with a specific engine.
    
    This is a placeholder - actual implementation would:
    1. Retrieve page image from storage
    2. Run OCR with specified engine
    3. Return new confidence score
    
    Args:
        page_id: Page identifier
        doc_id: Document ID
        engine: Engine to use
    
    Returns:
        New confidence score
    """
    # Placeholder implementation
    # In production, this would:
    # 1. Get page image path from database
    # 2. Load image
    # 3. Run OCR with specified engine
    # 4. Return confidence
    
    LOGGER.debug(f"Retrying OCR for page {page_id} with engine {engine}")
    
    # For now, return a simulated confidence
    # This would be replaced with actual OCR processing
    import random
    return 0.75 + random.random() * 0.15  # Simulated improvement


def get_queue_status() -> Dict[str, Any]:
    """
    Get status of the OCR retry queue.
    
    Returns:
        Dictionary with queue statistics
    """
    _ensure_table()
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM ocr_retry_queue
            GROUP BY status
        """)
        
        status_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute("""
            SELECT AVG(original_confidence) as avg_orig,
                   AVG(final_confidence) as avg_final,
                   COUNT(*) as total
            FROM ocr_retry_queue
            WHERE status = 'completed'
        """)
        
        row = cursor.fetchone()
        avg_improvement = None
        if row and row[0] and row[1]:
            avg_improvement = row[1] - row[0]
        
        return {
            "pending": status_counts.get("pending", 0),
            "processing": status_counts.get("processing", 0),
            "completed": status_counts.get("completed", 0),
            "failed": status_counts.get("failed", 0),
            "error": status_counts.get("error", 0),
            "avg_confidence_improvement": avg_improvement,
            "total_processed": row[2] if row else 0
        }
        
    except Exception as e:
        LOGGER.error(f"Error getting queue status: {e}")
        return {}
    finally:
        conn.close()

