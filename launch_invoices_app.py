#!/usr/bin/env python3
"""
Launch script for the enhanced invoices application.
This script sets up the environment and launches the Streamlit app for testing.
"""
import os
import sys
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_environment():
    """Set up the environment for the invoices app."""
    logger.info("🔧 Setting up environment...")
    
    # Ensure data directory exists
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Ensure upload directories exist
    upload_dir = data_dir / "uploads"
    upload_dir.mkdir(exist_ok=True)
    
    invoices_dir = upload_dir / "invoices"
    invoices_dir.mkdir(exist_ok=True)
    
    delivery_dir = upload_dir / "delivery_notes"
    delivery_dir.mkdir(exist_ok=True)
    
    logger.info("✅ Environment setup complete")

def run_migrations():
    """Run database migrations."""
    logger.info("🗄️ Running database migrations...")
    
    try:
        from app.db_migrations import run_migrations
        run_migrations()
        logger.info("✅ Database migrations completed")
    except Exception as e:
        logger.error(f"❌ Database migrations failed: {e}")
        return False
    
    return True

def check_dependencies():
    """Check if required dependencies are available."""
    logger.info("📦 Checking dependencies...")
    
    required_packages = [
        'streamlit',
        'pandas',
        'sqlite3',
        'cv2',
        'fitz',
        'numpy'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'sqlite3':
                import sqlite3
            elif package == 'cv2':
                import cv2
            elif package == 'fitz':
                import fitz
            else:
                __import__(package)
            logger.info(f"✅ {package} available")
        except ImportError:
            missing_packages.append(package)
            logger.warning(f"⚠️ {package} not available")
    
    if missing_packages:
        logger.warning(f"Missing packages: {missing_packages}")
        logger.info("Some features may not work without these packages")
    
    return True

def launch_streamlit():
    """Launch the Streamlit application."""
    logger.info("🚀 Launching Streamlit application...")
    
    # Set environment variables
    os.environ['STREAMLIT_SERVER_PORT'] = '8501'
    os.environ['STREAMLIT_SERVER_ADDRESS'] = 'localhost'
    os.environ['STREAMLIT_SERVER_HEADLESS'] = 'false'
    
    # Launch the enhanced invoices page
    try:
        cmd = [
            sys.executable, '-m', 'streamlit', 'run', 
            'app/enhanced_invoices_page.py',
            '--server.port=8501',
            '--server.address=localhost',
            '--server.headless=false'
        ]
        
        logger.info("🌐 Starting Streamlit server...")
        logger.info("📱 Open your browser to: http://localhost:8501")
        logger.info("🛑 Press Ctrl+C to stop the server")
        
        subprocess.run(cmd, check=True)
        
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to start Streamlit: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False
    
    return True

def main():
    """Main launcher function."""
    logger.info("🎯 Owlin Invoices App Launcher")
    logger.info("=" * 50)
    
    # Setup environment
    setup_environment()
    
    # Check dependencies
    if not check_dependencies():
        logger.error("❌ Dependency check failed")
        return False
    
    # Run migrations
    if not run_migrations():
        logger.error("❌ Migration failed")
        return False
    
    # Launch Streamlit
    if not launch_streamlit():
        logger.error("❌ Failed to launch application")
        return False
    
    logger.info("✅ Application launched successfully")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
