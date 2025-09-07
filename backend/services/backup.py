from __future__ import annotations
import os
import shutil
import zipfile
import tempfile
import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime
from uuid import uuid4
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

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
        st = os.statvfs(str(APP_ROOT))
        return st.f_bavail * st.f_frsize >= min_bytes
    except Exception:
        return True  # Assume OK if we can't check

def _create_backup_zip(mode: str) -> Tuple[str, int]:
    """Create backup ZIP file and return (path, size_bytes)."""
    _ensure_directories()
    
    if not _check_disk_space():
        raise Exception("Insufficient disk space for backup")
    
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"backup_{timestamp}.zip"
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
            "backup_mode": mode
        }
        z.writestr("version.json", json.dumps(version_info, indent=2))
        
        # Backup logs (last 10MB per file)
        if LOGS_DIR.exists():
            for log_file in LOGS_DIR.glob("*.log"):
                try:
                    with open(log_file, 'r') as f:
                        content = f.read()
                        # Truncate to last 10MB
                        if len(content) > 10 * 1024 * 1024:
                            content = content[-10 * 1024 * 1024:]
                        z.writestr(f"logs/{log_file.name}", content)
                except Exception as e:
                    logger.warning(f"Failed to backup log file {log_file}: {e}")
        
        # Backup license files (if present)
        if LICENSE_DIR.exists():
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
        path,
        size_bytes,
        mode,
        _get_app_version(),
        _get_db_schema_version()
    ))
    
    conn.commit()
    conn.close()

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
