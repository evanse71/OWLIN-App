from __future__ import annotations
import sqlite3
import os
import shutil
import zipfile
import tempfile
import json
import hashlib
from pathlib import Path
from datetime import datetime
from uuid import uuid4
from typing import List, Dict, Optional, Generator
import logging

logger = logging.getLogger(__name__)

# Constants
APP_ROOT = Path(__file__).parent.parent.parent
SUPPORT_PACKS_DIR = APP_ROOT / "support_packs"
DB_PATH = APP_ROOT / "data" / "owlin.db"
LOGS_DIR = APP_ROOT / "data" / "logs"
BACKUPS_DIR = APP_ROOT / "backups"
CONFIG_PATH = APP_ROOT / "data" / "settings.json"

def _get_conn():
    """Get database connection."""
    return sqlite3.connect(DB_PATH)

def _ensure_directories():
    """Ensure required directories exist."""
    SUPPORT_PACKS_DIR.mkdir(parents=True, exist_ok=True)

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

def _sanitize_config(config: Dict) -> Dict:
    """Sanitize configuration to remove sensitive data."""
    sanitized = config.copy()
    
    # Remove sensitive keys
    sensitive_keys = ['password', 'secret', 'token', 'key', 'api_key', 'private']
    for key in list(sanitized.keys()):
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            del sanitized[key]
    
    return sanitized

def _generate_environment_report() -> str:
    """Generate environment report."""
    import platform
    import sys
    
    report = []
    report.append("OWLIN Environment Report")
    report.append("=" * 50)
    report.append(f"Generated: {datetime.utcnow().isoformat()}")
    report.append(f"Python Version: {sys.version}")
    report.append(f"Platform: {platform.platform()}")
    report.append(f"Architecture: {platform.architecture()}")
    report.append(f"App Version: {_get_app_version()}")
    
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
        
        # Get some basic stats
        cur.execute("PRAGMA page_count")
        page_count = cur.fetchone()[0]
        cur.execute("PRAGMA page_size")
        page_size = cur.fetchone()[0]
        db_size_mb = (page_count * page_size) / (1024**2)
        report.append(f"Database Size: {db_size_mb:.1f}MB")
        
        conn.close()
    except Exception:
        report.append("Database Info: Unable to determine")
    
    return "\n".join(report)

def _create_support_pack_zip(notes: Optional[str] = None) -> Tuple[str, int, Dict]:
    """Create support pack ZIP file and return (path, size_bytes, manifest)."""
    _ensure_directories()
    
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    pack_filename = f"support_pack_{timestamp}.zip"
    pack_path = SUPPORT_PACKS_DIR / pack_filename
    
    manifest = {}
    
    with zipfile.ZipFile(pack_path, "w", zipfile.ZIP_DEFLATED) as z:
        # Add database snapshot
        if DB_PATH.exists():
            z.write(DB_PATH, arcname="data/owlin.db")
            with open(DB_PATH, 'rb') as f:
                manifest["data/owlin.db"] = hashlib.sha256(f.read()).hexdigest()
        
        # Add latest backup (if exists)
        if BACKUPS_DIR.exists():
            backup_files = list(BACKUPS_DIR.glob("backup_*.zip"))
            if backup_files:
                latest_backup = max(backup_files, key=lambda f: f.stat().st_mtime)
                z.write(latest_backup, arcname=f"backups/{latest_backup.name}")
                with open(latest_backup, 'rb') as f:
                    manifest[f"backups/{latest_backup.name}"] = hashlib.sha256(f.read()).hexdigest()
        
        # Add logs (truncated to last 10MB per file)
        if LOGS_DIR.exists():
            for log_file in LOGS_DIR.glob("*.log"):
                try:
                    with open(log_file, 'r') as f:
                        content = f.read()
                        # Truncate to last 10MB
                        if len(content) > 10 * 1024 * 1024:
                            content = content[-10 * 1024 * 1024:]
                        z.writestr(f"logs/{log_file.name}", content)
                        manifest[f"logs/{log_file.name}"] = hashlib.sha256(content.encode()).hexdigest()
                except Exception as e:
                    logger.warning(f"Failed to add log file {log_file}: {e}")
        
        # Add environment report
        env_report = _generate_environment_report()
        z.writestr("environment.txt", env_report)
        manifest["environment.txt"] = hashlib.sha256(env_report.encode()).hexdigest()
        
        # Add sanitized config
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, 'r') as f:
                    config = json.load(f)
                sanitized_config = _sanitize_config(config)
                z.writestr("config.json", json.dumps(sanitized_config, indent=2))
                manifest["config.json"] = hashlib.sha256(json.dumps(sanitized_config).encode()).hexdigest()
            except Exception as e:
                logger.warning(f"Failed to add config: {e}")
        
        # Add manifest
        z.writestr("manifest.json", json.dumps(manifest, indent=2))
    
    return str(pack_path), pack_path.stat().st_size, manifest

