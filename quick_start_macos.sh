#!/bin/bash

# Owlin Quick Start Script for macOS
# This script handles the Python command differences on macOS

echo "🚀 Owlin Quick Start for macOS"
echo "================================"

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ python3 not found. Installing Python 3..."
    
    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrew not found. Please install Homebrew first:"
        echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    
    echo "📦 Installing Python 3 via Homebrew..."
    brew install python
    
    if ! command -v python3 &> /dev/null; then
        echo "❌ Failed to install Python 3"
        exit 1
    fi
fi

echo "✅ Python 3 found: $(python3 --version)"

# Check if pip3 is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 not found. Installing pip..."
    python3 -m ensurepip --upgrade
fi

echo "✅ pip3 found: $(pip3 --version)"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
python3 -m pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install Python dependencies"
    exit 1
fi

echo "✅ Python dependencies installed"

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Installing Node.js..."
    brew install node
    
    if ! command -v node &> /dev/null; then
        echo "❌ Failed to install Node.js"
        exit 1
    fi
fi

echo "✅ Node.js found: $(node --version)"

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
npm install

if [ $? -ne 0 ]; then
    echo "❌ Failed to install Node.js dependencies"
    exit 1
fi

echo "✅ Node.js dependencies installed"

# Test if everything is working
echo "🧪 Testing setup..."

# Test Python imports
echo "Testing Python imports..."
python3 -c "
import fastapi
import uvicorn
import requests
print('✅ Python dependencies working')
" 2>/dev/null

if [ $? -ne 0 ]; then
    echo "❌ Python dependencies test failed"
    exit 1
fi

echo "✅ All dependencies installed and working!"

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "📋 Next Steps:"
echo "1. Start the backend server:"
echo "   python3 -m uvicorn backend.main:app --reload --port 8000"
echo ""
echo "2. Start the frontend server (in a new terminal):"
echo "   npm run dev"
echo ""
echo "3. Or use the automated start script:"
echo "   python3 start_servers.py"
echo ""
echo "🌐 Access URLs:"
echo "   Frontend: http://localhost:3000"
echo "   Backend: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "🧪 To test the upload flow:"
echo "   python3 test_upload_simple.py"
echo ""
echo "📝 Optional: Make 'python' point to 'python3'"
echo "   echo 'alias python=python3' >> ~/.zshrc"
echo "   source ~/.zshrc" 