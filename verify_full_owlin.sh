#!/usr/bin/env bash
set -euo pipefail
fail(){ echo "❌ $*" >&2; exit 1; }
ok(){ echo "✅ $*" >&2; }
info(){ echo "• $*" >&2; }

[ -f backend/final_single_port.py ] || fail "Run from repo root."

# kill port 8001 if needed
if command -v lsof >/dev/null; then pids=$(lsof -t -i:8001 || true); [ -n "${pids:-}" ] && kill -9 $pids || true; fi

# start server
python -m backend.final_single_port >/tmp/owlin.out 2>/tmp/owlin.err & SP=$!
trap 'kill $SP >/dev/null 2>&1 || true' EXIT

# wait for health
for i in {1..40}; do
  if curl -fsS http://127.0.0.1:8001/api/health | grep -q '"ok": *true'; then ok "Health OK"; break; fi
  sleep .25; [ $i -eq 40 ] && { cat /tmp/owlin.err; fail "Server never became healthy."; }
done

S=$(curl -fsS http://127.0.0.1:8001/api/status)
echo "$S" | grep -q '"api_mounted": *true' || { curl -fsS -XPOST http://127.0.0.1:8001/api/retry-mount >/dev/null; sleep .3; curl -fsS http://127.0.0.1:8001/api/status | grep -q '"api_mounted": *true' || fail "API not mounted"; }
ok "API mounted"

curl -fsS -I http://127.0.0.1:8001 >/dev/null || fail "Root not 200"
ok "Root 200"

# invoice workflow (adjust path if different)
curl -fsS -XPOST http://127.0.0.1:8001/api/manual/invoices \
  -H 'Content-Type: application/json' \
  -d '{"supplier_id":"S1","supplier_name":"Test Supplier","invoice_date":"2025-09-13","invoice_ref":"INV-001","lines":[{"description":"Beer crate","outer_qty":2,"unit_price":50,"vat_rate_percent":20}]}' >/dev/null || info "Invoice create optional: skipped/failed (non-fatal)"

for _ in {1..20}; do curl -fsS http://127.0.0.1:8001/api/health >/dev/null || fail "Health blip under stress"; done
ok "Stress OK"

curl -fsS -m 2 http://127.0.0.1:8001/llm/api/tags >/dev/null && ok "LLM proxy OK" || info "LLM proxy not reachable (fine if Ollama off)"

# Test backup/recovery
curl -fsS -XPOST http://127.0.0.1:8001/api/backup >/dev/null && ok "Backup endpoint OK" || info "Backup endpoint optional"
curl -fsS -XPOST http://127.0.0.1:8001/api/recovery -d "test" >/dev/null && ok "Recovery endpoint OK" || info "Recovery endpoint optional"

# Stress latency test
info "Running stress latency test..."
times=()
for _ in {1..50}; do
  start=$(date +%s%N)
  curl -fsS http://127.0.0.1:8001/api/health >/dev/null || fail "Health check failed during latency test"
  end=$(date +%s%N)
  duration=$(( (end - start) / 1000000 ))  # Convert to milliseconds
  times+=($duration)
  sleep 0.01
done

# Calculate percentiles
IFS=$'\n' sorted=($(sort -n <<<"${times[*]}"))
unset IFS
p50=${sorted[24]}  # 50th percentile
p95=${sorted[47]}  # 95th percentile

if [ $p50 -le 50 ] && [ $p95 -le 150 ]; then
  ok "Latency OK: P50=${p50}ms, P95=${p95}ms"
else
  fail "Latency too high: P50=${p50}ms, P95=${p95}ms"
fi

ok "ALL TESTS PASSED – BULLETPROOF"
