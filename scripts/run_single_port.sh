#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Starting OWLIN Single-Port Demo"
echo "=================================="

# 1) Build frontend (Vite) with correct API URL
export VITE_API_BASE_URL="${VITE_API_BASE_URL:-http://127.0.0.1:8000}"
echo "📦 Building frontend with API URL: $VITE_API_BASE_URL"

( cd tmp_lovable && npm ci && npm run build )

# 2) Start FastAPI serving API + built UI
echo "🌐 Starting FastAPI server on port 8000..."
echo "   Frontend: http://127.0.0.1:8000"
echo "   API: http://127.0.0.1:8000/api/health"
echo "   Upload: http://127.0.0.1:8000/api/upload"
echo ""
echo "Press Ctrl+C to stop"

# NOTE: backend looks for tmp_lovable/dist (you already mounted it in main)
python test_backend_simple.py
