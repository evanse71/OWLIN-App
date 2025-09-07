#!/bin/bash

# Kill any existing processes on port 8000
echo "🔄 Stopping any existing backend processes..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Wait a moment
sleep 2

# Start the backend server
echo "🚀 Starting Owlin Backend Server..."
echo "📍 Server will be available at: http://localhost:8000"
echo "✅ Health check: http://localhost:8000/health"

python3 -m uvicorn backend.main_fixed:app --host 0.0.0.0 --port 8000 