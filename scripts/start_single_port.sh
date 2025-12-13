#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Starting OWLIN Single-Port App..."

# Force working directory to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo "📁 Working directory: $REPO_ROOT"

# 1) Start LLM (Ollama) if present
echo ""
echo "🔧 Checking for LLM service..."
if command -v ollama >/dev/null 2>&1; then
  if ! pgrep -f "ollama serve" >/dev/null 2>&1; then
    nohup ollama serve >/dev/null 2>&1 &
    echo "✅ Ollama started in background"
  else
    echo "✅ Ollama already running"
  fi
else
  echo "⚠️  Ollama not found, skipping LLM service"
fi

# 2) Build UI if 'out/index.html' missing
echo ""
echo "🔧 Checking UI build..."
if [ ! -f "./out/index.html" ]; then
  if command -v npm >/dev/null 2>&1; then
    echo "📦 Building UI with npm..."
    npm run build
    echo "✅ UI build complete"
  else
    echo "⚠️  npm not found; skipping UI build. Ensure ./out exists."
  fi
else
  echo "✅ UI build found"
fi

# 3) Start FastAPI (single port)
echo ""
echo "🌐 Starting FastAPI server..."
echo "Opening http://127.0.0.1:8001 in your browser..."
echo ""
echo "Press Ctrl+C to stop the server"

exec python -m backend.final_single_port
