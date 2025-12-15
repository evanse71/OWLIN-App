#!/usr/bin/env python3
"""Check auto-backup status and verify implementation"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path("data/owlin.db")

if not DB_PATH.exists():
    print(f"ERROR: Database not found at {DB_PATH}")
    exit(1)

conn = sqlite3.connect(str(DB_PATH))
cur = conn.cursor()

print("=" * 60)
print("AUTO-BACKUP STATUS CHECK")
print("=" * 60)
print()

# 1. Check backup_sessions table
print("1. BACKUP SESSIONS TABLE")
print("-" * 60)
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='backup_sessions'")
if cur.fetchone():
    cur.execute("SELECT * FROM backup_sessions ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    if row:
        print(f"   Last backup at: {row[1]}")
        print(f"   Document count since backup: {row[2]}")
        print(f"   Last backup ID: {row[3] if len(row) > 3 and row[3] else 'None'}")
    else:
        print("   No session data found (table exists but empty)")
else:
    print("   backup_sessions table does not exist yet")
print()

# 2. Check recent backup audit log entries
print("2. RECENT BACKUP AUDIT LOG ENTRIES")
print("-" * 60)
cur.execute("PRAGMA table_info(audit_log)")
columns = [row[1] for row in cur.fetchall()]
print(f"   Available columns: {', '.join(columns)}")

# Find timestamp column
timestamp_col = None
for col in ['created_at', 'timestamp', 'ts', 'at']:
    if col in columns:
        timestamp_col = col
        break

# Build SELECT query based on available columns
select_cols = []
if 'action' in columns:
    select_cols.append('action')
if 'entity_type' in columns:
    select_cols.append('entity_type')
elif 'entity' in columns:
    select_cols.append('entity')
if 'entity_id' in columns:
    select_cols.append('entity_id')
if timestamp_col:
    select_cols.append(timestamp_col)
if 'metadata_json' in columns:
    select_cols.append('metadata_json')
elif 'details_json' in columns:
    select_cols.append('details_json')
elif 'details' in columns:
    select_cols.append('details')

if select_cols:
    select_str = ', '.join(select_cols)
    order_by = timestamp_col if timestamp_col else 'id'
    
    cur.execute(f"""
        SELECT {select_str}
        FROM audit_log 
        WHERE action LIKE '%backup%' 
        ORDER BY {order_by} DESC 
        LIMIT 5
    """)
    
    rows = cur.fetchall()
    if rows:
        for row in rows:
            for i, col in enumerate(select_cols):
                value = row[i] if i < len(row) else None
                if col in ['metadata_json', 'details_json', 'details'] and value:
                    try:
                        meta = json.loads(value)
                        print(f"   {col}: {json.dumps(meta, indent=6)}")
                    except:
                        print(f"   {col}: {value}")
                else:
                    print(f"   {col}: {value}")
            print()
    else:
        print("   No backup audit log entries found")
else:
    print("   Cannot determine audit_log schema")
print()

# 3. Check backup_index table
print("3. BACKUP INDEX (Recent Backups)")
print("-" * 60)
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='backup_index'")
if cur.fetchone():
    cur.execute("""
        SELECT id, created_at, path, size_bytes, mode 
        FROM backup_index 
        ORDER BY created_at DESC 
        LIMIT 5
    """)
    rows = cur.fetchall()
    
    if rows:
        for row in rows:
            size_mb = row[3] / (1024 * 1024) if row[3] else 0
            print(f"   Backup ID: {row[0]}")
            print(f"   Created: {row[1]}")
            print(f"   Path: {row[2]}")
            print(f"   Size: {size_mb:.2f} MB")
            print(f"   Mode: {row[4]}")
            print()
    else:
        print("   No backups in backup_index table")
else:
    print("   backup_index table does not exist yet")
print()

# 4. Check backup files on disk
print("4. BACKUP FILES ON DISK")
print("-" * 60)
backup_dir = Path("backups")
if backup_dir.exists():
    backups = sorted(backup_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    if backups:
        for backup in backups[:5]:
            size_kb = backup.stat().st_size / 1024
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            print(f"   {backup.name}")
            print(f"   Size: {size_kb:.2f} KB")
            print(f"   Modified: {mtime}")
            print()
    else:
        print("   No backup ZIP files found")
else:
    print("   Backups directory does not exist")
print()

print("=" * 60)
print("CHECK COMPLETE")
print("=" * 60)

conn.close()

