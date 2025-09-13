#!/usr/bin/env python3
"""
Diagnostics and Support Pack Utilities
"""

import os
import json
import glob
import shutil
from datetime import datetime
from pathlib import Path

def get_latest_diagnostics_csv():
    """Get the path to the latest diagnostics CSV file"""
    csv_dir = Path("backups/diagnostics")
    if not csv_dir.exists():
        return None
    
    csv_pattern = csv_dir / "ocr_post_pipeline_*.csv"
    csv_files = list(csv_dir.glob("ocr_post_pipeline_*.csv"))
    
    if not csv_files:
        return None
    
    # Return the most recent CSV file
    return str(max(csv_files, key=os.path.getmtime))

def get_health_snapshot():
    """Get current health snapshot"""
    try:
        import requests
        response = requests.get("http://localhost:8001/api/health/post_ocr", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Health endpoint returned {response.status_code}"}
    except Exception as e:
        return {"error": f"Failed to get health snapshot: {e}"}

def create_support_pack(max_jobs=10, include_ocr_traces=True):
    """Create a support pack with enhanced diagnostics"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pack_name = f"support_pack_{timestamp}"
    pack_dir = Path("support_packs") / pack_name
    pack_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy database
    db_path = os.environ.get("OWLIN_DB", "data/owlin.db")
    if os.path.exists(db_path):
        shutil.copy2(db_path, pack_dir / "owlin.db")
    
    # Copy latest diagnostics CSV
    latest_csv = get_latest_diagnostics_csv()
    if latest_csv and os.path.exists(latest_csv):
        shutil.copy2(latest_csv, pack_dir / "latest_diagnostics.csv")
    
    # Add health snapshot
    health_snapshot = get_health_snapshot()
    with open(pack_dir / "health_snapshot.json", "w") as f:
        json.dump(health_snapshot, f, indent=2)
    
    # Copy recent logs
    log_dir = Path("data/logs")
    if log_dir.exists():
        log_files = list(log_dir.glob("*.log"))
        for log_file in log_files[-5:]:  # Last 5 log files
            shutil.copy2(log_file, pack_dir / f"log_{log_file.name}")
    
    # Copy recent audit logs
    audit_log = Path("data/audit.log")
    if audit_log.exists():
        shutil.copy2(audit_log, pack_dir / "audit.log")
    
    # Create manifest
    manifest = {
        "created_at": datetime.now().isoformat(),
        "components": {
            "database": os.path.exists(pack_dir / "owlin.db"),
            "diagnostics_csv": os.path.exists(pack_dir / "latest_diagnostics.csv"),
            "health_snapshot": os.path.exists(pack_dir / "health_snapshot.json"),
            "logs": len(list(pack_dir.glob("log_*.log"))),
            "audit_log": os.path.exists(pack_dir / "audit.log")
        },
        "health_data": health_snapshot
    }
    
    with open(pack_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    
    # Create zip archive
    zip_path = f"support_packs/{pack_name}.zip"
    shutil.make_archive(str(pack_dir), 'zip', pack_dir)
    
    # Clean up temp directory
    shutil.rmtree(pack_dir)
    
    return zip_path

def list_support_packs():
    """List existing support packs"""
    pack_dir = Path("support_packs")
    if not pack_dir.exists():
        return []
    
    packs = []
    for zip_file in pack_dir.glob("support_pack_*.zip"):
        stat = zip_file.stat()
        packs.append({
            "name": zip_file.name,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
        })
    
    return sorted(packs, key=lambda x: x["created_at"], reverse=True) 