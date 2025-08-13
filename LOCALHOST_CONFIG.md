# Localhost Configuration Guide

This guide explains how to configure localhost settings for the Owlin application.

## 🚀 Quick Start

### Default Configuration
- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Start Servers
```bash
python3 start_servers.py
```

## ⚙️ Configuration Options

### 1. Using the Configuration Script

The `update_localhost.py` script provides easy ways to change localhost settings:

#### Set Custom Ports
```bash
# Change frontend to port 3001 and backend to port 8001
python3 update_localhost.py set-ports 3001 8001
```

#### Set Custom Host
```bash
# Change host to 127.0.0.1
python3 update_localhost.py set-host 127.0.0.1
```

#### Reset to Default
```bash
# Reset to default localhost:3000 and localhost:8000
python3 update_localhost.py reset
```

#### Show Current Configuration
```bash
# Display current settings
python3 update_localhost.py show
```

### 2. Manual Configuration

#### Environment Variables (.env.local)
```bash
# Localhost Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_HOST=localhost
NEXT_PUBLIC_PORT=3000

# Backend Configuration
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

# Development Settings
NODE_ENV=development
```

#### Next.js Configuration (next.config.js)
The Next.js configuration includes:
- API URL rewriting
- Environment variable injection
- Development server settings

#### Server Startup (start_servers.py)
The startup script includes:
- Configurable host and port settings
- Port availability checking
- External access support

## 🌐 External Access

### Allow External Connections
The servers are configured to allow external connections:

- **Frontend**: http://0.0.0.0:3000
- **Backend**: http://0.0.0.0:8000

### Network Access
To access from other devices on your network:

1. Find your local IP address:
   ```bash
   # On macOS/Linux
   ifconfig | grep "inet " | grep -v 127.0.0.1
   
   # On Windows
   ipconfig | findstr "IPv4"
   ```

2. Access using your local IP:
   - Frontend: `http://YOUR_IP:3000`
   - Backend: `http://YOUR_IP:8000`

## 🔧 Advanced Configuration

### Custom Port Ranges
If you need to use different port ranges:

```bash
# Use ports in 4000-5000 range
python3 update_localhost.py set-ports 4000 4001
```

### Development vs Production
For production deployment, update the environment variables:

```bash
# Production settings
NEXT_PUBLIC_API_URL=https://your-domain.com/api
NEXT_PUBLIC_HOST=your-domain.com
NODE_ENV=production
```

### Docker Configuration
When running in Docker, ensure proper port mapping:

```bash
docker run -p 3000:3000 -p 8000:8000 owlin-app
```

## 🛠️ Troubleshooting

### Port Already in Use
If you see "port already in use" warnings:

1. Check what's using the port:
   ```bash
   # Check port 3000
   lsof -i :3000
   
   # Check port 8000
   lsof -i :8000
   ```

2. Kill the process or use different ports:
   ```bash
   # Kill process using port 3000
   kill -9 $(lsof -t -i:3000)
   
   # Or use different ports
   python3 update_localhost.py set-ports 3001 8001
   ```

### Connection Refused
If you get connection refused errors:

1. Ensure servers are running:
   ```bash
   python3 start_servers.py
   ```

2. Check firewall settings
3. Verify host binding (0.0.0.0 for external access)

### CORS Issues
If you encounter CORS errors:

1. Check the backend CORS configuration in `backend/main.py`
2. Ensure the frontend is using the correct API URL
3. Verify both servers are running on the expected ports

## 📋 Configuration Files

### Key Files
- `.env.local` - Environment variables
- `next.config.js` - Next.js configuration
- `start_servers.py` - Server startup script
- `update_localhost.py` - Configuration management script

### File Locations
```
OWLIN-App-main/
├── .env.local              # Environment configuration
├── next.config.js          # Next.js settings
├── start_servers.py        # Server startup
├── update_localhost.py     # Configuration script
└── LOCALHOST_CONFIG.md     # This documentation
```

## 🎯 Best Practices

1. **Use the configuration script** for consistent changes
2. **Check port availability** before starting servers
3. **Use environment variables** for flexible configuration
4. **Test external access** if needed for network development
5. **Keep configuration files** in version control (except .env.local)

## 🚀 Quick Commands Reference

```bash
# Start servers with default settings
python3 start_servers.py

# Change to custom ports
python3 update_localhost.py set-ports 3001 8001

# Show current configuration
python3 update_localhost.py show

# Reset to defaults
python3 update_localhost.py reset

# Check if servers are running
curl http://localhost:3000
curl http://localhost:8000/health
``` 