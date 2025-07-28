#!/bin/bash

echo "🔍 Testing Owlin Localhost Configuration"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to test endpoint
test_endpoint() {
    local url=$1
    local description=$2
    local expected_content=$3
    
    echo -n "Testing $description... "
    
    # Try to get the response
    response=$(curl -s "$url" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        if echo "$response" | grep -q "$expected_content"; then
            echo -e "${GREEN}✅ PASS${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️  RESPONDED BUT NO EXPECTED CONTENT${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ FAIL${NC}"
        return 1
    fi
}

# Test backend endpoints
echo ""
echo "🔧 Backend Tests:"
test_endpoint "http://localhost:8000/" "Backend Root" "Owlin API is running"
test_endpoint "http://localhost:8000/health" "Backend Health" "healthy"
test_endpoint "http://localhost:8000/api/health" "Backend API Health" "ok"

# Test frontend endpoints
echo ""
echo "🌐 Frontend Tests:"
test_endpoint "http://localhost:3000/" "Frontend Root" "Owlin"
test_endpoint "http://localhost:3000/invoices" "Invoice Management Page" "Invoice Management"

# Test API endpoints
echo ""
echo "📡 API Tests:"
test_endpoint "http://localhost:8000/api/invoices" "Invoices API" "invoices"
test_endpoint "http://localhost:8000/api/suppliers" "Suppliers API" "suppliers"

# Test new line item functionality
echo ""
echo "📊 Line Item & VAT Tests:"
test_endpoint "http://localhost:8000/api/upload/review" "Upload Review API" "upload"
test_endpoint "http://localhost:8000/api/dev/clear-documents" "Dev Clear Documents API" "clear"

# Test port availability
echo ""
echo "🔌 Port Tests:"
if lsof -i :8000 >/dev/null 2>&1; then
    echo -e "Port 8000 (Backend): ${GREEN}✅ IN USE${NC}"
else
    echo -e "Port 8000 (Backend): ${RED}❌ NOT IN USE${NC}"
fi

if lsof -i :3000 >/dev/null 2>&1; then
    echo -e "Port 3000 (Frontend): ${GREEN}✅ IN USE${NC}"
else
    echo -e "Port 3000 (Frontend): ${RED}❌ NOT IN USE${NC}"
fi

# Environment check
echo ""
echo "⚙️  Environment Check:"
if [ -f ".env.local" ]; then
    echo -e "Environment file: ${GREEN}✅ EXISTS${NC}"
else
    echo -e "Environment file: ${RED}❌ MISSING${NC}"
fi

# Check for enhanced line item parsing files
echo ""
echo "🔍 Enhanced Line Item Parsing Check:"
if [ -f "backend/ocr/parse_invoice.py" ]; then
    echo -e "Enhanced parse_invoice.py: ${GREEN}✅ EXISTS${NC}"
else
    echo -e "Enhanced parse_invoice.py: ${RED}❌ MISSING${NC}"
fi

if [ -f "components/invoices/InvoiceDetailDrawer.tsx" ]; then
    echo -e "Enhanced InvoiceDetailDrawer: ${GREEN}✅ EXISTS${NC}"
else
    echo -e "Enhanced InvoiceDetailDrawer: ${RED}❌ MISSING${NC}"
fi

if [ -f "components/invoices/InvoiceLineItemTable.tsx" ]; then
    echo -e "InvoiceLineItemTable: ${GREEN}✅ EXISTS${NC}"
else
    echo -e "InvoiceLineItemTable: ${RED}❌ MISSING${NC}"
fi

# Check for test files
echo ""
echo "🧪 Test Files Check:"
if [ -f "test_line_item_parsing.py" ]; then
    echo -e "Line Item Parsing Test: ${GREEN}✅ EXISTS${NC}"
else
    echo -e "Line Item Parsing Test: ${RED}❌ MISSING${NC}"
fi

if [ -f "test_line_item_display.html" ]; then
    echo -e "Line Item Display Test: ${GREEN}✅ EXISTS${NC}"
else
    echo -e "Line Item Display Test: ${RED}❌ MISSING${NC}"
fi

# Summary
echo ""
echo "========================================"
echo "📊 Summary:"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "API Docs: http://localhost:8000/docs"
echo "Invoice Management: http://localhost:3000/invoices"
echo ""
echo -e "${BLUE}🎯 Enhanced Features Available:${NC}"
echo "• Multi-strategy line item parsing"
echo "• Comprehensive VAT calculations"
echo "• Responsive line item display"
echo "• VAT toggle functionality"
echo "• Enhanced detail drawer"
echo "========================================" 