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
