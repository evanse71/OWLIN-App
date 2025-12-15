#!/bin/bash
# ============================================
# Owlin - Backup-Everything.sh
# Full-folder backup with fallbacks + SHA256
# Cross-platform (Linux/macOS)
# ============================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 1) Resolve OWLIN_ROOT (folder where this script lives)
OWLIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo
echo "=========================================================="
echo "    OWLIN BACKUP - FULL FOLDER SNAPSHOT (Linux/macOS)"
echo "=========================================================="
echo " Root: $OWLIN_ROOT"
echo

# 2) Candidate destinations (in order)
DEST_1="$HOME/Owlin Backups"
DEST_2="$HOME/Documents/Owlin Backups"
DEST_3="$HOME/Desktop/Owlin Backups"
DEST_4="/tmp/OwlinBackups"

# 3) Pick first writable destination
BACKUP_DIR=""
for dest in "$DEST_1" "$DEST_2" "$DEST_3" "$DEST_4"; do
    if [[ -z "$BACKUP_DIR" ]]; then
        echo "🔍 Testing backup location: $dest"
        
        # Create directory if it doesn't exist
        if [[ ! -d "$dest" ]]; then
            echo "📁 Creating directory: $dest"
            mkdir -p "$dest" 2>/dev/null || true
        fi
        
        # Test write access
        if touch "$dest/.write_test.tmp" 2>/dev/null; then
            rm -f "$dest/.write_test.tmp" 2>/dev/null
            BACKUP_DIR="$dest"
            echo -e "${GREEN}✅ Using backup destination: $dest${NC}"
        else
            echo -e "${YELLOW}⚠️  Not writable: $dest — trying next...${NC}"
        fi
    fi
done

if [[ -z "$BACKUP_DIR" ]]; then
    echo -e "${RED}❌ ERROR: No writable backup destination found.${NC}"
    echo "Tried:"
    echo "  - $DEST_1"
    echo "  - $DEST_2"
    echo "  - $DEST_3"
    echo "  - $DEST_4"
    echo
    echo "Exiting."
    exit 1
fi

echo

# 4) Clean timestamp
TS=$(date '+%Y-%m-%d_%H-%M-%S')

# 5) Build archive filename
ZIP_NAME="Owlin_Backup_${TS}.tar.gz"
ZIP_PATH="$BACKUP_DIR/$ZIP_NAME"
echo "📦 Archive: $ZIP_PATH"
echo

# 6) Check for compression tools
if command -v tar >/dev/null 2>&1; then
    echo "🛠 Using tar for compression"
    echo "🔍 Excluding: node_modules, __pycache__, .git, .venv"
    
    # Create exclusion list
    EXCLUDE_FILE="/tmp/owlin_backup_exclude_$$.txt"
    cat > "$EXCLUDE_FILE" << EOF
node_modules
__pycache__
.git
.venv
.env
*.log
temp
tmp
EOF
    
    # Create the backup
    cd "$OWLIN_ROOT"
    tar -czf "$ZIP_PATH" \
        --exclude-from="$EXCLUDE_FILE" \
        --exclude="*.tmp" \
        --exclude="*.temp" \
        . 2>/dev/null
    
    ZIP_RC=$?
    rm -f "$EXCLUDE_FILE"
    
elif command -v zip >/dev/null 2>&1; then
    echo "🛠 Using zip for compression"
    echo "🔍 Excluding: node_modules, __pycache__, .git, .venv"
    
    # Create the backup
    cd "$OWLIN_ROOT"
    zip -r "$ZIP_PATH" . \
        -x "node_modules/*" "__pycache__/*" ".git/*" ".venv/*" \
        "*.log" "temp/*" "tmp/*" "*.tmp" "*.temp" 2>/dev/null
    
    ZIP_RC=$?
else
    echo -e "${RED}❌ ERROR: Neither tar nor zip found for compression!${NC}"
    exit 1
fi

if [[ $ZIP_RC -ne 0 ]]; then
    echo -e "${RED}❌ ERROR: Compression failed (code $ZIP_RC).${NC}"
    [[ -f "$ZIP_PATH" ]] && rm -f "$ZIP_PATH"
    exit 3
fi

# 7) Show size
ZIP_SIZE=$(stat -c%s "$ZIP_PATH" 2>/dev/null || stat -f%z "$ZIP_PATH" 2>/dev/null || echo "unknown")
echo -e "${GREEN}✅ Backup created.${NC}"
echo "   → $ZIP_PATH"
echo "   → Size: $ZIP_SIZE bytes"
echo

# 8) Generate SHA256 checksum
SHA_PATH="$ZIP_PATH.sha256.txt"
if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$ZIP_PATH" | cut -d' ' -f1 > "$SHA_PATH"
    echo "$(basename "$ZIP_PATH")" >> "$SHA_PATH"
elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$ZIP_PATH" | cut -d' ' -f1 > "$SHA_PATH"
    echo "$(basename "$ZIP_PATH")" >> "$SHA_PATH"
else
    echo -e "${YELLOW}⚠️  Could not create SHA256 file (no hash tools found).${NC}"
fi

if [[ -f "$SHA_PATH" ]]; then
    echo "🧾 SHA256: $SHA_PATH"
else
    echo -e "${YELLOW}⚠️  Could not create SHA256 file.${NC}"
fi

echo
echo "📂 Existing backups in $BACKUP_DIR:"
ls -la "$BACKUP_DIR"/Owlin_Backup_*.tar.gz 2>/dev/null | tail -10 || echo "   (No previous backups found)"
echo

echo "ℹ️  RESTORE:"
echo "   1) Extract: tar -xzf $ZIP_PATH -C /path/to/restore/location"
echo "   2) Replace the existing Owlin folder or keep as a dated snapshot."
echo

echo -e "${GREEN}🎉 Done.${NC}"
echo
