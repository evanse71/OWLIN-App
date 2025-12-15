#!/usr/bin/env python3
"""
Test Runner for Owlin Backend Tests
Runs the API contract tests and reports results.
"""
import subprocess
import sys
import os
from pathlib import Path

def run_backend_tests():
    """Run the backend API contract tests"""
    print("🧪 Running backend API contract tests...")
    
    # Change to the .github directory
    test_dir = Path(__file__).parent
    os.chdir(test_dir)
    
    try:
        result = subprocess.run([
            sys.executable, 'test_api_contract.py'
        ], capture_output=True, text=True, timeout=30)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Backend tests timed out")
        return False
    except Exception as e:
        print(f"❌ Error running backend tests: {e}")
        return False

def run_frontend_tests():
    """Run the frontend tests"""
    print("\n🧪 Running frontend tests...")
    
    # Change to the frontend directory
    frontend_dir = Path(__file__).parent.parent / "source_extracted" / "tmp_lovable"
    
    if not frontend_dir.exists():
        print("❌ Frontend directory not found")
        return False
    
    os.chdir(frontend_dir)
    
    try:
        result = subprocess.run([
            'npm', 'test'
        ], capture_output=True, text=True, timeout=60)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Frontend tests timed out")
        return False
    except FileNotFoundError:
        print("❌ npm not found. Make sure Node.js is installed")
        return False
    except Exception as e:
        print(f"❌ Error running frontend tests: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Owlin test suite...")
    
    backend_passed = run_backend_tests()
    frontend_passed = run_frontend_tests()
    
    print("\n📊 Test Results Summary:")
    print(f"Backend tests: {'✅ PASSED' if backend_passed else '❌ FAILED'}")
    print(f"Frontend tests: {'✅ PASSED' if frontend_passed else '❌ FAILED'}")
    
    if backend_passed and frontend_passed:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)
