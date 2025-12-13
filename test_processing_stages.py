#!/usr/bin/env python3
"""Test processing stages"""

import asyncio
import sys
import os
import uuid
import json
import traceback
sys.path.insert(0, 'backend')

from upload_pipeline_bulletproof import get_upload_pipeline

async def test_processing_stages():
    """Test that all processing stages are executed in order"""
    print("🧪 Testing processing stages...")
    
    # Create unique test file
    unique_content = f"Test document content for stage verification - {uuid.uuid4()}"
    test_file = "/tmp/test_stages_doc.txt"
    with open(test_file, "w") as f:
        f.write(unique_content)
    
    try:
        # Process the document
        pipeline = get_upload_pipeline()
        print("📋 Pipeline created, starting processing...")
        
        result = await pipeline.process_upload(test_file, "test_stages_doc.txt")
        
        print(f"✅ Processing result: {result.success}")
        
        # Check processing logs
        import sqlite3
        conn = sqlite3.connect("/tmp/test_stages.db")
        cursor = conn.execute("SELECT stage, status, error_message FROM processing_logs ORDER BY created_at")
        stages = cursor.fetchall()
        conn.close()
        
        print(f"📊 Processing stages: {len(stages)}")
        for stage, status, error in stages:
            print(f"   - {stage}: {status}" + (f" (error: {error})" if error else ""))
        
        # Check JSONL diagnostics
        import glob
        jsonl_files = glob.glob("/tmp/*.jsonl") + glob.glob("backups/diagnostics/*.jsonl")
        if jsonl_files:
            print("📄 JSONL diagnostics found:")
            for jsonl_file in jsonl_files:
                with open(jsonl_file, 'r') as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            if 'stage' in data:
                                print(f"   - {data.get('stage', 'unknown')}: {data.get('status', 'unknown')}")
                        except:
                            pass
        else:
            print("📄 No JSONL diagnostics found")
        
        # Verify all required stages are present
        expected_stages = ['enqueue', 'dedup_check', 'rasterize', 'parse', 'ocr', 'parse', 'validate', 'persist', 'pairing', 'finalize']
        actual_stages = [stage for stage, status, error in stages if status == 'completed']
        
        missing_stages = set(expected_stages) - set(actual_stages)
        if missing_stages:
            print(f"❌ Missing stages: {missing_stages}")
            return False
        else:
            print("✅ All expected stages completed")
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_processing_stages())
    sys.exit(0 if success else 1) 