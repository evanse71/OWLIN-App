#!/usr/bin/env python3
"""
OWLIN Streamlit Production Application

This is the main Streamlit application for the OWLIN platform,
integrating all the new modules for production use.
"""

import streamlit as st
import os
import sys
from pathlib import Path

# Import the integrated modules
from multi_upload_ui import create_streamlit_app
from db_manager import init_db, get_database_stats

def main():
    """Main application entry point"""
    
    # Initialize the database on startup
    db_path = "data/owlin.db"
    try:
        init_db(db_path)
        st.success("✅ Database initialized successfully")
    except Exception as e:
        st.error(f"❌ Database initialization failed: {e}")
        return
    
    # Create and run the Streamlit app
    create_streamlit_app()

if __name__ == "__main__":
    main() 