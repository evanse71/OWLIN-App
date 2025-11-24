# 🦉 OWLIN Local Environment Launcher

This directory contains launcher scripts to easily start the OWLIN local development environment.

## 🚀 Quick Start

### Option 1: Single Port Mode (Recommended)
```bash
start_owlin.bat
```
- Backend and frontend served from port 8000
- Frontend is built and served as static files
- Best for testing and demos

### Option 2: Split Mode (Development)
```bash
start_owlin_split.bat
```
- Backend on port 8000 (FastAPI)
- Frontend on port 5173 (Vite dev server)
- Best for active development with hot reload

### Option 3: Individual Services
```bash
start_backend_only.bat    # Backend only on port 8000
start_frontend_only.bat   # Frontend only on port 5173
```

### Stop All Services
```bash
stop_owlin.bat
```

## 📋 Prerequisites

1. **Python 3.8+** with pip
2. **Node.js 16+** with npm
3. **Required Python packages** (install with `pip install -r .github/requirements.txt`)

## 🔧 What Each Script Does

### `start_owlin.bat` (Single Port)
1. Kills any existing processes
2. Sets up environment variables
3. Creates necessary directories
4. Builds the frontend (`npm run build`)
5. Starts the backend with static file serving
6. Tests the connection
7. Opens browser to http://127.0.0.1:8000

### `start_owlin_split.bat` (Split Mode)
1. Kills any existing processes
2. Sets up environment variables
3. Creates necessary directories
4. Starts backend on port 8000
5. Starts frontend dev server on port 5173
6. Tests both connections
7. Opens browser to http://127.0.0.1:5173

## 🌐 URLs

### Single Port Mode
- **Main App**: http://127.0.0.1:8000
- **Health Check**: http://127.0.0.1:8000/api/health
- **Upload API**: http://127.0.0.1:8000/api/upload

### Split Mode
- **Frontend**: http://127.0.0.1:5173
- **Backend API**: http://127.0.0.1:8000
- **Health Check**: http://127.0.0.1:8000/api/health

## 🧪 Testing File Uploads

1. Start the environment using one of the launcher scripts
2. Navigate to the Invoices page
3. Upload a PDF invoice or delivery note
4. Check the backend window for OCR processing logs
5. Verify the document appears in the UI

## 🐛 Troubleshooting

### Backend Won't Start
- Check if port 8000 is already in use: `netstat -ano | findstr :8000`
- Kill the process: `taskkill /PID <pid> /F`
- Ensure Python dependencies are installed

### Frontend Won't Start
- Check if port 5173 is already in use: `netstat -ano | findstr :5173`
- Ensure Node.js and npm are installed
- Run `npm install` in the `source_extracted/tmp_lovable` directory

### CORS Errors
- The backend is configured to allow CORS from localhost:3000, localhost:5173, and localhost:8000
- If you're using a different port, you may need to update the CORS configuration

### Upload Directory Issues
- Ensure `data/uploads/` directory exists and is writable
- Check that the backend has permission to create files

## 📁 Directory Structure

```
owlin_backup_2025-10-02_225554/
├── data/                    # Database and uploads
│   ├── owlin.db            # SQLite database
│   ├── uploads/            # Uploaded files
│   └── logs/               # Application logs
├── source_extracted/       # Main application
│   ├── test_backend_simple.py  # FastAPI backend
│   └── tmp_lovable/        # React frontend
│       ├── package.json    # Frontend dependencies
│       └── dist/           # Built frontend (after build)
└── *.bat                   # Launcher scripts
```

## 🔄 Environment Variables

The scripts set these environment variables:

- `OWLIN_ENV=dev` - Development mode
- `OWLIN_DB_PATH` - Path to SQLite database
- `OWLIN_UPLOADS_DIR` - Path to uploads directory
- `OWLIN_DEMO=0` - Demo mode disabled
- `OWLIN_DEFAULT_VENUE=Royal Oak Hotel` - Default venue
- `OWLIN_SINGLE_PORT=1/0` - Single port mode toggle

## 📝 Notes

- The Royal Oak launcher (`source_extracted/Start-RoyalOak-Now.bat`) is preserved for Royal Oak specific deployments
- All launchers ensure the same localhost:8000 port as requested
- The backend includes OCR processing, file upload validation, and document pairing
- The frontend is a modern React app with Vite, TypeScript, and Tailwind CSS
