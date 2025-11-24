"""
Exploration History Service

Stores and retrieves exploration sessions for learning and replay.
"""

import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("owlin.services.exploration_history")

DB_PATH = "data/owlin.db"


def _get_db_connection():
    """Get database connection."""
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def _ensure_tables():
    """Ensure exploration history tables exist."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Create exploration_sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exploration_sessions (
                id TEXT PRIMARY KEY,
                user_message TEXT NOT NULL,
                response_text TEXT,
                created_at TEXT NOT NULL,
                exploration_time REAL,
                mode TEXT DEFAULT 'single_turn',
                success BOOLEAN DEFAULT 1,
                timeout BOOLEAN DEFAULT 0,
                model_used TEXT,
                request_id TEXT
            )
        """)
        
        # Create exploration_metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exploration_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                files_searched INTEGER DEFAULT 0,
                files_read TEXT,  -- JSON array of file paths
                searches_executed INTEGER DEFAULT 0,
                search_terms TEXT,  -- JSON array of search terms
                findings_count INTEGER DEFAULT 0,
                traces_executed INTEGER DEFAULT 0,
                FOREIGN KEY(session_id) REFERENCES exploration_sessions(id) ON DELETE CASCADE
            )
        """)
        
        # Create exploration_findings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exploration_findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                finding_type TEXT NOT NULL,  -- 'search', 'file', 'trace', 'grep', etc.
                file_path TEXT,
                line_number INTEGER,
                match_text TEXT,
                context TEXT,
                score REAL,
                FOREIGN KEY(session_id) REFERENCES exploration_sessions(id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON exploration_sessions(created_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_message ON exploration_sessions(user_message)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_metadata_session_id ON exploration_metadata(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_findings_session_id ON exploration_findings(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_findings_type ON exploration_findings(finding_type)")
        
        conn.commit()
        logger.debug("Exploration history tables ensured")
        
    except Exception as e:
        logger.error(f"Error ensuring exploration history tables: {e}")
        conn.rollback()
    finally:
        conn.close()


def save_exploration_session(
    session_id: str,
    user_message: str,
    response_text: Optional[str],
    exploration_metadata: Dict[str, Any],
    findings: List[Dict[str, Any]],
    request_id: Optional[str] = None
) -> bool:
    """
    Save an exploration session to the database.
    
    Args:
        session_id: Unique session identifier
        user_message: User's original message
        response_text: Final response text
        exploration_metadata: Metadata about the exploration
        findings: List of findings discovered
        request_id: Optional request ID for correlation
        
    Returns:
        True if saved successfully, False otherwise
    """
    _ensure_tables()
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Insert session
        cursor.execute("""
            INSERT OR REPLACE INTO exploration_sessions (
                id, user_message, response_text, created_at,
                exploration_time, mode, success, timeout, model_used, request_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            user_message,
            response_text,
            datetime.now().isoformat(),
            exploration_metadata.get("exploration_time"),
            exploration_metadata.get("mode", "single_turn"),
            exploration_metadata.get("success", True),
            exploration_metadata.get("timed_out", False),
            exploration_metadata.get("model_used"),
            request_id
        ))
        
        # Insert metadata
        cursor.execute("""
            INSERT OR REPLACE INTO exploration_metadata (
                session_id, files_searched, files_read, searches_executed,
                search_terms, findings_count, traces_executed
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            exploration_metadata.get("files_searched", 0),
            json.dumps(exploration_metadata.get("files_read", [])),
            exploration_metadata.get("searches_executed", 0),
            json.dumps(exploration_metadata.get("search_terms", [])),
            exploration_metadata.get("findings_count", 0),
            exploration_metadata.get("traces_executed", 0)
        ))
        
        # Delete old findings for this session
        cursor.execute("DELETE FROM exploration_findings WHERE session_id = ?", (session_id,))
        
        # Insert findings
        for finding in findings[:100]:  # Limit to 100 findings per session
            cursor.execute("""
                INSERT INTO exploration_findings (
                    session_id, finding_type, file_path, line_number,
                    match_text, context, score
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                finding.get("type", "unknown"),
                finding.get("file"),
                finding.get("line", 0),
                finding.get("match", "")[:500],  # Limit match text
                finding.get("context", "")[:2000],  # Limit context
                finding.get("score", 0.0)
            ))
        
        conn.commit()
        logger.info(f"Saved exploration session {session_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving exploration session: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_exploration_sessions(
    limit: int = 20,
    offset: int = 0,
    search_query: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve exploration sessions.
    
    Args:
        limit: Maximum number of sessions to return
        offset: Offset for pagination
        search_query: Optional search query to filter by user message
        
    Returns:
        List of session dictionaries
    """
    _ensure_tables()
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        if search_query:
            cursor.execute("""
                SELECT s.*, m.files_searched, m.files_read, m.searches_executed,
                       m.search_terms, m.findings_count, m.traces_executed
                FROM exploration_sessions s
                LEFT JOIN exploration_metadata m ON s.id = m.session_id
                WHERE s.user_message LIKE ?
                ORDER BY s.created_at DESC
                LIMIT ? OFFSET ?
            """, (f"%{search_query}%", limit, offset))
        else:
            cursor.execute("""
                SELECT s.*, m.files_searched, m.files_read, m.searches_executed,
                       m.search_terms, m.findings_count, m.traces_executed
                FROM exploration_sessions s
                LEFT JOIN exploration_metadata m ON s.id = m.session_id
                ORDER BY s.created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
        
        rows = cursor.fetchall()
        sessions = []
        
        for row in rows:
            session = {
                "id": row[0],
                "user_message": row[1],
                "response_text": row[2],
                "created_at": row[3],
                "exploration_time": row[4],
                "mode": row[5],
                "success": bool(row[6]),
                "timeout": bool(row[7]),
                "model_used": row[8],
                "request_id": row[9],
                "files_searched": row[10] if row[10] is not None else 0,
                "files_read": json.loads(row[11]) if row[11] else [],
                "searches_executed": row[12] if row[12] is not None else 0,
                "search_terms": json.loads(row[13]) if row[13] else [],
                "findings_count": row[14] if row[14] is not None else 0,
                "traces_executed": row[15] if row[15] is not None else 0,
            }
            sessions.append(session)
        
        return sessions
        
    except Exception as e:
        logger.error(f"Error retrieving exploration sessions: {e}")
        return []
    finally:
        conn.close()


def get_exploration_session(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific exploration session with all details.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Session dictionary with findings, or None if not found
    """
    _ensure_tables()
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get session and metadata
        cursor.execute("""
            SELECT s.*, m.files_searched, m.files_read, m.searches_executed,
                   m.search_terms, m.findings_count, m.traces_executed
            FROM exploration_sessions s
            LEFT JOIN exploration_metadata m ON s.id = m.session_id
            WHERE s.id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        session = {
            "id": row[0],
            "user_message": row[1],
            "response_text": row[2],
            "created_at": row[3],
            "exploration_time": row[4],
            "mode": row[5],
            "success": bool(row[6]),
            "timeout": bool(row[7]),
            "model_used": row[8],
            "request_id": row[9],
            "files_searched": row[10] if row[10] is not None else 0,
            "files_read": json.loads(row[11]) if row[11] else [],
            "searches_executed": row[12] if row[12] is not None else 0,
            "search_terms": json.loads(row[13]) if row[13] else [],
            "findings_count": row[14] if row[14] is not None else 0,
            "traces_executed": row[15] if row[15] is not None else 0,
        }
        
        # Get findings
        cursor.execute("""
            SELECT finding_type, file_path, line_number, match_text, context, score
            FROM exploration_findings
            WHERE session_id = ?
            ORDER BY score DESC, id ASC
        """, (session_id,))
        
        findings = []
        for finding_row in cursor.fetchall():
            findings.append({
                "type": finding_row[0],
                "file": finding_row[1],
                "line": finding_row[2],
                "match": finding_row[3],
                "context": finding_row[4],
                "score": finding_row[5]
            })
        
        session["findings"] = findings
        return session
        
    except Exception as e:
        logger.error(f"Error retrieving exploration session: {e}")
        return None
    finally:
        conn.close()


def delete_exploration_session(session_id: str) -> bool:
    """
    Delete an exploration session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        True if deleted, False otherwise
    """
    _ensure_tables()
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM exploration_sessions WHERE id = ?", (session_id,))
        conn.commit()
        logger.info(f"Deleted exploration session {session_id}")
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error deleting exploration session: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_exploration_stats() -> Dict[str, Any]:
    """
    Get statistics about exploration history.
    
    Returns:
        Dictionary with statistics
    """
    _ensure_tables()
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Total sessions
        cursor.execute("SELECT COUNT(*) FROM exploration_sessions")
        total_sessions = cursor.fetchone()[0]
        
        # Successful sessions
        cursor.execute("SELECT COUNT(*) FROM exploration_sessions WHERE success = 1")
        successful_sessions = cursor.fetchone()[0]
        
        # Average exploration time
        cursor.execute("SELECT AVG(exploration_time) FROM exploration_sessions WHERE exploration_time IS NOT NULL")
        avg_time = cursor.fetchone()[0] or 0.0
        
        # Total findings
        cursor.execute("SELECT SUM(findings_count) FROM exploration_metadata")
        total_findings = cursor.fetchone()[0] or 0
        
        # Most common search terms
        cursor.execute("""
            SELECT search_terms FROM exploration_metadata
            WHERE search_terms IS NOT NULL AND search_terms != '[]'
        """)
        all_terms = []
        for row in cursor.fetchall():
            terms = json.loads(row[0])
            all_terms.extend(terms)
        
        # Count term frequency
        from collections import Counter
        term_counts = Counter(all_terms)
        top_terms = [{"term": term, "count": count} for term, count in term_counts.most_common(10)]
        
        return {
            "total_sessions": total_sessions,
            "successful_sessions": successful_sessions,
            "success_rate": (successful_sessions / total_sessions * 100) if total_sessions > 0 else 0,
            "avg_exploration_time": round(avg_time, 2),
            "total_findings": total_findings,
            "top_search_terms": top_terms
        }
        
    except Exception as e:
        logger.error(f"Error getting exploration stats: {e}")
        return {}
    finally:
        conn.close()

