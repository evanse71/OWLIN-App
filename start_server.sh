#!/bin/bash

echo "🧊 BRUTAL JUDGE PROTOCOL - STARTING SERVER"
echo "=========================================="

# Kill any existing server
echo "🔪 Killing existing server..."
pkill -f "test_server.py" || true

# Wait a moment
sleep 1

# Start the server
echo "🚀 Starting test server..."
cd backend
nohup python3 test_server.py > ../server.log 2>&1 &

# Wait for server to start
echo "⏳ Waiting for server to start..."
sleep 3

# Check if server is running
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Server is running at http://localhost:8000"
    echo "📊 Health check: http://localhost:8000/health"
    echo "🔍 Deep health: http://localhost:8000/health/deep"
    echo "📄 Logs: server.log"
    echo ""
    echo "🎯 Now run: python3 brutal_judge_test.py"
else
    echo "❌ Server failed to start"
    echo "📄 Check logs: server.log"
    exit 1
fi 