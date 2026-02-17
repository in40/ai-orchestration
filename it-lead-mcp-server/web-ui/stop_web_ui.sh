#!/bin/bash

# Script to stop the MCP Agent Web UI
# Usage: ./stop_web_ui.sh

echo "Stopping MCP Agent Web UI..."

# Find and kill the backend and frontend processes
pkill -f "uvicorn main:app" 2>/dev/null
pkill -f "npm run dev" 2>/dev/null
pkill -f "node.*vite" 2>/dev/null

echo "MCP Agent Web UI stopped successfully!"