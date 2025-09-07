#!/bin/bash

# State-of-the-Art OWLIN System Startup Script
echo "🚀 Starting State-of-the-Art OWLIN System..."

# Kill any existing processes
echo "🔄 Stopping existing processes..."
pkill -f uvicorn
pkill -f "npm run dev"
sleep 2

# Install dependencies if needed
echo "📦 Checking dependencies..."
if [ ! -f "requirements_state_of_art.txt" ]; then
    echo "📝 Creating requirements file..."
    cat > requirements_state_of_art.txt << EOF
fastapi>=0.104.0
uvicorn>=0.24.0
python-multipart>=0.0.6
easyocr>=1.7.0
pytesseract>=0.3.10
opencv-python>=4.8.0
Pillow>=10.0.0
pdf2image>=1.16.3
PyMuPDF>=1.23.0
fuzzywuzzy>=0.18.0
python-Levenshtein>=0.21.0
numpy>=1.24.0
scikit-learn>=1.3.0
EOF
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements_state_of_art.txt

# Start backend with state-of-the-art system
echo "🔧 Starting state-of-the-art backend..."
cd /Users/glennevans/Downloads/OWLIN-App-main
python3 -m uvicorn backend.main_state_of_art:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 5

# Test backend health
echo "🏥 Testing backend health..."
curl -s http://localhost:8000/health
if [ $? -eq 0 ]; then
    echo "✅ Backend is healthy!"
else
    echo "❌ Backend health check failed"
    exit 1
fi

# Start frontend
echo "🎨 Starting frontend..."
cd /Users/glennevans/Downloads/OWLIN-App-main
npm run dev &
FRONTEND_PID=$!

# Wait for frontend to start
echo "⏳ Waiting for frontend to start..."
sleep 10

# Test frontend
echo "🌐 Testing frontend..."
curl -s http://localhost:3000 | head -5
if [ $? -eq 0 ]; then
    echo "✅ Frontend is running!"
else
    echo "❌ Frontend test failed"
    exit 1
fi

echo ""
echo "🎉 State-of-the-Art OWLIN System is ready!"
echo ""
echo "📊 System Status:"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo "   Health:   http://localhost:8000/health"
echo ""
echo "🔧 Features Available:"
echo "   ✅ State-of-the-art OCR processing"
echo "   ✅ Intelligent field extraction"
echo "   ✅ Advanced multi-invoice processing"
echo "   ✅ Unified confidence scoring"
echo "   ✅ Enhanced error handling"
echo "   ✅ Real-time progress tracking"
echo ""
echo "📝 To stop the system:"
echo "   pkill -f uvicorn"
echo "   pkill -f 'npm run dev'"
echo ""
echo "🔍 To view logs:"
echo "   tail -f logs/backend.log"
echo "   tail -f logs/frontend.log"
echo ""

# Keep script running
wait 