def _record_support_pack(pack_id: str, path: str, size_bytes: int, notes: Optional[str] = None):
    """Record support pack in database."""
    conn = _get_conn()
    cur = conn.cursor()
    
    # Ensure support_pack_index table exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS support_pack_index(
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            path TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            notes TEXT,
            has_checksum INTEGER NOT NULL DEFAULT 1,
            app_version TEXT NOT NULL
        )
    """)
    
    cur.execute("""
        INSERT INTO support_pack_index (id, created_at, path, size_bytes, notes, has_checksum, app_version)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        pack_id,
        datetime.utcnow().isoformat(),
        path,
        size_bytes,
        notes,
        1,  # has_checksum
        _get_app_version()
    ))
    
    conn.commit()
    conn.close()

def pack_create(notes: Optional[str] = None) -> Dict:
    """Create a new support pack."""
    try:
        pack_id = str(uuid4())
        path, size_bytes, manifest = _create_support_pack_zip(notes)
        _record_support_pack(pack_id, path, size_bytes, notes)
        
        logger.info(f"Support pack created: {pack_id} ({size_bytes} bytes)")
        
        return {
            "id": pack_id,
            "created_at": datetime.utcnow().isoformat(),
            "path": path,
            "size_bytes": size_bytes,
            "notes": notes,
            "app_version": _get_app_version()
        }
    except Exception as e:
        logger.error(f"Support pack creation failed: {e}")
        raise

def pack_list() -> List[Dict]:
    """List all support packs."""
    conn = _get_conn()
    cur = conn.cursor()
    
    # Ensure table exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS support_pack_index(
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            path TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            notes TEXT,
            has_checksum INTEGER NOT NULL DEFAULT 1,
            app_version TEXT NOT NULL
        )
    """)
    
    cur.execute("""
        SELECT id, created_at, path, size_bytes, notes, has_checksum, app_version
        FROM support_pack_index
        ORDER BY created_at DESC
    """)
    
    packs = []
    for row in cur.fetchall():
        packs.append({
            "id": row[0],
            "created_at": row[1],
            "path": row[2],
            "size_bytes": row[3],
            "notes": row[4],
            "has_checksum": bool(row[5]),
            "app_version": row[6]
        })
    
    conn.close()
    return packs

def pack_stream(pack_id: str) -> Optional[Generator[bytes, None, None]]:
    """Stream support pack file."""
    try:
        # Get pack info
        conn = _get_conn()
        cur = conn.cursor()
        
        cur.execute("SELECT path FROM support_pack_index WHERE id = ?", (pack_id,))
        row = cur.fetchone()
        
        if not row:
            return None
        
        pack_path = row[0]
        conn.close()
        
        if not Path(pack_path).exists():
            return None
        
        # Stream file in chunks
        chunk_size = 8192
        with open(pack_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    
    except Exception as e:
        logger.error(f"Support pack streaming failed: {e}")
        return None

def pack_get_info(pack_id: str) -> Optional[Dict]:
    """Get support pack information."""
    try:
        conn = _get_conn()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, created_at, path, size_bytes, notes, has_checksum, app_version
            FROM support_pack_index WHERE id = ?
        """, (pack_id,))
        
        row = cur.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            "id": row[0],
            "created_at": row[1],
            "path": row[2],
            "size_bytes": row[3],
            "notes": row[4],
            "has_checksum": bool(row[5]),
            "app_version": row[6]
        }
    
    except Exception as e:
        logger.error(f"Failed to get support pack info: {e}")
        return None
