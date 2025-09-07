#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m pip install -r requirements.txt
(lsof -ti:8001 | xargs -r kill -9) || true
PYTHONUNBUFFERED=1 \
UVICORN_LOG_LEVEL=info \
python3 -m uvicorn app:app --host 0.0.0.0 --port 8001 