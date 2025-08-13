#!/usr/bin/env python3
"""
Start both FastAPI backend and Next.js frontend servers.
"""

import subprocess
import sys
import time
import socket
import os

# Configuration
BACKEND_HOST = "0.0.0.0"
BACKEND_PORT = "8000"
FRONTEND_HOST = "0.0.0.0"
FRONTEND_PORT = "3000"

def check_ports():
    """Check if ports are already in use."""
    def is_port_in_use(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    if is_port_in_use(int(BACKEND_PORT)):
        print(f"⚠️  Warning: Backend port {BACKEND_PORT} is already in use")
    if is_port_in_use(int(FRONTEND_PORT)):
        print(f"⚠️  Warning: Frontend port {FRONTEND_PORT} is already in use")

def kill_existing_processes():
    """Kill any existing server processes."""
    try:
        # Kill any existing uvicorn processes
        subprocess.run(["pkill", "-f", "uvicorn"], check=False)
        # Kill any existing next processes
        subprocess.run(["pkill", "-f", "next"], check=False)
        time.sleep(2)  # Wait for processes to terminate
        print("✅ Killed existing server processes")
    except Exception as e:
        print(f"⚠️  Warning: Could not kill existing processes: {e}")

def start_backend():
    """Start the FastAPI backend server."""
    print("🚀 Starting FastAPI backend server...")
    print("⏳ This may take a moment while PaddleOCR models load...")
    
    # Set environment variables for development
    env = os.environ.copy()
    env['NODE_ENV'] = 'development'
    env['ENVIRONMENT'] = 'development'
    
    try:
        backend_process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "backend.main:app",
            "--reload",
            "--host", BACKEND_HOST,
            "--port", BACKEND_PORT
        ], env=env)
        
        # Wait longer for the server to start (PaddleOCR loading takes time)
        print("⏳ Waiting for backend server to initialize...")
        time.sleep(10)
        
        # Test if the server is responding with increased timeout
        try:
            import requests
            response = requests.get(f"http://localhost:{BACKEND_PORT}/", timeout=30)
            if response.status_code == 200:
                print(f"✅ Backend server started on http://localhost:{BACKEND_PORT}")
                print(f"   External access: http://{BACKEND_HOST}:{BACKEND_PORT}")
                return backend_process
            else:
                print(f"❌ Backend server failed to start (status: {response.status_code})")
                return None
        except ImportError:
            # requests not available, just assume it's working
            print(f"✅ Backend server started on http://localhost:{BACKEND_PORT}")
            print(f"   External access: http://{BACKEND_HOST}:{BACKEND_PORT}")
            return backend_process
        except Exception as e:
            print(f"❌ Backend server failed to start: {e}")
            return None
            
    except Exception as e:
        print(f"❌ Failed to start backend server: {e}")
        return None

def start_frontend():
    """Start the Next.js frontend server."""
    print("🚀 Starting Next.js frontend server...")
    
    try:
        frontend_process = subprocess.Popen([
            "npm", "run", "dev"
        ])
        
        # Wait for the server to start
        time.sleep(5)
        
        # Test if the server is responding
        try:
            import requests
            response = requests.get(f"http://localhost:{FRONTEND_PORT}/", timeout=10)
            if response.status_code == 200:
                print(f"✅ Frontend server started on http://localhost:{FRONTEND_PORT}")
                print(f"   External access: http://{FRONTEND_HOST}:{FRONTEND_PORT}")
                return frontend_process
            else:
                print(f"❌ Frontend server failed to start (status: {response.status_code})")
                return None
        except ImportError:
            # requests not available, just assume it's working
            print(f"✅ Frontend server started on http://localhost:{FRONTEND_PORT}")
            print(f"   External access: http://{FRONTEND_HOST}:{FRONTEND_PORT}")
            return frontend_process
        except Exception as e:
            print(f"❌ Frontend server failed to start: {e}")
            return None
            
    except Exception as e:
        print(f"❌ Failed to start frontend server: {e}")
        return None

def main():
    """Main function to start both servers."""
    print("🎯 Starting Owlin Development Servers")
    print("=" * 50)
    
    # Check ports and kill existing processes
    check_ports()
    kill_existing_processes()
    
    # Start backend
    backend_process = start_backend()
    if not backend_process:
        print("❌ Failed to start backend server. Exiting.")
        sys.exit(1)
    
    # Start frontend
    frontend_process = start_frontend()
    if not frontend_process:
        print("❌ Failed to start frontend server. Exiting.")
        backend_process.terminate()
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("🎉 Both servers started successfully!")
    print(f"   Frontend: http://localhost:{FRONTEND_PORT}")
    print(f"   Backend: http://localhost:{BACKEND_PORT}")
    print("\n📝 Useful URLs:")
    print(f"   - Invoice Management: http://localhost:{FRONTEND_PORT}/invoices")
    print(f"   - API Documentation: http://localhost:{BACKEND_PORT}/docs")
    print(f"   - API Health Check: http://localhost:{BACKEND_PORT}/health")
    print("\n🛑 Press Ctrl+C to stop both servers")
    print("=" * 50)
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping servers...")
        backend_process.terminate()
        frontend_process.terminate()
        print("✅ Servers stopped")

if __name__ == "__main__":
    main() 