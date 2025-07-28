#!/usr/bin/env python3
"""
Setup and test script for Owlin application.
This script installs dependencies and runs tests to verify everything is working.
"""

import subprocess
import sys
import os
import time

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible."""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} is not compatible. Need Python 3.8+")
        return False

def install_python_dependencies():
    """Install Python dependencies."""
    print("📦 Installing Python dependencies...")
    
    # Check if requirements.txt exists
    if not os.path.exists("requirements.txt"):
        print("❌ requirements.txt not found")
        return False
    
    # Install dependencies using python3 -m pip
    return run_command("python3 -m pip install -r requirements.txt", "Installing Python dependencies")

def check_node_dependencies():
    """Check if Node.js dependencies are installed."""
    print("📦 Checking Node.js dependencies...")
    
    # Check if package.json exists
    if not os.path.exists("package.json"):
        print("❌ package.json not found")
        return False
    
    # Check if node_modules exists
    if not os.path.exists("node_modules"):
        print("⚠️ node_modules not found. Installing Node.js dependencies...")
        return run_command("npm install", "Installing Node.js dependencies")
    else:
        print("✅ Node.js dependencies already installed")
        return True

def test_backend():
    """Test if backend is working."""
    print("🔧 Testing backend...")
    
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running and healthy")
            return True
        else:
            print(f"⚠️ Backend responded with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend test failed: {str(e)}")
        print("   Make sure the backend server is running:")
        print("   python3 -m uvicorn backend.main:app --reload --port 8000")
        return False

def test_frontend():
    """Test if frontend is working."""
    print("🌐 Testing frontend...")
    
    try:
        import requests
        response = requests.get("http://localhost:3000", timeout=5)
        if response.status_code == 200:
            print("✅ Frontend is running")
            return True
        else:
            print(f"⚠️ Frontend responded with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Frontend test failed: {str(e)}")
        print("   Make sure the frontend server is running:")
        print("   npm run dev")
        return False

def run_upload_test():
    """Run the upload flow test."""
    print("🧪 Running upload flow test...")
    
    if os.path.exists("test_upload_simple.py"):
        return run_command("python3 test_upload_simple.py", "Upload flow test")
    elif os.path.exists("test_upload_flow.py"):
        return run_command("python3 test_upload_flow.py", "Upload flow test")
    else:
        print("⚠️ No test script found")
        return True

def main():
    """Main setup and test function."""
    print("🚀 Owlin Setup and Test Script")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        return False
    
    print("\n" + "=" * 50)
    
    # Install Python dependencies
    if not install_python_dependencies():
        print("❌ Failed to install Python dependencies")
        return False
    
    print("\n" + "=" * 50)
    
    # Check Node.js dependencies
    if not check_node_dependencies():
        print("❌ Failed to install Node.js dependencies")
        return False
    
    print("\n" + "=" * 50)
    
    # Test backend
    if not test_backend():
        print("⚠️ Backend test failed - you may need to start the backend server")
    
    print("\n" + "=" * 50)
    
    # Test frontend
    if not test_frontend():
        print("⚠️ Frontend test failed - you may need to start the frontend server")
    
    print("\n" + "=" * 50)
    
    # Run upload test
    if not run_upload_test():
        print("⚠️ Upload test failed")
    
    print("\n" + "=" * 50)
    print("🎉 Setup and testing completed!")
    print("\n📋 Next Steps:")
    print("1. Start the backend server:")
    print("   python3 -m uvicorn backend.main:app --reload --port 8000")
    print("2. Start the frontend server:")
    print("   npm run dev")
    print("3. Or use the automated start script:")
    print("   python3 start_servers.py")
    print("\n🌐 Access URLs:")
    print("   Frontend: http://localhost:3000")
    print("   Backend: http://localhost:8000")
    print("   API Docs: http://localhost:8000/docs")

if __name__ == "__main__":
    main() 