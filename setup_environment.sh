#!/bin/bash

# Owlin OCR Environment Setup Script
# This script sets up the Python environment and installs all dependencies

echo "🚀 Setting up Owlin OCR Environment..."

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "📦 Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH for this session
    if [[ -f "/opt/homebrew/bin/brew" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [[ -f "/usr/local/bin/brew" ]]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
else
    echo "✅ Homebrew is already installed"
fi

# Install Python 3
echo "🐍 Installing Python 3..."
brew install python

# Install system dependencies
echo "📚 Installing system dependencies..."
brew install tesseract
brew install leptonica
brew install cmake
brew install opencv

# Create virtual environment
echo "🔧 Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install additional dependencies
echo "📦 Installing additional dependencies..."
pip install streamlit
pip install opencv-python
pip install pytesseract
pip install PyMuPDF
pip install easyocr
pip install pandas
pip install numpy
pip install Pillow
pip install pdf2image

# Create data directory
echo "📁 Creating data directory..."
mkdir -p data

# Set up Tesseract data
echo "🔤 Setting up Tesseract data..."
if [[ -d "/opt/homebrew/share/tessdata" ]]; then
    echo "✅ Tesseract data found at /opt/homebrew/share/tessdata"
elif [[ -d "/usr/local/share/tessdata" ]]; then
    echo "✅ Tesseract data found at /usr/local/share/tessdata"
else
    echo "⚠️ Tesseract data not found. Please install Tesseract language data."
fi

# Build C++ preprocessing module
echo "🔨 Building C++ preprocessing module..."
cd cpp_preprocessing
mkdir -p build
cd build
cmake ..
make -j$(nproc)
cd ../..

echo "✅ Environment setup complete!"
echo ""
echo "🎉 To run the application:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Run Streamlit: streamlit run app/main.py --server.headless true --server.runOnSave true --server.port 8501"
echo ""
echo "🔧 If you encounter any issues:"
echo "- Make sure all dependencies are installed: pip install -r requirements.txt"
echo "- Check Tesseract installation: tesseract --version"
echo "- Verify OpenCV installation: python -c 'import cv2; print(cv2.__version__)'" 