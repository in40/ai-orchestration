#!/bin/bash

# Master Shutdown Script for Complete MCP System
# Stops all servers in reverse dependency order:
# 1. Web UI (port 8000/5173)
# 2. DevOps Release Engineer (port 3071)
# 3. Team Management Server (port 3063)
# 4. IT Lead Server (port 3061)
# 5. Requirements Engineer (port 3062)
# 6. Implementation Engineer (port 3060)
# 7. Registry Server (mcp-std-skeleton) - port 3031

set -e

echo "================================================"
echo "Stopping Complete MCP System..."
echo "================================================"

# Cleanup function
cleanup() {
    echo ""
    echo "Shutting down MCP System..."

    # Stop Web UI first (reverse order)
    if [ -n "$WEBUI_PID" ]; then
        echo "Step 1/7: Stopping Web UI (PID $WEBUI_PID)..."
        kill $WEBUI_PID 2>/dev/null || true
        sleep 2
    fi

    # Stop DevOps Release Engineer
    if [ -n "$DEVOPS_PID" ]; then
        echo "Step 2/7: Stopping DevOps Release Engineer (PID $DEVOPS_PID)..."
        kill $DEVOPS_PID 2>/dev/null || true
        sleep 1
    fi

    # Stop Team Management Server
    if [ -n "$TMGT_PID" ]; then
        echo "Step 3/7: Stopping Team Management Server (PID $TMGT_PID)..."
        kill $TMGT_PID 2>/dev/null || true
        sleep 1
    fi

    # Stop IT Lead Server
    if [ -n "$IT_LEAD_PID" ]; then
        echo "Step 4/7: Stopping IT Lead Server (PID $IT_LEAD_PID)..."
        kill $IT_LEAD_PID 2>/dev/null || true
        sleep 1
    fi

    # Stop Requirements Engineer
    if [ -n "$REQ_ENG_PID" ]; then
        echo "Step 5/7: Stopping Requirements Engineer (PID $REQ_ENG_PID)..."
        kill $REQ_ENG_PID 2>/dev/null || true
        sleep 1
    fi

    # Stop Implementation Engineer
    if [ -n "$IMPL_PID" ]; then
        echo "Step 6/7: Stopping Implementation Engineer (PID $IMPL_PID)..."
        kill $IMPL_PID 2>/dev/null || true
        sleep 1
    fi

    # Stop Registry Server last
    if [ -n "$REG_PID" ]; then
        echo "Step 7/7: Stopping Registry Server (PID $REG_PID)..."
        kill $REG_PID 2>/dev/null || true
        sleep 1
    fi

    # Fallback: Kill any remaining MCP processes
    echo ""
    echo "Cleaning up any remaining MCP processes..."
    pkill -f "mcp_std_server" 2>/dev/null || true
    pkill -f "it_lead_mcp_server" 2>/dev/null || true
    pkill -f "team_management" 2>/dev/null || true
    pkill -f "devops_release_engineer_mcp_server" 2>/dev/null || true
    pkill -f "uvicorn.*web-backend" 2>/dev/null || true

    echo ""
    echo "MCP System has been shut down."
}

# Set up trap to handle Ctrl+C and other termination signals
trap cleanup INT TERM

# Capture PIDs from the log files if they exist (for restart scenarios)
echo ""
echo "Detecting running MCP processes..."

if [ -f /tmp/mcp_registry.log ]; then
    REG_PID=$(grep "PID:" /tmp/mcp_registry.log 2>/dev/null | tail -1 | awk '{print $NF}')
    echo "  Found Registry Server PID: ${REG_PID:-none}"
fi

if [ -f /tmp/implement_eng.log ]; then
    IMPL_PID=$(grep "PID:" /tmp/implement_eng.log 2>/dev/null | tail -1 | awk '{print $NF}')
    echo "  Found Implementation Engineer PID: ${IMPL_PID:-none}"
fi

if [ -f /tmp/req_eng.log ]; then
    REQ_ENG_PID=$(grep "PID:" /tmp/req_eng.log 2>/dev/null | tail -1 | awk '{print $NF}')
    echo "  Found Requirements Engineer PID: ${REQ_ENG_PID:-none}"
fi

if [ -f /tmp/it_lead.log ]; then
    IT_LEAD_PID=$(grep "PID:" /tmp/it_lead.log 2>/dev/null | tail -1 | awk '{print $NF}')
    echo "  Found IT Lead Server PID: ${IT_LEAD_PID:-none}"
fi

if [ -f /tmp/team_management.log ]; then
    TMGT_PID=$(grep "PID:" /tmp/team_management.log 2>/dev/null | tail -1 | awk '{print $NF}')
    echo "  Found Team Management Server PID: ${TMGT_PID:-none}"
fi

if [ -f /tmp/devops_eng.log ]; then
    DEVOPS_PID=$(grep "PID:" /tmp/devops_eng.log 2>/dev/null | tail -1 | awk '{print $NF}')
    echo "  Found DevOps Release Engineer PID: ${DEVOPS_PID:-none}"
fi

if [ -f /tmp/webui.log ]; then
    WEBUI_PID=$(grep "PID:" /tmp/webui.log 2>/dev/null | tail -1 | awk '{print $NF}')
    echo "  Found Web UI PID: ${WEBUI_PID:-none}"
fi

# Verify processes are actually running before attempting to stop them
verify_and_stop() {
    local pid=$1
    local name=$2
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        echo "Stopping $name (PID: $pid)..."
        kill "$pid" 2>/dev/null || true
        sleep 1

        # Force kill if still running
        if kill -0 "$pid" 2>/dev/null; then
            echo "  Process still running, forcing kill..."
            kill -9 "$pid" 2>/dev/null || true
        fi
    else
        echo "$name is not running"
    fi
}

echo ""
echo "Stopping MCP System services..."

# Stop in reverse order with verification
verify_and_stop $WEBUI_PID "Web UI"
verify_and_stop $DEVOPS_PID "DevOps Release Engineer"
verify_and_stop $TMGT_PID "Team Management Server"
verify_and_stop $IT_LEAD_PID "IT Lead Server"
verify_and_stop $REQ_ENG_PID "Requirements Engineer"
verify_and_stop $IMPL_PID "Implementation Engineer"
verify_and_stop $REG_PID "Registry Server"

# Final cleanup
echo ""
echo "Final cleanup..."
pkill -f "mcp_std_server" 2>/dev/null || true
pkill -f "it_lead_mcp_server" 2>/dev/null || true
pkill -f "team_management" 2>/dev/null || true
pkill -f "devops_release_engineer_mcp_server" 2>/dev/null || true

sleep 1

# Check if any processes are still running
echo ""
echo "Verifying shutdown..."
RUNNING=$(pgrep -c -f "(mcp_std_server|it_lead_mcp_server|team_management|devops_release_engineer_mcp_server)" 2>/dev/null || echo "0")
if [ "$RUNNING" -eq 0 ]; then
    echo "✓ All MCP processes have been stopped."
else
    echo "⚠ $RUNNING MCP process(es) may still be running. Run 'pkill -f mcp' to force stop."
fi

echo ""
echo "================================================"
echo "MCP System Shutdown Complete!"
echo "================================================"
