#!/bin/bash

echo "🚀 Installing Advanced OCR Dependencies..."

# Install Python dependencies
echo "📦 Installing Python packages..."
pip3 install -r requirements_advanced_ocr.txt

# Install spaCy model
echo "🧠 Installing spaCy English model..."
python3 -m spacy download en_core_web_sm

# Install Tesseract (if not already installed)
if ! command -v tesseract &> /dev/null; then
    echo "🔍 Installing Tesseract..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        brew install tesseract
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        sudo apt-get update
        sudo apt-get install -y tesseract-ocr
    else
        echo "⚠️ Please install Tesseract manually for your OS"
    fi
fi

# Install Poppler (for PDF processing)
if ! command -v pdftoppm &> /dev/null; then
    echo "📄 Installing Poppler..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        brew install poppler
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        sudo apt-get install -y poppler-utils
    else
        echo "⚠️ Please install Poppler manually for your OS"
    fi
fi

echo "✅ Advanced OCR dependencies installed!"
echo "🎯 You can now use the advanced OCR processor with:"
echo "   python3 -m uvicorn backend.main_advanced:app --host 0.0.0.0 --port 8000" 