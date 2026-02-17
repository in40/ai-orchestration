#!/bin/bash

# Script to stop the complete MCP system (IT Lead server and Web UI)
# Usage: ./stop_system.sh

echo "Stopping MCP System (IT Lead Server + Web UI)..."

# Terminate processes associated with the IT Lead server
echo "Stopping IT Lead Server..."
pkill -f "it_lead_mcp_server.server" 2>/dev/null || true
pkill -f "python.*server.py" 2>/dev/null || true

# Terminate processes associated with the Web UI
echo "Stopping Web UI Backend..."
pkill -f "uvicorn" 2>/dev/null || true

echo "Stopping Web UI Frontend..."
pkill -f "npm run dev" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true

# Also try to stop any processes on the known ports
echo "Terminating any remaining processes on ports 3061, 8000, 5173..."
if command -v lsof >/dev/null 2>&1; then
  lsof -ti:3061 | xargs -r kill -TERM 2>/dev/null || true
  lsof -ti:8000 | xargs -r kill -TERM 2>/dev/null || true
  lsof -ti:5173 | xargs -r kill -TERM 2>/dev/null || true
  # Force kill if still running
  lsof -ti:3061 | xargs -r kill -KILL 2>/dev/null || true
  lsof -ti:8000 | xargs -r kill -KILL 2>/dev/null || true
  lsof -ti:5173 | xargs -r kill -KILL 2>/dev/null || true
elif command -v netstat >/dev/null 2>&1; then
  netstat -tulpn 2>/dev/null | grep ":3061 " | awk '{print $7}' | cut -d'/' -f1 | xargs -r kill -TERM 2>/dev/null || true
  netstat -tulpn 2>/dev/null | grep ":8000 " | awk '{print $7}' | cut -d'/' -f1 | xargs -r kill -TERM 2>/dev/null || true
  netstat -tulpn 2>/dev/null | grep ":5173 " | awk '{print $7}' | cut -d'/' -f1 | xargs -r kill -TERM 2>/dev/null || true
  # Force kill if still running
  netstat -tulpn 2>/dev/null | grep ":3061 " | awk '{print $7}' | cut -d'/' -f1 | xargs -r kill -KILL 2>/dev/null || true
  netstat -tulpn 2>/dev/null | grep ":8000 " | awk '{print $7}' | cut -d'/' -f1 | xargs -r kill -KILL 2>/dev/null || true
  netstat -tulpn 2>/dev/null | grep ":5173 " | awk '{print $7}' | cut -d'/' -f1 | xargs -r kill -KILL 2>/dev/null || true
fi

# Use the individual stop scripts as well
echo "Using individual stop scripts..."
cd /root/qwen/base/it-lead-mcp-server
./stop_it_lead_server.sh 2>/dev/null || true
./stop_ui.sh 2>/dev/null || true

echo "MCP System has been stopped."