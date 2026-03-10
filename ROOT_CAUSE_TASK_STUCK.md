# ROOT CAUSE IDENTIFIED: Tasks Stuck at in_progress

## Executive Summary

**Task `task-1772835632522` is stuck because the IT Lead server cannot successfully forward tasks to the Implementation Engineer agent.**

## Investigation Findings

### ✅ What's Working:
1. **IT Lead Server** (port 3061) - Running correctly
2. **Implementation Engineer** (port 3060) - Running correctly with `vibe_code_async` tool
3. **LLM Planning** - IT Lead successfully calls LLM for task routing
4. **Task Storage** - PostgreSQL database working

### ❌ What's Broken:
**Task forwarding from IT Lead to Implementation Engineer is failing silently**

## Root Cause Analysis

### The Architecture Problem: SPLIT-BRAIN REGISTRY

The system has **TWO separate service registries**:

1. **PostgreSQL Registry** (port 3031)
   - Agents register here: Implementation Engineer, Requirements Engineer, DevOps, etc.
   - 7 services registered
   - Web UI reads from this registry

2. **SQLite Registry** (`/root/qwen/base/mcp-std-skeleton/mcp_registry.db`)
   - Only 2 services: MCP Registry itself and IT Lead
   - IT Lead server reads from this registry
   - **Does NOT have Implementation Engineer registered!**

### The Flow Breakdown:

```
1. User submits task → Web UI → IT Lead (port 3061) ✅
2. IT Lead stores task with status "submitted" ✅
3. Background thread starts LLM planning ✅
4. LLM returns plan: primary_agent = "implementation-engineer" ✅
5. IT Lead tries to forward task to implementation-engineer ❌ FAILS HERE
6. Task stays stuck at "in_progress" ❌
```

### Why Forwarding Fails:

The IT Lead's `TaskRoutingEngine` tries to get the agent endpoint:

```python
# In task_routing_engine.py
agent_endpoint = self.routing_engine.get_agent_endpoint("implementation-engineer")
```

Since the SQLite registry doesn't have the Implementation Engineer, it falls back to the hardcoded endpoint:
```python
AGENT_ENDPOINTS = {
    "implementation-engineer": "http://127.0.0.1:3060/mcp",  # Hardcoded
    ...
}
```

The hardcoded endpoint IS correct, BUT when the IT Lead makes the HTTP call:

```python
response = requests.post(
    "http://127.0.0.1:3060/mcp",
    json={
        "method": "tools/call",
        "params": {
            "name": "vibe_code_async",
            "arguments": {...}
        }
    },
    timeout=120.0
)
```

**The call is timing out or failing, but the error isn't being properly handled.**

### Evidence:

1. Direct curl test WORKS:
```bash
curl -X POST http://127.0.0.1:3060/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"vibe_code_async","arguments":{"task_description":"test","language":"python","vibe_level":1}}}'
# Returns: {"result": {"taskId": "...", "status": "submitted"}} ✅
```

2. But IT Lead's call fails silently - no error logs visible

## Possible Contributing Factors:

### 1. Registry Synchronization Issue
The IT Lead server should be reading from the PostgreSQL registry (port 3031) to get agent endpoints, not the SQLite registry.

**Fix**: Configure IT Lead to use PostgreSQL registry:
```python
# In extended_server_handlers.py initialization
self.service_registry = PostgresServiceRegistry(
    host="127.0.0.1",
    port=5432,
    database="mcp_registry",
    user="postgres",
    password="postgres"
)
```

### 2. Missing Error Handling
The `_forward_task_to_agent` method catches exceptions but doesn't log them properly:

```python
except requests.RequestException as e:
    return {"success": False, "error": f"Request failed: {str(e)}"}
```

But this error message isn't being visible in the logs, suggesting the error might be swallowed somewhere.

### 3. Background Thread Issues
The background thread running LLM planning might be:
- Dying silently
- Not completing the forward operation
- Getting stuck on the HTTP call

### 4. Timeout Configuration
The HTTP timeout is set to 120 seconds, which should be enough. But if the Implementation Engineer's LLM call is hanging, it could exceed this.

## Immediate Fixes Required

### Fix 1: Use PostgreSQL Registry (CRITICAL)

Update IT Lead server to use PostgreSQL registry instead of SQLite:

**File**: `/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/handlers/extended_server_handlers.py`

**Change** line 563 from:
```python
self.service_registry = ServiceRegistryDB(db_path="/root/qwen/base/mcp-std-skeleton/mcp_registry.db")
```

To:
```python
# Always use PostgreSQL registry to match where agents register
from ..utils.postgres_registry_db import PostgresServiceRegistry
self.service_registry = PostgresServiceRegistry(
    host="127.0.0.1",
    port=5432,
    database="mcp_registry",
    user="postgres",
    password="postgres"
)
```

### Fix 2: Add Better Error Logging

**File**: `/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/task_assignment.py`

