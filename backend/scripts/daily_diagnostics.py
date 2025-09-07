#!/usr/bin/env python3
"""
Daily OCR Diagnostics Runner
Runs diagnostics daily and maintains only the last 14 CSV files
"""

import os
import glob
import subprocess
import sys
from datetime import datetime

def run_diagnostics():
    """Run the OCR post-pipeline diagnostics"""
    try:
        # Run the diagnostics script
        result = subprocess.run([
            sys.executable, 
            "backend/scripts/ocr_post_pipeline_diagnostics.py"
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode == 0:
            print(f"✅ Diagnostics completed successfully at {datetime.now()}")
            print(result.stdout)
            return True
        else:
            print(f"❌ Diagnostics failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error running diagnostics: {e}")
        return False

def cleanup_old_csvs():
    """Keep only the last 14 CSV files"""
    try:
        csv_dir = "backups/diagnostics"
        if not os.path.exists(csv_dir):
            return
        
        # Get all CSV files sorted by modification time (newest first)
        csv_pattern = os.path.join(csv_dir, "ocr_post_pipeline_*.csv")
        csv_files = glob.glob(csv_pattern)
        csv_files.sort(key=os.path.getmtime, reverse=True)
        
        # Remove files beyond the 14th
        if len(csv_files) > 14:
            files_to_remove = csv_files[14:]
            for file_path in files_to_remove:
                os.remove(file_path)
                print(f"🗑️  Removed old CSV: {os.path.basename(file_path)}")
        
        print(f"📊 Kept {min(len(csv_files), 14)} CSV files")
        
    except Exception as e:
        print(f"❌ Error cleaning up CSVs: {e}")

def main():
    print(f"🔄 Starting daily diagnostics at {datetime.now()}")
    
    # Run diagnostics
    success = run_diagnostics()
    
    # Clean up old files
    cleanup_old_csvs()
    
    if success:
        print("✅ Daily diagnostics completed successfully")
        sys.exit(0)
    else:
        print("❌ Daily diagnostics failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 