#!/usr/bin/env python3
"""
Minimal test to verify database connectivity and basic operations
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_manager_unified import get_db_manager

def test_minimal():
    """Test minimal database operations"""
    try:
        db_manager = get_db_manager()
        
        # Test database connection
        with db_manager.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM invoices")
            count = cursor.fetchone()['count']
            print(f"✅ Database connected. Invoice count: {count}")
            
            # Test basic query
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row['name'] for row in cursor.fetchall()]
            print(f"✅ Tables found: {tables}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_minimal() 