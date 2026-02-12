#!/bin/bash
# Script to restart the AI Coding Agent Server with the fix applied

echo "🔄 Stopping existing AI Coding Agent Server..."
pkill -f "ai_coding_agent_server" || true

sleep 2

echo "🚀 Starting AI Coding Agent Server..."
cd /root/qwen/base/mcp-coder/mcp_ai_coding_agent
python ai_coding_agent_server.py --port 3050 &

echo "AI Coding Agent Server started on port 3050"
echo "PID: $!"

sleep 3

# Check if the server is running
if pgrep -f "ai_coding_agent_server" > /dev/null; then
    echo "✅ Server is running successfully"
else
    echo "❌ Server failed to start"
fi