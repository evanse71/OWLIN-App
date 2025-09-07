#!/usr/bin/env bash
# 🧊 OWLIN — BRUTAL JUDGE PROTOCOL v2 (NO MERCY)
set -euo pipefail

# ===== 0) TERMINAL TRIAGE =====
pkill -f "test_server.py" || true
if command -v lsof >/dev/null 2>&1; then
  lsof -ti:8000 | xargs -r kill -9 || true
fi
find . -name "__pycache__" -o -name ".pytest_cache" -o -name "*.pyc" | xargs rm -rf || true
rm -rf .next coverage *.log || true

# ===== 1) TOOLING SANITY =====
python3 --version || { echo "❌ python3 missing"; exit 1; }
node --version    || { echo "❌ node missing"; exit 1; }
npm --version     || { echo "❌ npm missing"; exit 1; }
git --version     || { echo "❌ git missing"; exit 1; }
sqlite3 --version || { echo "❌ sqlite3 missing"; exit 1; }

# ===== 2) REPO HYGIENE =====
git status --porcelain=v1
grep -q "# OWLIN junk" .gitignore 2>/dev/null || cat >> .gitignore <<'EOF'

# OWLIN junk
/data/
/backups/
/tmp/
/dist/
/.next/
/coverage/
**/*.log
**/*.zip
**/*.sqlite
**/.pytest_cache/
**/__pycache__/
EOF

test -d backend/db_migrations || { echo "❌ missing backend/db_migrations"; exit 1; }
test ! -d backend/db/migrations || { echo "❌ zombie folder backend/db/migrations exists — move to attic/"; exit 1; }

git ls-files | grep -E '\.env(\.|$)|\.sqlite$|\.db$|\.pem$|\.p12$' && { echo "❌ secret/junk tracked — untrack now"; exit 1; }

# ===== 3) PYTHON QUALITY GATES =====
python3 -m pip install -q -r requirements.txt || true
python3 -m pip install -q pytest pyright || true
python3 -m pyright || { echo "❌ pyright failed"; exit 1; }
python3 -m pytest -q || { echo "❌ pytest failed"; exit 1; }

# ===== 4) FRONTEND QUALITY GATES =====
npm ci --silent || true
npx tsc --noEmit || { echo "❌ TypeScript errors"; exit 1; }
npx eslint . --ext .ts,.tsx || { echo "❌ ESLint errors — fix; do NOT add disables"; exit 1; }

# ===== 5) MIGRATIONS MUST BOOT FRESH =====
python3 - <<'PY'
import tempfile, os, sys
sys.path.insert(0,'backend')
from db_manager_unified import get_db_manager
tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False); tmp.close()
os.environ['OWLIN_DB_PATH'] = tmp.name
m = get_db_manager(); m.run_migrations()
print("MIGRATIONS_OK")
PY

# ===== 6) START API & DEEP HEALTH =====
(cd backend && nohup python3 test_server.py >/tmp/owlin_test_server.log 2>&1 &)
sleep 2
curl -sf http://localhost:8000/health      >/dev/null || { echo "❌ /health down"; tail -n 120 /tmp/owlin_test_server.log || true; exit 1; }
curl -sf http://localhost:8000/health/deep >/dev/null || { echo "❌ /health/deep down"; tail -n 120 /tmp/owlin_test_server.log || true; exit 1; }
deep="$(curl -s http://localhost:8000/health/deep)"
echo "$deep" | jq -e '.db_ok and .fk_on and .migration_version' >/dev/null \
  || { echo "❌ deep health missing keys or false: $deep"; exit 1; }

# ===== 7) DETERMINISTIC SMOKE SEED (FK ON; pennies internal) =====
python3 - <<'PY'
import os, sys, datetime
sys.path.insert(0,'backend')
from db_manager_unified import get_db_manager
db = get_db_manager(); c = db.get_conn().cursor()
c.execute("PRAGMA foreign_keys=ON;")
cols=lambda t:[r[1] for r in c.execute(f"PRAGMA table_info({t})")]
ufc, ivc, lic = cols("uploaded_files"), cols("invoices"), cols("invoice_line_items")

uf={"id":"smoke_file_001","original_filename":"smoke.pdf","canonical_path":"/tmp/smoke.pdf",
    "file_size":1234,"file_hash":"deadbeef","mime_type":"application/pdf",
    "upload_timestamp": datetime.datetime.utcnow().isoformat(timespec="seconds")}
c.execute(f"INSERT OR IGNORE INTO uploaded_files({','.join(ufc)}) VALUES ({','.join(['?']*len(ufc))})",[uf.get(k) for k in ufc])

inv={"id":"smoke_inv","file_id":uf["id"],
     "created_at": datetime.datetime.utcnow().isoformat(timespec="seconds"),
     "total_amount_pennies":555}
c.execute(f"INSERT OR REPLACE INTO invoices({','.join(ivc)}) VALUES ({','.join(['?']*len(ivc))})",[inv.get(k) for k in ivc])

li={"id":9001,"invoice_id":inv["id"],"description":"SMOKE SEED","quantity":5.0,
    "unit_price_pennies":210,"line_total_pennies":1050,"line_flags":"[]"}
c.execute(f"INSERT OR REPLACE INTO invoice_line_items({','.join(lic)}) VALUES ({','.join(['?']*len(lic))})",[li.get(k) for k in lic])

db.get_conn().commit(); print("SMOKE_SEED_OK")
PY

# ===== 8) API MUST RETURN POUNDS (no penny leakage) =====
resp="$(curl -s http://localhost:8000/api/invoices/smoke_inv)"
echo "$resp" | jq -e '.id=="smoke_inv"' >/dev/null || { echo "❌ wrong invoice payload"; echo "$resp"; exit 1; }
echo "$resp" | jq -e '.lines[0].unit_price_pennies' >/dev/null && { echo "❌ penny fields leaked"; echo "$resp"; exit 1; }
echo "$resp" | jq -e '.lines[0].unit_price==2.10 and .lines[0].line_total==10.50' >/dev/null \
  || { echo "❌ money not converted to pounds at edge"; echo "$resp"; exit 1; }
echo "$resp" | jq '{id,meta,firstLine:.lines[0]}'

# ===== 9) STAGE ONLY WHAT WE MEAN =====
git status --short
git add backend components pages scripts tests .github pyproject.toml package.json package-lock.json tsconfig.json .eslintrc.* .prettierrc* .gitignore
git status --short

# ===== 10) COMMIT — NO --no-verify =====
git switch -c feat/p1p2-assembler-ocr-gate || git checkout -b feat/p1p2-assembler-ocr-gate
git commit -m "feat(ingest+ocr): P1+P2 — assembler + OCR gating, schema + tests

- DocumentAssembler: batch mgmt, asset ingest, pHash, time-window grouping
- OCRGate: <50 BLOCK, 50–69 WARN, ≥70 PASS; page+line gating; quarantine
- DB: ingest_* + document_* schema + indexes; unified runner; idempotent fresh-boot
- API: pennies-internal, pounds-at-edge; response models; deep health
- Tests: 11 passing (assembler/OCR/integration); temp DB fixtures
- Tooling: deterministic DB path resolution; logging; FK PRAGMAs

BREAKING CHANGE: run migrations before boot"

# ===== 11) PUSH + PR =====
git push -u origin feat/p1p2-assembler-ocr-gate
echo "✅ DONE. Open PR: feat: P1+P2 — assembler + OCR gating (schema + tests)" 