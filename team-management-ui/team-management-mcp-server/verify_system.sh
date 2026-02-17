#!/bin/bash

echo "=== Team Management System Verification ==="
echo ""

echo "1. Checking if services are running..."
echo "   MCP Server (port 3063):"
if netstat -tuln | grep ':3063' > /dev/null; then
    echo "   ✓ Running"
else
    echo "   ✗ Not running"
fi

echo "   API Server (port 5001):"
if netstat -tuln | grep ':5001' > /dev/null; then
    echo "   ✓ Running"
else
    echo "   ✗ Not running"
fi

echo "   Web UI (port 3001):"
if netstat -tuln | grep ':3001' > /dev/null; then
    echo "   ✓ Running"
else
    echo "   ✗ Not running"
fi

echo ""
echo "2. Testing API endpoints..."
echo "   Testing /api/tasks:"
TASK_RESPONSE=$(curl -s -o /tmp/tasks_response.txt -w "%{http_code}" http://localhost:5001/api/tasks)
if [ "$TASK_RESPONSE" = "200" ]; then
    echo "   ✓ Tasks API working (HTTP $TASK_RESPONSE)"
else
    echo "   ✗ Tasks API not working (HTTP $TASK_RESPONSE)"
fi

echo "   Testing /api/team-members (registry members):"
MEMBER_RESPONSE=$(curl -s -o /tmp/members_response.txt -w "%{http_code}" http://localhost:5001/api/team-members)
if [ "$MEMBER_RESPONSE" = "200" ]; then
    echo "   ✓ Team members API working (HTTP $MEMBER_RESPONSE)"
    MEMBER_COUNT=$(cat /tmp/members_response.txt | python3 -m json.tool 2>/dev/null | grep -c '"id"' || echo "0")
    echo "   Found $MEMBER_COUNT registered AI agents"
else
    echo "   ✗ Team members API not working (HTTP $MEMBER_RESPONSE)"
fi

echo ""
echo "3. Testing MCP server connectivity..."
MCP_RESPONSE=$(curl -s -X POST http://localhost:3063/mcp -H "Content-Type: application/json" -d '{"jsonrpc": "2.0", "id": "test", "method": "ping", "params": {}}' | python3 -m json.tool 2>/dev/null | grep -c "healthy" || echo "0")
if [ "$MCP_RESPONSE" -gt 0 ]; then
    echo "   ✓ MCP server responding to ping"
else
    echo "   ✗ MCP server not responding to ping"
fi

echo ""
echo "4. Testing registry connectivity..."
REGISTRY_RESPONSE=$(curl -s -X POST http://localhost:3031/mcp -H "Content-Type: application/json" -d '{"jsonrpc": "2.0", "id": "test", "method": "registry/list", "params": {}}' | python3 -m json.tool 2>/dev/null | grep -c "services" || echo "0")
if [ "$REGISTRY_RESPONSE" -gt 0 ]; then
    echo "   ✓ Registry server responding"
else
    echo "   ✗ Registry server not responding"
fi

echo ""
echo "5. Checking registered AI agents in registry:"
AGENT_COUNT=$(curl -s -X POST http://localhost:3031/mcp -H "Content-Type: application/json" -d '{"jsonrpc": "2.0", "id": "list", "method": "registry/list", "params": {}}' | python3 -m json.tool 2>/dev/null | grep -c "Agent\|Engineer\|Architect\|Reviewer\|Tester\|Writer" || echo "0")
echo "   Found $AGENT_COUNT AI agents/services in registry"

echo ""
echo "6. Verifying UI accessibility..."
UI_RESPONSE=$(curl -s -o /tmp/ui_response.txt -w "%{http_code}" http://localhost:5001/)
if [ "$UI_RESPONSE" = "200" ]; then
    echo "   ✓ Web UI accessible (HTTP $UI_RESPONSE)"
    TITLE_CHECK=$(grep -c "Team Management" /tmp/ui_response.txt || echo "0")
    if [ "$TITLE_CHECK" -gt 0 ]; then
        echo "   ✓ Correct title found in UI"
    else
        echo "   ✗ Incorrect title in UI"
    fi
else
    echo "   ✗ Web UI not accessible (HTTP $UI_RESPONSE)"
fi

echo ""
echo "=== Summary ==="
echo "Team Management System with AI Agent Registry Integration:"
echo "- MCP Server: Available at http://localhost:3063/mcp"
echo "- API Server: Available at http://localhost:5001/api/"
echo "- Web UI: Available at http://localhost:5001/"
echo "- AI Agents: Loaded from MCP registry (currently $AGENT_COUNT agents)"
echo ""
echo "The system is now managing a virtual team of AI agents registered in the MCP registry."
echo "The UI displays these AI agents as team members and allows interaction with them."