#!/usr/bin/env python3
"""
Launcher script for the Owlin OCR application.
This script runs from the project root and properly handles relative imports.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the main application
from app.main import *

if __name__ == "__main__":
    # This will be handled by Streamlit
    pass 