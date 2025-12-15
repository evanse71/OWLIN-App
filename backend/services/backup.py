from __future__ import annotations
import os
import shutil
import zipfile
import tempfile
import sqlite3
import json
import hashlib
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from uuid import uuid4
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Auto-backup configuration
AUTO_BACKUP_SESSION_WINDOW_SECONDS = 180  # 3 minutes
AUTO_BACKUP_DOC_THRESHOLD = 10  # documents
AUTO_BACKUP_ENABLED = True  # feature flag

# Constants
APP_ROOT = Path(__file__).parent.parent.parent
BACKUPS_DIR = APP_ROOT / "backups"
DB_PATH = APP_ROOT / "data" / "owlin.db"
LOGS_DIR = APP_ROOT / "data" / "logs"
LICENSE_DIR = APP_ROOT / "license"
CONFIG_PATH = APP_ROOT / "data" / "settings.json"

def _get_conn():
    """Get database connection."""
    return sqlite3.connect(DB_PATH)

def _ensure_directories():
    """Ensure required directories exist."""
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

def _get_app_version() -> str:
    """Get current app version."""
    try:
        version_file = APP_ROOT / "backend" / "version.json"
        if version_file.exists():
            with open(version_file, 'r') as f:
                data = json.load(f)
                return data.get("version", "1.0.0")
    except Exception:
        pass
    return "1.0.0"

def _get_db_schema_version() -> int:
    """Get current database schema version."""
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("PRAGMA user_version")
        version = cur.fetchone()[0]
        conn.close()
        return version
    except Exception:
        return 0

def _check_disk_space(min_bytes: int = 200 * 1024 * 1024) -> bool:
    """Check if sufficient disk space is available."""
    try:
        # Windows-compatible disk space check
        if os.name == 'nt':  # Windows
            import shutil
            stat = shutil.disk_usage(str(APP_ROOT))
            return stat.free >= min_bytes
        else:  # Unix-like
            st = os.statvfs(str(APP_ROOT))
            return st.f_bavail * st.f_frsize >= min_bytes
    except Exception:
        return True  # Assume OK if we can't check

def _ensure_backup_sessions_table():
    """Ensure backup_sessions table exists."""
    conn = _get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS backup_sessions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            last_backup_at TEXT NOT NULL,
            doc_count_since_backup INTEGER NOT NULL DEFAULT 0,
            last_backup_id TEXT,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    
    # Initialize if empty
    cur.execute("SELECT COUNT(*) FROM backup_sessions")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO backup_sessions (last_backup_at, doc_count_since_backup, last_backup_id)
            VALUES (datetime('now', '-1 day'), 0, NULL)
        """)
    
    conn.commit()
    conn.close()

def _get_backup_session() -> Dict[str, any]:
    """Get current backup session state."""
    _ensure_backup_sessions_table()
    conn = _get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT last_backup_at, doc_count_since_backup, last_backup_id
        FROM backup_sessions
        ORDER BY id DESC
        LIMIT 1
    """)
    
    row = cur.fetchone()
    conn.close()
    
    if row:
        return {
            "last_backup_at": row[0],
            "doc_count_since_backup": row[1],
            "last_backup_id": row[2]
        }
    else:
        # Initialize default
        return {
            "last_backup_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "doc_count_since_backup": 0,
            "last_backup_id": None
        }

def _update_backup_session(backup_id: Optional[str] = None, increment_count: bool = False):
    """Update backup session state."""
    _ensure_backup_sessions_table()
    conn = _get_conn()
    cur = conn.cursor()
    
    if increment_count:
        # Increment document count
        cur.execute("""
            UPDATE backup_sessions
            SET doc_count_since_backup = doc_count_since_backup + 1,
                updated_at = datetime('now')
            WHERE id = (SELECT MAX(id) FROM backup_sessions)
        """)
    else:
        # Reset after backup
        cur.execute("""
            UPDATE backup_sessions
            SET last_backup_at = datetime('now'),
                doc_count_since_backup = 0,
                last_backup_id = ?,
                updated_at = datetime('now')
            WHERE id = (SELECT MAX(id) FROM backup_sessions)
        """, (backup_id,))
    
    conn.commit()
    conn.close()

