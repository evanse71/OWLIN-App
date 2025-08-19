import os
import json
import hashlib
import sqlite3
import zipfile
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from uuid import uuid4

# Constants
BACKUP_DIR = Path("backups")
DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "owlin.db"
VERSION_FILE = DATA_DIR / "version.json"

# Ensure directories exist
BACKUP_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)


def get_db_connection():
    """Get database connection."""
    return sqlite3.connect(DB_PATH)


def sha256_file(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    hash_obj = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def get_app_version() -> str:
    """Get current app version."""
    try:
        if VERSION_FILE.exists():
            with open(VERSION_FILE, 'r') as f:
                data = json.load(f)
                return data.get("app_version", "1.0.0")
    except Exception:
        pass
    return "1.0.0"


def get_schema_version() -> int:
    """Get current schema version."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check for alembic version table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'")
        if cursor.fetchone():
            cursor.execute("SELECT version_num FROM alembic_version LIMIT 1")
            version_row = cursor.fetchone()
            if version_row:
                conn.close()
                return int(version_row[0])
        
        # Fallback: count migrations
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        conn.close()
        return len(tables)  # Rough estimate
    except Exception:
        return 0


def check_integrity() -> Dict[str, Any]:
    """Check database integrity and schema."""
    details = []
    integrity_ok = True
    
    try:
        if not DB_PATH.exists():
            return {
                "integrity_ok": False,
                "details": ["Database file missing"],
                "state": "recovery"
            }
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # PRAGMA integrity check
        cursor.execute("PRAGMA integrity_check")
        integrity_result = cursor.fetchone()
        if integrity_result and integrity_result[0] != "ok":
            integrity_ok = False
            details.append(f"PRAGMA integrity_check: {integrity_result[0]}")
        
        # Check for required tables
        required_tables = [
            "invoices", "suppliers", "users", "audit_log", 
            "backups_meta", "support_pack_index"
        ]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row[0] for row in cursor.fetchall()}
        
        for table in required_tables:
            if table not in existing_tables:
                integrity_ok = False
                details.append(f"Missing required table: {table}")
        
        # Check for schema version consistency
        schema_version = get_schema_version()
        if schema_version == 0:
            integrity_ok = False
            details.append("Schema version could not be determined")
        
        conn.close()
        
    except Exception as e:
        integrity_ok = False
        details.append(f"Database error: {str(e)}")
    
    # Determine state
    if integrity_ok:
        state = "normal"
    elif len(details) <= 2:
        state = "degraded"
    else:
        state = "recovery"
    
    return {
        "integrity_ok": integrity_ok,
        "details": details,
        "state": state
    }


def get_snapshots() -> List[Dict[str, Any]]:
    """Get list of available snapshots."""
    snapshots = []
    
    try:
        for backup_file in BACKUP_DIR.glob("*.zip"):
            try:
                with zipfile.ZipFile(backup_file, 'r') as z:
                    # Check for manifest
                    manifest_ok = False
                    size_bytes = backup_file.stat().st_size
                    
                    if "manifest.json" in z.namelist():
                        manifest_data = json.loads(z.read("manifest.json").decode())
                        manifest_ok = True
                        created_at = manifest_data.get("created_at", "")
                    else:
                        # Fallback to file modification time
                        created_at = datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat()
                    
                    snapshot_id = backup_file.stem
                    snapshots.append({
                        "id": snapshot_id,
                        "size_bytes": size_bytes,
                        "created_at": created_at,
                        "manifest_ok": manifest_ok
                    })
            except Exception:
                continue
        
        # Sort by creation time (newest first)
        snapshots.sort(key=lambda x: x["created_at"], reverse=True)
        
    except Exception:
        pass
    
    return snapshots


def get_live_db_hash() -> str:
    """Get SHA256 hash of live database."""
    try:
        if DB_PATH.exists():
            return sha256_file(DB_PATH)
    except Exception:
        pass
    return ""


def get_recovery_status() -> Dict[str, Any]:
    """Get comprehensive recovery status."""
    integrity = check_integrity()
    snapshots = get_snapshots()
    live_db_hash = get_live_db_hash()
    
    return {
        "state": integrity["state"],
        "reason": "INTEGRITY_FAILED" if not integrity["integrity_ok"] else None,
        "details": integrity["details"],
        "snapshots": snapshots,
        "live_db_hash": live_db_hash,
        "schema_version": get_schema_version(),
        "app_version": get_app_version()
    }


def create_snapshot() -> str:
    """Create a new snapshot with manifest."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
    snapshot_id = timestamp
    snapshot_path = BACKUP_DIR / f"{snapshot_id}.zip"
    
    try:
        with zipfile.ZipFile(snapshot_path, 'w', zipfile.ZIP_DEFLATED) as z:
            # Add database
            if DB_PATH.exists():
                z.write(DB_PATH, arcname="owlin.db")
            
            # Add audit log
            audit_file = DATA_DIR / "audit.log"
            if audit_file.exists():
                z.write(audit_file, arcname="audit_tail.log")
            
            # Add metadata
            meta_data = {
                "app_version": get_app_version(),
                "schema_version": get_schema_version(),
                "created_at": timestamp,
                "device_id": "OWLIN-device"  # Placeholder
            }
            z.writestr("meta.json", json.dumps(meta_data, indent=2))
            
            # Create manifest
            manifest = {
                "files": [],
                "created_at": timestamp,
                "id": snapshot_id
            }
            
            for info in z.infolist():
                if not info.is_dir():
                    manifest["files"].append({
                        "path": info.filename,
                        "size": info.file_size,
                        "sha256": ""  # Would calculate in real implementation
                    })
            
            z.writestr("manifest.json", json.dumps(manifest, indent=2))
        
        return snapshot_id
        
    except Exception as e:
        raise Exception(f"Failed to create snapshot: {str(e)}")


def get_primary_keys(table: str) -> List[str]:
    """Get primary key columns for a table."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get table info
        cursor.execute("PRAGMA table_info(?)", (table,))
        columns = cursor.fetchall()
        
        # Find primary key columns
        pk_columns = []
        for col in columns:
            if col[5] == 1:  # pk column
                pk_columns.append(col[1])  # column name
        
        # If no explicit PK, use all columns
        if not pk_columns:
            pk_columns = [col[1] for col in columns]
        
        conn.close()
        return pk_columns
        
    except Exception:
        return []


def build_row_key(table: str, row_data: Dict[str, Any]) -> str:
    """Build a stable row key from primary key columns."""
    pk_columns = get_primary_keys(table)
    
    if not pk_columns:
        # Fallback: use all columns
        pk_columns = list(row_data.keys())
    
    # Build key from PK columns
    key_parts = []
    for col in pk_columns:
        if col in row_data:
            value = row_data[col]
            if value is None:
                value = "NULL"
            key_parts.append(f"{col}={value}")
    
    return "|".join(sorted(key_parts))


def deep_equal(a: Any, b: Any) -> bool:
    """Deep equality comparison with type-aware rules."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    
    # Handle different types
    if type(a) != type(b):
        return False
    
    # Handle floats with epsilon comparison
    if isinstance(a, float) and isinstance(b, float):
        return abs(a - b) < 1e-9
    
    # Handle strings (null vs empty string are different)
    if isinstance(a, str) and isinstance(b, str):
        # Check if they look like timestamps
        if "T" in a and "T" in b:
            try:
                # Normalize to ISO format for comparison
                dt_a = datetime.fromisoformat(a.replace('Z', '+00:00'))
                dt_b = datetime.fromisoformat(b.replace('Z', '+00:00'))
                return dt_a == dt_b
            except:
                pass
        return a == b
    
    # Default comparison
    return a == b


def get_table_data(table: str, limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
    """Get table data with pagination."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT * FROM {table} LIMIT ? OFFSET ?", (limit, offset))
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
        
    except Exception:
        return []


def extract_snapshot_data(snapshot_id: str, table: str) -> List[Dict[str, Any]]:
    """Extract table data from snapshot."""
    snapshot_path = BACKUP_DIR / f"{snapshot_id}.zip"
    
    if not snapshot_path.exists():
        return []
    
    try:
        with zipfile.ZipFile(snapshot_path, 'r') as z:
            # Check if table data exists in snapshot
            db_file = "owlin.db"
            if db_file not in z.namelist():
                return []
            
            # Extract database to temp location
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
                temp_db.write(z.read(db_file))
                temp_db_path = temp_db.name
            
            try:
                # Query the extracted database
                conn = sqlite3.connect(temp_db_path)
                cursor = conn.cursor()
                
                cursor.execute(f"SELECT * FROM {table}")
                columns = [description[0] for description in cursor.description]
                rows = cursor.fetchall()
                
                conn.close()
                
                return [dict(zip(columns, row)) for row in rows]
                
            finally:
                # Clean up temp file
                os.unlink(temp_db_path)
                
    except Exception:
        return []


def compare_tables(table: str, snapshot_id: str, limit: int = 200, offset: int = 0) -> Dict[str, Any]:
    """Compare live table with snapshot table."""
    live_data = get_table_data(table, limit, offset)
    snapshot_data = extract_snapshot_data(snapshot_id, table)
    
    # Build row key maps
    live_keys = {build_row_key(table, row): row for row in live_data}
    snapshot_keys = {build_row_key(table, row): row for row in snapshot_data}
    
    # Find differences
    all_keys = set(live_keys.keys()) | set(snapshot_keys.keys())
    
    rows = []
    stats = {"add": 0, "remove": 0, "change": 0, "identical": 0}
    
    for key in all_keys:
        live_row = live_keys.get(key)
        snapshot_row = snapshot_keys.get(key)
        
        if live_row and snapshot_row:
            # Both exist - check for changes
            cells = []
            changed = False
            
            all_columns = set(live_row.keys()) | set(snapshot_row.keys())
            for col in sorted(all_columns):
                old_val = live_row.get(col)
                new_val = snapshot_row.get(col)
                cell_changed = not deep_equal(old_val, new_val)
                
                cells.append({
                    "col": col,
                    "old": old_val,
                    "new": new_val,
                    "changed": cell_changed
                })
                
                if cell_changed:
                    changed = True
            
            if changed:
                rows.append({
                    "key": key,
                    "op": "change",
                    "cells": cells
                })
                stats["change"] += 1
            else:
                rows.append({
                    "key": key,
                    "op": "identical",
                    "cells": cells
                })
                stats["identical"] += 1
                
        elif snapshot_row:
            # Only in snapshot (to be added)
            cells = []
            for col in sorted(snapshot_row.keys()):
                cells.append({
                    "col": col,
                    "old": None,
                    "new": snapshot_row[col],
                    "changed": True
                })
            
            rows.append({
                "key": key,
                "op": "add",
                "cells": cells
            })
            stats["add"] += 1
            
        elif live_row:
            # Only in live (to be removed)
            cells = []
            for col in sorted(live_row.keys()):
                cells.append({
                    "col": col,
                    "old": live_row[col],
                    "new": None,
                    "changed": True
                })
            
            rows.append({
                "key": key,
                "op": "remove",
                "cells": cells
            })
            stats["remove"] += 1
    
    return {
        "table": table,
        "pk": get_primary_keys(table),
        "stats": stats,
        "rows": rows
    }


def create_restore_preview(snapshot_id: str, limit: int = 200, offset: int = 0) -> Dict[str, Any]:
    """Create restore preview for a snapshot."""
    # Get snapshot info
    snapshots = get_snapshots()
    snapshot = next((s for s in snapshots if s["id"] == snapshot_id), None)
    
    if not snapshot:
        raise Exception("Snapshot not found")
    
    # Get list of tables
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
    except Exception:
        tables = []
    
    # Compare each table
    table_diffs = []
    total_stats = {"add": 0, "remove": 0, "change": 0, "identical": 0}
    
    for table in tables[:5]:  # Limit to first 5 tables for preview
        try:
            diff = compare_tables(table, snapshot_id, limit, offset)
            table_diffs.append(diff)
            
            # Aggregate stats
            for key in total_stats:
                total_stats[key] += diff["stats"][key]
        except Exception:
            continue
    
    return {
        "snapshot": snapshot,
        "tables": table_diffs,
        "summary": {
            "rows_add": total_stats["add"],
            "rows_remove": total_stats["remove"],
            "rows_change": total_stats["change"]
        }
    }


def apply_resolve_plan(snapshot_id: str, resolve_plan: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a resolve plan to restore data."""
    # Create pre-commit snapshot
    pre_commit_id = create_snapshot()
    
    try:
        # Get snapshot data
        snapshot_path = BACKUP_DIR / f"{snapshot_id}.zip"
        if not snapshot_path.exists():
            raise Exception("Snapshot not found")
        
        # Extract decisions
        decisions = resolve_plan.get("decisions", {})
        merge_fields = resolve_plan.get("merge_fields", {})
        
        # Apply decisions table by table
        for table, table_decisions in decisions.items():
            apply_table_decisions(table, snapshot_id, table_decisions, merge_fields.get(table, {}))
        
        # Create post-commit snapshot
        post_commit_id = create_snapshot()
        
        # Log audit event
        log_audit_event("recovery.commit", {
            "snapshot_id": snapshot_id,
            "pre_commit_id": pre_commit_id,
            "post_commit_id": post_commit_id,
            "decisions": decisions
        })
        
        return {
            "ok": True,
            "restore_id": str(uuid4()),
            "pre_commit_id": pre_commit_id,
            "post_commit_id": post_commit_id
        }
        
    except Exception as e:
        # Rollback to pre-commit snapshot
        try:
            rollback_to_snapshot(pre_commit_id)
        except:
            pass
        
        raise Exception(f"Restore failed: {str(e)}")


def apply_table_decisions(table: str, snapshot_id: str, table_decisions: Dict[str, str], merge_fields: Dict[str, Dict[str, str]]):
    """Apply decisions for a specific table."""
    # Get live and snapshot data
    live_data = get_table_data(table, limit=10000)  # Get all data
    snapshot_data = extract_snapshot_data(snapshot_id, table)
    
    # Build key maps
    live_keys = {build_row_key(table, row): row for row in live_data}
    snapshot_keys = {build_row_key(table, row): row for row in snapshot_data}
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        for key, decision in table_decisions.items():
            if decision == "take_snapshot":
                # Insert/update from snapshot
                if key in snapshot_keys:
                    snapshot_row = snapshot_keys[key]
                    if key in live_keys:
                        # Update existing row
                        set_clause = ", ".join([f"{col} = ?" for col in snapshot_row.keys()])
                        cursor.execute(f"UPDATE {table} SET {set_clause} WHERE {build_where_clause(table, key)}", 
                                     list(snapshot_row.values()) + parse_key_conditions(key))
                    else:
                        # Insert new row
                        columns = ", ".join(snapshot_row.keys())
                        placeholders = ", ".join(["?" for _ in snapshot_row])
                        cursor.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", 
                                     list(snapshot_row.values()))
                        
            elif decision == "keep_live":
                # Keep live data (no action needed)
                pass
                
            elif decision == "merge":
                # Merge fields
                if key in live_keys and key in snapshot_keys:
                    live_row = live_keys[key]
                    snapshot_row = snapshot_keys[key]
                    
                    # Apply merge field decisions
                    merged_row = live_row.copy()
                    table_merge_fields = merge_fields.get(key, {})
                    
                    for col, choice in table_merge_fields.items():
                        if choice == "new" and col in snapshot_row:
                            merged_row[col] = snapshot_row[col]
                    
                    # Update with merged data
                    set_clause = ", ".join([f"{col} = ?" for col in merged_row.keys()])
                    cursor.execute(f"UPDATE {table} SET {set_clause} WHERE {build_where_clause(table, key)}", 
                                 list(merged_row.values()) + parse_key_conditions(key))
        
        conn.commit()
        
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def build_where_clause(table: str, key: str) -> str:
    """Build WHERE clause from row key."""
    pk_columns = get_primary_keys(table)
    conditions = []
    
    for condition in key.split("|"):
        if "=" in condition:
            col, val = condition.split("=", 1)
            if val == "NULL":
                conditions.append(f"{col} IS NULL")
            else:
                conditions.append(f"{col} = ?")
    
    return " AND ".join(conditions)


def parse_key_conditions(key: str) -> List[Any]:
    """Parse key conditions into parameter values."""
    values = []
    
    for condition in key.split("|"):
        if "=" in condition:
            col, val = condition.split("=", 1)
            if val != "NULL":
                values.append(val)
    
    return values


def rollback_to_snapshot(snapshot_id: str) -> bool:
    """Rollback to a specific snapshot."""
    snapshot_path = BACKUP_DIR / f"{snapshot_id}.zip"
    
    if not snapshot_path.exists():
        return False
    
    try:
        with zipfile.ZipFile(snapshot_path, 'r') as z:
            if "owlin.db" in z.namelist():
                # Extract database
                with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
                    temp_db.write(z.read("owlin.db"))
                    temp_db_path = temp_db.name
                
                try:
                    # Replace live database
                    shutil.copy2(temp_db_path, DB_PATH)
                    return True
                finally:
                    os.unlink(temp_db_path)
    except Exception:
        pass
    
    return False


def log_audit_event(action: str, data: Dict[str, Any]):
    """Log audit event."""
    try:
        audit_file = DATA_DIR / "audit.log"
        audit_file.parent.mkdir(exist_ok=True)
        
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "data": data
        }
        
        with open(audit_file, 'a') as f:
            f.write(json.dumps(event) + "\n")
            
    except Exception:
        pass  # Don't fail if audit logging fails 


def check_recovery_license() -> Dict[str, Any]:
    """Check if recovery features are licensed."""
    try:
        from services.license_service import check_license_state
        license_state = check_license_state()
        
        if not license_state.get("valid", False):
            return {
                "licensed": False,
                "reason": "LICENSE_INVALID",
                "message": "Recovery features require a valid license"
            }
        
        # Check if recovery features are enabled in license
        summary = license_state.get("summary", {})
        features = summary.get("features", {})
        
        if not features.get("recovery", False):
            return {
                "licensed": False,
                "reason": "RECOVERY_NOT_LICENSED",
                "message": "Recovery features are not included in your license"
            }
        
        return {
            "licensed": True,
            "reason": None,
            "message": None
        }
        
    except ImportError:
        # License service not available, assume licensed
        return {
            "licensed": True,
            "reason": None,
            "message": None
        }
    except Exception as e:
        return {
            "licensed": False,
            "reason": "LICENSE_CHECK_ERROR",
            "message": f"License check failed: {str(e)}"
        }


def require_recovery_license():
    """Decorator to require recovery license for operations."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            license_check = check_recovery_license()
            if not license_check["licensed"]:
                raise Exception(license_check["message"])
            return func(*args, **kwargs)
        return wrapper
    return decorator 