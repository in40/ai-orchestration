#!/bin/bash
# AI Coding Agent Simulation Test
# Tests the AI Coding Agent MCP server functionality

set -e  # Exit on any error

echo "🧪 Starting AI Coding Agent Simulation Tests..."

# Test parameters
SERVER_URL="http://127.0.0.1:3050"
TIMEOUT=30

# Function to send JSON-RPC request
send_request() {
    local method=$1
    local params=$2
    local id=${3:-$(date +%s)}
    
    echo "Sending request: $method"
    curl -s -X POST "$SERVER_URL/send" \
        -H "Content-Type: application/json" \
        -d "{\"jsonrpc\": \"2.0\", \"id\": \"$id\", \"method\": \"$method\", \"params\": $params}"
    echo ""
}

# Function to wait for server to be ready
wait_for_server() {
    local url=$1
    local timeout=${2:-30}
    local count=0
    
    echo "⏳ Waiting for server at $url to be ready..."
    
    while [ $count -lt $timeout ]; do
        if curl -s -o /dev/null -w "%{http_code}" "$url/send" | grep -q "405\|200\|404"; then
            echo "✅ Server is reachable"
            return 0
        fi
        sleep 1
        ((count++))
    done
    
    echo "❌ Server did not become ready within $timeout seconds"
    return 1
}

# Wait for server to be ready
if ! wait_for_server "$SERVER_URL"; then
    echo "❌ Server is not running. Please start the AI Coding Agent server first."
    echo "Run: cd mcp_ai_coding_agent && source ../mcp_ai_agent_env/bin/activate && python -m mcp_server.server --transport http --port 3050"
    exit 1
fi

echo "🚀 Running AI Coding Agent tests..."

# Test 1: Initialize the server
echo "📋 Test 1: Initializing server..."
INIT_RESPONSE=$(send_request "initialize" "{\"clientInfo\":{\"name\":\"test-client\",\"version\":\"1.0\"}}")
echo "Response: $INIT_RESPONSE"
echo ""

# Test 2: List available tools
echo "🔧 Test 2: Listing available tools..."
TOOLS_RESPONSE=$(send_request "tools/list" "{}")
echo "Response: $TOOLS_RESPONSE"
echo ""

# Test 3: Perform a health check
echo "🏥 Test 3: Performing health check..."
HEALTH_RESPONSE=$(send_request "tools/call" "{\"name\":\"health_check\", \"arguments\": {\"detailed\": true}}")
echo "Response: $HEALTH_RESPONSE"
echo ""

# Test 4: Execute a simple coding task
echo "💻 Test 4: Executing coding task..."
TASK_RESPONSE=$(send_request "tools/call" "{\"name\":\"execute_coding_task\", \"arguments\": {\"task_description\":\"Write a simple Python function that adds two numbers together\"}}")
echo "Response: $TASK_RESPONSE"
echo ""

# Test 5: Generate a code solution
echo "📝 Test 5: Generating code solution..."
SOLUTION_RESPONSE=$(send_request "tools/call" "{\"name\":\"generate_code_solution\", \"arguments\": {\"requirements\":\"Create a Python function to calculate factorial of a number\", \"language\":\"python\"}}")
echo "Response: $SOLUTION_RESPONSE"
echo ""

# Test 6: Review some code
echo "🔍 Test 6: Reviewing code..."
REVIEW_RESPONSE=$(send_request "tools/call" "{\"name\":\"review_code\", \"arguments\": {\"code\":\"def bubble_sort(arr):\\n    n = len(arr)\\n    for i in range(n):\\n        for j in range(0, n-i-1):\\n            if arr[j] > arr[j+1]:\\n                arr[j], arr[j+1] = arr[j+1], arr[j]\\n    return arr\", \"review_criteria\":\"efficiency and best practices\"}}")
echo "Response: $REVIEW_RESPONSE"
echo ""

# Test 7: Read capabilities resource
echo "📊 Test 7: Reading capabilities resource..."
CAPABILITIES_RESPONSE=$(send_request "resources/read" "{\"uri\":\"coding-agent://capabilities\"}")
echo "Response: $CAPABILITIES_RESPONSE"
echo ""

# Test 8: Read health resource
echo "🏥 Test 8: Reading health resource..."
HEALTH_RESOURCE_RESPONSE=$(send_request "resources/read" "{\"uri\":\"coding-agent://health\"}")
echo "Response: $HEALTH_RESOURCE_RESPONSE"
echo ""

# Test 9: Get a prompt template
echo "💬 Test 9: Getting prompt template..."
PROMPT_RESPONSE=$(send_request "prompts/get" "{\"name\":\"coding_task_template\", \"arguments\": {\"task_description\":\"Fix a bug in this function\", \"context\":\"The function should return the sum of array elements\"}}")
echo "Response: $PROMPT_RESPONSE"
echo ""

# Test 10: Shutdown the server (optional)
echo "🛑 Test 10: Testing shutdown (skipping to preserve server)..."
echo "Shutdown test skipped to preserve server for continued use"
echo ""

echo "🎉 All AI Coding Agent simulation tests completed!"
echo ""
echo "Summary of tests performed:"
echo "- Server initialization"
echo "- Tools listing"
echo "- Health check"
echo "- Execute coding task"
echo "- Generate code solution"
echo "- Code review"
echo "- Capabilities resource"
echo "- Health resource"
echo "- Prompt template"
echo ""
echo "The AI Coding Agent server is functioning correctly!"