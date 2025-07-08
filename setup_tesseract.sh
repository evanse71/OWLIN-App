#!/bin/bash

# Owlin OCR - Tesseract Setup Script
# This script downloads and sets up bundled Tesseract binaries for the Owlin app

set -e

echo "🔧 Setting up bundled Tesseract OCR for Owlin..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect platform
PLATFORM=$(uname -s)
ARCH=$(uname -m)

print_status "Detected platform: $PLATFORM ($ARCH)"

# Create tesseract_bin directory structure
mkdir -p tesseract_bin/{win,mac,linux}

# Function to download and extract Tesseract
download_tesseract() {
    local platform=$1
    local url=$2
    local filename=$3
    local extract_dir=$4
    
    print_status "Downloading Tesseract for $platform..."
    
    if [ -f "$filename" ]; then
        print_warning "File $filename already exists, skipping download"
    else
        curl -L -o "$filename" "$url"
        print_success "Downloaded $filename"
    fi
    
    if [ -d "$extract_dir" ]; then
        print_warning "Directory $extract_dir already exists, skipping extraction"
    else
        print_status "Extracting $filename..."
        if [[ "$filename" == *.zip ]]; then
            unzip -q "$filename" -d "$extract_dir"
        elif [[ "$filename" == *.tar.gz ]]; then
            tar -xzf "$filename" -C "$extract_dir"
        fi
        print_success "Extracted to $extract_dir"
    fi
}

# Download Tesseract binaries based on platform
case "$PLATFORM" in
    "Darwin")
        print_status "Setting up Tesseract for macOS..."
        
        # For macOS, we'll use Homebrew to install and then copy the binary
        if command -v brew &> /dev/null; then
            print_status "Homebrew found, installing Tesseract..."
            brew install tesseract
            
            # Copy the binary to our bundled location
            TESSERACT_PATH=$(which tesseract)
            if [ -n "$TESSERACT_PATH" ]; then
                cp "$TESSERACT_PATH" "tesseract_bin/mac/tesseract"
                chmod +x "tesseract_bin/mac/tesseract"
                
                # Copy tessdata if it exists
                TESSDATA_PATH=$(brew --prefix tesseract)/share/tessdata
                if [ -d "$TESSDATA_PATH" ]; then
                    cp -r "$TESSDATA_PATH" "tesseract_bin/mac/"
                    print_success "Copied tessdata to tesseract_bin/mac/"
                fi
                
                print_success "Tesseract binary copied to tesseract_bin/mac/tesseract"
            else
                print_error "Could not find Tesseract binary after Homebrew installation"
                exit 1
            fi
        else
            print_warning "Homebrew not found. Please install Tesseract manually:"
            echo "  brew install tesseract"
            echo "  Then copy the binary to tesseract_bin/mac/tesseract"
        fi
        ;;
        
    "Linux")
        print_status "Setting up Tesseract for Linux..."
        
        # For Linux, download pre-compiled binary
        TESSERACT_VERSION="5.3.3"
        DOWNLOAD_URL="https://github.com/tesseract-ocr/tesseract/releases/download/${TESSERACT_VERSION}/tesseract-ocr-${TESSERACT_VERSION}-linux-x86_64.tar.gz"
        FILENAME="tesseract-linux.tar.gz"
        
        download_tesseract "Linux" "$DOWNLOAD_URL" "$FILENAME" "tesseract-linux"
        
        # Copy binary to our bundled location
        if [ -f "tesseract-linux/bin/tesseract" ]; then
            cp "tesseract-linux/bin/tesseract" "tesseract_bin/linux/tesseract"
            chmod +x "tesseract_bin/linux/tesseract"
            
            # Copy tessdata
            if [ -d "tesseract-linux/share/tessdata" ]; then
                cp -r "tesseract-linux/share/tessdata" "tesseract_bin/linux/"
                print_success "Copied tessdata to tesseract_bin/linux/"
            fi
            
            print_success "Tesseract binary copied to tesseract_bin/linux/tesseract"
        else
            print_error "Could not find Tesseract binary in downloaded archive"
            exit 1
        fi
        ;;
        
    "MINGW"*|"MSYS"*|"CYGWIN"*)
        print_status "Setting up Tesseract for Windows..."
        
        # For Windows, download pre-compiled binary
        TESSERACT_VERSION="5.3.3"
        DOWNLOAD_URL="https://github.com/UB-Mannheim/tesseract/releases/download/v${TESSERACT_VERSION}/tesseract-ocr-w64-setup-${TESSERACT_VERSION}.exe"
        FILENAME="tesseract-windows-setup.exe"
        
        print_warning "Windows setup requires manual installation:"
        echo "1. Download Tesseract from: $DOWNLOAD_URL"
        echo "2. Install to default location (C:\\Program Files\\Tesseract-OCR\\)"
        echo "3. Copy tesseract.exe to tesseract_bin/win/tesseract.exe"
        echo "4. Copy tessdata folder to tesseract_bin/win/tessdata/"
        ;;
        
    *)
        print_error "Unsupported platform: $PLATFORM"
        print_warning "Please install Tesseract manually for your platform"
        exit 1
        ;;
