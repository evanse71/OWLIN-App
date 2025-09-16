#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BE="$ROOT/backend"
FE="$ROOT/frontend"

echo "==> Backend venv & deps"
cd "$BE"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
if [ -f requirements.txt ]; then pip install -r requirements.txt; else echo "ERROR: requirements.txt missing"; exit 1; fi

echo "==> Backend .env"
[ -f .env ] || { [ -f .env.example ] && cp .env.example .env || echo -e "DB_PATH=./data/owlin.db\nLICENSE_DIR=./license\nLOG_DIR=./logs\nALLOW_ORIGINS=http://localhost:3000\nOCR_LANG=en" > .env; }
mkdir -p data logs license

echo "==> DB init (if available)"
if command -v alembic >/dev/null 2>&1; then alembic upgrade head || true; fi
[ -f scripts/init_db.py ] && python scripts/init_db.py || true

echo "==> Tesseract/Poppler check"
command -v tesseract >/dev/null 2>&1 || echo "WARN: tesseract not found on PATH"
command -v pdftoppm >/dev/null 2>&1 || echo "WARN: poppler (pdftoppm) not found on PATH"

echo "==> Start backend :8001"
if lsof -ti :8001 >/dev/null 2>&1; then kill -9 "$(lsof -ti :8001)"; fi
( uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload > ../.backend.log 2>&1 & )
sleep 2

echo "==> Frontend deps"
cd "$FE"
[ -f package.json ] || { echo "ERROR: frontend/package.json missing"; exit 1; }
npm install

echo "==> Frontend .env.local"
[ -f .env.local ] || { [ -f .env.example ] && cp .env.example .env.local || echo "NEXT_PUBLIC_API_BASE=http://localhost:8001" > .env.local; }

echo "==> Start frontend :3000"
if lsof -ti :3000 >/dev/null 2>&1; then kill -9 "$(lsof -ti :3000)"; fi
( npm run dev > ../.frontend.log 2>&1 & )
sleep 3

echo "==> Healthcheck"
cd "$ROOT/scripts"
bash healthcheck.sh || { echo "Healthcheck failed"; exit 1; }

echo "==> Done. Open http://localhost:3000"
