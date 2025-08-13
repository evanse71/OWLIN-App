# 🎯 Owlin React Application

A modern React/Next.js frontend for the Owlin invoice processing system, featuring real-time data integration, interactive dashboards, and comprehensive supplier analytics.

## 🚀 Features

### 📊 **Enhanced Dashboard**
- **Real-time Metrics**: Live system statistics from backend API
- **Recent Activity**: Last 7 days of invoice processing activity
- **Top Suppliers**: Performance overview of leading suppliers
- **Success Rate Tracking**: System-wide processing success metrics
- **Interactive Cards**: Clickable navigation to all major sections

### 📄 **Invoice Management**
- **File Upload**: Drag-and-drop interface for invoices and delivery notes
- **Real-time Processing**: Live status updates during OCR processing
- **Smart Pairing**: Automatic matching of invoices with delivery notes
- **Issue Detection**: Flagged discrepancies and quality issues
- **Detailed View**: Comprehensive invoice information with line items

### ⚠️ **Flagged Issues Management**
- **Issue Summary**: Overview of all flagged discrepancies
- **Supplier Breakdown**: Issues categorized by supplier
- **Action Buttons**: Resolve or escalate issues directly
- **Real-time Updates**: Live status changes and issue resolution
- **Detailed Context**: Full invoice and item information for each issue

### 🏢 **Supplier Analytics**
- **Performance Metrics**: Comprehensive supplier performance data
- **Mismatch Rate Tracking**: Quality and accuracy metrics
- **Value Analysis**: Total spend and average invoice values
- **Trend Analysis**: Historical performance over time
- **Top Suppliers**: Ranking by value and performance

### ⚙️ **System Settings**
- **User Management**: Role-based access control
- **Venue Configuration**: Multi-venue support
- **System Preferences**: Customizable settings
- **API Configuration**: Backend connection settings

## 🏗️ Architecture

### **Frontend (React/Next.js)**
- **TypeScript**: Full type safety and better development experience
- **Tailwind CSS**: Modern, responsive styling
- **Component-based**: Modular, reusable components
- **API Integration**: Real-time data from FastAPI backend
- **Responsive Design**: Mobile and desktop optimized

### **Backend (FastAPI)**
- **RESTful API**: Clean, documented endpoints
- **Database Integration**: SQLite with comprehensive queries
- **Real-time Processing**: Live data updates
- **Error Handling**: Robust error management
- **CORS Support**: Cross-origin resource sharing

### **Data Flow**
```
React Frontend ↔ FastAPI Backend ↔ SQLite Database
     ↓              ↓              ↓
UI Components   Business Logic   Data Storage
```

## 🛠️ Installation & Setup

### **Prerequisites**
- Node.js 18+ and npm
- Python 3.8+ with pip
- Git

### **1. Clone and Setup**
```bash
git clone <repository-url>
cd owlin-app
```

