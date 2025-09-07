#!/usr/bin/env bash
set -euo pipefail

# ===========================
# COLD-WAR JUDGE GAUNTLET
# ===========================
# Runs schema probes, idempotent migrations, golden tests,
# API contract checks, UI typecheck, and evidence queries.
# Any failure = NO-GO. No mercy.

RED='\033[0;31m'; GRN='\033[0;32m'; YEL='\033[1;33m'; NC='\033[0m'
fail() { echo -e "${RED}✗ $*${NC}"; exit 1; }
warn() { echo -e "${YEL}! $*${NC}"; }
pass() { echo -e "${GRN}✓ $*${NC}"; }

ROOT="$(pwd)"
DB="${ROOT}/data/owlin.db"
API="${OWLIN_API:-http://localhost:8001}"

need() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing tool: $1. Install it."
}

section() { echo -e "\n${YEL}=== $* ===${NC}"; }

# ---------- 0) TOOLING SANITY ----------
section "Tooling sanity"
need sqlite3
need python3
need curl
need jq || warn "jq not found; JSON validation will be weaker"
if command -v npx >/dev/null 2>&1; then
  :
else
  warn "npx not found; TypeScript check will be skipped"
fi
python3 - <<'PY' >/dev/null 2>&1 || fail "Python not working"
print("ok")
PY
pass "Tooling present"

# ---------- 1) MIGRATIONS (IDEMPOTENT) ----------
section "Migrations (idempotent)"
python3 - <<'PY'
import sys; sys.path.insert(0,'backend')
from db_manager_unified import get_db_manager
mgr = get_db_manager()
mgr.run_migrations(); print("First run OK")
mgr.run_migrations(); print("Second run (no-op) OK")
PY
pass "Migrations executed twice without error"

test -f "$DB" || fail "Database not found at $DB after migrations"

# ---------- 2) SCHEMA TRUTH ----------
section "Schema truth (the court of record)"
# Core tables
CORE_TABLES="ingest_batches ingest_assets doc_sets documents document_pages supplier_discounts match_links match_link_items invoice_items"
for t in $CORE_TABLES; do
  sqlite3 "$DB" ".tables" | grep -qw "$t" || fail "Missing table: $t"
done
pass "Core tables present"

# OCR confidence columns
sqlite3 "$DB" "PRAGMA table_info(invoices);" | grep -E "ocr_avg_conf|ocr_min_conf" >/dev/null || fail "Missing invoices.*ocr_* confidence columns"
sqlite3 "$DB" "PRAGMA table_info(invoice_pages);" | grep -E "ocr_avg_conf_page|ocr_min_conf_line" >/dev/null || fail "Missing invoice_pages.*ocr_* columns"
pass "OCR confidence columns present"

# Canonical + discount + verdict fields
sqlite3 "$DB" "SELECT name FROM pragma_table_info('invoice_items')" | grep -E \
  "quantity_each|quantity_ml|quantity_l|quantity_g|packs|units_per_pack|discount_kind|discount_value|discount_residual_pennies|line_verdict" >/dev/null \
  || fail "Missing canonical/discount/verdict columns on invoice_items"
pass "invoice_items columns present"

# ---------- 3) FIXTURES EXIST ----------
section "Fixtures presence"
req_files=(
  "tests/fixtures/three_png_pages" 
  "tests/fixtures/multi_mix_2inv_1dn.pdf"
  "tests/fixtures/golden/tia_maria.json"
)
for f in "${req_files[@]}"; do
  [ -e "$f" ] || fail "Missing fixture: $f"
done
pass "All key fixtures present"

# ---------- 4) GOLDEN TESTS ----------
section "Golden tests (trial by fire)"
need python3
python3 -m pytest -q tests/test_units_normalisation.py || fail "Units 25-case matrix failed"
python3 -m pytest -q tests/test_invoice_math.py       || fail "Math/VAT tests failed"
python3 -m pytest -q tests/test_discount_solver.py    || fail "Discount solver tests failed (Tia Maria included)"
python3 -m pytest -q tests/test_pairing_math.py       || fail "Pairing tests failed"
python3 -m pytest -q tests/test_verdicts.py           || fail "Verdict exclusivity tests failed"
# Optional but expected
if [ -f tests/test_assembler.py ]; then
  python3 -m pytest -q tests/test_assembler.py || fail "Assembler tests failed"