esac

# Create a test script to verify the installation
cat > test_tesseract.py << 'EOF'
#!/usr/bin/env python3
"""
Test script to verify bundled Tesseract installation
"""

import os
import sys
import platform
import subprocess

def test_bundled_tesseract():
    print("🧪 Testing bundled Tesseract installation...")
    
    # Determine platform
    if platform.system() == "Windows":
        tess_path = os.path.join("tesseract_bin", "win", "tesseract.exe")
    elif platform.system() == "Darwin":
        tess_path = os.path.join("tesseract_bin", "mac", "tesseract")
    else:
        tess_path = os.path.join("tesseract_bin", "linux", "tesseract")
    
    # Check if binary exists
    if not os.path.exists(tess_path):
        print(f"❌ Tesseract binary not found at: {tess_path}")
        return False
    
    # Test if binary is executable
    try:
        result = subprocess.run([tess_path, "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ Tesseract binary is working: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Tesseract binary failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error testing Tesseract binary: {e}")
        return False

if __name__ == "__main__":
    success = test_bundled_tesseract()
    sys.exit(0 if success else 1)
EOF

chmod +x test_tesseract.py

# Test the installation
print_status "Testing bundled Tesseract installation..."
if python3 test_tesseract.py; then
    print_success "Bundled Tesseract setup completed successfully!"
else
    print_warning "Tesseract test failed. You may need to install manually."
fi

# Create README for bundled Tesseract
cat > tesseract_bin/README.md << 'EOF'
# Bundled Tesseract OCR Binaries

This directory contains bundled Tesseract OCR binaries for the Owlin application.

## Directory Structure

```
tesseract_bin/
├── win/
│   ├── tesseract.exe
│   └── tessdata/
├── mac/
│   ├── tesseract
│   └── tessdata/
├── linux/
│   ├── tesseract
│   └── tessdata/
└── README.md
```

## Installation

### Automatic Setup
Run the setup script:
```bash
./setup_tesseract.sh
```

### Manual Setup

#### Windows
1. Download Tesseract from: https://github.com/UB-Mannheim/tesseract/releases
2. Install to default location (C:\Program Files\Tesseract-OCR\)
3. Copy `tesseract.exe` to `tesseract_bin/win/tesseract.exe`
4. Copy `tessdata` folder to `tesseract_bin/win/tessdata/`

#### macOS
1. Install via Homebrew: `brew install tesseract`
2. Copy binary: `cp $(which tesseract) tesseract_bin/mac/tesseract`
3. Copy tessdata: `cp -r $(brew --prefix tesseract)/share/tessdata tesseract_bin/mac/`

#### Linux
1. Download from: https://github.com/tesseract-ocr/tesseract/releases
2. Extract and copy binary to `tesseract_bin/linux/tesseract`
3. Copy tessdata folder to `tesseract_bin/linux/tessdata/`

## Testing

Run the test script to verify installation:
```bash
python3 test_tesseract.py
```

## Troubleshooting

- Ensure binaries have execute permissions
- Check that tessdata directory contains language files
- Verify platform-specific binary is in correct directory
- Run `./test_tesseract.py` to diagnose issues
EOF

print_success "Setup complete! Check tesseract_bin/README.md for detailed instructions."
print_status "You can now run the Owlin app with bundled Tesseract OCR support." 