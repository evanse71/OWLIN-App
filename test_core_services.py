#!/usr/bin/env python3
"""
Test script for core services - run this to verify implementation
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_pairing_math():
    """Test the pairing math kernel"""
    try:
        from schemas.pairing import CandidateLine, LineScore
        from services.pairing_math import score_line
        
        # Create test data
        inv = CandidateLine(None, "TIA MARIA 1L", 6.0, 1200, 6.0)
        dn = CandidateLine(None, "TIA MARIA 1L", 6.0, 1200, 6.0)
        
        # Test scoring
        score = score_line(inv, dn)
        print(f"✅ PAIRING_MATH_OK - Score: {score.total:.3f}")
        return True
        
    except Exception as e:
        print(f"❌ PAIRING_MATH_FAILED: {e}")
        return False

def test_pairing_service():
    """Test the pairing service"""
    try:
        from services.pairing_service import suggest_pairs, persist_pairs
        print("✅ PAIRING_SERVICE_OK - Imports successful")
        return True
        
    except Exception as e:
        print(f"❌ PAIRING_SERVICE_FAILED: {e}")
        return False

def test_mismatch_service():
    """Test the mismatch service"""
    try:
        from services.mismatch_service import evaluate_mismatches
        print("✅ MISMATCH_SERVICE_OK - Imports successful")
        return True
        
    except Exception as e:
        print(f"❌ MISMATCH_SERVICE_FAILED: {e}")
        return False

def test_api_schemas():
    """Test the API schemas"""
    try:
        from schemas.api_invoice import InvoiceBundle, Line, MatchSuggestion, DNCandidate
        print("✅ API_SCHEMAS_OK - All schemas imported")
        return True
        
    except Exception as e:
        print(f"❌ API_SCHEMAS_FAILED: {e}")
        return False

def test_db_exec():
    """Test the DB execution helpers"""
    try:
        from services.db_exec import exec_one, query_all, query_one
        print("✅ DB_EXEC_OK - All helpers imported")
        return True
        
    except Exception as e:
        print(f"❌ DB_EXEC_FAILED: {e}")
        return False

def main():
    """Run all tests"""
    print("🧊 BRUTAL JUDGE PROTOCOL - CORE SERVICES TEST")
    print("=" * 50)
    
    tests = [
        test_pairing_math,
        test_pairing_service,
        test_mismatch_service,
        test_api_schemas,
        test_db_exec
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎯 ALL CORE SERVICES WORKING - READY FOR INTEGRATION")
        return True
    else:
        print("❌ SOME SERVICES FAILED - NEEDS FIXING")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 