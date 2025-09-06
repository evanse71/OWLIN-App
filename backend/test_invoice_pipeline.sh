#!/bin/bash

# Invoice API Pipeline Test Script
# This script tests the complete invoice API pipeline

set -e

echo "🧪 Testing Invoice API Pipeline..."
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if we're in the right directory
if [ ! -f "test_server.py" ]; then
    print_error "Please run this script from the backend directory"
    exit 1
fi

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed"
    exit 1
fi

# Check if required packages are installed
echo "🔍 Checking dependencies..."
python3 -c "import fastapi, uvicorn" 2>/dev/null || {
    print_error "FastAPI or uvicorn not installed. Please install with: pip install fastapi uvicorn"
    exit 1
}

print_status "Dependencies OK"

# Kill any existing test server
echo "🔄 Stopping any existing test server..."
pkill -f "test_server.py" 2>/dev/null || true
sleep 1

# Start the test server in the background
echo "🚀 Starting test server..."
python3 test_server.py &
SERVER_PID=$!

# Wait for server to start
echo "⏳ Waiting for server to start..."
sleep 3

# Check if server is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    print_error "Server failed to start"
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

print_status "Server started successfully"

# Seed the database
echo "🌱 Seeding test database..."
if python3 seed_test_data.py; then
    print_status "Database seeded successfully"
else
    print_error "Failed to seed database"
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

# Test the API
echo "🧪 Testing API endpoints..."
if python3 test_invoice_api.py; then
    print_status "API tests passed"
else
    print_error "API tests failed"
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

# Manual curl tests
echo "🔍 Running manual curl tests..."

# Test health endpoint
echo "   Testing health endpoint..."
if curl -s http://localhost:8000/health | grep -q "ok"; then
    print_status "Health endpoint OK"
else
    print_error "Health endpoint failed"
fi

# Test database path endpoint
echo "   Testing database path endpoint..."
DB_PATH_RESPONSE=$(curl -s http://localhost:8000/api/debug/db-path)
if echo "$DB_PATH_RESPONSE" | grep -q "db_path"; then
    print_status "Database path endpoint OK"
    echo "   Database: $(echo "$DB_PATH_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['db_path'])")"
else
    print_error "Database path endpoint failed"
fi

# Test invoice endpoint
echo "   Testing invoice endpoint..."
INVOICE_RESPONSE=$(curl -s http://localhost:8000/api/invoices/inv_seed_001)
if echo "$INVOICE_RESPONSE" | grep -q "inv_seed_001"; then
    print_status "Invoice endpoint OK"
    echo "   Invoice ID: $(echo "$INVOICE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")"
    echo "   Total: $(echo "$INVOICE_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"£{data['meta']['total_inc']}\")")"
else
    print_error "Invoice endpoint failed"
    echo "   Response: $INVOICE_RESPONSE"
fi

# Test debug raw endpoint
echo "   Testing debug raw endpoint..."
RAW_RESPONSE=$(curl -s http://localhost:8000/api/invoices/debug/raw/inv_seed_001)
if echo "$RAW_RESPONSE" | grep -q "raw"; then
    print_status "Debug raw endpoint OK"
else
    print_error "Debug raw endpoint failed"
fi

# Cleanup
echo "🧹 Cleaning up..."
kill $SERVER_PID 2>/dev/null || true

echo ""
echo "🎉 Invoice API Pipeline Test Complete!"
echo "======================================"
echo ""
echo "If all tests passed, your invoice API is working correctly!"
echo ""
echo "Next steps:"
echo "1. Test with the React frontend"
echo "2. Add more test data"
echo "3. Test edge cases and error handling"
echo "4. Performance testing with larger datasets" 