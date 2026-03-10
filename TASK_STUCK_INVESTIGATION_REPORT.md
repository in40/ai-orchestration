# Task Stuck Investigation Report

## Problem Statement

Task `task-1772835632522` is stuck at status `in_progress`:
- **Task ID**: task-1772835632522
- **Status**: in_progress
- **Assigned To**: implementation-engineer
- **Created**: 06.03.2026, 22:19:42
- **Status History**:
  - `submitted` at 22:20:34 - Task submitted for processing, LLM planning in progress
  - `received` at 22:20:54 - Task received, routing to implementation-engineer
  - `in_progress` - Current status (stuck here)

**User Observation**: 
> "I can see that first call to LLM is happening, so I believe LLM planning is completed. But implementation engineer never calls LLM model - so task is not submitted to implementation engineer or implementation engineer is unable to call LLM model."

## Architecture Overview

```
Web UI (port 3000)
    ↓ submits task via MCP
IT Lead Server (port 3061)
    ↓ LLM planning + routing
    ↓ forwards via HTTP POST
Implementation Engineer (port 3062?)
    ↓ calls LLM to generate code
    ↓ returns result
IT Lead Server
    ↓ updates task status to "done"
```

## Root Cause Analysis

### Flow Analysis

1. **Task Submission** ✅ WORKING
   - Web UI calls `assign_task` tool on IT Lead
   - Task stored in PostgreSQL with status `"submitted"`
   - Background thread spawned for LLM planning

2. **LLM Planning** ✅ WORKING  
   - IT Lead's LLM client calls LLM for task routing
   - LLM returns plan with `primary_agent: "implementation-engineer"`
   - Task status updated to `"received"` then `"in_progress"`

3. **Task Forwarding** ❌ **LIKELY FAILING HERE**
   - IT Lead tries to forward task to implementation-engineer via HTTP POST
   - Makes request to agent endpoint: `http://<host>:<port>/mcp`
   - Tool called: `vibe_code_async`
   - **This is where the task gets stuck**

4. **Agent Processing** ❌ NOT HAPPENING
   - Implementation engineer should receive the task
   - Should call LLM to generate code
   - Should return result or async task ID
   - **This never happens**

### Possible Root Causes

#### 1. **Implementation Engineer Not Running** (MOST LIKELY)
The implementation-engineer MCP server is not running or not accessible.

**Evidence**:
- Task status is `in_progress` but no further updates
- No LLM call from implementation-engineer
- Background thread in IT Lead is likely blocking on HTTP request timeout

**How to Verify**:
```bash
# Check if implementation-engineer is running
curl http://127.0.0.1:3062/mcp -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/list","params":{}}'

# Check registered services in MCP Registry
curl http://127.0.0.1:3031/api/services
```

**Expected ports for implementation-engineer**:
- Port 3062 (primary)
- Port 3060 (alternative)
- Port 3063 (alternative)

#### 2. **Agent Endpoint Mismatch**
IT Lead has wrong endpoint for implementation-engineer.

**Where endpoint is configured**:
- `/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/task_routing_engine.py`
- Line 60: `self.agent_endpoints["implementation-engineer"] = endpoint`
- Updated from service registry during initialization

**How to Verify**:
Check IT Lead server logs for:
```
DEBUG: agent_endpoint for implementation-engineer: http://...
```

#### 3. **Tool Name Mismatch**
IT Lead is calling `vibe_code_async` but implementation-engineer doesn't have this tool.

**Where tool is selected**:
- `/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/task_assignment.py`
- Line 200: `tool = llm_plan.get("tools", {}).get(primary_agent, "vibe_code_async")`

**How to Verify**:
Check implementation-engineer's tools/list response for available tools.

#### 4. **HTTP Request Timeout**
The HTTP request to implementation-engineer is timing out silently.

**Current timeout**: 120 seconds (line 410 in task_assignment.py)

**How to Verify**:
Check IT Lead server logs for:
```
Request failed: Connection refused
or
Request failed: Timeout
```

#### 5. **Background Thread Deadlock**
Background thread running LLM planning is deadlocking.

**Where**:
- `_background_task_processing()` in `extended_server_handlers.py`
- Line 1283-1301

**How to Verify**:
Check if background thread is actually running and completing.

## Diagnostic Steps

### Step 1: Run Diagnostic Script

I've created a diagnostic script to check all components:

```bash
cd /root/qwen/base
python diagnose_task_stuck.py
```

This will check:
- ✅ MCP Registry status
- ✅ IT Lead server status  
- ✅ Implementation Engineer status
- ✅ Task status in database
- ✅ Agent endpoint connectivity

### Step 2: Check IT Lead Server Logs

Look for these log messages in IT Lead server output:

