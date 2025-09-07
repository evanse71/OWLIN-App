#!/usr/bin/env bash
set -euo pipefail
base="http://127.0.0.1:8000"
fail=0

echo "🧪 Testing manual pairing endpoint..."

echo "1) 422 missing dn_id"
curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST "$base/api/invoices/inv_seed/pairing/manual" \
  -H "content-type: application/json" -d '{}' | grep -q '^422$' || fail=1

echo "prep DN"
sqlite3 data/owlin.db "PRAGMA foreign_keys=ON; INSERT OR IGNORE INTO delivery_notes (id,file_id,status,confidence) VALUES ('dn_demo_ok','seed_file','pending',0.8);"

echo "2) 200 create"
curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST "$base/api/invoices/inv_seed/pairing/manual" \
  -H "content-type: application/json" -d '{"dn_id":"dn_demo_ok"}' | grep -q '^200$' || fail=1

echo "3) 200 idempotent"
curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST "$base/api/invoices/inv_seed/pairing/manual" \
  -H "content-type: application/json" -d '{"dn_id":"dn_demo_ok"}' | grep -q '^200$' || fail=1

echo "4) 404 not found"
curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST "$base/api/invoices/inv_seed/pairing/manual" \
  -H "content-type: application/json" -d '{"dn_id":"dn_missing_001"}' | grep -q '^404$' || fail=1

if [ $fail -eq 0 ]; then
    echo "✅ All tests passed!"
else
    echo "❌ Some tests failed!"
fi

exit $fail
