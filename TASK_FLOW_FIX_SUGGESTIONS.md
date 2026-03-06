# Task Flow Bug Fixes - Suggestions & Implementation Plan

## Executive Summary

The task `task-1772378783506` got stuck in "received" state after the LLM generated code successfully. After investigation, we identified **three critical bugs** in the MCP system:

| Bug # | Location | Severity | Impact |
|-------|----------|----------|--------|
| 1 | `task_assignment.py:337` | Critical | Status never updates after forwarding |
| 2 | `task_assignment.py:125` | High | Task status overwritten to "received" |
| 3 | `vibe_coder.py:223` | Critical | No result backflow from async tasks |

---

## Bug #1: `_update_task_status` is a Placeholder

### Current Code (`it-lead-mcp-server/it_lead_mcp_server/utils/task_assignment.py`)
```python
def _update_task_status(self, task_id: str, status: str, 
                       status_reason: str, extra_metadata: Optional[Dict[str, Any]] = None):
    """Update task status in the database"""
    if not self.task_storage:
        return
    
    # Note: We would need to add an update_task_status method to TaskStorage
    # For now, this is a placeholder
    print(f"Updating task {task_id} status to {status}: {status_reason}")
```

### Problem
- Only prints to console
- Never calls the actual task storage update method
- Tasks get stuck in intermediate states forever

### Proposed Fix

#### Option A: Implement using existing TaskStorage method (Recommended)
```python
def _update_task_status(self, task_id: str, status: str, 
                       status_reason: str, extra_metadata: Optional[Dict[str, Any]] = None):
    """Update task status in the database"""
    if not self.task_storage:
        return
    
    try:
        # Use the existing update_task_status_if_exists method from TaskStorage
        if hasattr(self.task_storage, 'update_task_status_if_exists'):
            self.task_storage.update_task_status_if_exists(
                task_id=task_id,
                status=status,
                status_reason=status_reason,
                extra_metadata=extra_metadata
            )
        else:
            print(f"WARNING: TaskStorage does not have update_task_status_if_exists method")
            # Fallback: create a status update entry in the history
            self.task_storage.store_received_task(
                task_id=task_id,
                title=None,  # Keep existing title
                description=None,  # Keep existing description
                status=status,
                status_reason=status_reason,
                metadata=extra_metadata,
                # Pass None to keep existing values
                keep_existing=True  # Add parameter to preserve existing data
            )
    except Exception as e:
        print(f"ERROR updating task {task_id} status: {e}")
```

#### Option B: Add new method to TaskStorage (Cleaner)
**Add to `task_storage.py`:**
```python
def update_task_status(self, task_id: str, status: str, 
                      status_reason: Optional[str] = None,
                      extra_metadata: Optional[Dict[str, Any]] = None) -> bool:
    """Update task status without overwriting all fields"""
    try:
        cursor = self.connection.cursor()
        
        # Build dynamic UPDATE query
        updates = ["status = %s", "updated_at = CURRENT_TIMESTAMP"]
        values = [status]
        
        if status_reason:
            updates.append("status_reason = %s")
            values.append(status_reason)
        
        if extra_metadata:
            updates.append("metadata = metadata || %s")
            values.append(json.dumps(extra_metadata))
        
        values.append(task_id)
        
        query = f"UPDATE task_registry SET {', '.join(updates)} WHERE task_id = %s"
        cursor.execute(query, values)
        
        self.connection.commit()
        cursor.close()
        
        affected = cursor.rowcount if hasattr(cursor, 'rowcount') else cursor.rowcount
        print(f"✅ Task status updated: {task_id} -> {status}")
        return affected > 0
    except Exception as e:
        print(f"❌ Error updating task status: {e}")
        self.connection.rollback()
        return False
```

---

## Bug #2: Task Status Overwritten in `assign_and_forward_task`

### Current Code (`it-lead-mcp-server/it_lead_mcp_server/utils/task_assignment.py:125-147`)
```python
# Step 3: Store task in database with initial status
if self.task_storage:
    status_history_entry = {
        "status": "received",
        "timestamp": time.time(),
        "reason": f"Task assigned via assign_task tool, routed to {primary_agent}"
    }

    self.task_storage.store_received_task(
        task_id=task_id,
        # ... all parameters ...
        status="received",  # ← This overwrites "submitted"
        status_reason=f"Task received, routing to {primary_agent}"
    )
```

### Problem
- `_execute_assign_task_async` stores task with `"submitted"` status
- `assign_and_forward_task` immediately overwrites it with `"received"`
- The `"submitted"` → `"forwarded"` status transition is lost

### Proposed Fix

#### Option A: Check if task exists before overwriting (Recommended)
```python
# Step 3: Update task status if it exists, otherwise store
if self.task_storage:
    # Check if task already exists (was stored as "submitted")
    existing_task = self.task_storage.get_task(task_id)
    
    status_reason = f"Task assigned via assign_task tool, routed to {primary_agent}"
    
    if existing_task:
        # Update only status and history for existing task
        self.task_storage.update_task_status(
            task_id=task_id,
            status="received",
            status_reason=status_reason,
            extra_metadata={
                "tool_call": "assign_task",
                "routing_decision": {
                    "matched_rule_id": routing_decision.matched_rule_id,
                    "confidence": routing_decision.confidence,
                    "requires_llm_planning": routing_decision.requires_llm_planning
                },
                "llm_plan": llm_plan
            }
        )
    else:
        # Store new task
        self.task_storage.store_received_task(
            task_id=task_id,
            title=f"Task: {task_id}",
            description=task_description,
            # ... other parameters ...
            status="received",
            status_reason=status_reason
        )
```

