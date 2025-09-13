# OWLIN - Production Deployment Guide

Complete production deployment guide for Windows (NSSM), Linux (systemd), and Docker.

## 🚀 Quick Start

### Windows (One-Click)
```powershell
# Run as Administrator
.\scripts\windows_service_setup.ps1
```

### Linux (One-Click)
```bash
# Run as root
sudo ./scripts/linux_service_setup.sh
```

### Docker (One-Click)
```bash
# Complete stack with Ollama
docker-compose up -d
```

---

## 📋 Prerequisites

### Windows
- Windows 10/11 or Windows Server 2019+
- PowerShell 5.1+
- Python 3.11+
- Node.js 18+ (for UI build)
- NSSM (Non-Sucking Service Manager)

### Linux
- Ubuntu 20.04+ / CentOS 8+ / RHEL 8+
- Python 3.11+
- Node.js 18+ (for UI build)
- systemd

### Docker
- Docker 20.10+
- Docker Compose 2.0+

---

## 🪟 Windows Deployment (NSSM)

### 1. Download NSSM
```powershell
# Download from https://nssm.cc/download
# Extract nssm.exe to C:\Owlin\tools\nssm.exe
```

### 2. Install Service
```powershell
# Run as Administrator
.\scripts\windows_service_setup.ps1
```

### 3. Management Commands
```powershell
# Start/Stop/Status
Start-Service Owlin
Stop-Service Owlin
Get-Service Owlin

# View logs
Get-Content C:\Owlin\logs\owlin.out.log -Tail 20
Get-Content C:\Owlin\logs\owlin.err.log -Tail 20

# Restart service
Restart-Service Owlin
```

### 4. Update Application
```powershell
Stop-Service Owlin
# Copy new files to C:\Owlin
Start-Service Owlin
```

---

## 🐧 Linux Deployment (systemd)

### 1. Install Service
```bash
# Run as root
sudo ./scripts/linux_service_setup.sh
```

### 2. Management Commands
```bash
# Start/Stop/Status
sudo systemctl start owlin
sudo systemctl stop owlin
sudo systemctl status owlin

# View logs
sudo journalctl -u owlin -f
sudo journalctl -u owlin --since "1 hour ago"

# Restart service
sudo systemctl restart owlin
```

### 3. Update Application
```bash
sudo systemctl stop owlin
sudo rsync -a ./ /opt/owlin/
sudo chown -R owlin:owlin /opt/owlin
sudo -u owlin bash -c 'cd /opt/owlin; . .venv/bin/activate; pip install -r requirements.txt; npm ci; npm run build'
sudo systemctl start owlin
```

---

## 🐳 Docker Deployment

### 1. Build and Run
```bash
# Build image
docker build -t owlin:latest .

# Run with Ollama
docker-compose up -d

# Or run standalone
docker run -d \
  --name owlin \
  -p 8001:8001 \
  -e OWLIN_PORT=8001 \
  -e LLM_BASE=http://host.docker.internal:11434 \
  -v owlin_data:/app/data \
  owlin:latest
```

### 2. Management Commands
```bash
# View logs
docker logs owlin-app -f
docker logs owlin-ollama -f

# Restart services
docker-compose restart

# Stop services
docker-compose down

# Update and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## 🔧 Configuration

### Environment Variables
```bash
OWLIN_PORT=8001                    # Port to run on
LLM_BASE=http://127.0.0.1:11434   # Ollama URL
OWLIN_DB_URL=sqlite:///./owlin.db # Database URL
PYTHONUNBUFFERED=1                 # Python logging
```

### Firewall Rules

#### Windows
```powershell
New-NetFirewallRule -DisplayName "Owlin 8001" -Direction Inbound -Protocol TCP -LocalPort 8001 -Action Allow
```

#### Linux
```bash
sudo ufw allow 8001/tcp
# or
sudo firewall-cmd --permanent --add-port=8001/tcp
sudo firewall-cmd --reload
```

---

## 🔍 Health Checks

### Quick Verification
```bash
# Windows (PowerShell)
irm http://127.0.0.1:8001/api/health | % Content
irm http://127.0.0.1:8001/api/status | % Content

# Linux
curl -fsS http://127.0.0.1:8001/api/health
curl -fsS http://127.0.0.1:8001/api/status

