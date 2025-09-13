#!/bin/bash
# OWLIN - Linux Service Setup (systemd)
# Installs Owlin as a systemd service
# Run as root or with sudo

set -e

# Configuration
SERVICE_NAME="owlin"
INSTALL_PATH="/opt/owlin"
SERVICE_USER="owlin"
PORT="8001"
LLM_BASE="http://127.0.0.1:11434"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

function info() { echo -e "${BLUE}•${NC} $1"; }
function ok() { echo -e "${GREEN}✅${NC} $1"; }
function fail() { echo -e "${RED}❌${NC} $1"; }
function warn() { echo -e "${YELLOW}⚠️${NC} $1"; }

echo -e "${CYAN}🚀 OWLIN - Linux Service Setup${NC}"
echo -e "${CYAN}===============================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    fail "This script must be run as root or with sudo"
    echo "Usage: sudo $0"
    exit 1
fi

# Check if systemd is available
if ! command -v systemctl &> /dev/null; then
    fail "systemd is not available on this system"
    exit 1
fi

# Check if Python 3.11+ is available
if ! command -v python3.11 &> /dev/null; then
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        warn "Using python3 (python3.11 not found)"
    else
        fail "Python 3.11+ is required but not found"
        exit 1
    fi
else
    PYTHON_CMD="python3.11"
fi

ok "Using Python: $PYTHON_CMD"

# Create service user if it doesn't exist
if ! id "$SERVICE_USER" &>/dev/null; then
    info "Creating service user: $SERVICE_USER"
    useradd -r -s /bin/false "$SERVICE_USER"
    ok "Service user created"
else
    info "Service user already exists: $SERVICE_USER"
fi

# Create directories
info "Creating directories..."
mkdir -p "$INSTALL_PATH" "/var/log/$SERVICE_NAME" "/etc/$SERVICE_NAME"
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_PATH" "/var/log/$SERVICE_NAME" "/etc/$SERVICE_NAME"
ok "Directories created and permissions set"

# Check if source files exist
if [ ! -f "backend/final_single_port.py" ]; then
    fail "backend/final_single_port.py not found"
    echo "Please run this script from the Owlin repository root"
    exit 1
fi

# Copy files to install path
info "Copying files to $INSTALL_PATH..."
rsync -a --exclude='.git' --exclude='node_modules' --exclude='.venv' ./ "$INSTALL_PATH/"
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_PATH"
ok "Files copied"

# Create virtual environment and install dependencies
info "Setting up Python virtual environment..."
sudo -u "$SERVICE_USER" bash -c "
    cd '$INSTALL_PATH'
    $PYTHON_CMD -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
"
ok "Python dependencies installed"

# Install Node.js dependencies and build UI
if command -v npm &> /dev/null; then
    info "Building UI..."
    sudo -u "$SERVICE_USER" bash -c "
        cd '$INSTALL_PATH'
        npm ci
        npm run build
    "
    ok "UI built successfully"
else
    warn "npm not found, skipping UI build (will use JSON fallback)"
fi

# Create environment file
info "Creating environment file..."
cat > "/etc/$SERVICE_NAME/owlin.env" << EOF
OWLIN_PORT=$PORT
LLM_BASE=$LLM_BASE
OWLIN_DB_URL=sqlite:///$INSTALL_PATH/owlin.db
PYTHONUNBUFFERED=1
EOF
chown "$SERVICE_USER:$SERVICE_USER" "/etc/$SERVICE_NAME/owlin.env"
ok "Environment file created: /etc/$SERVICE_NAME/owlin.env"

# Create systemd service file
info "Creating systemd service file..."
cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF
[Unit]
Description=Owlin Single-Port Service
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_PATH
EnvironmentFile=/etc/$SERVICE_NAME/owlin.env
ExecStart=$INSTALL_PATH/.venv/bin/python -m backend.final_single_port
Restart=always
RestartSec=3
StandardOutput=append:/var/log/$SERVICE_NAME/owlin.out.log
StandardError=append:/var/log/$SERVICE_NAME/owlin.err.log

[Install]
WantedBy=multi-user.target
EOF
ok "Systemd service file created"

# Reload systemd and enable service
info "Reloading systemd and enabling service..."
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
ok "Service enabled"

# Start service
info "Starting service..."
systemctl start "$SERVICE_NAME"
sleep 3

# Check service status
if systemctl is-active --quiet "$SERVICE_NAME"; then
    ok "Service started successfully"
else
    fail "Service failed to start"
    echo "Service status:"
    systemctl status "$SERVICE_NAME" --no-pager
    echo ""
    echo "Error logs:"
    tail -20 "/var/log/$SERVICE_NAME/owlin.err.log" 2>/dev/null || echo "No error logs found"
    exit 1
fi

# Wait for health check
info "Waiting for service to become healthy..."
BASE_URL="http://127.0.0.1:$PORT"
HEALTH_URL="$BASE_URL/api/health"
READY=false

for i in {1..30}; do
    if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then
        READY=true
        break
    fi
    sleep 1
done

if [ "$READY" = true ]; then
    ok "Service is healthy and responding"
else
    warn "Service may not be fully ready yet"
    echo "Check logs: journalctl -u $SERVICE_NAME -f"
fi

# Final verification
echo ""
echo -e "${GREEN}🎉 OWLIN SERVICE INSTALLED SUCCESSFULLY${NC}"
echo -e "${GREEN}=======================================${NC}"
echo ""
ok "Service Name: $SERVICE_NAME"
ok "Install Path: $INSTALL_PATH"
ok "Port: $PORT"
ok "URL: $BASE_URL"
echo ""
echo -e "${CYAN}📋 Management Commands:${NC}"
echo -e "  Start:   systemctl start $SERVICE_NAME${NC}"
echo -e "  Stop:    systemctl stop $SERVICE_NAME${NC}"
echo -e "  Status:  systemctl status $SERVICE_NAME${NC}"
echo -e "  Logs:    journalctl -u $SERVICE_NAME -f${NC}"
echo -e "  Restart: systemctl restart $SERVICE_NAME${NC}"
echo ""
echo -e "${CYAN}🌐 Test URLs:${NC}"
echo -e "  Health:  $HEALTH_URL${NC}"
echo -e "  Status:  $BASE_URL/api/status${NC}"
echo -e "  App:     $BASE_URL${NC}"
echo ""

# Test URLs
echo -e "${YELLOW}🔍 Quick Health Check:${NC}"
if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then
    HEALTH_RESPONSE=$(curl -fsS "$HEALTH_URL" 2>/dev/null)
    echo -e "${GREEN}✅ Health: $HEALTH_RESPONSE${NC}"
else
    echo -e "${RED}❌ Health check failed${NC}"
fi

if curl -fsS "$BASE_URL/api/status" >/dev/null 2>&1; then
    STATUS_RESPONSE=$(curl -fsS "$BASE_URL/api/status" 2>/dev/null)
    echo -e "${GREEN}✅ Status: $STATUS_RESPONSE${NC}"
else
    echo -e "${RED}❌ Status check failed${NC}"
fi

echo ""
echo -e "${GREEN}🚀 Owlin is now running as a systemd service!${NC}"
echo -e "${CYAN}Open $BASE_URL in your browser to access the application.${NC}"
