#!/bin/bash

echo "🚀 Starting Simplified Advanced OCR Backend..."

# Kill any existing uvicorn processes
pkill -f uvicorn
sleep 2

# Start the simplified advanced backend
echo "🔧 Starting backend with simplified advanced OCR..."
python3 -m uvicorn backend.main_advanced_simple:app --host 0.0.0.0 --port 8000 --reload 