```
# Background thread started
🚀 Starting background thread for task task-1772835632522

# LLM Planning
📞 Calling LLM for task planning...
✅ LLM response received

# Agent Forwarding
DEBUG: agent_endpoint for implementation-engineer: http://...
DEBUG: _forward_task_to_agent: agent_id=implementation-engineer, tool=vibe_code_async

# Forwarding Result
✅ Task forwarded to implementation-engineer
OR
❌ Agent forwarding failed: <error message>
```

### Step 3: Check Implementation Engineer Logs

Look for incoming task notifications:
```
Received task: task-1772835632522
Calling LLM for code generation
```

## Recommended Fixes

### Fix 1: Start Implementation Engineer (If Not Running)

If diagnostic shows implementation-engineer is not running:

```bash
# Navigate to implementation-engineer directory
cd /root/qwen/base/mcp-std-coder/mcp-vibe-coding-agent

# Start the server
python -m mcp_vibe_coding_agent.server --port 3062
```

### Fix 2: Verify Agent Registration

Ensure implementation-engineer is registered with MCP Registry:

```bash
# Check registration
curl http://127.0.0.1:3031/api/services | jq '.[] | select(.name | contains("Implementation"))'

# If not registered, check implementation-engineer startup logs
# It should auto-register on startup
```

### Fix 3: Add Better Error Handling

The current code doesn't properly handle forwarding failures. Add this to `task_assignment.py`:

```python
# After line 280 in task_assignment.py
if forward_result.get("success"):
    # ... existing success handling ...
else:
    # IMPROVED ERROR HANDLING
    error_msg = forward_result.get("error", "Unknown error")
    print(f"❌ CRITICAL: Task forwarding FAILED for {task_id}")
    print(f"   Agent: {primary_agent}")
    print(f"   Endpoint: {agent_endpoint}")
    print(f"   Tool: {tool}")
    print(f"   Error: {error_msg}")
    
    # Update task status to failed
    if self.task_storage:
        self._update_task_status(
            task_id, "failed",
            f"Task forwarding failed: {error_msg}",
            {"forwarding_error": error_msg}
        )
```

### Fix 4: Add Timeout Handling

Add explicit timeout error handling:

```python
# In _forward_task_to_agent, line 398-428
try:
    response = requests.post(
        agent_endpoint,
        json={...},
        timeout=120.0
    )
    # ... existing response handling ...
except requests.Timeout as e:
    print(f"❌ TIMEOUT: Agent {agent_id} did not respond within 120 seconds")
    return {"success": False, "error": f"Request timeout: {str(e)}"}
except requests.ConnectionError as e:
    print(f"❌ CONNECTION ERROR: Cannot reach agent {agent_id} at {agent_endpoint}")
    return {"success": False, "error": f"Connection error: {str(e)}"}
except requests.RequestException as e:
    return {"success": False, "error": f"Request failed: {str(e)}"}
```

### Fix 5: Add Task Status Timeout

If task stays in `in_progress` too long, mark as failed:

```python
# Add background monitoring thread
def _monitor_task_timeout(self, task_id: str, timeout_seconds: int = 600):
    """Monitor task and mark as failed if stuck too long"""
    time.sleep(timeout_seconds)
    
    task = self.task_storage.get_task(task_id)
    if task and task.get("status") == "in_progress":
        print(f"⚠️ Task {task_id} stuck in in_progress for >{timeout_seconds}s, marking as failed")
        self._update_task_status(
            task_id, "failed",
            "Task processing timeout - agent did not complete within expected time"
        )
```

## Immediate Action Plan

1. **Run diagnostic script** to identify which component is failing
2. **Check IT Lead server logs** for forwarding errors
3. **Verify implementation-engineer is running** on expected port
4. **Test agent endpoint directly** with curl
5. **If agent is running**, check agent logs for incoming task
6. **If agent not running**, start it and resubmit task

## Long-term Improvements

1. **Add circuit breaker pattern** - Don't keep tasks in `in_progress` indefinitely
2. **Add health checks** - Periodically check agent availability
3. **Add retry logic** - Retry failed task forwarding
4. **Add dead letter queue** - Move stuck tasks to manual review
5. **Improve logging** - More detailed error messages for debugging
6. **Add monitoring dashboard** - Real-time task status visualization

## Files Analyzed

- `/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/handlers/extended_server_handlers.py`
- `/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/task_assignment.py`
- `/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/task_routing_engine.py`
- `/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/llm_task_planner.py`
- `/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/llm_client.py`
- `/root/qwen/base/ACTUAL_FLOW_EXPLANATION.md`

## Conclusion

The most likely root cause is that the **Implementation Engineer MCP server is not running or not accessible**. The IT Lead server successfully completes LLM planning and tries to forward the task, but the HTTP request to the implementation-engineer fails (either connection refused or timeout).

The task remains stuck at `in_progress` because:
1. The background thread is waiting for the HTTP request to complete
2. No proper timeout/error handling updates the task status to "failed"
3. The system assumes the agent will eventually respond

**Priority Fix**: Start the implementation-engineer server and verify it's registered with the MCP registry.
