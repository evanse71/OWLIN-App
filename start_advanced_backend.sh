#!/bin/bash

echo "🚀 Starting Advanced OCR Backend..."

# Kill any existing uvicorn processes
pkill -f uvicorn
sleep 2

# Start the advanced backend
echo "🔧 Starting backend with advanced OCR..."
python3 -m uvicorn backend.main_advanced:app --host 0.0.0.0 --port 8000 --reload 