# Docker
docker exec owlin-app curl -fsS http://localhost:8001/api/health
```

### Expected Responses
- **Health:** `{"ok":true}`
- **Status:** `{"ok":true,"api_mounted":true,"api_error":null,"message":"Single-port Owlin running successfully"}`

---

## 🛠️ Troubleshooting

### Common Issues

#### "Unexpected token '<'" Error
- **Cause:** Route order issue, catch-all intercepting API
- **Fix:** Ensure `/api/*` routes are defined before catch-all
- **Verify:** Check `backend/final_single_port.py` route order

#### "Module not found" Error
- **Cause:** PYTHONPATH not set or wrong working directory
- **Fix:** Ensure service runs from repo root with correct PYTHONPATH
- **Verify:** Check service WorkingDirectory and environment

#### Port Already in Use
- **Cause:** Another process using port 8001
- **Fix:** Change port or kill existing process
- **Windows:** `netstat -ano | findstr :8001`
- **Linux:** `sudo lsof -i :8001`

#### Service Won't Start
- **Check logs:** Windows (Event Viewer) or Linux (`journalctl -u owlin`)
- **Verify files:** Ensure all required files exist
- **Check permissions:** Ensure service user has access
- **Test manually:** Run `python -m backend.final_single_port` directly

### Log Locations

#### Windows
- **Service logs:** `C:\Owlin\logs\owlin.out.log`
- **Error logs:** `C:\Owlin\logs\owlin.err.log`
- **Event logs:** Event Viewer → Windows Logs → Application

#### Linux
- **Service logs:** `journalctl -u owlin -f`
- **File logs:** `/var/log/owlin/owlin.out.log`

#### Docker
- **Container logs:** `docker logs owlin-app -f`
- **Ollama logs:** `docker logs owlin-ollama -f`

---

## 🔄 Updates and Maintenance

### Windows Update Process
1. Stop service: `Stop-Service Owlin`
2. Backup current installation
3. Copy new files to `C:\Owlin`
4. Rebuild UI if needed: `npm run build`
5. Start service: `Start-Service Owlin`

### Linux Update Process
1. Stop service: `sudo systemctl stop owlin`
2. Backup current installation
3. Copy new files: `sudo rsync -a ./ /opt/owlin/`
4. Update dependencies: `sudo -u owlin bash -c 'cd /opt/owlin; . .venv/bin/activate; pip install -r requirements.txt'`
5. Rebuild UI: `sudo -u owlin bash -c 'cd /opt/owlin; npm ci; npm run build'`
6. Start service: `sudo systemctl start owlin`

### Docker Update Process
1. Stop containers: `docker-compose down`
2. Build new image: `docker-compose build --no-cache`
3. Start containers: `docker-compose up -d`

---

## 📊 Monitoring

### Health Check Endpoints
- **Health:** `GET /api/health` - Basic health check
- **Status:** `GET /api/status` - Detailed status with API mount info
- **Deep Health:** `GET /api/healthz?deep=true` - Comprehensive health check

### Monitoring Scripts
```bash
# Simple health check script
#!/bin/bash
if curl -fsS http://127.0.0.1:8001/api/health >/dev/null; then
    echo "✅ Owlin is healthy"
else
    echo "❌ Owlin is down"
    exit 1
fi
```

---

## 🔒 Security Considerations

### Production Security
- Run service as non-root user (Linux)
- Use firewall rules to restrict access
- Enable HTTPS with reverse proxy (nginx/Apache)
- Regular security updates
- Monitor logs for suspicious activity

### Database Security
- Use absolute paths for database file
- Set proper file permissions
- Consider encrypted database for sensitive data
- Regular backups

---

## 📈 Performance Tuning

### Python Optimizations
- Use virtual environment
- Set `PYTHONUNBUFFERED=1`
- Consider using gunicorn for production
- Monitor memory usage

### Database Optimizations
- Regular VACUUM for SQLite
- Consider PostgreSQL for high-load scenarios
- Monitor database file size

### System Resources
- Monitor CPU and memory usage
- Set appropriate restart policies
- Consider resource limits in Docker

---

## 🆘 Support

### Quick Diagnostics
```bash
# Check service status
systemctl status owlin  # Linux
Get-Service Owlin       # Windows

# Check logs
journalctl -u owlin -f  # Linux
Get-Content C:\Owlin\logs\owlin.out.log -Tail 20  # Windows

# Test connectivity
curl -v http://127.0.0.1:8001/api/health
```

### Emergency Recovery
1. Stop service
2. Check logs for errors
3. Verify file permissions
4. Test manual startup
5. Restart service

---

**🎉 You're now ready for production deployment!** Choose your preferred method and follow the steps above for a robust, production-ready Owlin installation.
