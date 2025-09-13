#!/usr/bin/env bash
set -euo pipefail

fail(){ echo "❌ $*" >&2; exit 1; }
info(){ echo "• $*" >&2; }
ok(){ echo "✅ $*" >&2; }

[ -f ./backend/final_single_port.py ] || fail "Where is backend/final_single_port.py? Stand in repo root."

# kill 8001 politely
if command -v lsof >/dev/null 2>&1; then
  pids=$(lsof -t -i:8001 || true)
  [ -n "${pids:-}" ] && kill -9 $pids || true
fi

# start server
info "Launching server: python -m backend.final_single_port"
python -m backend.final_single_port >/tmp/owlin.out 2>/tmp/owlin.err &
SPID=$!

cleanup(){ kill $SPID >/dev/null 2>&1 || true; }
trap cleanup EXIT

# wait for health
for i in $(seq 1 40); do
  if curl -fsS http://127.0.0.1:8001/api/health | grep -q '"ok": *true'; then
    ok "Health says OK."
    break
  fi
  sleep 0.25
  [ $i -eq 40 ] && { echo "STDERR:"; cat /tmp/owlin.err; echo "STDOUT:"; cat /tmp/owlin.out; fail "Server never became healthy."; }
done

# status
S=$(curl -fsS http://127.0.0.1:8001/api/status)
echo "$S" | grep -q '"api_mounted": *true' || {
  info "API not mounted. We command it to obey."
  curl -fsS -X POST http://127.0.0.1:8001/api/retry-mount >/dev/null || true
  sleep 0.3
  S=$(curl -fsS http://127.0.0.1:8001/api/status)
  echo "$S" | grep -q '"api_mounted": *true' || { echo "$S"; fail "API refuses to mount."; }
}
ok "API mounted. Discipline restored."

# root
curl -fsS -I http://127.0.0.1:8001 >/dev/null || fail "Root / does not respond 200. Shame."

# LLM (non-fatal)
curl -fsS -m 2 http://127.0.0.1:8001/llm/api/tags >/dev/null && ok "LLM proxy reachable." || info "LLM proxy not reachable—fine if Ollama is off."

# invoices smoke (optional)
curl -fsS -m 3 http://127.0.0.1:8001/api/manual/invoices >/dev/null && ok "Manual invoices endpoint replies." || info "Manual invoices endpoint not present—non-fatal."

ok "Verdict: PASS. The server stands like granite."
