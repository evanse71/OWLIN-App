#!/usr/bin/env python3
"""
OWLIN Support Pack CLI Tool

Usage:
    python scripts/owlin_support_pack.py create --notes "post-incident"
    python scripts/owlin_support_pack.py list
    python scripts/owlin_support_pack.py download --id <UUID> --out ./pack.zip
"""

import sys
import argparse
import shutil
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services import support_pack as support_pack_service

def create_support_pack(notes: str = None):
    """Create a new support pack."""
    try:
        result = support_pack_service.pack_create(notes)
        print(f"✅ Support pack created successfully")
        print(f"   ID: {result['id']}")
        print(f"   Path: {result['path']}")
        print(f"   Size: {result['size_bytes']:,} bytes")
        print(f"   Created: {result['created_at']}")
        if notes:
            print(f"   Notes: {notes}")
        return 0
    except Exception as e:
        print(f"❌ Support pack creation failed: {e}")
        return 1

def list_support_packs():
    """List all support packs."""
    try:
        packs = support_pack_service.pack_list()
        
        if not packs:
            print("No support packs found.")
            return 0
        
        print(f"Found {len(packs)} support pack(s):")
        print("-" * 80)
        
        for pack in packs:
            print(f"ID: {pack['id']}")
            print(f"Created: {pack['created_at']}")
            print(f"Size: {pack['size_bytes']:,} bytes")
            print(f"App Version: {pack['app_version']}")
            if pack.get('notes'):
                print(f"Notes: {pack['notes']}")
            print(f"Path: {pack['path']}")
            print("-" * 80)
        
        return 0
    except Exception as e:
        print(f"❌ Failed to list support packs: {e}")
        return 1

def download_support_pack(pack_id: str, output_path: str):
    """Download support pack to specified path."""
    try:
        # Get pack info
        pack_info = support_pack_service.pack_get_info(pack_id)
        if not pack_info:
            print(f"❌ Support pack {pack_id} not found")
            return 1
        
        print(f"📦 Downloading support pack {pack_id}...")
        
        # Stream and save
        with open(output_path, 'wb') as f:
            for chunk in support_pack_service.pack_stream(pack_id):
                if chunk:
                    f.write(chunk)
        
        print(f"✅ Support pack downloaded to {output_path}")
        print(f"   Size: {pack_info['size_bytes']:,} bytes")
        return 0
    
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return 1

def main():
    parser = argparse.ArgumentParser(description="OWLIN Support Pack CLI Tool")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new support pack')
    create_parser.add_argument('--notes', help='Optional notes for the support pack')
    
    # List command
    subparsers.add_parser('list', help='List all support packs')
    
    # Download command
    download_parser = subparsers.add_parser('download', help='Download support pack')
    download_parser.add_argument('--id', required=True, help='Support pack ID')
    download_parser.add_argument('--out', required=True, help='Output file path')
    
    args = parser.parse_args()
    
    if args.command == 'create':
        return create_support_pack(args.notes)
    elif args.command == 'list':
        return list_support_packs()
    elif args.command == 'download':
        return download_support_pack(args.id, args.out)
    else:
        parser.print_help()
        return 1

if __name__ == '__main__':
    sys.exit(main())
