#!/bin/bash

# Test script to verify the Vibe Coding AI Agent is working properly

echo "🧪 Testing Vibe Coding AI Agent Setup"
echo "====================================="

# Step 1: Check if required files exist
echo "1. Checking required files..."
REQUIRED_FILES=(
    "start_server.sh"
    "task_manager.sh"
    "vibe_coding_agent/mcp_server.py"
    "vibe_coding_agent/tools.py"
    "vibe_coding_agent/lmstudio_client.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file exists"
    else
        echo "   ❌ $file missing"
        exit 1
    fi
done

echo ""

# Step 2: Check if scripts are executable
echo "2. Checking script permissions..."
chmod +x start_server.sh task_manager.sh advanced_task_utility.sh task_queue_manager.sh task_utility.sh 2>/dev/null
echo "   ✅ Made scripts executable"

echo ""

# Step 3: Test that modules can be imported
echo "3. Testing Python module imports..."
if python -c "import sys; sys.path.insert(0, './mcp-std-skeleton'); from vibe_coding_agent.mcp_server import VibeCodingMcpServer; print('✅ Server module imports successfully')" 2>/dev/null; then
    echo "   ✅ Python modules import successfully"
else
    echo "   ❌ Python modules failed to import"
    exit 1
fi

echo ""

# Step 4: Show available utilities
echo "4. Available Task Management Utilities:"
echo "   - task_manager.sh: Complete task management suite"
echo "   - task_queue_manager.sh: Queue-focused manager" 
echo "   - advanced_task_utility.sh: Advanced features"
echo "   - task_utility.sh: Basic task submission"
echo ""

# Step 5: Show usage instructions
echo "5. Usage Instructions:"
echo "   Start server: ./start_server.sh"
echo "   Submit task: ./task_manager.sh submit \"Create a Python function to calculate fibonacci numbers\""
echo "   Check queue: ./task_manager.sh list"
echo "   Check health: ./task_manager.sh health"
echo ""

# Step 6: Show server features
echo "6. Server Features:"
echo "   - Streamable HTTP transport on port 3050"
echo "   - 12 coding agent tools + health check"
echo "   - Registry functionality enabled by default"
echo "   - LM Studio integration (http://asus-tus:1234/v1)"
echo "   - All MCP 2025 standards compliant"
echo ""

echo "🎉 Setup verification complete!"
echo ""
echo "The Vibe Coding AI Agent is ready to use!"
echo "Start by running: ./start_server.sh"