#!/bin/bash
# Final integration test for the AI Coding Agent Client and Server

echo "🧪 Running final integration test..."

# Step 1: Make sure no servers are running
echo "🧹 Cleaning up any existing processes..."
./stop_ai_coding_agent.sh

# Step 2: Start mock LLM server
echo "🚀 Starting mock LLM server..."
source ../mcp_ai_agent_env/bin/activate && python mock_llm_server.py 1234 &
MOCK_PID=$!

# Give it a moment to start
sleep 2

# Step 3: Start AI Coding Agent server with mock LLM
echo "🚀 Starting AI Coding Agent server with mock LLM..."
LLM_BASE_URL=http://asus-tus:1234/v1 source ../mcp_ai_agent_env/bin/activate && python ai_coding_agent_server.py --port 3050 &
SERVER_PID=$!

# Give it a moment to start
sleep 3

# Step 4: Test the client
echo "💬 Testing client communication..."
RESULT=$(timeout 25 LLM_BASE_URL=http://asus-tus:1234/v1 source ../mcp_ai_agent_env/bin/activate && python ai_coding_agent_client.py --task "create simple 'Hello world' app on python" --timeout 20 2>&1)

if echo "$RESULT" | grep -q "TASK COMPLETED SUCCESSFULLY"; then
    echo "✅ SUCCESS: Client-server communication works perfectly!"
    echo "✅ Async/await fix is working correctly"
    echo "✅ Client receives proper responses from server"
else
    echo "❌ FAILED: Communication test failed"
    echo "Output was:"
    echo "$RESULT"
fi

# Step 5: Clean up
echo "🧹 Cleaning up test processes..."
kill $SERVER_PID $MOCK_PID 2>/dev/null || true
./stop_ai_coding_agent.sh

echo "🏁 Integration test completed!"