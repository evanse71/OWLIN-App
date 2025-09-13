# 🪪 Carry Card — Start & Verify

## Windows

```powershell
# from repo root
.\scripts\start_and_verify.ps1

# sanity checks
irm http://127.0.0.1:8001/api/health  | % Content
irm http://127.0.0.1:8001/api/status  | % Content
```

## Linux / macOS

```bash
chmod +x scripts/start_and_verify.sh   # first time
./scripts/start_and_verify.sh

# sanity checks
curl -fsS http://127.0.0.1:8001/api/health
curl -fsS http://127.0.0.1:8001/api/status
```

# 🧭 Modes

* **Static UI (default):** `npm run build` produces `out/`; server serves it.
* **Full Next SSR (one port):**

  ```bash
  # terminal 1
  npm run build && npm run start       # Next on :3000
  # terminal 2
  UI_MODE=PROXY_NEXT NEXT_BASE=http://127.0.0.1:3000 \
    python -m backend.final_single_port
  ```

# 🛡 Guardrails

* Route order: `/api/*` → `/llm/*` → UI catch-all last (and it must ignore `api/`, `llm/`).
* Frontend fetches: always `fetch('/api/...')`.
* PYTHONPATH points to repo root (launchers already set this).
* If API didn't mount: `POST /api/retry-mount`.

# 🧪 CI Snippets

**Ubuntu:**

```yaml
- name: Start Owlin (Linux)
  run: |
    chmod +x scripts/start_and_verify.sh
    ./scripts/start_and_verify.sh &
    for i in {1..40}; do
      curl -fsS http://127.0.0.1:8001/api/health && break
      sleep 0.25
    done
    curl -fsS http://127.0.0.1:8001/api/status
```

**Windows:**

```yaml
- name: Start Owlin (Windows)
  run: |
    powershell -ExecutionPolicy Bypass -File .\scripts\start_and_verify.ps1
    Start-Sleep -s 10
    irm http://127.0.0.1:8001/api/health  | % Content
    irm http://127.0.0.1:8001/api/status  | % Content
```

# 🧯 Quick Fixes

* **Port in use:** set `OWLIN_PORT` env or let the launcher clear it.
* **Unexpected token '<':** recheck route order; use leading `/api/`.
* **Unicode console errors:** launchers are ASCII-only and set UTF-8 already.
* **UI not built:** run `npm ci && npm run build` (you'll still get JSON fallback meanwhile).

You're done — one command on any platform brings Owlin up, verifies health, mounts the real API, and opens the UI. If you want a tiny desktop shortcut (.lnk) or `.command` file to trigger these launchers with custom icons, say the word and I'll spit out the exact steps.