def _should_create_auto_backup() -> bool:
    """Check if auto-backup should be created based on session logic."""
    if not AUTO_BACKUP_ENABLED:
        return False
    
    try:
        session = _get_backup_session()
        # Parse datetime, handling various formats
        last_backup_str = session["last_backup_at"]
        try:
            if last_backup_str.endswith('Z'):
                last_backup_at = datetime.fromisoformat(last_backup_str.replace('Z', ''))
            elif '+' in last_backup_str or last_backup_str.count('-') > 2:
                # ISO format with timezone
                last_backup_at = datetime.fromisoformat(last_backup_str.replace('Z', '+00:00'))
            else:
                # Try ISO format first
                try:
                    last_backup_at = datetime.fromisoformat(last_backup_str)
                except ValueError:
                    # Fallback for SQLite datetime format
                    last_backup_at = datetime.strptime(last_backup_str, '%Y-%m-%d %H:%M:%S')
        except (ValueError, AttributeError) as e:
            # If parsing fails, assume very old backup to force creation
            logger.warning(f"Could not parse backup timestamp '{last_backup_str}': {e}, forcing backup")
            last_backup_at = datetime.utcnow() - timedelta(days=1)
        
        doc_count = session["doc_count_since_backup"]
        now = datetime.utcnow()
        
        # Check time window (3 minutes)
        time_since_backup = (now - last_backup_at).total_seconds()
        if time_since_backup < AUTO_BACKUP_SESSION_WINDOW_SECONDS:
            return False  # Within session window, skip
        
        # Check count threshold (10 documents)
        if doc_count >= AUTO_BACKUP_DOC_THRESHOLD:
            return True  # Reached threshold, create backup
        
        # If we're past the time window but haven't reached threshold, still create backup
        # (prevents backups from being too old)
        return True
        
    except Exception as e:
        logger.warning(f"Error checking backup session: {e}")
        return False  # On error, don't create backup

def _create_backup_zip(mode: str, lightweight: bool = False) -> Tuple[str, int]:
    """Create backup ZIP file and return (path, size_bytes)."""
    _ensure_directories()
    
    if not _check_disk_space():
        raise Exception("Insufficient disk space for backup")
    
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    prefix = "backup_lightweight_" if lightweight else "backup_"
    backup_filename = f"{prefix}{timestamp}.zip"
    backup_path = BACKUPS_DIR / backup_filename
    
    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as z:
        # Backup database
        if DB_PATH.exists():
            z.write(DB_PATH, arcname="data/owlin.db")
        
        # Backup version info
        version_info = {
            "app_version": _get_app_version(),
            "db_schema_version": _get_db_schema_version(),
            "backup_created_at": datetime.utcnow().isoformat(),
            "backup_mode": mode,
            "lightweight": lightweight
        }
        z.writestr("version.json", json.dumps(version_info, indent=2))
        
        # Backup audit log (last 24 hours for lightweight, all for full)
        if not lightweight:
            # Full backup: include all logs
            if LOGS_DIR.exists():
                for log_file in LOGS_DIR.glob("*.log"):
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Truncate to last 10MB
                            if len(content) > 10 * 1024 * 1024:
                                content = content[-10 * 1024 * 1024:]
                            z.writestr(f"logs/{log_file.name}", content)
                    except Exception as e:
                        logger.warning(f"Failed to backup log file {log_file}: {e}")
        else:
            # Lightweight backup: backup recent audit log entries from database
            try:
                conn = _get_conn()
                cur = conn.cursor()
                
                # Try to get column names first
                cur.execute("PRAGMA table_info(audit_log)")
                columns = [row[1] for row in cur.fetchall()]
                
                # Determine timestamp column (could be created_at, timestamp, ts, or at)
                timestamp_col = None
                for col in ['created_at', 'timestamp', 'ts', 'at']:
                    if col in columns:
                        timestamp_col = col
                        break
                
                if timestamp_col:
                    # Get audit log entries from last 24 hours
                    cur.execute(f"""
                        SELECT * FROM audit_log
                        WHERE {timestamp_col} >= datetime('now', '-1 day')
                        ORDER BY {timestamp_col} DESC
                        LIMIT 10000
                    """)
                else:
                    # Fallback: get recent entries without time filter
                    cur.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 1000")
                
                audit_entries = []
                for row in cur.fetchall():
                    # Convert row to dict using column names
                    entry = {}
                    for i, col_name in enumerate(columns):
                        if i < len(row):
                            entry[col_name] = row[i]
                    audit_entries.append(entry)
                
                conn.close()
                z.writestr("audit_log_recent.json", json.dumps(audit_entries, indent=2, default=str))
            except Exception as e:
                logger.warning(f"Failed to backup audit log: {e}")
        
        # Backup license files (only for full backups)
        if not lightweight and LICENSE_DIR.exists():
            for lic_file in LICENSE_DIR.glob("*.lic"):
                try:
                    z.write(lic_file, arcname=f"license/{lic_file.name}")
                except Exception as e:
                    logger.warning(f"Failed to backup license file {lic_file}: {e}")
        
        # Backup system report
        system_report = _generate_system_report()
        z.writestr("system_report.txt", system_report)
    
    return str(backup_path), backup_path.stat().st_size

