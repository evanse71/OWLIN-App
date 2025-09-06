#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
export OWLIN_ENV=dev
DB="data/owlin.db"

echo "🔧 Killing any old servers..."
pkill -f test_server.py >/dev/null 2>&1 || true
pkill -f uvicorn       >/dev/null 2>&1 || true

need(){ command -v "$1" >/dev/null || { echo "❌ Missing $1. Install it and re-run."; exit 3; }; }
need python3; need sqlite3; need curl; need jq

[[ -f "$DB" ]] || { echo "❌ DB not found at $DB"; exit 2; }

echo "🔎 Checking schema tables exist..."
for t in uploaded_files invoices invoice_line_items; do
  if ! sqlite3 "$DB" "SELECT name FROM sqlite_master WHERE type='table' AND name='$t';" | grep -q "$t"; then
    echo "❌ Missing table: $t in $DB"; exit 2
  fi
done

echo "🌱 Seeding minimal rows..."
sqlite3 "$DB" <<'SQL'
PRAGMA foreign_keys=ON;
INSERT OR REPLACE INTO uploaded_files
(id, original_filename, canonical_path, file_size, file_hash, mime_type,
 doc_type, doc_type_confidence, upload_timestamp, processing_status, processing_progress,
 created_at, updated_at)
VALUES
('seed_file','seed.pdf','/tmp/seed.pdf',123,'deadbeef','application/pdf',
 'invoice',1.0,datetime('now'),'completed',100,datetime('now'),datetime('now'));

INSERT OR REPLACE INTO invoices
(id,file_id,total_amount_pennies,status,created_at,updated_at)
VALUES
('inv_seed','seed_file',7200,'parsed',datetime('now'),datetime('now'));

INSERT OR REPLACE INTO invoice_line_items
(id,invoice_id,row_idx,page,description,quantity,unit_price_pennies,line_total_pennies,created_at,updated_at)
VALUES
(4001,'inv_seed',0,1,'TIA MARIA 1L',6.0,1200,7200,datetime('now'),datetime('now'));
SQL

LOG=/tmp/owlin_server.log
echo "🚀 Starting server (logging to $LOG)..."
python3 -u backend/test_server.py >"$LOG" 2>&1 &
PID=$!
cleanup(){ kill "$PID" >/dev/null 2>&1 || true; }
trap cleanup EXIT

echo "⏳ Waiting for /health..."
for i in {1..60}; do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null; then break; fi
  sleep 0.25
  if ! kill -0 "$PID" 2>/dev/null; then echo "❌ server died. Log:"; tail -n +1 "$LOG"; exit 1; fi
done

echo "📥 Fetching /api/invoices/inv_seed..."
RAW="$(curl -sS http://127.0.0.1:8000/api/invoices/inv_seed || true)"
if ! echo "$RAW" | jq . >/dev/null 2>&1; then
  echo "❌ Non-JSON response:"; echo "$RAW"; echo "— Server log tail —"; tail -n 60 "$LOG"; exit 1
fi

ID="$(echo "$RAW" | jq -r '.id // empty')"
DESC="$(echo "$RAW" | jq -r '.lines[0].desc // empty')"
UNIT="$(echo "$RAW" | jq -r '.lines[0].unit_price // empty')"
TOTAL="$(echo "$RAW" | jq -r '.meta.total_inc // empty')"

echo "🔎 id=$ID, desc=$DESC, unit_price=$UNIT, total_inc=$TOTAL"

if [[ "$ID" == "inv_seed" && "$DESC" == "TIA MARIA 1L" ]]; then
  echo "✅ PASS: /api/invoices/inv_seed returned expected data"
else
  echo "❌ FAIL: unexpected payload"; echo "$RAW" | jq .; echo "— Server log tail —"; tail -n 60 "$LOG"; exit 1
fi

echo "📚 OpenAPI routes (first 15):"
curl -s http://127.0.0.1:8000/openapi.json | jq -r '.paths | keys[]' | sed -n '1,15p' || echo "openapi fetch failed"

echo "🏁 Done." 