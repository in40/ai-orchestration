#!/bin/bash

# Master Startup Script for Complete MCP System
# Starts all servers in dependency order:
# 1. Registry Server (mcp-std-skeleton) - provides service discovery on port 3031
# 2. Implementation Engineer (port 3060)
# 3. Requirements Engineer (port 3062)
# 4. IT Lead Server (port 3061)
# 5. Team Management Server (port 3063)
# 6. DevOps Release Engineer (port 3071)
# 7. Web UI (port 8000/5173)

set -e

echo "================================================"
echo "Starting Complete MCP System..."
echo "================================================"

# Cleanup function
cleanup() {
    echo ""
    echo "Shutting down MCP System..."
    pkill -f "mcp_std_server" 2>/dev/null || true
    pkill -f "it_lead_mcp_server" 2>/dev/null || true
    pkill -f "team_management" 2>/dev/null || true
    pkill -f "devops_release_engineer_mcp_server" 2>/dev/null || true
    pkill -f "requirement-engineer" 2>/dev/null || true
    pkill -f "mcp-vibe-coding-agent" 2>/dev/null || true
    echo "MCP System has been shut down."
    exit 0
}

trap cleanup INT TERM

echo ""
echo "Step 1/7: Starting Registry Server on port 3031..."
echo "---------------------------------------------------"
cd /root/qwen/base/mcp-std-skeleton
nohup bash ./start_registry_server.sh --port 3031 > /tmp/mcp_registry.log 2>&1 &
REG_PID=$!
echo "  PID: $REG_PID"

# Wait for registry to be ready
echo -n "  Waiting for Registry Server... "
for i in {1..30}; do
    if curl -s http://localhost:3031/ > /dev/null 2>&1; then
        echo "✓"
        break
    fi
    sleep 1
done

echo ""
echo "Step 2/6: Starting Implementation Engineer Server on port 3060..."
echo "-------------------------------------------------------------------"
cd /root/qwen/base/mcp-std-coder/mcp-vibe-coding-agent
nohup bash ./start_mcp_server.sh --port 3060 > /tmp/implement_eng.log 2>&1 &
IMPL_PID=$!
echo "  PID: $IMPL_PID"

# Wait for Implementation Engineer to be ready
echo -n "  Waiting for Implementation Engineer Server... "
for i in {1..30}; do
    if curl -s http://localhost:3060/ > /dev/null 2>&1; then
        echo "✓"
        break
    fi
    sleep 1
done

echo ""
echo "Step 3/6: Starting Requirements Engineer Server on port 3062..."
echo "------------------------------------------------------------------"
cd /root/qwen/base/requirements-engineer-mcp-server/requirement-engineer-mcp-server
nohup bash ./start_requirement_engineer_server.sh > /tmp/req_eng.log 2>&1 &
REQ_ENG_PID=$!
echo "  PID: $REQ_ENG_PID"

# Wait for Requirements Engineer to be ready
echo -n "  Waiting for Requirements Engineer Server... "
for i in {1..30}; do
    if curl -s http://localhost:3062/ > /dev/null 2>&1; then
        echo "✓"
        break
    fi
    sleep 1
done

echo ""
echo "Step 3/6: Starting IT Lead Server on port 3061..."
echo "---------------------------------------------------"
cd /root/qwen/base/it-lead-mcp-server
nohup bash ./start_it_lead_server.sh --use-postgres --postgres-password postgres > /tmp/it_lead.log 2>&1 &
IT_LEAD_PID=$!
echo "  PID: $IT_LEAD_PID"

# Wait for IT Lead to be ready  
echo -n "  Waiting for IT Lead Server... "
for i in {1..30}; do
    if curl -s http://localhost:3061/ > /dev/null 2>&1; then
        echo "✓"
        break
    fi
    sleep 1
done

