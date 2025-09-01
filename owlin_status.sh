#!/usr/bin/env bash
set -euo pipefail

API="${API:-http://localhost:8000}"
DB="${DB:-data/owlin.db}"

RED='\033[0;31m'; GRN='\033[0;32m'; YEL='\033[1;33m'; NC='\033[0m'
say() { echo -e "${YEL}=== $* ===${NC}"; }
ok()  { echo -e "${GRN}✓ $*${NC}"; }
bad() { echo -e "${RED}✗ $*${NC}"; }

need() { command -v "$1" >/dev/null 2>&1 || { bad "Missing tool: $1"; exit 1; }; }

say "Tooling sanity"
need sqlite3
need python3
command -v jq >/dev/null || echo "! jq not found (JSON pretty will be limited)"
ok "Tools present"

# 1) Database Reality
say "1) Database reality — schema & migrations"
if [ ! -f "$DB" ]; then
  bad "Database not found at $DB"
else
  echo "-- .tables"
  sqlite3 "$DB" ".tables" || true

  echo "-- PRAGMA invoices"
  sqlite3 "$DB" "PRAGMA table_info(invoices);" || true

  echo "-- PRAGMA invoice_line_items"
  sqlite3 "$DB" "PRAGMA table_info(invoice_line_items);" || true

  echo "-- Migration history"
  sqlite3 "$DB" "SELECT version, name FROM migrations ORDER BY version;" || true

  # Canonical & discount columns quick check
  echo "-- Canonical/discount/verdict columns present?"
  sqlite3 "$DB" "SELECT name FROM pragma_table_info('invoice_line_items');" | \
    grep -E "quantity_each|quantity_ml|quantity_l|quantity_g|packs|units_per_pack|discount_kind|discount_value|discount_residual_pennies|line_flags|line_verdict" \
    >/dev/null && ok "Canonical/discount/verdict columns detected" || bad "Missing canonical/discount/verdict columns"
fi

# 2) API Contracts
say "2) API contracts — health & one invoice"
# Try to start a dev server only if nothing is listening
if ! curl -sf "${API}/health" >/dev/null 2>&1; then
  if [ -f backend/test_server.py ]; then
    echo "! Backend not responding on ${API}. Attempting to start backend/test_server.py"
    pkill -f "backend/test_server.py" >/dev/null 2>&1 || true
    (cd backend && nohup python3 test_server.py >/tmp/owlin_test_server.log 2>&1 &)
    sleep 2
  fi
fi

if curl -sf "${API}/health" >/dev/null 2>&1; then
  ok "Backend reachable: ${API}/health"
  curl -sf "${API}/health" | (command -v jq >/dev/null && jq . || cat)
else
  bad "Backend NOT reachable at ${API}. Start it and re-run this script."
fi

# Probe a latest invoice if present
INV_ID="$(sqlite3 "$DB" "SELECT id FROM invoices ORDER BY ROWID DESC LIMIT 1;" 2>/dev/null || true)"
if [ -n "${INV_ID:-}" ]; then
  say "GET /api/invoices/${INV_ID}"
  curl -sf "${API}/api/invoices/${INV_ID}" | (command -v jq >/dev/null && jq . || cat) || bad "Invoice API failed"
else
  echo "! No invoices found in DB; skipping invoice API probe."
fi

# 3) Test Suite Snapshot
say "3) Test suite snapshot (collect only)"
if command -v pytest >/dev/null 2>&1; then
  pytest --collect-only -q | head -80 || echo "! pytest collection problem"
else
  echo "! pytest not installed — skipping test collection"
fi

# 4) TypeScript status
say "4) TypeScript status"
if command -v npx >/dev/null 2>&1; then
  if npx tsc --noEmit >/dev/null 2>&1; then
    ok "TypeScript compile: clean"
  else
    bad "TypeScript compile errors — run: npx tsc --noEmit"
  fi
else
  echo "! npx not found — skipping frontend typecheck"
fi

# 5) Git/File Integrity
say "5) Git/file integrity"
if command -v git >/dev/null 2>&1; then
  git status --porcelain=v1 || true
  echo "-- Diff stat (uncommitted)"
  git diff --stat || true
else
  echo "! git not installed — skipping git status"
fi

say "Forensics complete. Read outputs above. Anything red is a blocker." 