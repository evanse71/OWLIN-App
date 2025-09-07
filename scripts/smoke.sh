#!/usr/bin/env bash
set -euo pipefail
RED=$(printf '\033[0;31m'); GRN=$(printf '\033[0;32m'); YEL=$(printf '\033[1;33m'); NC=$(printf '\033[0m')
say(){ echo "${YEL}=== $* ===${NC}"; }; ok(){ echo "${GRN}✓ $*${NC}"; }; bad(){ echo "${RED}✗ $*${NC}"; }

export OWLIN_DB_PATH="$(mktemp -t owlin_db_XXXXXX).sqlite"

say "Run migrations on temp DB"
python3 - <<'PY'
import sys, os
sys.path.insert(0,'backend')
from db_manager_unified import get_db_manager
m = get_db_manager(); m.run_migrations()
conn = m.get_conn()
fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
assert fk == 1, "foreign_keys PRAGMA OFF"
print("MIGRATIONS OK")
PY
ok "Migrations & PRAGMA OK"

say "Seed minimal invoice"
python3 - <<'PY'
import sys, os
sys.path.insert(0,'backend')
from db_manager_unified import get_db_manager
c = get_db_manager().get_conn().cursor()

# Create uploaded file first (required by foreign key)
c.execute("INSERT OR IGNORE INTO uploaded_files(id, original_filename, canonical_path, file_size, file_hash, mime_type, upload_timestamp) VALUES('smoke_file_001', 'smoke.pdf', '/tmp/smoke.pdf', 1024, 'hash123', 'application/pdf', datetime('now'))")

# Insert invoice with file_id reference
c.execute("INSERT OR IGNORE INTO invoices(id, file_id, created_at, total_amount_pennies) VALUES('smoke_inv', 'smoke_file_001', datetime('now'), 555)")

# Then insert line items
c.execute("""INSERT OR IGNORE INTO invoice_line_items
(id, invoice_id, description, quantity, unit_price_pennies, line_total_pennies, line_flags)
VALUES(3001,'smoke_inv','SMOKE SEED',5.0,210,1050,'[]')""")
c.connection.commit()
PY
ok "Seeded"

say "Service read"
python3 - <<'PY'
import sys, os
sys.path.insert(0,'backend')
from services.invoice_query import fetch_invoice
p = fetch_invoice('smoke_inv')
assert p and p['meta']['total_amount_pennies'] == 555, "meta pennies mismatch"
ln = p['lines'][0]
assert ln['unit_price_pennies'] == 210 and ln['line_total_pennies'] == 1050, "line pennies mismatch"
print("SERVICE OK")
PY
ok "Service returns real DB data"

say "TS check"
npx tsc --noEmit >/dev/null
ok "TypeScript clean"

say "Smoke PASS" 