echo ""
echo "Step 5/7: Starting Team Management Server on port 3063..."
echo "----------------------------------------------------------"
cd /root/qwen/base/team-management-ui/team-management-mcp-server
if [ -f "./start_team_management_server.sh" ]; then
    nohup bash ./start_team_management_server.sh > /tmp/team_management.log 2>&1 &
    TMGT_PID=$!
    echo "  PID: $TMGT_PID"

    # Wait for Team Mgmt to be ready
    echo -n "  Waiting for Team Management Server... "
    for i in {1..30}; do
        if curl -s http://localhost:3063/ > /dev/null 2>&1; then
            echo "✓"
            break
        fi
        sleep 1
    done
else
    echo "  ⚠ Team Management startup script not found, skipping..."
fi

echo ""
echo "Step 6/7: Starting DevOps Release Engineer Server on port 3071..."
echo "------------------------------------------------------------------"
cd /root/qwen/base/devops-release-engineer-mcp-server
nohup bash ./start_devops_release_engineer_server.sh > /tmp/devops_eng.log 2>&1 &
DEVOPS_PID=$!
echo "  PID: $DEVOPS_PID"

# Wait for DevOps Release Engineer to be ready
echo -n "  Waiting for DevOps Release Engineer Server... "
for i in {1..30}; do
    if curl -s http://localhost:3071/ > /dev/null 2>&1; then
        echo "✓"
        break
    fi
    sleep 1
done

echo ""
echo "Step 7/7: Starting Web UI (IT Lead) on ports 8000/5173..."
echo "----------------------------------------------------------"

# CRITICAL: Kill any existing Web UI processes before starting
echo "  Cleaning up existing Web UI processes..."
pkill -9 -f "uvicorn.*main:app" 2>/dev/null || true
pkill -9 -f "vite.*5173" 2>/dev/null || true
pkill -9 -f "start_ui.sh" 2>/dev/null || true
sleep 2

# Verify ports are free
if ss -tlnp 2>/dev/null | grep -q ":8000 "; then
    echo "  ⚠️  Port 8000 is still in use, waiting..."
    sleep 3
fi
if ss -tlnp 2>/dev/null | grep -q ":5173 "; then
    echo "  ⚠️  Port 5173 is still in use, waiting..."
    sleep 3
fi

cd /root/qwen/base/it-lead-mcp-server
if [ -f "./start_ui.sh" ]; then
    nohup bash ./start_ui.sh \
        --web-backend-port 8000 \
        --web-frontend-port 5173 \
        --registry-host 127.0.0.1 \
        --registry-port 3031 \
        > /tmp/webui.log 2>&1 &
    WEBUI_PID=$!
    echo "  PID: $WEBUI_PID"

    # Wait for Web UI to be ready
    echo -n "  Waiting for Web UI... "
    for i in {1..15}; do
        if curl -s http://localhost:8000/ > /dev/null 2>&1 || [ $i -eq 15 ]; then
            break
        fi
        sleep 2
    done
    echo "✓"
else
    echo "  ⚠️  Web UI startup script (start_ui.sh) not found, skipping..."
fi

echo ""
echo "================================================"
echo "MCP System Startup Complete!"
echo "================================================"
echo ""
echo "Registry Server:           http://localhost:3031/mcp"
echo "Implementation Engineer:    http://localhost:3060/mcp"
echo "Requirements Engineer:      http://localhost:3062/mcp"
echo "IT Lead Server:             http://localhost:3061/mcp"
echo "Team Management:           http://localhost:3063/mcp  (if started)"
echo "DevOps Release Engineer:    http://localhost:3071/mcp  (NEW!)"
echo "Web UI:                    http://localhost:5173/"
echo ""
echo "Process IDs:"
echo "  Registry Server:         PID $REG_PID"
echo "  Implementation Engineer: PID $IMPL_PID"
echo "  Requirements Engineer:   PID $REQ_ENG_PID"
echo "  IT Lead Server:          PID $IT_LEAD_PID"
echo "  Team Management:         PID $TMGT_PID (if started)"
echo "  DevOps Release Engineer: PID $DEVOPS_PID (NEW!)"
echo "  Web UI:                  PID $WEBUI_PID (if started)"
echo ""

# Keep script running
wait
