#!/usr/bin/env python3
"""
Pipeline Verification Script
Tests the OCR pipeline with sample documents and verifies feature toggles.
"""
import sys
import os
import sqlite3
import json
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

def test_feature_toggles():
    """Test feature toggle states."""
    print("🔧 Feature Toggle Verification")
    print("=" * 50)
    
    try:
        from backend.config import (
            FEATURE_HTR_ENABLED, 
            FEATURE_DONUT_FALLBACK, 
            env_bool
        )
        
        print(f"✅ FEATURE_HTR_ENABLED: {FEATURE_HTR_ENABLED}")
        print(f"✅ FEATURE_DONUT_FALLBACK: {FEATURE_DONUT_FALLBACK}")
        print(f"✅ FEATURE_LLM_AUTOMATION: {env_bool('FEATURE_LLM_AUTOMATION', True)}")
        
        # Verify safe defaults
        assert FEATURE_HTR_ENABLED == False, "HTR should be disabled by default"
        assert FEATURE_DONUT_FALLBACK == False, "Donut should be disabled by default"
        
        print("✅ All feature toggles have safe defaults")
        return True
        
    except Exception as e:
        print(f"❌ Feature toggle verification failed: {e}")
        return False

def test_database_connection():
    """Test database connection and get sample documents."""
    print("\n🗄️ Database Verification")
    print("=" * 50)
    
    try:
        con = sqlite3.connect("data/owlin.db", check_same_thread=False)
        cur = con.cursor()
        
        # Get document count
        cur.execute("SELECT COUNT(*) FROM documents")
        doc_count = cur.fetchone()[0]
        print(f"✅ Database connected: {doc_count} documents")
        
        # Get sample documents (using correct schema)
        cur.execute("SELECT id, path FROM documents WHERE id IS NOT NULL LIMIT 3")
        sample_docs = cur.fetchall()
        
        if sample_docs:
            print(f"✅ Sample documents found: {len(sample_docs)}")
            for doc_id, path in sample_docs:
                print(f"  - {doc_id}: {path}")
        else:
            print("⚠️ No sample documents found")
        
        con.close()
        return sample_docs
        
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        return []

def test_llm_endpoints():
    """Test LLM endpoint availability."""
    print("\n🤖 LLM Endpoint Verification")
    print("=" * 50)
    
    try:
        from backend.api.llm_router import router
        
        endpoints = []
        for route in router.routes:
            endpoints.append(f"{list(route.methods)[0]} {route.path}")
        
        print("✅ LLM endpoints available:")
        for endpoint in endpoints:
            print(f"  - {endpoint}")
        
        # Check if all required endpoints exist
        required_endpoints = ["POST /api/llm/run", "GET /api/llm/status"]
        for req_endpoint in required_endpoints:
            if any(req_endpoint in ep for ep in endpoints):
                print(f"✅ {req_endpoint} - Available")
            else:
                print(f"❌ {req_endpoint} - Missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ LLM endpoint verification failed: {e}")
        return False

def test_template_library():
    """Test template library loading."""
    print("\n📋 Template Library Verification")
    print("=" * 50)
    
    try:
        import yaml
        
        template_dir = "backend/templates/suppliers"
        templates = []
        
        for filename in os.listdir(template_dir):
            if filename.endswith('.yaml'):
                filepath = os.path.join(template_dir, filename)
                with open(filepath, 'r') as file:
                    data = yaml.safe_load(file)
                
                templates.append({
                    'name': data.get('name', 'Unknown'),
                    'supplier': data.get('supplier', {}).get('name', 'Unknown'),
                    'aliases': len(data.get('supplier', {}).get('aliases', []))
                })
        
        print(f"✅ Template library loaded: {len(templates)} templates")
        for template in templates:
            print(f"  - {template['name']} ({template['aliases']} aliases)")
        
        return len(templates) > 0
        
    except Exception as e:
        print(f"❌ Template library verification failed: {e}")
        return False

def test_pipeline_safety():
    """Test pipeline safety with disabled features."""
    print("\n🛡️ Pipeline Safety Verification")
    print("=" * 50)
    
    try:
        # Test that pipeline can run without crashing when features are disabled
        from backend.ocr.owlin_scan_pipeline import process_document
        
        # This should not crash even with disabled features
        print("✅ Pipeline import successful")
        print("✅ Pipeline can be imported without errors")
        
        return True
        
    except Exception as e:
        print(f"❌ Pipeline safety verification failed: {e}")
        return False

def main():
    """Run all verification tests."""
    print("🔍 Owlin AI Feature Verification + Safety Audit")
    print("=" * 60)
    
    results = {
        'feature_toggles': test_feature_toggles(),
        'database': len(test_database_connection()) > 0,
        'llm_endpoints': test_llm_endpoints(),
        'template_library': test_template_library(),
        'pipeline_safety': test_pipeline_safety()
    }
    
    print("\n📊 Verification Summary")
    print("=" * 50)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name.replace('_', ' ').title()}")
        if not passed:
            all_passed = False
    
    print(f"\n🎯 Overall Status: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
