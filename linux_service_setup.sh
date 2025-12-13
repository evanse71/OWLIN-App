#!/bin/bash
# Linux systemd Service Setup for Owlin Single-Port
# Run as root or with sudo

set -euo pipefail

echo "🔧 Setting up Owlin as Linux systemd service..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root or with sudo"
    exit 1
fi

# Get project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_USER="owlin"
SERVICE_GROUP="owlin"
INSTALL_DIR="/opt/owlin"
LOG_DIR="/var/log/owlin"
DATA_DIR="/var/lib/owlin"

echo "📁 Project root: $PROJECT_ROOT"
echo "🏠 Install directory: $INSTALL_DIR"

# Create service user
if ! id "$SERVICE_USER" &>/dev/null; then
    echo "👤 Creating service user: $SERVICE_USER"
    useradd --system --no-create-home --shell /bin/false "$SERVICE_USER"
fi

# Create directories
echo "📁 Creating directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$DATA_DIR"

# Copy application files
echo "📦 Installing application files..."
cp -r "$PROJECT_ROOT"/* "$INSTALL_DIR/"
chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"
chown -R "$SERVICE_USER:$SERVICE_GROUP" "$LOG_DIR"
chown -R "$SERVICE_USER:$SERVICE_GROUP" "$DATA_DIR"

# Set permissions
chmod +x "$INSTALL_DIR/scripts/start_single_port.sh"
chmod +x "$INSTALL_DIR/verify_full_owlin.sh"

# Install systemd service
echo "🔧 Installing systemd service..."
cp "$PROJECT_ROOT/owlin.service" "/etc/systemd/system/owlin.service"

# Update service file with correct paths
sed -i "s|WorkingDirectory=.*|WorkingDirectory=$INSTALL_DIR|g" "/etc/systemd/system/owlin.service"
sed -i "s|ExecStart=.*|ExecStart=/usr/bin/python3 -m backend.final_single_port|g" "/etc/systemd/system/owlin.service"

# Reload systemd
systemctl daemon-reload

# Enable service
systemctl enable owlin.service

# Start service
echo "🚀 Starting Owlin service..."
systemctl start owlin.service

# Wait for service to start
sleep 5

# Check service status
if systemctl is-active --quiet owlin.service; then
    echo "✅ Owlin service is running!"
    echo "🌐 Service URL: http://127.0.0.1:8001"
    echo "📊 Service status: $(systemctl is-active owlin.service)"
else
    echo "❌ Failed to start Owlin service"
    echo "📋 Service logs:"
    journalctl -u owlin.service --no-pager -n 20
    exit 1
fi

echo ""
echo "🔧 Service Management Commands:"
echo "  Start:   sudo systemctl start owlin"
echo "  Stop:    sudo systemctl stop owlin"
echo "  Restart: sudo systemctl restart owlin"
echo "  Status:  sudo systemctl status owlin"
echo "  Logs:    sudo journalctl -u owlin -f"
echo "  Enable:  sudo systemctl enable owlin"
echo "  Disable: sudo systemctl disable owlin"
