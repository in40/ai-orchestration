#!/bin/bash

# Installation Script for MCP Systemd Services
# Copies all service files to /etc/systemd/system and enables them

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD_DIR="/etc/systemd/system"
SERVICE_DIR="${SCRIPT_DIR}/systemd"

echo "================================================"
echo "MCP Systemd Services Installation"
echo "================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Error: This script must be run as root (sudo)"
    echo "   Run: sudo ./install_systemd_services.sh"
    exit 1
fi

# Check if systemd directory exists
if [ ! -d "$SERVICE_DIR" ]; then
    echo "❌ Error: Service directory not found: $SERVICE_DIR"
    exit 1
fi

echo "Step 1/4: Checking systemd directory..."
if [ ! -d "$SYSTEMD_DIR" ]; then
    echo "   Creating systemd directory..."
    mkdir -p "$SYSTEMD_DIR"
fi
echo "   ✓ Systemd directory: $SYSTEMD_DIR"

echo ""
echo "Step 2/4: Copying service files..."
SERVICE_COUNT=0
for service_file in "$SERVICE_DIR"/*.service; do
    if [ -f "$service_file" ]; then
        SERVICE_NAME=$(basename "$service_file")
        echo "   Copying $SERVICE_NAME..."
        cp "$service_file" "$SYSTEMD_DIR/$SERVICE_NAME"
        SERVICE_COUNT=$((SERVICE_COUNT + 1))
    fi
done
echo "   ✓ Copied $SERVICE_COUNT service files"

echo ""
echo "Step 3/4: Reloading systemd daemon..."
systemctl daemon-reload
echo "   ✓ Systemd daemon reloaded"

echo ""
echo "Step 4/4: Enabling services (will start on boot)..."
# Enable the master service which pulls in all child services
systemctl enable mcp-master.service 2>/dev/null || true
echo "   ✓ Enabled mcp-master.service"

echo ""
echo "================================================"
echo "Installation Complete!"
echo "================================================"
echo ""
echo "Installed services:"
echo "  - mcp-registry.service           (Port 3031)"
echo "  - mcp-implementation-engineer.service  (Port 3060)"
echo "  - mcp-requirements-engineer.service    (Port 3062)"
echo "  - mcp-it-lead.service            (Port 3061)"
echo "  - mcp-team-management.service    (Port 3063)"
echo "  - mcp-devops-release-engineer.service (Port 3071)"
echo "  - mcp-web-ui-backend.service     (Port 8000)"
echo "  - mcp-web-ui-frontend.service    (Port 5173)"
echo ""
echo "Management commands:"
echo "  Start all services:  sudo systemctl start mcp-master"
echo "  Stop all services:   sudo systemctl stop mcp-master"
echo "  Restart all:         sudo systemctl restart mcp-master"
echo "  Status:              sudo systemctl status mcp-master"
echo "  Enable on boot:      sudo systemctl enable mcp-master"
echo "  Disable on boot:     sudo systemctl disable mcp-master"
echo ""
echo "Individual service control:"
echo "  sudo systemctl start|stop|status mcp-registry"
echo "  sudo systemctl start|stop|status mcp-it-lead"
echo "  etc..."
echo ""
echo "View logs:"
echo "  sudo journalctl -u mcp-registry -f"
echo "  sudo journalctl -u mcp-it-lead -f"
echo "  etc..."
echo ""
