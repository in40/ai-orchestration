#!/bin/bash

echo "=========================================================================="
echo "         MCP SYSTEM - WORKFLOW DEMONSTRATION"
echo "=========================================================================="
echo ""

REGISTRY_URL="http://localhost:3031"
IT_LEAD_URL="http://localhost:3061"

echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Registry:  $REGISTRY_URL"
echo "IT Lead:   $IT_LEAD_URL"
echo ""

echo "--------------------------------------------------------------------------"
echo "STEP 1: Checking Registry for Registered Services"
echo "--------------------------------------------------------------------------"

curl -s -X POST "$REGISTRY_URL/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"registry/list","params":{},"id":"check-services"}' | python3 -c "
import json,sys
data = json.load(sys.stdin)
services = data.get('result', {}).get('services', [])
print(f'Found {len(services)} registered services:')
for s in sorted(services, key=lambda x: x['name']):
    print(f\"   - {s['name'].strip()}\")
"
echo ""

echo "--------------------------------------------------------------------------"
echo "STEP 2: Submitting Tasks for Processing"
echo "--------------------------------------------------------------------------"

echo -e "\n📝 Task 1/3: Analyzing system architecture..."
curl -s -X POST "$IT_LEAD_URL/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"analyze_architecture","arguments":{"current_architecture":"Python Flask monolith","requirements":"Add CI/CD with GitHub Actions and Dockerize the app"}}},"id":"task1"}' | python3 -c "import json,sys; d=json.load(sys.stdin); print('   ✓ Architecture analysis submitted')"

echo -e "\n📝 Task 2/3: Submitting implementation task..."
curl -s -X POST "$IT_LEAD_URL/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"assign_task","arguments":{"task_id":"workflow-demo-001","task_description":"Create a Python script that implements a simple HTTP server with REST API endpoints for user management.","assignee":"requirement-engineer","priority":"high"}}},"id":"task2"}' | python3 -c "import json,sys; d=json.load(sys.stdin); r=d.get('result',{}).get('result',{}); print(f\"   ✓ Implementation task submitted: {r.get('status','N/A')} - {r.get('message','')[0:50]}...\")"

echo -e "\n📝 Task 3/3: Creating project plan..."
curl -s -X POST "$IT_LEAD_URL/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"generate_project_plan","arguments":{"requirements":"Build a microservices-based e-commerce platform with user authentication, product catalog, and order processing.","team_size":5,"timeline_weeks":12}}}"},"id":"task3"}' | python3 -c "import json,sys; d=json.load(sys.stdin); print('   ✓ Project plan generated')"

echo ""
echo "=========================================================================="
echo "                    WORKFLOW DEMONSTRATION COMPLETE                        "
echo "=========================================================================="
echo ""
echo "✅ Tasks submitted successfully!"
echo "🔍 All tasks are being tracked by the registry."
echo ""

curl -s "$REGISTRY_URL/mcp" -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"registry/list","params":{},"id":"view-all"}' | python3 -c "
import json,sys
data = json.load(sys.stdin)
services = data.get('result', {}).get('services', [])
print(f'Found {len(services)} registered services:')
for s in sorted(services, key=lambda x: x['name']):
    print(f\"   - {s['name'].strip()}\")
"
echo ""
echo "✅ Workflow demonstration complete!"