### **2. Install Dependencies**
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies
npm install
```

### **3. Database Setup**
```bash
# Create sample data (optional)
python create_sample_data.py
```

### **4. Start Servers**

#### **Option A: Automatic (Recommended)**
```bash
python start_servers.py
```

#### **Option B: Manual**
```bash
# Terminal 1: Start backend
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Start frontend
npm run dev
```

### **5. Access the Application**
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 📱 Usage Guide

### **Dashboard Overview**
1. **System Metrics**: View total invoices, value, and success rates
2. **Recent Activity**: Monitor daily processing activity
3. **Quick Actions**: Navigate to key features
4. **Top Suppliers**: See leading supplier performance

### **Invoice Processing**
1. **Upload Files**: Drag and drop invoices and delivery notes
2. **Monitor Processing**: Watch real-time OCR processing
3. **Review Results**: Check for discrepancies and issues
4. **Pair Documents**: Match invoices with delivery notes

### **Issue Management**
1. **View Flagged Issues**: See all detected discrepancies
2. **Analyze Patterns**: Identify supplier-specific issues
3. **Take Action**: Resolve or escalate issues
4. **Track Progress**: Monitor resolution status

### **Supplier Analytics**
1. **Performance Overview**: View supplier metrics
2. **Quality Analysis**: Check mismatch rates and trends
3. **Value Tracking**: Monitor spend and efficiency
4. **Comparative Analysis**: Compare supplier performance

## 🔧 API Endpoints

### **Analytics**
- `GET /api/analytics/dashboard` - Dashboard metrics
- `GET /api/analytics/trends` - Historical trends
- `GET /api/analytics/performance` - System performance
- `GET /api/analytics/health` - System health status

### **Invoices**
- `GET /api/invoices/` - List all invoices
- `GET /api/invoices/summary` - Invoice summary metrics
- `GET /api/invoices/{id}` - Invoice details
- `POST /api/invoices/{id}/pair` - Pair with delivery note
- `DELETE /api/invoices/{id}` - Delete invoice

### **Flagged Issues**
- `GET /api/flagged-issues/` - List flagged issues
- `GET /api/flagged-issues/summary` - Issue summary
- `POST /api/flagged-issues/{id}/resolve` - Resolve issue
- `POST /api/flagged-issues/{id}/escalate` - Escalate issue

### **Suppliers**
- `GET /api/suppliers/` - List suppliers
- `GET /api/suppliers/analytics` - Supplier analytics
- `GET /api/suppliers/{name}` - Supplier details
- `GET /api/suppliers/{name}/performance` - Performance metrics

### **File Upload**
- `POST /api/upload/invoice` - Upload invoice files
- `POST /api/upload/delivery` - Upload delivery note files

## 🎨 UI Components

### **Layout Components**
- `Layout.tsx` - Main application layout with navigation
- `NavBar.tsx` - Top navigation bar with active page highlighting

### **Page Components**
- `pages/index.tsx` - Dashboard with metrics and quick actions
- `pages/invoices.tsx` - Invoice upload and management
- `pages/flagged.tsx` - Flagged issues management
- `pages/suppliers.tsx` - Supplier analytics and performance
- `pages/notes.tsx` - Staff notes and communications
- `pages/settings.tsx` - System settings and configuration

### **Feature Components**
- `components/invoices/InvoicesUploadPanel.tsx` - File upload interface
- Custom components for metrics, tables, and interactive elements

## 🔒 Security & Performance

### **Security Features**
- **CORS Configuration**: Proper cross-origin handling
- **Input Validation**: Server-side validation of all inputs
- **Error Handling**: Secure error messages without data leakage
- **File Upload Security**: Type and size validation

### **Performance Optimizations**
- **Lazy Loading**: Components load on demand
- **API Caching**: Efficient data fetching
- **Responsive Design**: Optimized for all screen sizes
- **Real-time Updates**: Minimal API calls with smart refresh

## 🧪 Testing

### **Backend Testing**
```bash
# Run backend tests
python -m pytest tests/

# Test specific modules
python -m pytest tests/test_invoices.py
python -m pytest tests/test_suppliers.py
```

### **Frontend Testing**
```bash
# Run frontend tests
npm test

# Run with coverage
npm run test:coverage
```

## 🚀 Deployment

### **Development**
```bash
# Start development servers
python start_servers.py
```

### **Production**
```bash
# Build frontend
npm run build

# Start production servers
npm start
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## 📊 Monitoring & Analytics

### **System Health**
- **API Health Checks**: `/api/analytics/health`
- **Performance Metrics**: Processing times and success rates
- **Error Tracking**: Comprehensive error logging
- **Usage Analytics**: User activity and feature usage

### **Business Intelligence**
- **Supplier Performance**: Quality metrics and trends
- **Processing Efficiency**: Success rates and bottlenecks
- **Cost Analysis**: Invoice value tracking and analysis
- **Issue Patterns**: Discrepancy identification and resolution

## 🔄 Migration from Streamlit

### **Completed Features**
- ✅ **Dashboard**: Enhanced with real-time data
- ✅ **Invoice Upload**: Modern drag-and-drop interface
- ✅ **Issue Management**: Interactive flagged issues handling
- ✅ **Supplier Analytics**: Comprehensive performance tracking
- ✅ **API Integration**: Full backend connectivity

### **Benefits of React Migration**
- **Better Performance**: Faster loading and interactions
- **Enhanced UX**: Modern, responsive interface
- **Real-time Updates**: Live data without page refreshes
- **Scalability**: Better architecture for growth
- **Maintainability**: Cleaner code structure

## 🤝 Contributing

### **Development Workflow**
1. **Feature Branch**: Create branch for new features
2. **Code Review**: Submit pull requests for review
3. **Testing**: Ensure all tests pass
4. **Documentation**: Update relevant documentation

### **Code Standards**
- **TypeScript**: Full type safety required
- **ESLint**: Code quality and consistency
- **Prettier**: Code formatting
- **Component Structure**: Modular, reusable components

## 📞 Support

### **Documentation**
- **API Docs**: http://localhost:8000/docs
- **Component Library**: Inline documentation
- **Code Comments**: Comprehensive inline documentation

### **Troubleshooting**
- **Backend Issues**: Check FastAPI logs
- **Frontend Issues**: Check browser console
- **Database Issues**: Verify SQLite file permissions
- **Network Issues**: Check CORS configuration

---

**🎉 The Owlin React Application is now fully functional with comprehensive features, real-time data integration, and a modern user interface!** 