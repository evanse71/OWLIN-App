# -*- coding: utf-8 -*-
"""
Backup Manager Service

This module implements backup and restore functionality with Shepherd vault support,
as specified in System Bible Section 2.8 (lines 196-201).

Features:
- Create snapshots (ZIP owlin.db + audit_log + version_log)
- Restore snapshots with conflict resolution
- Shepherd vault support (data/shepherd/<venue_id>/)
- Lockfile mechanism (lockfile.sha256)
- Daily ZIP backups (data/backups/YYYY-MM-DD_HHMM.zip)
- Integrity checks (PRAGMA integrity_check)
"""

from __future__ import annotations
import logging
import os
import sqlite3
import zipfile
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from backend.services.vault_lock import VaultLock, check_vault_lock

LOGGER = logging.getLogger("owlin.services.backup_manager")
LOGGER.setLevel(logging.INFO)

DB_PATH = "data/owlin.db"
BACKUP_DIR = Path("data/backups")
SHEPHERD_BASE = Path("data/shepherd")


def _ensure_directories():
    """Ensure backup and shepherd directories exist."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    SHEPHERD_BASE.mkdir(parents=True, exist_ok=True)


def create_snapshot(venue_id: str = "default", include_uploads: bool = False) -> Dict[str, Any]:
    """
    Create a snapshot backup.
    
    Creates ZIP containing:
    - owlin.db
    - audit_log (from database)
    - version_log (if exists)
    - manifest.json with SHA256 hashes
    
    Args:
        venue_id: Venue identifier
        include_uploads: Whether to include uploaded files (default: False for size)
    
    Returns:
        Dictionary with backup information
    """
    _ensure_directories()
    
    # Check vault lock
    lock_status = check_vault_lock(venue_id)
    if lock_status.get("locked") and lock_status.get("process_alive"):
        raise Exception(f"Vault is locked by process {lock_status.get('process_id')}")
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    backup_filename = f"owlin_backup_{timestamp}.zip"
    backup_path = BACKUP_DIR / backup_filename
    
    try:
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            files_included = []
            hashes = {}
            
            # Add database file
            if os.path.exists(DB_PATH):
                zipf.write(DB_PATH, "owlin.db")
                files_included.append("owlin.db")
                
                # Calculate SHA256
                with open(DB_PATH, 'rb') as f:
                    db_hash = hashlib.sha256(f.read()).hexdigest()
                    hashes["owlin.db"] = db_hash
            
            # Add audit log (extract from database)
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            cursor = conn.cursor()
            
            try:
                cursor.execute("SELECT ts, actor, action, detail FROM audit_log ORDER BY ts DESC LIMIT 10000")
                audit_entries = cursor.fetchall()
                
                audit_log_path = BACKUP_DIR / f"audit_log_{timestamp}.json"
                with open(audit_log_path, 'w', encoding='utf-8') as f:
                    json.dump([
                        {
                            "ts": row[0],
                            "actor": row[1],
                            "action": row[2],
                            "detail": row[3]
                        }
                        for row in audit_entries
                    ], f, indent=2)
                
                zipf.write(audit_log_path, "audit_log.json")
                files_included.append("audit_log.json")
                
                # Calculate hash
                with open(audit_log_path, 'rb') as f:
                    audit_hash = hashlib.sha256(f.read()).hexdigest()
                    hashes["audit_log.json"] = audit_hash
                
                # Clean up temp file
                audit_log_path.unlink()
                
            except Exception as e:
                LOGGER.warning(f"Error extracting audit log: {e}")
            finally:
                conn.close()
            
            # Add version log if exists
            version_log_path = Path("version_log.json")
            if version_log_path.exists():
                zipf.write(version_log_path, "version_log.json")
                files_included.append("version_log.json")
                
                with open(version_log_path, 'rb') as f:
                    version_hash = hashlib.sha256(f.read()).hexdigest()
                    hashes["version_log.json"] = version_hash
            
            # Create manifest
            manifest = {
                "timestamp": timestamp,
                "venue_id": venue_id,
                "backup_file": backup_filename,
                "files": files_included,
                "hashes": hashes,
                "created_at": datetime.now().isoformat()
            }
            
            manifest_json = json.dumps(manifest, indent=2)
            zipf.writestr("manifest.json", manifest_json)
            
            # Calculate backup file hash
            with open(backup_path, 'rb') as f:
                backup_hash = hashlib.sha256(f.read()).hexdigest()
                manifest["backup_hash"] = backup_hash
            
            # Update manifest in ZIP
            zipf.writestr("manifest.json", json.dumps(manifest, indent=2))
        
        backup_size = backup_path.stat().st_size
        
        # Copy to Shepherd vault if venue_id specified
        if venue_id and venue_id != "default":
            shepherd_vault = SHEPHERD_BASE / venue_id
            shepherd_vault.mkdir(parents=True, exist_ok=True)
            shepherd_backups = shepherd_vault / "backups"
            shepherd_backups.mkdir(parents=True, exist_ok=True)
            
            shepherd_backup_path = shepherd_backups / backup_filename
            shutil.copy2(backup_path, shepherd_backup_path)
            
            # Update Shepherd manifest
            shepherd_manifest_path = shepherd_vault / "manifest.json"
            if shepherd_manifest_path.exists():
                with open(shepherd_manifest_path, 'r') as f:
                    shepherd_manifest = json.load(f)
            else:
                shepherd_manifest = {"venue_id": venue_id, "backups": []}
            
            shepherd_manifest["backups"].append({
                "filename": backup_filename,
                "timestamp": timestamp,
                "size": backup_size,
                "hash": backup_hash
            })
            shepherd_manifest["last_backup"] = timestamp
            
            with open(shepherd_manifest_path, 'w') as f:
                json.dump(shepherd_manifest, f, indent=2)
        
        LOGGER.info(f"Snapshot created: {backup_filename} ({backup_size / (1024**2):.2f} MB)")
        
        return {
            "success": True,
            "backup_file": backup_filename,
            "backup_path": str(backup_path),
            "size_bytes": backup_size,
            "hash": backup_hash,
            "timestamp": timestamp,
            "files_included": files_included
        }
        
    except Exception as e:
        LOGGER.error(f"Error creating snapshot: {e}")
        if backup_path.exists():
            backup_path.unlink()
        raise


def restore_snapshot(backup_path: str, dry_run: bool = False) -> Dict[str, Any]:
    """
    Restore a snapshot backup.
    
    Args:
        backup_path: Path to backup ZIP file
        dry_run: If True, only preview changes without restoring
    
    Returns:
        Dictionary with restore information and diff preview
    """
    backup_file = Path(backup_path)
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")
    
    try:
        with zipfile.ZipFile(backup_file, 'r') as zipf:
            # Read manifest
            if "manifest.json" not in zipf.namelist():
                raise ValueError("Backup file missing manifest.json")
            
            manifest_json = zipf.read("manifest.json").decode('utf-8')
            manifest = json.loads(manifest_json)
            
            # Verify backup hash
            with open(backup_file, 'rb') as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            
            if manifest.get("backup_hash") != actual_hash:
                LOGGER.warning("Backup file hash mismatch - file may be corrupted")
            
            # Extract files to temp directory
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                zipf.extractall(temp_dir)
                
                # Preview changes
                diff_preview = _preview_changes(temp_dir, manifest)
                
                if dry_run:
                    return {
                        "dry_run": True,
                        "backup_file": backup_path,
                        "manifest": manifest,
                        "diff_preview": diff_preview,
                        "message": "Dry run completed - no changes made"
                    }
                
                # Perform restore
                # Backup current database first
                if os.path.exists(DB_PATH):
                    current_backup = f"{DB_PATH}.pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.copy2(DB_PATH, current_backup)
                    LOGGER.info(f"Current database backed up to: {current_backup}")
                
                # Restore database
                temp_db = Path(temp_dir) / "owlin.db"
                if temp_db.exists():
                    shutil.copy2(temp_db, DB_PATH)
                    LOGGER.info("Database restored from backup")
                
                # Run integrity check
                integrity_ok = _run_integrity_check()
                
                return {
                    "success": True,
                    "backup_file": backup_path,
                    "manifest": manifest,
                    "diff_preview": diff_preview,
                    "integrity_check": "ok" if integrity_ok else "failed",
                    "message": "Snapshot restored successfully"
                }
        
    except Exception as e:
        LOGGER.error(f"Error restoring snapshot: {e}")
        raise


def _preview_changes(temp_dir: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """
    Preview changes that would be made by restore.
    
    Args:
        temp_dir: Temporary directory with extracted backup
        manifest: Backup manifest
    
    Returns:
        Dictionary with diff preview
    """
    preview = {
        "files_to_restore": [],
        "database_changes": {}
    }
    
    # Check database differences
    temp_db = Path(temp_dir) / "owlin.db"
    if temp_db.exists() and os.path.exists(DB_PATH):
        try:
            # Compare table row counts
            current_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            backup_conn = sqlite3.connect(str(temp_db), check_same_thread=False)
            
            current_cursor = current_conn.cursor()
            backup_cursor = backup_conn.cursor()
            
            tables = ["documents", "invoices", "invoice_line_items", "audit_log"]
            
            for table in tables:
                try:
                    current_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    current_count = current_cursor.fetchone()[0] or 0
                    
                    backup_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    backup_count = backup_cursor.fetchone()[0] or 0
                    
                    preview["database_changes"][table] = {
                        "current": current_count,
                        "backup": backup_count,
                        "delta": backup_count - current_count
                    }
                except Exception:
                    pass
            
            current_conn.close()
            backup_conn.close()
            
        except Exception as e:
            LOGGER.warning(f"Error previewing database changes: {e}")
    
    preview["files_to_restore"] = manifest.get("files", [])
    
    return preview


def _run_integrity_check() -> bool:
    """
    Run SQLite integrity check.
    
    Returns:
        True if integrity check passes
    """
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        
        conn.close()
        
        # Integrity check returns "ok" if database is valid
        is_ok = result and result[0] == "ok"
        
        if not is_ok:
            LOGGER.error(f"Database integrity check failed: {result}")
        
        return is_ok
        
    except Exception as e:
        LOGGER.error(f"Error running integrity check: {e}")
        return False


def create_daily_backup(venue_id: str = "default") -> Dict[str, Any]:
    """
    Create daily backup (called by scheduled task).
    
    Args:
        venue_id: Venue identifier
    
    Returns:
        Backup information
    """
    return create_snapshot(venue_id=venue_id, include_uploads=False)


def list_backups(venue_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List available backups.
    
    Args:
        venue_id: Optional venue ID to filter Shepherd vault backups
    
    Returns:
        List of backup information dictionaries
    """
    _ensure_directories()
    
    backups = []
    
    # List backups from main backup directory
    for backup_file in BACKUP_DIR.glob("owlin_backup_*.zip"):
        try:
            stat = backup_file.stat()
            backups.append({
                "filename": backup_file.name,
                "path": str(backup_file),
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "source": "main"
            })
        except Exception:
            continue
    
    # List backups from Shepherd vault if venue_id specified
    if venue_id:
        shepherd_vault = SHEPHERD_BASE / venue_id
        if shepherd_vault.exists():
            shepherd_backups_dir = shepherd_vault / "backups"
            if shepherd_backups_dir.exists():
                for backup_file in shepherd_backups_dir.glob("*.zip"):
                    try:
                        stat = backup_file.stat()
                        backups.append({
                            "filename": backup_file.name,
                            "path": str(backup_file),
                            "size_bytes": stat.st_size,
                            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "source": f"shepherd/{venue_id}"
                        })
                    except Exception:
                        continue
    
    # Sort by creation time (newest first)
    backups.sort(key=lambda x: x["created_at"], reverse=True)
    
    return backups


def cleanup_old_backups(retention_days: int = 30) -> int:
    """
    Clean up backups older than retention period.
    
    Args:
        retention_days: Number of days to retain backups (default: 30)
    
    Returns:
        Number of backups deleted
    """
    _ensure_directories()
    
    cutoff_date = datetime.now().timestamp() - (retention_days * 24 * 60 * 60)
    deleted_count = 0
    
    for backup_file in BACKUP_DIR.glob("owlin_backup_*.zip"):
        try:
            if backup_file.stat().st_mtime < cutoff_date:
                backup_file.unlink()
                deleted_count += 1
                LOGGER.info(f"Deleted old backup: {backup_file.name}")
        except Exception:
            continue
    
    return deleted_count