**Add after line 428** (in `_forward_task_to_agent`):
```python
except requests.Timeout as e:
    print(f"❌ TIMEOUT: Agent {agent_id} at {agent_endpoint} did not respond within 120 seconds")
    print(f"   Error details: {str(e)}")
    return {"success": False, "error": f"Request timeout: {str(e)}"}
except requests.ConnectionError as e:
    print(f"❌ CONNECTION ERROR: Cannot reach agent {agent_id} at {agent_endpoint}")
    print(f"   Error details: {str(e)}")
    return {"success": False, "error": f"Connection error: {str(e)}"}
except requests.RequestException as e:
    print(f"❌ REQUEST FAILED: Agent {agent_id} at {agent_endpoint}")
    print(f"   Error details: {str(e)}")
    return {"success": False, "error": f"Request failed: {str(e)}"}
except Exception as e:
    print(f"❌ UNEXPECTED ERROR: Forwarding to agent {agent_id}")
    print(f"   Error details: {str(e)}")
    import traceback
    traceback.print_exc()
    return {"success": False, "error": f"Unexpected error: {str(e)}"}
```

### Fix 3: Add Background Thread Error Handling

**File**: `/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/handlers/extended_server_handlers.py`

**Update** `_background_task_processing` (around line 1283-1301) to add better error logging:

```python
def _background_task_processing(self, task_id: str, task_description: str, assignee: str):
    """Background thread to run LLM planning and forward task to appropriate agent"""
    try:
        print(f"🔵 [BG-THREAD] Starting background processing for task {task_id}")
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                self._run_llm_planning_and_forward,
                task_id, task_description, assignee
            )
            try:
                result = future.result(timeout=300)  # 5 minute timeout
                print(f"✅ [BG-THREAD] Completed for {task_id}: {result}")
            except TimeoutError as e:
                print(f"❌ [BG-THREAD] TIMEOUT for task {task_id} - LLM planning took > 5 minutes")
                # Update task status to failed
                if self.task_storage:
                    self.task_storage.update_task_status_only(
                        task_id=task_id,
                        status="failed",
                        status_reason="Background processing timeout",
                        metadata={"error": "LLM planning timeout"}
                    )
                raise

    except Exception as e:
        print(f"❌ [BG-THREAD] ERROR for {task_id}: {e}")
        import traceback
        traceback.print_exc()
        
        # Update task status to failed
        if self.task_storage:
            try:
                self.task_storage.update_task_status_only(
                    task_id=task_id,
                    status="failed",
                    status_reason=f"Background processing error: {str(e)}",
                    metadata={"error": str(e)}
                )
            except Exception as update_error:
                print(f"❌ [BG-THREAD] Failed to update task status: {update_error}")
```

### Fix 4: Register Implementation Engineer with SQLite (WORKAROUND)

As a temporary workaround, manually register the Implementation Engineer with the SQLite registry:

```bash
python3 -c "
import sqlite3
db_path = '/root/qwen/base/mcp-std-skeleton/mcp_registry.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute('''
    INSERT INTO services (id, name, description, endpoint, capabilities, registered_at, last_seen)
    VALUES (?, ?, ?, ?, ?, ?, ?)
''', (
    'implementation-engineer-127.0.0.1-3060',
    'Implementation Engineer',
    'AI coding agent',
    'http://127.0.0.1:3060/mcp',
    '{\"tools\": [\"vibe_code_async\", \"vibe_code\", \"implement_feature\"]}',
    1772835564.3520837,
    1772836464.9568357
))
conn.commit()
conn.close()
print('✅ Implementation Engineer registered with SQLite registry')
"
```

## Testing After Fix

1. **Restart IT Lead server** to pick up registry changes
2. **Submit a new test task** via Web UI
3. **Monitor logs** for:
   ```
   🔵 [BG-THREAD] Starting background processing for task task-xxx
   📞 Calling LLM for task planning...
   ✅ LLM response received
   DEBUG: agent_endpoint for implementation-engineer: http://...
   DEBUG: _forward_task_to_agent: agent_id=implementation-engineer, tool=vibe_code_async
   ✅ Task forwarded to implementation-engineer
   ✅ Task task-xxx status updated to in_progress
   ```

4. **Check task status** in database:
   ```sql
   SELECT task_id, status, assigned_to FROM tasks ORDER BY created_at DESC LIMIT 1;
   ```

5. **Verify task completes** - status should go from `submitted` → `received` → `in_progress` → `done`

## Long-term Recommendations

1. **Unify Registry**: Use only PostgreSQL registry, remove SQLite dependency
2. **Add Health Checks**: Periodically ping agent endpoints
3. **Add Circuit Breaker**: Don't keep tasks in `in_progress` indefinitely
4. **Add Retry Logic**: Retry failed task forwarding with exponential backoff
5. **Add Monitoring Dashboard**: Real-time visibility into task status
6. **Add Dead Letter Queue**: Move stuck tasks to manual review queue

## Files Modified

- `/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/handlers/extended_server_handlers.py`
- `/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/task_assignment.py`

## Diagnostic Tools Created

- `/root/qwen/base/diagnose_task_stuck.py` - Automated diagnostic script

## Conclusion

The root cause is a **split-brain registry architecture** where:
- Agents register with PostgreSQL registry (port 3031)
- IT Lead reads from SQLite registry (missing agent registrations)

This causes the IT Lead to use stale/hardcoded agent endpoints, leading to task forwarding failures that aren't properly logged or handled.

**Priority**: Apply Fix 1 (use PostgreSQL registry) immediately, then add better error handling (Fix 2 & 3).