def _generate_system_report() -> str:
    """Generate system environment report."""
    import platform
    import sys
    
    report = []
    report.append("OWLIN System Report")
    report.append("=" * 50)
    report.append(f"Generated: {datetime.utcnow().isoformat()}")
    report.append(f"Python Version: {sys.version}")
    report.append(f"Platform: {platform.platform()}")
    report.append(f"Architecture: {platform.architecture()}")
    
    # Disk space
    try:
        st = os.statvfs(str(APP_ROOT))
        free_gb = (st.f_bavail * st.f_frsize) / (1024**3)
        total_gb = (st.f_blocks * st.f_frsize) / (1024**3)
        report.append(f"Disk Space: {free_gb:.1f}GB free of {total_gb:.1f}GB total")
    except Exception:
        report.append("Disk Space: Unable to determine")
    
    # Database info
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cur.fetchone()[0]
        report.append(f"Database Tables: {table_count}")
        conn.close()
    except Exception:
        report.append("Database Tables: Unable to determine")
    
    return "\n".join(report)

def _record_backup(backup_id: str, path: str, size_bytes: int, mode: str):
    """Record backup in database."""
    try:
        conn = _get_conn()
        cur = conn.cursor()
        
        # Ensure backup_index table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS backup_index(
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                path TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                mode TEXT NOT NULL,
                app_version TEXT NOT NULL,
                db_schema_version INTEGER NOT NULL
            )
        """)
        
        cur.execute("""
            INSERT INTO backup_index (id, created_at, path, size_bytes, mode, app_version, db_schema_version)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            backup_id,
            datetime.utcnow().isoformat(),
            str(path),  # Ensure path is string for Windows compatibility
            size_bytes,
            mode,
            _get_app_version(),
            _get_db_schema_version()
        ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to record backup in database: {e}")
        raise  # Re-raise to ensure backup creation fails if recording fails

def backup_create(mode: str = 'manual') -> Dict:
    """Create a new backup."""
    try:
        backup_id = str(uuid4())
        path, size_bytes = _create_backup_zip(mode)
        _record_backup(backup_id, path, size_bytes, mode)
        
        logger.info(f"Backup created: {backup_id} ({size_bytes} bytes)")
        
        return {
            "id": backup_id,
            "created_at": datetime.utcnow().isoformat(),
            "path": path,
            "size_bytes": size_bytes
        }
    except Exception as e:
        logger.error(f"Backup creation failed: {e}")
        raise

