#!/usr/bin/env python3
"""
Force Upload Script - Bypass Frontend and Upload Directly to Backend

This script uploads a PDF file directly to the backend API, bypassing any
frontend issues. This is useful for testing the LLM extraction pipeline.

Usage:
    python force_upload.py [path/to/file.pdf]
    python force_upload.py  # Auto-finds latest _Fresh_ file
"""

import sys
import requests
from pathlib import Path
from datetime import datetime

def find_latest_fresh_file():
    """Find the latest _Fresh_ PDF file in Downloads."""
    downloads_dir = Path.home() / "Downloads"
    
    if not downloads_dir.exists():
        return None
    
    # Find all _Fresh_ PDF files
    fresh_files = list(downloads_dir.glob("*_Fresh_*.pdf"))
    
    if not fresh_files:
        return None
    
    # Sort by modification time, newest first
    fresh_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    return fresh_files[0]

def find_file_in_uploads(pattern: str = "Stori_Short.pdf"):
    """Find files matching pattern in data/uploads directory."""
    uploads_dir = Path("data") / "uploads"
    
    if not uploads_dir.exists():
        return None
    
    # First try exact match for Stori_Short.pdf
    exact_match = uploads_dir / "Stori_Short.pdf"
    if exact_match.exists():
        return exact_match
    
    # Fallback to pattern matching
    matches = list(uploads_dir.glob(pattern))
    if matches:
        # Sort by modification time, newest first
        matches.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return matches[0]
    
    return None

def force_upload(file_path: str, api_url: str = "http://127.0.0.1:5176"):
    """
    Upload a file directly to the backend API.
    
    Args:
        file_path: Path to the PDF file to upload
        api_url: Base URL of the backend API
        use_ocr_endpoint: If True, use /api/ocr/run, else use /api/upload
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")
    
    # Use the main upload endpoint which triggers full pipeline including LLM
    # Endpoint: /api/upload (defined in backend/main.py:2003)
    upload_url = f"{api_url}/api/upload"
    file_size = file_path.stat().st_size / 1024  # Size in KB
    
    print("=" * 80)
    print("🚀 FORCE UPLOAD - Bypassing Frontend")
    print("=" * 80)
    print()
    print(f"📄 File: {file_path.name}")
    print(f"   Path: {file_path}")
    print(f"   Size: {file_size:.2f} KB")
    print()
    print(f"🌐 API: {upload_url}")
    print()
    print("📤 Uploading...")
    print()
    
    try:
        # Open file and upload
        with open(file_path, 'rb') as f:
            files = {
                'file': (file_path.name, f, 'application/pdf')
            }
            
            # Send POST request
            response = requests.post(
                upload_url,
                files=files,
                timeout=60  # 60 second timeout for large files
            )
        
        # Check response
        response.raise_for_status()
        result = response.json()
        
        print("=" * 80)
        print("✅ UPLOAD SUCCESS!")
        print("=" * 80)
        print()
        print("📋 Response:")
        print(f"   Status: {response.status_code}")
        print(f"   Doc ID: {result.get('doc_id', 'N/A')}")
        print(f"   Filename: {result.get('filename', 'N/A')}")
        print(f"   Status: {result.get('status', 'N/A')}")
        if 'hash' in result:
            print(f"   Hash: {result.get('hash', 'N/A')}")
        print()
        print("=" * 80)
        print("👁️  CHECK YOUR LOGS NOW!")
        print("=" * 80)
        print()
        print("Watch for the Golden Sequence:")
        print("  → [AUDIT REQUEST] POST /api/upload")
        print("  → 🔥🔥🔥 BRUTE FORCE: LLM EXTRACTION IS ON! 🔥🔥🔥")
        print("  → [LLM_EXTRACTION] ⚡ Starting LLM reconstruction")
        print("  → [LLM_PARSER] Sending ... text lines to LLM")
        print("  → [LLM_PARSER] Success")
        print()
        
        return result
        
    except requests.exceptions.ConnectionError:
        print("=" * 80)
        print("❌ CONNECTION ERROR")
        print("=" * 80)
        print()
        print(f"Could not connect to: {upload_url}")
        print()
        print("Make sure the backend is running:")
        print("  - Check: http://127.0.0.1:5176/api/health")
        print("  - Or try: http://127.0.0.1:8000/api/health")
        print()
        sys.exit(1)
        
    except requests.exceptions.Timeout:
        print("=" * 80)
        print("❌ TIMEOUT ERROR")
        print("=" * 80)
        print()
        print("Upload timed out after 60 seconds.")
        print("The file might be too large or the backend is slow.")
        print()
        sys.exit(1)
        
    except requests.exceptions.HTTPError as e:
        print("=" * 80)
        print("❌ HTTP ERROR")
        print("=" * 80)
        print()
        print(f"Status Code: {e.response.status_code}")
        print(f"Response: {e.response.text}")
        print()
        sys.exit(1)
        
    except Exception as e:
        print("=" * 80)
        print("❌ ERROR")
        print("=" * 80)
        print()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print()
        sys.exit(1)

def main():
    """Main entry point."""
    # Determine file to upload
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        # First try data/uploads, then Downloads
        print("🔍 Searching for _Fresh_ file...")
        file_path = find_file_in_uploads("*_Fresh_*.pdf")
        
        if not file_path:
            print("   Not found in data/uploads, checking Downloads...")
            file_path = find_latest_fresh_file()
        
        if not file_path:
            print("❌ No _Fresh_ PDF file found!")
            print()
            print("Usage:")
            print("  python force_upload.py [path/to/file.pdf]")
            print()
            print("Or run make_unique_invoice.py first to create a fresh file.")
            sys.exit(1)
        
        print(f"✓ Found: {file_path.name}")
        print(f"   Location: {file_path}")
        print()
    
    # Try port 5176 first, fallback to 8000
    api_urls = [
        "http://127.0.0.1:5176",
        "http://127.0.0.1:8000"
    ]
    
    for api_url in api_urls:
        try:
            # Quick health check
            health_url = f"{api_url}/api/health"
            response = requests.get(health_url, timeout=2)
            if response.status_code == 200:
                print(f"✓ Backend found at: {api_url}")
                print()
                force_upload(file_path, api_url)
                return
        except:
            continue
    
    print("❌ Backend not found!")
    print()
    print("Tried:")
    for api_url in api_urls:
        print(f"  - {api_url}")
    print()
    print("Make sure the backend is running.")
    sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(1)

