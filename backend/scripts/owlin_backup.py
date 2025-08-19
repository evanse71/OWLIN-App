#!/usr/bin/env python3
"""
OWLIN Backup CLI Tool

Usage:
    python scripts/owlin_backup.py create --mode manual
    python scripts/owlin_backup.py list
    python scripts/owlin_backup.py restore --id <UUID> --dry-run
    python scripts/owlin_backup.py restore --id <UUID> --commit
"""

import sys
import argparse
from pathlib import Path
import json

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services import backup as backup_service

def create_backup(mode: str):
    """Create a new backup."""
    try:
        result = backup_service.backup_create(mode)
        print(f"✅ Backup created successfully")
        print(f"   ID: {result['id']}")
        print(f"   Path: {result['path']}")
        print(f"   Size: {result['size_bytes']:,} bytes")
        print(f"   Created: {result['created_at']}")
        return 0
    except Exception as e:
        print(f"❌ Backup creation failed: {e}")
        return 1

def list_backups():
    """List all backups."""
    try:
        backups = backup_service.backup_list()
        
        if not backups:
            print("No backups found.")
            return 0
        
        print(f"Found {len(backups)} backup(s):")
        print("-" * 80)
        
        for backup in backups:
            print(f"ID: {backup['id']}")
            print(f"Created: {backup['created_at']}")
            print(f"Mode: {backup['mode']}")
            print(f"Size: {backup['size_bytes']:,} bytes")
            print(f"App Version: {backup['app_version']}")
            print(f"DB Schema: {backup['db_schema_version']}")
            print(f"Path: {backup['path']}")
            print("-" * 80)
        
        return 0
    except Exception as e:
        print(f"❌ Failed to list backups: {e}")
        return 1

def restore_backup(backup_id: str, dry_run: bool):
    """Restore from backup."""
    try:
        if dry_run:
            print(f"🔍 Previewing restore from backup {backup_id}...")
            result = backup_service.restore_preview(backup_id)
            
            if not result['ok']:
                print(f"❌ Restore preview failed: {result['reason']}")
                return 1
            
            print("✅ Restore preview successful")
            print("Changes that would be made:")
            
            if not result['changes']:
                print("   No changes detected")
            else:
                for change in result['changes']:
                    print(f"   Table: {change['table']}")
                    print(f"     Adds: {change['adds']}")
                    print(f"     Updates: {change['updates']}")
                    print(f"     Deletes: {change['deletes']}")
            
            return 0
        else:
            print(f"🔄 Restoring from backup {backup_id}...")
            result = backup_service.restore_commit(backup_id)
            
            if not result['ok']:
                print(f"❌ Restore failed: {result['reason']}")
                return 1
            
            print("✅ Restore completed successfully")
            if 'pre_restore_backup_id' in result:
                print(f"   Pre-restore backup created: {result['pre_restore_backup_id']}")
            
            return 0
    
    except Exception as e:
        print(f"❌ Restore failed: {e}")
        return 1

def main():
    parser = argparse.ArgumentParser(description="OWLIN Backup CLI Tool")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new backup')
    create_parser.add_argument('--mode', choices=['manual', 'scheduled'], default='manual',
                              help='Backup mode (default: manual)')
    
    # List command
    subparsers.add_parser('list', help='List all backups')
    
    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore from backup')
    restore_parser.add_argument('--id', required=True, help='Backup ID')
    restore_parser.add_argument('--dry-run', action='store_true', help='Preview only')
    restore_parser.add_argument('--commit', action='store_true', help='Actually perform restore')
    
    args = parser.parse_args()
    
    if args.command == 'create':
        return create_backup(args.mode)
    elif args.command == 'list':
        return list_backups()
    elif args.command == 'restore':
        if not args.commit and not args.dry_run:
            print("❌ Must specify either --dry-run or --commit")
            return 1
        return restore_backup(args.id, args.dry_run)
    else:
        parser.print_help()
        return 1

if __name__ == '__main__':
    sys.exit(main())
