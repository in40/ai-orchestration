#!/bin/bash
# Test script to verify the AI Coding Agent Client

echo "Testing AI Coding Agent Client..."

# Check if the script exists
if [ ! -f "/root/qwen/base/mcp-coder/mcp_ai_coding_agent/ai_coding_agent_client.py" ]; then
    echo "❌ Error: AI Coding Agent Client script not found!"
    exit 1
fi

# Check if the script is executable
if [ -x "/root/qwen/base/mcp-coder/mcp_ai_coding_agent/ai_coding_agent_client.py" ]; then
    echo "✅ Script exists and is executable"
else
    chmod +x /root/qwen/base/mcp-coder/mcp_ai_coding_agent/ai_coding_agent_client.py
    echo "✅ Made script executable"
fi

# Display script info
echo " "
echo "📄 Script content preview:"
head -20 /root/qwen/base/mcp-coder/mcp_ai_coding_agent/ai_coding_agent_client.py

echo " "
echo "✅ AI Coding Agent Client created successfully!"
echo " "
echo "To use the client, run:"
echo "python /root/qwen/base/mcp-coder/mcp_ai_coding_agent/ai_coding_agent_client.py"
echo " "
echo "For help, run:"
echo "python /root/qwen/base/mcp-coder/mcp_ai_coding_agent/ai_coding_agent_client.py --help"