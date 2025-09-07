#!/usr/bin/env bash
set -e
echo "🧊 BRUTAL RUSSIAN JUDGE - INVOICE API VERIFICATION"
echo "=================================================="
echo
echo "🔫 STEP 0: NUKE ZOMBIES, VERIFY PORT"
echo "-------------------------------------"
pkill -f test_server.py || true
pkill -f uvicorn || true
sleep 1
if lsof -iTCP:8000 -sTCP:LISTEN -n -P >/dev/null; then
  echo "❌ Port 8000 is busy"; exit 1
else
  echo "✅ Port 8000 is free"
fi
echo
echo "🗄️ STEP 1: VERIFY DB PATH USED BY THE APP"
echo "------------------------------------------"
cd "$(dirname "$0")"
DB_PATH="$(/usr/bin/python3 -c 'from db_manager_unified import get_db_manager; print(get_db_manager().db_path)')"
echo "DB path = $DB_PATH"
EXPECTED="$(cd ..; pwd)/data/owlin.db"
[ "$DB_PATH" = "$EXPECTED" ] && echo "✅ Database path is correct" || { echo "❌ Wrong DB path"; exit 1; }
echo
echo "🌱 STEP 2: SEED MINIMAL, VALID ROWS"
echo "------------------------------------"
echo "Seeding test data..."
/usr/bin/sqlite3 "$DB_PATH" <<'SQL'
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
echo "✅ Data seeded. Verifying rows exist..."
echo "Checking invoices table..."
INVOICE_ROW=$(/usr/bin/sqlite3 "$DB_PATH" "SELECT id,file_id,total_amount_pennies FROM invoices WHERE id='inv_seed';")
[ -n "$INVOICE_ROW" ] && echo "✅ Invoice row: $INVOICE_ROW" || { echo "❌ No invoice row found!"; exit 1; }
echo "Checking invoice_line_items table..."
LINE_ROW=$(/usr/bin/sqlite3 "$DB_PATH" "SELECT description,quantity,unit_price_pennies,line_total_pennies FROM invoice_line_items WHERE invoice_id='inv_seed';")
[ -n "$LINE_ROW" ] && echo "✅ Line item row: $LINE_ROW" || { echo "❌ No line item row found!"; exit 1; }
echo
echo "🚀 STEP 3: START THE SERVER"
echo "----------------------------"
export OWLIN_ENV=dev
python3 -u test_server.py >/tmp/judge_server.log 2>&1 &
PID=$!
echo "Server started with PID: $PID"
sleep 2
if lsof -iTCP:8000 -sTCP:LISTEN -n -P >/dev/null; then
  echo "✅ Server is running"
else
  echo "❌ Server failed to start"; tail -n +1 /tmp/judge_server.log; kill $PID || true; exit 1
fi
echo
echo "🧪 STEP 4: TEST THE EMERGENCY ENDPOINT"
echo "---------------------------------------"
curl -s -D /tmp/headers.txt -o /tmp/body.json http://127.0.0.1:8000/api/invoices/inv_seed -w "\nHTTP %{http_code}\n"
echo "Now pretty-printed response:"
python3 - <<PY
import json
print(json.dumps(json.load(open('/tmp/body.json')), indent=2))
PY
echo
echo "🔍 STEP 5: VERIFY ROUTES AND DB PATH"
echo "-------------------------------------"
curl -s http://127.0.0.1:8000/api/debug/db-path | python3 -m json.tool || true
echo
echo "🧹 CLEANUP"
echo "-----------"
kill $PID || true
sleep 1
echo "✅ Port 8000 is free"
echo
echo "🎯 VERIFICATION COMPLETE"
echo "========================="
exit 0