#### Option B: Use different status based on flow
```python
# Skip storing "received" status - the "submitted" from _execute_assign_task_async is sufficient
# The forwarding step will update to "forwarded" status
```

---

## Bug #3: No Result Backflow from Async Tasks

### Current Code (`mcp-std-coder/mcp-vibe-coding-agent/dependencies/vibe_coder.py:223-241`)
```python
elif tool["name"] == "vibe_code_async":
    # Create an async task
    try:
        task_id = task_manager.create_task(arguments)

        # Submit for background processing
        def llm_call_wrapper(input_args):
            prompt = create_vibe_code_prompt(input_args)
            return {"result": call_llm_sync(prompt, input_args.get("vibe_level", 5), server_handlers)}

        task_manager.submit_for_processing(task_id, llm_call_wrapper)

        return {"taskId": task_id, "status": "submitted"}  # ← Returns immediately
    except Exception as e:
        return {"error": f"Failed to create async task: {str(e)}"}
```

### Problem
1. Returns `{"taskId": "async-123", "status": "submitted"}` immediately
2. LLM generates code in background
3. Result stored in `async_tasks` table
4. **IT Lead never retrieves the result!**

### Proposed Fix

#### Option A: Poll for completion and update IT Lead's registry (Recommended)
**Add to `task_assignment.py`:**
```python
def _poll_async_task_completion(self, task_id: str, agent_endpoint: str, 
                                timeout: int = 300, poll_interval: int = 2) -> Dict[str, Any]:
    """Poll async task for completion and return result"""
    import time
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.post(
                agent_endpoint,
                json={
                    "jsonrpc": "2.0",
                    "id": f"task-status-{task_id}",
                    "method": "tools/call",
                    "params": {
                        "name": "tasks/get",
                        "arguments": {"task_id": task_id}
                    }
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    task_data = result["result"]
                    status = task_data.get("status", "unknown")
                    
                    if status == "completed":
                        # Get the actual result
                        result_response = requests.post(
                            agent_endpoint,
                            json={
                                "jsonrpc": "2.0",
                                "id": f"task-result-{task_id}",
                                "method": "tools/call",
                                "params": {
                                    "name": "tasks/result",
                                    "arguments": {"task_id": task_id}
                                }
                            },
                            timeout=10.0
                        )
                        
                        if result_response.status_code == 200:
                            result_data = result_response.json()
                            return {
                                "success": True,
                                "result": result_data.get("result"),
                                "taskId": task_id
                            }
                    
                    elif status == "failed":
                        return {
                            "success": False,
                            "error": task_data.get("error", "Task failed"),
                            "taskId": task_id
                        }
            
            time.sleep(poll_interval)
            
        except Exception as e:
            print(f"Error polling task {task_id}: {e}")
            time.sleep(poll_interval)
    
    return {
        "success": False,
        "error": f"Timeout waiting for task {task_id}",
        "taskId": task_id
    }
```

**Modify `assign_and_forward_task` to poll async tasks:**
```python
# After forwarding to agent
if tool == "vibe_code_async" and forward_result.get("success"):
    # Get the async task ID from response
    async_task_id = forward_result.get("response", {}).get("result", {}).get("taskId")
    
    if async_task_id:
        # Poll for completion
        poll_result = self._poll_async_task_completion(
            async_task_id, 
            agent_endpoint,
            timeout=300,  # 5 minutes
            poll_interval=2
        )
        
        if poll_result.get("success"):
            result["status"] = "completed"
            result["result"] = poll_result.get("result")
            
            # Update task storage with final result
            if self.task_storage:
                self.task_storage.update_task_status(
                    task_id=task_id,
                    status="completed",
                    status_reason=f"Async task {async_task_id} completed",
                    extra_metadata={"async_task_id": async_task_id, "code_result": poll_result.get("result")}
                )
        else:
            result["status"] = "failed"
            result["error"] = poll_result.get("error")
```

#### Option B: Use callback mechanism (More complex)
Implement a webhook/callback endpoint that the implementation engineer calls when async tasks complete.

---

## Implementation Priority

### Phase 1: Critical (Fix task getting stuck)
1. **Fix Bug #1** - Implement `_update_task_status` to actually update database
2. **Fix Bug #2** - Prevent status overwrite in `assign_and_forward_task`

### Phase 2: High Priority (Enable code retrieval)
3. **Fix Bug #3** - Add async task polling and result backflow

### Phase 3: Optional (Enhancements)
4. Add async task monitoring dashboard
5. Add task timeout handling
6. Add retry logic for failed forwarding

---

## Testing Checklist

After implementing fixes:
- [ ] Task should move from "submitted" → "received" → "forwarded" → "completed"
- [ ] LLM-generated code should be stored in task registry
- [ ] Web UI should show task completion with code result
- [ ] `tasks/get` should return async task status
- [ ] `tasks/result` should return async task result
- [ ] Task history should show all status transitions

---

## Files to Modify

| File | Lines | Change Type |
|------|-------|-------------|
| `it-lead-mcp-server/it_lead_mcp_server/utils/task_assignment.py` | 337-341 | Fix Bug #1 |
| `it-lead-mcp-server/it_lead_mcp_server/utils/task_assignment.py` | 125-147 | Fix Bug #2 |
| `it-lead-mcp-server/it_lead_mcp_server/utils/task_assignment.py` | Add new method | Fix Bug #3 |
| `it-lead-mcp-server/it_lead_mcp_server/utils/task_storage.py` | Add new method | Fix Bug #1 (Option B) |
