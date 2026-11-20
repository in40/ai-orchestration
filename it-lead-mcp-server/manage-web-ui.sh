#!/bin/bash
# Web UI Management Script (systemd-based)
# Usage: ./manage-web-ui.sh {start|stop|restart|status|logs}

set -e

SERVICE_BACKEND="mcp-web-ui-backend.service"
SERVICE_WATCHDOG="mcp-web-ui-watchdog.service"
FRONTEND_DIR="/root/qwen/base/it-lead-mcp-server/web-ui/frontend"

case "$1" in
  start)
    echo "Starting Web UI..."
    systemctl start $SERVICE_BACKEND $SERVICE_WATCHDOG
    sleep 3
    echo "✅ Backend: $(systemctl is-active $SERVICE_BACKEND)"
    echo "✅ Watchdog: $(systemctl is-active $SERVICE_WATCHDOG)"
    echo "   Backend: http://192.168.51.215:8000"
    echo "   Frontend: http://192.168.51.215:5173"
    ;;
  stop)
    echo "Stopping Web UI..."
    systemctl stop $SERVICE_BACKEND $SERVICE_WATCHDOG
    echo "✅ Services stopped"
    ;;
  restart)
    echo "Restarting Web UI..."
    systemctl restart $SERVICE_BACKEND $SERVICE_WATCHDOG
    sleep 3
    echo "✅ Restarted"
    ;;
  status)
    echo "=== Web UI Status ==="
    systemctl status $SERVICE_BACKEND --no-pager
    echo ""
    systemctl status $SERVICE_WATCHDOG --no-pager
    echo ""
    echo "=== Port Status ==="
    ss -tlnp | grep -E ":(8000|5173)"
    ;;
  logs)
    echo "=== Backend Logs (last 50 lines) ==="
    tail -50 /tmp/web_ui_backend.log
    echo ""
    echo "=== Watchdog Logs ==="
    cat /tmp/web_ui_watchdog.log 2>/dev/null || echo "No watchdog log yet"
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|logs}"
    exit 1
    ;;
esac
