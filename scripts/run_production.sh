#!/usr/bin/env bash
set -euo pipefail

# Production runner with optimized uvicorn settings
export VITE_API_BASE_URL="${VITE_API_BASE_URL:-http://127.0.0.1:8000}"
export OWLIN_SINGLE_PORT="${OWLIN_SINGLE_PORT:-1}"

# Build frontend
echo "Building frontend..."
( cd tmp_lovable && npm ci && npm run build )

# Start with production settings
echo "Starting OWLIN in production mode..."
uvicorn test_backend_simple:app \
  --host 0.0.0.0 \
  --port 8000 \
  --timeout-keep-alive 10 \
  --proxy-headers \
  --access-log \
  --log-level info
