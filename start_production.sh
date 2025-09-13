#!/bin/bash

# OWLIN Production Startup Script
# This script initializes the database and starts both the Next.js app and Streamlit app

echo "🚀 Starting OWLIN Production Environment..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js and try again."
    exit 1
fi

# Check if npm is available
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm and try again."
    exit 1
fi

# Check if streamlit is available
if ! command -v streamlit &> /dev/null; then
    echo "⚠️ Streamlit is not installed. Installing streamlit..."
    pip3 install streamlit
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p data
mkdir -p uploads
mkdir -p logs

# Initialize the database
echo "🗄️ Initializing database..."
cd app
python3 -c "
import sys
sys.path.append('..')
from db_manager import init_db
try:
    init_db('data/owlin.db')
    print('✅ Database initialized successfully')
except Exception as e:
    print(f'❌ Database initialization failed: {e}')
    sys.exit(1)
"
cd ..

# Install Node.js dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing Node.js dependencies..."
    npm install
fi

# Function to cleanup background processes
cleanup() {
    echo "🛑 Shutting down OWLIN..."
    kill $NEXT_PID $STREAMLIT_PID 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start Next.js app in background
echo "🌐 Starting Next.js app..."
npm run dev &
NEXT_PID=$!

# Wait a moment for Next.js to start
sleep 3

# Start Streamlit app in background
echo "📊 Starting Streamlit app..."
cd app
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 &
STREAMLIT_PID=$!
cd ..

# Wait a moment for Streamlit to start
sleep 3

echo ""
echo "🎉 OWLIN Production Environment is running!"
echo ""
echo "📱 Next.js App (Frontend): http://localhost:3000"
echo "📊 Streamlit App (Upload): http://localhost:8501"
echo "🗄️ Database: data/owlin.db"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for background processes
wait 