else
  warn "tests/test_assembler.py missing — assembler claims unproven"
fi
if [ -f tests/test_ocr_confidence.py ]; then
  python3 -m pytest -q tests/test_ocr_confidence.py || fail "OCR confidence tests failed"
else
  warn "tests/test_ocr_confidence.py missing — OCR gating claims unproven"
fi
if [ -f tests/test_supplier_insights.py ]; then
  python3 -m pytest -q tests/test_supplier_insights.py || fail "Supplier insights tests failed"
else
  warn "tests/test_supplier_insights.py missing — insights claims unproven"
fi
if [ -f tests/test_support_pack.py ]; then
  python3 -m pytest -q tests/test_support_pack.py || fail "Support pack tests failed"
else
  warn "tests/test_support_pack.py missing — support pack claims unproven"
fi
pass "Golden tests green"

# ---------- 5) API CONTRACTS ----------
section "API contracts (no backdoors)"
if curl -sf "${API}/health" >/dev/null; then
  pass "Backend reachable: ${API}"
else
  fail "Backend not reachable at ${API}. Start server and re-run."
fi

# Pick latest invoice id if available
INV_ID="$(sqlite3 "$DB" "SELECT id FROM invoices ORDER BY ROWID DESC LIMIT 1;" || true)"
if [ -n "${INV_ID:-}" ]; then
  body="$(curl -sf "${API}/api/invoices/${INV_ID}")" || fail "GET /api/invoices/${INV_ID} failed"
  echo "$body" | jq . >/dev/null 2>&1 || warn "jq not present or invalid JSON pretty-print skipped"
  echo "$body" | grep -q "\"lines\"" || fail "Invoice payload missing lines[]"
  echo "$body" | grep -q "ocr_avg_conf" || fail "Invoice payload missing ocr_avg_conf"
  echo "$body" | grep -q "line_verdict" || warn "Invoice lines missing line_verdict — verify persistence"
  pass "Invoice fetch contract OK"

  # Try auto pairing (may be no-op if no DN exists)
  curl -sf -X POST "${API}/api/invoices/${INV_ID}/pairing/auto" >/dev/null || warn "Auto pairing endpoint failed or no candidates — verify with fixtures"
else
  warn "No invoices found in DB to test API payloads. Ingest fixtures and re-run."
fi

# ---------- 6) UI TYPECHECK ----------
section "UI typecheck (no lies on screen)"
if command -v npx >/dev/null 2>&1; then
  npx tsc --noEmit || fail "TypeScript errors — UI cannot be trusted"
  pass "TypeScript clean"
else
  warn "Skipping TypeScript check (npx missing)"
fi

# ---------- 7) EVIDENCE QUERIES ----------
section "Evidence queries (discounts, pairing, verdicts)"
# Tia Maria outcome
TIA="$(sqlite3 "$DB" "SELECT discount_kind, discount_value, discount_residual_pennies FROM invoice_items WHERE desc LIKE '%Tia Maria%' LIMIT 1;" || true)"
if [ -n "${TIA:-}" ]; then
  echo "$TIA" | grep -qi "percent" || fail "Tia Maria not solved as percent"
  echo "$TIA" | awk -F'|' '{exit ($3+0)<=1 ? 0:1}' || fail "Tia Maria residual > 1p"
  pass "Tia Maria: percent with residual ≤1p"
else
  warn "No Tia Maria line found in DB — run discount fixtures before claiming victory"
fi

# Pairing reasons presence
sqlite3 "$DB" "SELECT reason, COUNT(*) FROM match_link_items GROUP BY reason;" || warn "No pairing reasons found — verify pairing fixtures"

# Verdict distribution sanity
sqlite3 "$DB" "SELECT line_verdict, COUNT(*) FROM invoice_items GROUP BY line_verdict;" || warn "No verdicts aggregated — ensure lines exist"

# ---------- 8) PERFORMANCE SMOKE ----------
section "Performance smoke (not theatre)"
# If bench script exists, run it; otherwise warn.
if [ -f scripts/bench_engine.py ]; then
  python3 scripts/bench_engine.py || fail "Benchmark failed or exceeded target"
  pass "Benchmark OK"
else
  warn "scripts/bench_engine.py missing — performance claims unproven"
fi

echo -e "\n${GRN}ALL CHECKS COMPLETED. If you saw any red, the system is NOT production-ready.${NC}" 