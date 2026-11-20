#!/bin/bash
# Web UI Backend Watchdog
# Automatically restarts the Web UI backend if it crashes

WEB_BACKEND_PORT="${WEB_UI_BACKEND_PORT:-8000}"
LOG_FILE="/tmp/web_ui_watchdog.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

log "Watchdog started"

while true; do
    # Check if backend is running
    if ! ss -tlnp 2>/dev/null | grep -q ":${WEB_BACKEND_PORT} "; then
        log "⚠️  Backend not running on port ${WEB_BACKEND_PORT}, restarting..."
        
        # Kill any stale processes
        pkill -9 -f "uvicorn.*main:app.*${WEB_BACKEND_PORT}" 2>/dev/null || true
        sleep 1
        
        # Start backend
        cd /root/qwen/base/it-lead-mcp-server/web-ui/backend
        source venv/bin/activate
        nohup uvicorn main:app --host 0.0.0.0 --port "${WEB_BACKEND_PORT}" >> /tmp/web_ui_backend.log 2>&1 &
        BACKEND_PID=$!
        
        log "✅ Backend restarted with PID ${BACKEND_PID}"
        
        # Wait and verify
        sleep 3
        if ! ps -p $BACKEND_PID > /dev/null 2>&1; then
            log "❌ Backend failed to start!"
        fi
    fi
    
    # Check every 30 seconds
    sleep 30
done
