#!/usr/bin/env bash
set -euo pipefail

echo "📦 Creating OWLIN Support Pack..."

# Generate timestamp
ts=$(date +"%Y%m%d_%H%M%S")
out="support_pack_${ts}.zip"

echo "⏰ Timestamp: $ts"
echo "📁 Output: $out"

# Create support pack
echo "📋 Collecting files..."

# Create temporary directory for support pack
TEMP_DIR=$(mktemp -d)
SUPPORT_DIR="$TEMP_DIR/owlin_support_$ts"

mkdir -p "$SUPPORT_DIR"

# Copy essential files
echo "📄 Copying backend files..."
cp -r backend/*.py "$SUPPORT_DIR/" 2>/dev/null || echo "⚠️  Backend files not found"

echo "📄 Copying uploads directory..."
cp -r data/uploads "$SUPPORT_DIR/" 2>/dev/null || echo "⚠️  Uploads directory not found"

echo "📄 Copying logs..."
cp -r data/logs "$SUPPORT_DIR/" 2>/dev/null || echo "⚠️  Logs directory not found"

echo "📄 Copying configuration..."
cp env.local "$SUPPORT_DIR/" 2>/dev/null || echo "⚠️  env.local not found"
cp lib/config.ts "$SUPPORT_DIR/" 2>/dev/null || echo "⚠️  config.ts not found"

# Create system info file
echo "💻 Collecting system information..."
{
    echo "=== OWLIN Support Pack ==="
    echo "Generated: $(date)"
    echo "Hostname: $(hostname)"
    echo "OS: $(uname -a)"
    echo "Python: $(python --version 2>/dev/null || echo 'Not found')"
    echo "Node: $(node --version 2>/dev/null || echo 'Not found')"
    echo "Git: $(git --version 2>/dev/null || echo 'Not found')"
    echo ""
    echo "=== Backend Status ==="
    curl -s http://127.0.0.1:8000/api/health 2>/dev/null || echo "Backend not responding"
    echo ""
    echo "=== Upload Directory ==="
    ls -la data/uploads/ 2>/dev/null || echo "Uploads directory not found"
    echo ""
    echo "=== Recent Logs ==="
    tail -20 data/logs/*.log 2>/dev/null || echo "No log files found"
} > "$SUPPORT_DIR/system_info.txt"

# Create git info
echo "📋 Collecting git information..."
{
    echo "=== Git Status ==="
    git status 2>/dev/null || echo "Not a git repository"
    echo ""
    echo "=== Recent Commits ==="
    git log --oneline -10 2>/dev/null || echo "No git history"
    echo ""
    echo "=== Current Branch ==="
    git branch --show-current 2>/dev/null || echo "No current branch"
} > "$SUPPORT_DIR/git_info.txt"

# Create test results
echo "🧪 Running diagnostic tests..."
{
    echo "=== Diagnostic Tests ==="
    echo "Backend health check:"
    curl -s http://127.0.0.1:8000/api/health || echo "FAILED"
    echo ""
    echo "Upload test:"
    echo "test content" > "$TEMP_DIR/test_file.txt"
    curl -s -X POST http://127.0.0.1:8000/api/upload -F "file=@$TEMP_DIR/test_file.txt" || echo "FAILED"
    echo ""
} > "$SUPPORT_DIR/diagnostics.txt" 2>&1

# Create zip file
echo "📦 Creating zip file..."
cd "$TEMP_DIR"
zip -r "$out" "owlin_support_$ts" >/dev/null

# Move to current directory
mv "$out" "$(pwd)/$out"

# Cleanup
rm -rf "$TEMP_DIR"

echo ""
echo "✅ Support pack created: $out"
echo "📁 Contents:"
echo "  - Backend Python files"
echo "  - Uploads directory"
echo "  - Log files"
echo "  - Configuration files"
echo "  - System information"
echo "  - Git information"
echo "  - Diagnostic test results"
echo ""
echo "💡 Send this file to support for debugging assistance!"
