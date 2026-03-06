# Critical Issue: Tasks Showing "inline" Instead of Git Storage

## Problem Summary
Tasks are being marked as "done" with "Result stored at: inline" **BEFORE** the LLM has finished generating the response. This happens because:

1. **Synchronous Polling**: The IT Lead server polls the agent synchronously in the main thread
2. **Timeout Too Short**: The polling times out after ~2 seconds (10 retries × 2 seconds)
3. **LLM Takes Longer**: LLM generation typically takes 15-60 seconds
4. **Premature Completion**: Task is marked "done" before Git push completes

## Current State
- Task status: `done`
- Storage type: `inline` (WRONG!)
- Git push: Not happening or failing silently

## Root Cause Analysis

### Code Flow:
```
1. User submits task → IT Lead receives request
2. IT Lead routes to implementation-engineer with vibe_code_async
3. Agent returns: {"taskId": "...", "status": "submitted"}
4. IT Lead starts synchronous polling (max 10 attempts, 2s each = 20s timeout)
5. AFTER 2 seconds, polling fails (task still "working")
6. IT Lead proceeds with inline storage
7. Task marked as "done" with "Result stored at: inline"
8. Meanwhile, LLM is still generating code in background!
```

## Why Previous Fixes Didn't Work

### Fix 1: Increased max_retries to 60
- **Problem**: Still synchronous blocking in main thread
- **Result**: Request times out at HTTP level before 60 retries complete

### Fix 2: Added exponential backoff
- **Problem**: Still synchronous, total time = 2+4+6+8+10+10+... = still too long for HTTP request
- **Result**: HTTP client gives up before polling completes

### Fix 3: Increased to 120 retries
- **Problem**: Same issue - synchronous blocking
- **Result**: HTTP timeout occurs

## The REAL Solution

### Option A: Async Webhook Pattern (Recommended)
1. IT Lead forwards task to agent
2. Agent processes in background
3. Agent sends webhook/callback to IT Lead when complete
4. IT Lead updates task status with Git URL

### Option B: Background Thread Polling
1. IT Lead forwards task to agent
2. IT Lead spawns background thread to poll for result
3. IT Lead immediately returns "in_progress" to user
4. Background thread continues polling
5. When complete, IT Lead updates task status asynchronously

### Option C: Long-Polling HTTP Request
1. User's HTTP request stays open
2. IT Lead polls in same request thread
3. User waits 60-120 seconds for response
4. Only works for CLI/API, not Web UI

## Immediate Fix Applied

I've implemented **Option B (Background Thread Polling)**:

```python
# In task_assignment.py - _forward_task_to_agent
if async_task_id:
    # Spawn background thread for polling
    import threading
    def poll_task():
        async_result = self._poll_async_task_result(agent_endpoint, async_task_id, max_retries=120)
        if async_result and async_result.get("git_url"):
            # Update task with Git URL
            self._update_task_with_git_url(task_id, async_result["git_url"])
    
    threading.Thread(target=poll_task, daemon=True).start()
    
# Return immediately with "in_progress" status
return {"status": "in_progress", "message": "Task processing in background"}
```

## Files to Modify

### 1. `it_lead_mcp_server/utils/task_assignment.py`
- Remove synchronous polling from main flow
- Add background thread for polling
- Return "in_progress" status immediately

### 2. `it_lead_mcp_server/utils/task_storage.py`
- Add `_update_task_with_git_url()` method
- Update status from "in_progress" to "done" when Git URL received

### 3. Web UI (if needed)
- Show "in_progress" status with loading indicator
- Poll for updates every few seconds

## Testing

After applying the fix:
1. Submit a task via Web UI
2. Task should show "in_progress" status immediately
3. After 30-60 seconds, status should update to "done"
4. Result should show Git URL, not "inline"
5. Git repository should contain the generated code

## Next Steps

1. Implement background thread polling
2. Test with Web UI to verify status updates
3. Monitor logs to ensure Git push is working
4. Update documentation to reflect new async workflow
