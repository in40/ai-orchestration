#!/bin/bash

# AI Agent Simulation Tests for Team Management Server
# Tests the custom team management functionality

echo "Starting AI Agent Simulation Tests for Team Management Server..."

# Test 1: Initialize connection
echo "Test 1: Initializing connection to Team Management Server"
RESPONSE=$(curl -s -X POST http://localhost:3063/mcp -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "initialize",
  "params": {
    "clientInfo": {
      "name": "test-client",
      "version": "1.0"
    }
  }
}')
echo "Initialize response: $RESPONSE"
echo ""

# Test 2: List available tools
echo "Test 2: Listing available tools"
RESPONSE=$(curl -s -X POST http://localhost:3063/mcp -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0",
  "id": "2",
  "method": "tools/list",
  "params": {}
}')
echo "Tools list response: $RESPONSE"
echo ""

# Test 3: Create a task
echo "Test 3: Creating a new task"
RESPONSE=$(curl -s -X POST http://localhost:3063/mcp -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0",
  "id": "3",
  "method": "tools/call",
  "params": {
    "name": "team_management/create_task",
    "arguments": {
      "title": "Implement user authentication",
      "description": "Create a user authentication system with login and logout functionality",
      "assignee_id": "member-123",
      "due_date": "2024-12-31",
      "priority": "high",
      "tags": ["security", "frontend", "backend"]
    }
  }
}')
echo "Create task response: $RESPONSE"
TASK_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['result']['task_id'])" 2>/dev/null | tr -d '\n' || echo "task-123")
echo "Created task with ID: $TASK_ID"
echo ""

# Test 4: Get the created task
echo "Test 4: Retrieving the created task"
RESPONSE=$(curl -s -X POST http://localhost:3063/mcp -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0",
  "id": "4",
  "method": "tools/call",
  "params": {
    "name": "team_management/get_task",
    "arguments": {
      "task_id": "'"$TASK_ID"'"
    }
  }
}')
echo "Get task response: $RESPONSE"
echo ""

# Test 5: List tasks
echo "Test 5: Listing all tasks"
RESPONSE=$(curl -s -X POST http://localhost:3063/mcp -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0",
  "id": "5",
  "method": "tools/call",
  "params": {
    "name": "team_management/list_tasks",
    "arguments": {}
  }
}')
echo "List tasks response: $RESPONSE"
echo ""

# Test 6: Create a team member
echo "Test 6: Creating a new team member"
RESPONSE=$(curl -s -X POST http://localhost:3063/mcp -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0",
  "id": "6",
  "method": "tools/call",
  "params": {
    "name": "team_management/create_team_member",
    "arguments": {
      "name": "John Doe",
      "email": "john.doe@example.com",
      "role": "Senior Developer",
      "skills": ["Python", "JavaScript", "React"],
      "availability": "full_time"
    }
  }
}')
echo "Create team member response: $RESPONSE"
MEMBER_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['result']['member_id'])" 2>/dev/null | tr -d '\n' || echo "member-123")
echo "Created member with ID: $MEMBER_ID"
echo ""

# Test 7: Get the created team member
echo "Test 7: Retrieving the created team member"
RESPONSE=$(curl -s -X POST http://localhost:3063/mcp -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0",
  "id": "7",
  "method": "tools/call",
  "params": {
    "name": "team_management/get_team_member",
    "arguments": {
      "member_id": "'"$MEMBER_ID"'"
    }
  }
}')
echo "Get team member response: $RESPONSE"
echo ""

# Test 8: List team members
echo "Test 8: Listing all team members"
RESPONSE=$(curl -s -X POST http://localhost:3063/mcp -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0",
  "id": "8",
  "method": "tools/call",
  "params": {
    "name": "team_management/list_team_members",
    "arguments": {}
  }
}')
echo "List team members response: $RESPONSE"
echo ""

# Test 9: Get team queues
echo "Test 9: Getting team queues"
RESPONSE=$(curl -s -X POST http://localhost:3063/mcp -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0",
  "id": "9",
  "method": "tools/call",
  "params": {
    "name": "team_management/get_team_queues",
    "arguments": {}
  }
}')
echo "Get team queues response: $RESPONSE"
echo ""

# Test 10: Ping server for health check
echo "Test 10: Health check with ping"
RESPONSE=$(curl -s -X POST http://localhost:3063/mcp -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0",
  "id": "10",
  "method": "ping",
  "params": {}
}')
echo "Ping response: $RESPONSE"
echo ""

echo "AI Agent Simulation Tests completed!"