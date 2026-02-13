#!/bin/bash

# IT Lead MCP Server Simulation Test
# Tests the IT Lead server functionality by simulating an AI agent interacting with it

set -e  # Exit on any error

echo "Starting IT Lead MCP Server Simulation Test..."

# Start the IT Lead server in the background
echo "Starting IT Lead server on port 3061..."
cd /root/qwen/base/it-lead-mcp-server
source venv/bin/activate
python -m it_lead_mcp_server.server --port 3061 --registry-port 3031 --register-with-registry --llm-provider-url http://asus-tus:1234/v1/chat/completions --llm-model qwen3-4b &
SERVER_PID=$!

# Give the server time to start
sleep 5

echo "Server started with PID: $SERVER_PID"

# Test 1: Initialize connection
echo "Test 1: Initializing connection..."
INIT_RESPONSE=$(curl -s -X POST http://localhost:3061/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "initialize",
    "params": {
      "clientInfo": {
        "name": "test-agent",
        "version": "1.0.0"
      }
    }
  }')

echo "Initialize response: $INIT_RESPONSE"
if [[ $INIT_RESPONSE == *"serverInfo"* ]]; then
  echo "✓ Initialize test PASSED"
else
  echo "✗ Initialize test FAILED"
fi

# Test 2: List tools
echo "Test 2: Listing tools..."
TOOLS_RESPONSE=$(curl -s -X POST http://localhost:3061/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "2",
    "method": "tools/list",
    "params": {}
  }')

echo "Tools response: $TOOLS_RESPONSE"
if [[ $TOOLS_RESPONSE == *"assign_task"* ]] && [[ $TOOLS_RESPONSE == *"review_code"* ]]; then
  echo "✓ Tools list test PASSED"
else
  echo "✗ Tools list test FAILED"
fi

# Test 3: Call assign_task tool
echo "Test 3: Calling assign_task tool..."
ASSIGN_TASK_RESPONSE=$(curl -s -X POST http://localhost:3061/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "3",
    "method": "tools/call",
    "params": {
      "name": "assign_task",
      "arguments": {
        "task_id": "TASK-001",
        "task_description": "Implement user authentication module",
        "assignee": "developer-john",
        "priority": "high",
        "deadline": "2023-12-31T23:59:59Z"
      }
    }
  }')

echo "Assign task response: $ASSIGN_TASK_RESPONSE"
if [[ $ASSIGN_TASK_RESPONSE == *"result"* ]] && [[ $ASSIGN_TASK_RESPONSE == *"TASK-001"* ]]; then
  echo "✓ Assign task test PASSED"
else
  echo "✗ Assign task test FAILED"
fi

# Test 4: Call generate_project_plan tool
echo "Test 4: Calling generate_project_plan tool..."
PROJECT_PLAN_RESPONSE=$(curl -s -X POST http://localhost:3061/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "4",
    "method": "tools/call",
    "params": {
      "name": "generate_project_plan",
      "arguments": {
        "requirements": "Build a REST API for user management with authentication",
        "team_size": 3,
        "timeline_weeks": 8
      }
    }
  }')

echo "Project plan response: $PROJECT_PLAN_RESPONSE"
if [[ $PROJECT_PLAN_RESPONSE == *"result"* ]]; then
  echo "✓ Project plan test PASSED"
else
  echo "✗ Project plan test FAILED"
fi

# Test 5: List resources
echo "Test 5: Listing resources..."
RESOURCES_RESPONSE=$(curl -s -X POST http://localhost:3061/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "5",
    "method": "resources/list",
    "params": {}
  }')

echo "Resources response: $RESOURCES_RESPONSE"
if [[ $RESOURCES_RESPONSE == *"team-status"* ]] && [[ $RESOURCES_RESPONSE == *"project-plan"* ]]; then
  echo "✓ Resources list test PASSED"
else
  echo "✗ Resources list test FAILED"
fi

# Test 6: Read team status resource
echo "Test 6: Reading team status resource..."
RESOURCE_READ_RESPONSE=$(curl -s -X POST http://localhost:3061/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "6",
    "method": "resources/read",
    "params": {
      "uri": "it-lead://resource/team-status"
    }
  }')

echo "Resource read response: $RESOURCE_READ_RESPONSE"
if [[ $RESOURCE_READ_RESPONSE == *"contents"* ]]; then
  echo "✓ Resource read test PASSED"
else
  echo "✗ Resource read test FAILED"
fi

# Test 7: Health check (ping)
echo "Test 7: Performing health check..."
PING_RESPONSE=$(curl -s -X POST http://localhost:3061/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "7",
    "method": "ping",
    "params": {}
  }')

echo "Ping response: $PING_RESPONSE"
if [[ $PING_RESPONSE == *"healthy"* ]]; then
  echo "✓ Health check test PASSED"
else
  echo "✗ Health check test FAILED"
fi

# Test 8: List prompts
echo "Test 8: Listing prompts..."
PROMPTS_RESPONSE=$(curl -s -X POST http://localhost:3061/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "8",
    "method": "prompts/list",
    "params": {}
  }')

echo "Prompts response: $PROMPTS_RESPONSE"
if [[ $PROMPTS_RESPONSE == *"task_assignment_prompt"* ]]; then
  echo "✓ Prompts list test PASSED"
else
  echo "✗ Prompts list test FAILED"
fi

# Test 9: Get a prompt
echo "Test 9: Getting a prompt..."
GET_PROMPT_RESPONSE=$(curl -s -X POST http://localhost:3061/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "9",
    "method": "prompts/get",
    "params": {
      "name": "task_assignment_prompt",
      "arguments": {
        "task_description": "Fix login bug",
        "assignee": "senior-dev-alice",
        "deadline": "tomorrow"
      }
    }
  }')

echo "Get prompt response: $GET_PROMPT_RESPONSE"
if [[ $GET_PROMPT_RESPONSE == *"contents"* ]]; then
  echo "✓ Get prompt test PASSED"
else
  echo "✗ Get prompt test FAILED"
fi

# Shutdown the server
echo "Shutting down server..."
kill $SERVER_PID 2>/dev/null || true

# Wait a bit for the server to shut down
sleep 2

# Double-check and force kill if necessary
kill -9 $SERVER_PID 2>/dev/null || true

echo "All tests completed!"