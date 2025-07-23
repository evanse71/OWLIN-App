#!/usr/bin/env python3
"""
Script to start both the FastAPI backend and Next.js frontend servers.
"""

import subprocess
import sys
import os
import time
import signal
import threading
from pathlib import Path

def start_backend():
    """Start the FastAPI backend server."""
    print("🚀 Starting FastAPI backend server...")
    try:
        # Start the backend server
        backend_process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "backend.main:app", 
            "--host", "0.0.0.0", "--port", "8000", "--reload",
            "--reload-exclude", "node_modules",
            "--reload-exclude", ".next",
            "--reload-exclude", "data/uploads",
            "--reload-exclude", "venv"
        ], cwd=os.getcwd())
        
        print("✅ Backend server started on http://localhost:8000")
        return backend_process
    except Exception as e:
        print(f"❌ Failed to start backend server: {e}")
        return None

def start_frontend():
    """Start the Next.js frontend server."""
    print("🚀 Starting Next.js frontend server...")
    try:
        # Check if node_modules exists
        if not Path("node_modules").exists():
            print("📦 Installing npm dependencies...")
            subprocess.run(["npm", "install"], check=True)
        
        # Start the frontend server on port 3000 (standard Next.js port)
        frontend_process = subprocess.Popen([
            "npm", "run", "dev", "--", "--port", "3000"
        ], cwd=os.getcwd())
        
        print("✅ Frontend server started on http://localhost:3000")
        return frontend_process
    except Exception as e:
        print(f"❌ Failed to start frontend server: {e}")
        return None

def main():
    """Main function to start both servers."""
    print("🎯 Starting Owlin Application Servers...")
    print("=" * 50)
    
    # Start backend
    backend_process = start_backend()
    if not backend_process:
        print("❌ Backend failed to start. Exiting.")
        sys.exit(1)
    
    # Wait a moment for backend to initialize
    time.sleep(2)
    
    # Start frontend
    frontend_process = start_frontend()
    if not frontend_process:
        print("❌ Frontend failed to start. Stopping backend...")
        backend_process.terminate()
        sys.exit(1)
    
    print("\n🎉 Both servers are running!")
    print("📱 Frontend: http://localhost:3000")
    print("🔧 Backend API: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop both servers...")
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
            
            # Check if processes are still running
            if backend_process.poll() is not None:
                print("❌ Backend server stopped unexpectedly")
                break
                
            if frontend_process.poll() is not None:
                print("❌ Frontend server stopped unexpectedly")
                break
                
    except KeyboardInterrupt:
        print("\n🛑 Stopping servers...")
        
        # Terminate both processes
        if backend_process:
            backend_process.terminate()
            print("✅ Backend server stopped")
            
        if frontend_process:
            frontend_process.terminate()
            print("✅ Frontend server stopped")
            
        print("👋 Goodbye!")

if __name__ == "__main__":
    main() 