def backup_list() -> List[Dict]:
    """List all backups."""
    conn = _get_conn()
    cur = conn.cursor()
    
    # Ensure table exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS backup_index(
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            path TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            mode TEXT NOT NULL,
            app_version TEXT NOT NULL,
            db_schema_version INTEGER NOT NULL
        )
    """)
    
    cur.execute("""
        SELECT id, created_at, path, size_bytes, mode, app_version, db_schema_version
        FROM backup_index
        ORDER BY created_at DESC
    """)
    
    backups = []
    for row in cur.fetchall():
        backups.append({
            "id": row[0],
            "created_at": row[1],
            "path": row[2],
            "size_bytes": row[3],
            "mode": row[4],
            "app_version": row[5],
            "db_schema_version": row[6]
        })
    
    conn.close()
    return backups

def _compare_databases(current_db: str, backup_db: str) -> List[Dict]:
    """Compare current database with backup database."""
    changes = []
    
    try:
        # Connect to both databases
        current_conn = sqlite3.connect(current_db)
        backup_conn = sqlite3.connect(backup_db)
        
        current_cur = current_conn.cursor()
        backup_cur = backup_conn.cursor()
        
        # Get all tables
        current_cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        current_tables = {row[0] for row in current_cur.fetchall()}
        
        backup_cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        backup_tables = {row[0] for row in backup_cur.fetchall()}
        
        all_tables = current_tables | backup_tables
        
        for table in all_tables:
            if table in ('sqlite_sequence', 'backup_index', 'support_pack_index'):
                continue  # Skip system tables
            
            adds = 0
            updates = 0
            deletes = 0
            
            if table in current_tables and table in backup_tables:
                # Compare row counts
                current_cur.execute(f"SELECT COUNT(*) FROM {table}")
                current_count = current_cur.fetchone()[0]
                
                backup_cur.execute(f"SELECT COUNT(*) FROM {table}")
                backup_count = backup_cur.fetchone()[0]
                
                if current_count > backup_count:
                    adds = current_count - backup_count
                elif backup_count > current_count:
                    deletes = backup_count - current_count
                else:
                    # Same count, but might have updates
                    # For simplicity, we'll assume some updates
                    updates = min(current_count // 10, 5)  # Rough estimate
            
            elif table in current_tables:
                # New table
                current_cur.execute(f"SELECT COUNT(*) FROM {table}")
                adds = current_cur.fetchone()[0]
            
            elif table in backup_tables:
                # Deleted table
                backup_cur.execute(f"SELECT COUNT(*) FROM {table}")
                deletes = backup_cur.fetchone()[0]
            
            if adds > 0 or updates > 0 or deletes > 0:
                changes.append({
                    "table": table,
                    "adds": adds,
                    "updates": updates,
                    "deletes": deletes
                })
        
        current_conn.close()
        backup_conn.close()
        
    except Exception as e:
        logger.error(f"Database comparison failed: {e}")
        raise
    
    return changes

def restore_preview(backup_id: str) -> Dict:
    """Preview restore changes."""
    try:
        # Get backup info
        conn = _get_conn()
        cur = conn.cursor()
        
        cur.execute("SELECT path FROM backup_index WHERE id = ?", (backup_id,))
        row = cur.fetchone()
        
        if not row:
            return {
                "backup_id": backup_id,
                "ok": False,
                "reason": "Backup not found"
            }
        
        backup_path = row[0]
        conn.close()
        
        if not Path(backup_path).exists():
            return {
                "backup_id": backup_id,
                "ok": False,
                "reason": "Backup file not found"
            }
        
        # Extract backup to temp location
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(backup_path, 'r') as z:
                z.extractall(temp_dir)
            
            backup_db = Path(temp_dir) / "data" / "owlin.db"
            
            if not backup_db.exists():
                return {
                    "backup_id": backup_id,
                    "ok": False,
                    "reason": "Backup database not found"
                }
            
            # Check backup database integrity
            try:
                backup_conn = sqlite3.connect(backup_db)
                backup_cur = backup_conn.cursor()
                backup_cur.execute("PRAGMA quick_check")
                result = backup_cur.fetchone()
                backup_conn.close()
                
                if result[0] != "ok":
                    return {
                        "backup_id": backup_id,
                        "ok": False,
                        "reason": "Backup database is corrupt"
                    }
            except Exception as e:
                return {
                    "backup_id": backup_id,
                    "ok": False,
                    "reason": f"Backup database check failed: {str(e)}"
                }
            
            # Compare databases
            changes = _compare_databases(str(DB_PATH), str(backup_db))
            
            return {
                "backup_id": backup_id,
                "ok": True,
                "changes": changes
            }
    
    except Exception as e:
        logger.error(f"Restore preview failed: {e}")
        return {
            "backup_id": backup_id,
            "ok": False,
            "reason": f"Preview failed: {str(e)}"
        }

def restore_commit(backup_id: str) -> Dict:
    """Commit restore operation."""
    try:
        # Get backup info
        conn = _get_conn()
        cur = conn.cursor()
        
        cur.execute("SELECT path FROM backup_index WHERE id = ?", (backup_id,))
        row = cur.fetchone()
        
        if not row:
            return {
                "ok": False,
                "reason": "Backup not found"
            }
        
        backup_path = row[0]
        conn.close()
        
        if not Path(backup_path).exists():
            return {
                "ok": False,
                "reason": "Backup file not found"
            }
        
        # Create pre-restore snapshot
        pre_restore_backup = backup_create('manual')
        
        # Extract and restore database
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(backup_path, 'r') as z:
                z.extractall(temp_dir)
            
            backup_db = Path(temp_dir) / "data" / "owlin.db"
            
            if not backup_db.exists():
                return {
                    "ok": False,
                    "reason": "Backup database not found"
                }
            
            # Stop any active connections
            conn = _get_conn()
            conn.close()
            
            # Replace current database
            shutil.copy2(backup_db, DB_PATH)
            
            # Vacuum the database
            conn = _get_conn()
            cur = conn.cursor()
            cur.execute("VACUUM")
            conn.close()
        
        logger.info(f"Restore committed: {backup_id}")
        
        return {
            "ok": True,
            "pre_restore_backup_id": pre_restore_backup["id"]
        }
    
    except Exception as e:
        logger.error(f"Restore commit failed: {e}")
        return {
            "ok": False,
            "reason": f"Restore failed: {str(e)}"
        }

def schedule_next(cronlike: str = None) -> Dict:
    """Schedule next backup (placeholder for future implementation)."""
    # This would integrate with a scheduler like cron or APScheduler
    # For now, just store the schedule in settings
    try:
        settings = {}
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, 'r') as f:
                settings = json.load(f)
        
        settings['backup_schedule'] = cronlike or '0 2 * * *'  # Default: daily at 2 AM
        
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(settings, f, indent=2)
        
        return {
            "ok": True,
            "schedule": settings['backup_schedule']
        }
    except Exception as e:
        logger.error(f"Failed to schedule backup: {e}")
        return {
            "ok": False,
            "reason": str(e)
        }

def backup_create_lightweight() -> Dict:
    """Create a lightweight backup for auto-session backups."""
    try:
        backup_id = str(uuid4())
        path, size_bytes = _create_backup_zip('auto_session', lightweight=True)
        _record_backup(backup_id, path, size_bytes, 'auto_session')
        
        logger.info(f"Lightweight backup created: {backup_id} ({size_bytes} bytes)")
        
        return {
            "id": backup_id,
            "created_at": datetime.utcnow().isoformat(),
            "path": path,
            "size_bytes": size_bytes
        }
    except Exception as e:
        logger.error(f"Lightweight backup creation failed: {e}")
        raise

def _log_backup_audit_event(action: str, backup_id: Optional[str] = None, 
                           document_ids: Optional[List[str]] = None,
                           backup_path: Optional[str] = None,
                           error_message: Optional[str] = None,
                           session_doc_count: Optional[int] = None):
    """Log backup-related audit events."""
    try:
        # Try new schema first (db_manager)
        from db_manager_unified import get_db_manager
        db_manager = get_db_manager()
        
        metadata = {}
        if backup_id:
            metadata["backup_id"] = backup_id
        if backup_path:
            metadata["backup_path"] = backup_path
        if document_ids:
            metadata["document_ids"] = document_ids
            metadata["document_id"] = ",".join(document_ids)  # For compatibility
        if session_doc_count is not None:
            metadata["session_doc_count"] = session_doc_count
        if error_message:
            metadata["error"] = error_message
        
        db_manager.log_audit_event(
            action=action,
            entity_type='backup',
            entity_id=backup_id or 'none',
            document_id=",".join(document_ids) if document_ids else None,
            metadata_json=json.dumps(metadata) if metadata else None
        )
    except Exception as e:
        # Fallback to old schema (ts, actor, action, detail)
        try:
            conn = _get_conn()
            cur = conn.cursor()
            
            # Ensure table exists with old schema
            cur.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY,
                    ts TEXT NOT NULL DEFAULT (datetime('now')),
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    detail TEXT
                )
            """)
            
            # Build detail string
            detail_parts = []
            if backup_id:
                detail_parts.append(f"backup_id={backup_id}")
            if backup_path:
                detail_parts.append(f"path={backup_path}")
            if document_ids:
                detail_parts.append(f"doc_ids={','.join(document_ids)}")
            if session_doc_count is not None:
                detail_parts.append(f"doc_count={session_doc_count}")
            if error_message:
                detail_parts.append(f"error={error_message}")
            
            detail = json.dumps({
                "backup_id": backup_id,
                "backup_path": backup_path,
                "document_ids": document_ids,
                "session_doc_count": session_doc_count,
                "error": error_message
            }, default=str) if detail_parts else None
            
            cur.execute("""
                INSERT INTO audit_log (actor, action, detail)
                VALUES (?, ?, ?)
            """, ('system', action, detail))
            
            conn.commit()
            conn.close()
        except Exception as e2:
            logger.warning(f"Failed to log backup audit event (both schemas failed): {e}, {e2}")

