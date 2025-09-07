#!/usr/bin/env bash
set -euo pipefail

REPO="${REPO:-$(cd "$(dirname "$0")/.."; pwd)}"
DB="$REPO/data/owlin.db"
NONCE="$(date +%s%N)"
LOG="$REPO/backend/.server.$NONCE.log"

say() { printf "=== %s ===\n" "$*"; }
step() {
  local NAME="$1"; shift || true
  echo "STEP_NAME: $NAME"
  echo "PWD: $(pwd)"
  echo "START_TIME: $(date -u +%FT%TZ)"
  echo "CMD: $*"
  set +e; "$@"; EC=$?; set -e
  echo "EXIT_CODE: $EC"
  echo "END_TIME: $(date -u +%FT%TZ)"
  echo
  return $EC
}

cd "$REPO"

# A) Sanity
step "Sanity" bash -lc 'pwd; which bash; which zsh; uname -a; python3 --version; sqlite3 --version'

# B) Seed DB (idempotent) and prove rows exist
step "Seed DB" bash -lc "test -f '$DB' || { echo 'DB missing: $DB' >&2; exit 1; }; sqlite3 '$DB' < '$REPO/backend/seed_minimal.sql'"
step "Counts after seed" bash -lc "
  echo 'uploaded_files:'; sqlite3 '$DB' \"SELECT count(*) FROM uploaded_files;\";
  echo 'invoices(inv_seed):'; sqlite3 '$DB' \"SELECT count(*) FROM invoices WHERE id='inv_seed';\";
  echo 'line_items(inv_seed):'; sqlite3 '$DB' \"SELECT id,description,quantity,unit_price_pennies,line_total_pennies FROM invoice_line_items WHERE invoice_id='inv_seed';\"
"

# C) Start server cleanly
step "Kill stale servers" bash -lc "pkill -f test_server.py || true; pkill -f uvicorn || true"
step "Start server" bash -lc "cd '$REPO/backend'; export OWLIN_ENV=dev; nohup python3 -u test_server.py > '$LOG' 2>&1 & echo PID=\$!"
sleep 2
say "recent server log"; tail -n 60 "$LOG" || true

# D) Wait for /health (up to 15s)
ATTEMPTS=15
until curl -fsS http://127.0.0.1:8000/health >/tmp/health.$NONCE.json 2>/tmp/health.$NONCE.err; do
  ((ATTEMPTS--)) || { echo "Health never became ready. See $LOG" >&2; exit 1; }
  sleep 1
done
say "health body"; python3 -m json.tool </tmp/health.$NONCE.json

# E) Invoice endpoint with headers/body split
step "Invoice: headers+body" bash -lc "
  curl -sS -D /tmp/headers.$NONCE.txt http://127.0.0.1:8000/api/invoices/inv_seed -o /tmp/body.$NONCE.json"
say "headers"; sed -n '1,200p' /tmp/headers.$NONCE.txt
say "body";    python3 -m json.tool /tmp/body.$NONCE.json

# F) OpenAPI paths
say "routes"; curl -s http://127.0.0.1:8000/openapi.json | python3 -c "import sys, json; d=json.load(sys.stdin); print('\n'.join(sorted(d.get('paths',{}).keys())))"

echo "✅ VERIFY COMPLETE"
