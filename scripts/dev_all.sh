#!/usr/bin/env bash
set -euo pipefail

# kill stale
pkill -f uvicorn || true
pkill -f node || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
lsof -ti:8001 | xargs kill -9 2>/dev/null || true

# ensure env
mkdir -p data
printf "NEXT_PUBLIC_API_BASE=http://127.0.0.1:8001\n" > .env.local

# start backend
PYTHONPATH="$PWD" python3 -m uvicorn backend.app:app --reload --port 8001 --host 127.0.0.1 &
BACK_PID=$!

# start frontend
(
  npm run dev
) &
FRONT_PID=$!

# cleanup on exit
trap "kill $BACK_PID $FRONT_PID 2>/dev/null || true" EXIT

# wait for either to exit
wait -n