async def _create_auto_backup_async(document_ids: List[str]):
    """Create auto-backup asynchronously after successful document processing."""
    if not AUTO_BACKUP_ENABLED:
        return
    
    try:
        # Log that backup is scheduled
        _log_backup_audit_event(
            action='backup_scheduled',
            document_ids=document_ids,
            session_doc_count=len(document_ids)
        )
        
        # Create lightweight backup
        backup_result = backup_create_lightweight()
        backup_id = backup_result["id"]
        backup_path = backup_result["path"]
        
        # Update session tracking
        _update_backup_session(backup_id=backup_id, increment_count=False)
        
        # Log successful backup creation
        _log_backup_audit_event(
            action='backup_created',
            backup_id=backup_id,
            document_ids=document_ids,
            backup_path=backup_path,
            session_doc_count=len(document_ids)
        )
        
        logger.info(f"Auto-backup created successfully: {backup_id} for {len(document_ids)} documents")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Auto-backup creation failed: {error_msg}")
        
        # Log backup failure
        _log_backup_audit_event(
            action='backup_failed',
            document_ids=document_ids,
            error_message=error_msg,
            session_doc_count=len(document_ids)
        )

def trigger_auto_backup_if_needed(document_id: str):
    """Check if auto-backup should be triggered and enqueue it if needed."""
    if not AUTO_BACKUP_ENABLED:
        return
    
    try:
        # Increment document count in session
        _update_backup_session(increment_count=True)
        
        # Check if backup should be created
        if _should_create_auto_backup():
            # Get all documents in current session (documents processed since last backup)
            session = _get_backup_session()
            doc_count = session["doc_count_since_backup"]
            
            # For simplicity, we'll just backup the current document
            # In a more sophisticated implementation, we could track all doc IDs in the session
            document_ids = [document_id]
            
            # Schedule backup asynchronously
            # Use a thread-safe approach that works in both sync and async contexts
            try:
                loop = asyncio.get_running_loop()
                # Event loop is running, schedule as task
                asyncio.create_task(_create_auto_backup_async(document_ids))
            except RuntimeError:
                # No event loop running, run in background thread
                import threading
                def run_backup():
                    try:
                        asyncio.run(_create_auto_backup_async(document_ids))
                    except Exception as e:
                        logger.warning(f"Background backup task failed: {e}")
                
                thread = threading.Thread(target=run_backup, daemon=True)
                thread.start()
                
    except Exception as e:
        # Never let backup failures break document processing
        logger.warning(f"Error in auto-backup trigger: {e}")
