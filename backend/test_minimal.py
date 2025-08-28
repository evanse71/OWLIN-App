#!/usr/bin/env python3
"""Minimal test to verify backend can start"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

try:
    print("Testing imports...")
    from db import init, migrate, get_conn
    print("✅ DB imports OK")
    
    print("Testing DB init...")
    init()
    print("✅ DB init OK")
    
    print("Testing DB migrate...")
    migrate()
    print("✅ DB migrate OK")
    
    print("Testing DB connection...")
    with get_conn() as c:
        c.execute("SELECT 1").fetchone()
    print("✅ DB connection OK")
    
    print("Testing services import...")
    from services import handle_upload_and_queue
    print("✅ Services import OK")
    
    print("Testing app import...")
    from app import app
    print("✅ App import OK")
    
    print("\n🎉 All tests passed! Backend should start successfully.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1) 