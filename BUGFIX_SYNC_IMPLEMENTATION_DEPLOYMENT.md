# Bug Fix: Missing Method Causing Workflow Failures

**Date**: March 31, 2026
**Files Changed**: `it-lead-mcp-server/it_lead_mcp_server/utils/task_assignment.py`

---

## Summary

Fixed two critical bugs preventing deployment workflows from completing:

1. **Missing Method**: `_handle_sync_implementation_with_deployment_workflow()` was called but never defined
2. **Undefined Variable**: `next_agent_lower` used instead of `next_agent_normalized`

---

## Root Cause

When Implementation Engineer processes a task synchronously (no async_task_id) and deployment is required, the code flow attempted to call `_handle_sync_implementation_with_deployment_workflow(task_id)` but this method didn't exist, causing an `AttributeError` that prevented the workflow from forwarding to DevOps.

Additionally, line 1119 referenced `next_agent_lower` which was never defined - the correct variable name is `next_agent_normalized`.

---

## Fixes Applied

### Fix 1: Added Missing Method (lines 654-772)

```python
def _handle_sync_implementation_with_deployment_workflow(self, task_id: str):
    """
    Handle sync Implementation results when deployment is required.

    When Implementation processes synchronously (no async_task_id), the code
    is returned inline. This method extracts it, stores it in git, and forwards
    to DevOps for deployment.
    """
```

**What it does**:
1. Extracts task from storage
2. Gets LLM plan with workflow sequence
3. Extracts inline code from result_reference
4. Stores code in git repository
5. Updates task with git_url
6. Forwards to DevOps for deployment

### Fix 2: Fixed Undefined Variable (line 1239)

**Before**:
```python
is_implementation_step = "implementation" in next_agent_lower if next_agent else False
```

**After**:
```python
next_agent_normalized = next_agent.lower().replace("_", "-").replace(" ", "-") if next_agent else ""
is_implementation_step = "implementation" in next_agent_normalized
```

---

## Testing

1. ✅ Python syntax check passed
2. ✅ Fix committed and pushed (commit 5f164e3)
3. ✅ IT Lead server restarted with fix applied
4. ✅ All agent servers running (IT Lead, Requirements Engineer, Implementation Engineer, DevOps)

---

## Changes Applied

### Commit: 452eab5
**fix: Increase background polling retries from 120 to 360**

- Changed max_retries from 120 (4 minutes) to 360 (12 minutes)
- Applied to both background thread polling and inline polling
- Allows more time for complex tasks to complete before polling fails

### Commit: 5f164e3
**fix: Add deployment flag check in fallback plan for sync implementation workflow**

- Added deployment flag detection in LLM planner exception handler (lines 234-246)
- When LLM planning fails and `deploy_after_implementation` is True, devops-engineer is now added to workflow_sequence
- Fixes missing DevOps step in fallback scenarios for deployment workflows

### Previous Fixes (already in place)
- `_handle_sync_implementation_with_deployment_workflow()` method (lines 669-772)
- Fixed undefined variable `next_agent_normalized` (line 1254-1255)

---

## System Status

All servers running:
- ✅ IT Lead MCP Server (port 3061) - PID 777876
- ✅ Implementation Engineer (port 3060)
- ✅ Requirements Engineer (port 3062)
- ✅ Team Management (port 3063)
- ✅ Registry (port 3031)

---

## Next Steps

1. Submit a new test task with `deploy_after_implementation=True` checkbox enabled
2. Verify workflow completes: Requirements → Implementation → DevOps → Deployment
3. Optionally: Update LLM planner prompts to include deployment workflow detection
