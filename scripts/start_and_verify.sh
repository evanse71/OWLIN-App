#!/usr/bin/env bash
# Owlin — One-Click Start & Verify (Linux/macOS)
# ASCII-only output (no emojis). UTF-8 safe.

set -euo pipefail

# -------------------------
# 0) UTF-8 & repo root
# -------------------------
export LC_ALL=C.UTF-8 || true
export LANG=C.UTF-8   || true
export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo "===================================="
echo " OWLIN - One-Click Start & Verify"
echo "===================================="
echo "• Repo root: $REPO_ROOT"

# -------------------------
# 1) Ensure backend package marker
# -------------------------
if [[ ! -f "$REPO_ROOT/backend/__init__.py" ]]; then
  touch "$REPO_ROOT/backend/__init__.py"
  echo "• Created backend/__init__.py"
fi

# -------------------------
# 2) Load .env (simple KEY=VALUE)
# -------------------------
ENV_FILE="$REPO_ROOT/.env"
if [[ -f "$ENV_FILE" ]]; then
  echo "• Loading .env"
  # shellcheck disable=SC2046
  export $(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$ENV_FILE" | sed 's/#.*//')
fi

# -------------------------
# 3) Resolve env defaults
# -------------------------
: "${OWLIN_PORT:=${PORT:-8001}}"
: "${LLM_BASE:=http://127.0.0.1:11434}"
: "${OWLIN_DB_URL:=sqlite:///./owlin.db}"
export OWLIN_PORT LLM_BASE OWLIN_DB_URL
echo "• PORT:     $OWLIN_PORT"
echo "• LLM_BASE: $LLM_BASE"
echo "• DB_URL:   $OWLIN_DB_URL"

# Ensure Python sees repo root as a package root
export PYTHONPATH="$REPO_ROOT"

# -------------------------
# 4) Build UI if missing (if npm exists)
# -------------------------
INDEX_PATH="$REPO_ROOT/out/index.html"
if [[ ! -f "$INDEX_PATH" ]]; then
  if command -v npm >/dev/null 2>&1; then
    echo "• UI not built. Running: npm ci && npm run build"
    npm ci
    npm run build
  else
    echo "• npm not found; proceeding with JSON fallback for UI."
  fi
fi

# -------------------------
# 5) Free the port (best-effort)
# -------------------------
PORT="$OWLIN_PORT"
echo "• Clearing processes on port $PORT (best-effort)"
if command -v lsof >/dev/null 2>&1; then
  PIDS="$(lsof -ti tcp:"$PORT" || true)"
  if [[ -n "${PIDS:-}" ]]; then
    echo "$PIDS" | xargs -r kill -9 || true
    sleep 0.3
  fi
else
  # macOS fallback: netstat + awk
  if command -v netstat >/dev/null 2>&1; then
    PIDS="$(netstat -vanp tcp 2>/dev/null | awk -v p=".$PORT" '$4 ~ p {print $9}' | sort -u || true)"
    if [[ -n "${PIDS:-}" ]]; then
      echo "$PIDS" | xargs -r kill -9 || true
      sleep 0.3
    fi
  fi
fi

# -------------------------
# 6) ASCII-safe Python import test
# -------------------------
echo "• Testing Python module import..."
python - <<'PYCODE'
import importlib, sys, os
print("Python OK:", sys.version)
print("CWD:", os.getcwd())
importlib.import_module("backend")
print("backend import OK")
PYCODE
if [[ $? -ne 0 ]]; then
  echo "Python cannot import backend module"
  echo "• Make sure you are in the repo root and Python is installed"
  exit 1
fi

# -------------------------
# 7) Launch the server (module run, then file fallback)
# -------------------------
echo "• Launching server..."
set +e
( python -m backend.final_single_port ) >"$REPO_ROOT/owlin.out" 2>"$REPO_ROOT/owlin.err" &
PID=$!
sleep 0.4
if ! kill -0 "$PID" 2>/dev/null; then
  ( python "$REPO_ROOT/backend/final_single_port.py" ) >"$REPO_ROOT/owlin.out" 2>"$REPO_ROOT/owlin.err" &
  PID=$!
  sleep 0.4
fi
set -e

if ! kill -0 "$PID" 2>/dev/null; then
  echo "Failed to launch Owlin server (see owlin.err)."
  exit 1
fi

BASE="http://127.0.0.1:$OWLIN_PORT"
HEALTH="$BASE/api/health"
STATUS="$BASE/api/status"
RETRY="$BASE/api/retry-mount"

# -------------------------
# 8) Readiness wait
# -------------------------
echo "• Waiting for health..."
ok=0
for i in $(seq 1 60); do
  if curl -fsS "$HEALTH" | grep -q '"ok":[[:space:]]*true'; then
    ok=1
    break
  fi
  sleep 0.25
done
if [[ "$ok" -ne 1 ]]; then
  echo "Server did not become healthy at $HEALTH"
  echo "--- STDOUT ---"; tail -n +1 "$REPO_ROOT/owlin.out" || true
  echo "--- STDERR ---"; tail -n +1 "$REPO_ROOT/owlin.err" || true
  kill "$PID" 2>/dev/null || true
  exit 1
fi
echo "• Health OK"

# -------------------------
# 9) Ensure API mounted (retry if needed)
# -------------------------
if ! curl -fsS "$STATUS" | grep -q '"api_mounted":[[:space:]]*true'; then
  echo "• API not mounted. Attempting retry-mount..."
  curl -fsS -X POST "$RETRY" >/dev/null || true
  sleep 0.3
  if ! curl -fsS "$STATUS" | grep -q '"api_mounted":[[:space:]]*true'; then
    echo "API failed to mount. /api/status:"
    curl -fsS "$STATUS" || true
    kill "$PID" 2>/dev/null || true
    exit 1
  fi
fi
echo "• API mounted"

# -------------------------
# 10) Open browser (best-effort)
# -------------------------
echo ""
echo "PASS: Owlin is running on $BASE"
echo "UI:     $BASE"
echo "Health: $HEALTH"
echo "Status: $STATUS"
echo ""

if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$BASE" >/dev/null 2>&1 || true
elif command -v open >/dev/null 2>&1; then
  open "$BASE" >/dev/null 2>&1 || true
fi

# Tail logs (Ctrl+C to exit)
echo "Tailing logs (Ctrl+C to stop)..."
tail -f "$REPO_ROOT/owlin.out" "$REPO_ROOT/owlin.err"
