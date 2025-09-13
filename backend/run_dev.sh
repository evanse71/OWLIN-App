#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m pip install -r requirements.txt
# Kill anything on 8001 to avoid "port already in use"
(lsof -ti:8001 | xargs -r kill -9) || true
# Clear old uvicorn reload state (sometimes keeps a watcher process)
pkill -f "uvicorn.*app:app" || true
# Start
PYTHONUNBUFFERED=1 \
UVICORN_LOG_LEVEL=info \
python3 -m uvicorn app:app --reload --port 8001 