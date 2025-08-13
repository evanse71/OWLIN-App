#!/usr/bin/env python3
"""
Simple backend test to identify startup issues
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test if all required modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        print("  Testing FastAPI...")
        from fastapi import FastAPI
        print("  ✅ FastAPI imported")
        
        print("  Testing routes...")
        from routes import invoices
        print("  ✅ invoices imported")
        
        print("  Testing backend modules...")
        from backend import main
        print("  ✅ backend.main imported")
        
        print("  Testing OCR modules...")
        from backend.ocr import enhanced_ocr_engine
        print("  ✅ OCR engine imported")
        
        print("  Testing upload modules...")
        from backend.upload import adaptive_processor
        print("  ✅ adaptive processor imported")
        
        print("✅ All imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_app():
    """Test creating a simple FastAPI app"""
    print("\n🔍 Testing simple app creation...")
    
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        
        app = FastAPI(title="Test API")
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        @app.get("/")
        async def root():
            return {"message": "Test API is running"}
        
        @app.get("/health")
        async def health():
            return {"status": "ok"}
        
        print("✅ Simple app created successfully!")
        return app
        
    except Exception as e:
        print(f"❌ Simple app creation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Run all tests"""
    print("🔬 Backend Startup Diagnostic")
    print("=" * 40)
    
    # Test 1: Imports
    if not test_imports():
        print("❌ Import test failed")
        return
    
    # Test 2: Simple app
    app = test_simple_app()
    if not app:
        print("❌ Simple app test failed")
        return
    
    print("\n✅ All tests passed!")
    print("The issue might be with OCR model loading during startup.")

if __name__ == "__main__":
    main() 