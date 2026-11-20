# IT Lead Workflow Sequence Fix

## Problem

When LLM planning returns a workflow sequence like:
```json
{
  "primary_agent": "requirements-engineer",
  "workflow_sequence": ["requirements-engineer", "implementation-engineer"],
  ...
}
```

The task was only forwarded to the first agent (Requirements Engineer) and stopped there, never continuing to Implementation Engineer.

## Root Cause

The background poller in `task_assignment.py` only:
1. Polled for task completion
2. Updated Git URL
3. Marked task as "done"

It didn't check for `workflow_sequence` or forward to the next agent.

## Solution

### 1. Added `_handle_workflow_sequence()` Method

This method:
- Gets `workflow_sequence` from LLM plan
- Finds current agent's position in sequence
- Forwards task to next agent if sequence continues
- Updates task status to show workflow progress

### 2. Updated Background Poller

The poller now calls `_handle_workflow_sequence()` after:
- Successfully getting Git URL from completed agent
- Or even without Git URL (to continue workflow)

### 3. Updated LLM Prompts

All LLM planning prompts now explicitly request `workflow_sequence`:

```json
{
    "primary_agent": "requirements-engineer",
    "workflow_sequence": ["requirements-engineer", "implementation-engineer"],
    "tools": {
        "requirements-engineer": "analyze_requirements",
        "implementation-engineer": "vibe_code_async"
    },
    ...
}
```

**Key instructions added to prompts:**
- "**ALWAYS provide the full workflow_sequence** - list ALL agents that should be involved in order"
- "If NO language/technology specified, the workflow MUST start with requirements-engineer"
- "If task is ambiguous or lacks technical details: start with requirements-engineer, then forward to implementation-engineer"

### 4. Workflow Flow

```
Task Submitted
    ↓
IT Lead LLM Planning
    ↓
LLM Returns: {workflow_sequence: ["requirements-engineer", "implementation-engineer"]}
    ↓
Forward to Requirements Engineer (step 1/2)
    ↓
Background Poller waits for completion
    ↓
Requirements Engineer completes → Git URL stored
    ↓
_handle_workflow_sequence() checks sequence
    ↓
Finds next agent: "implementation-engineer"
    ↓
Forward to Implementation Engineer (step 2/2)
    ↓
Background Poller waits again
    ↓
Implementation Engineer completes → Git URL stored
    ↓
_handle_workflow_sequence() checks sequence
    ↓
No more agents in sequence → Task marked "done"
```

## Files Modified

1. **`it-lead-mcp-server/it_lead_mcp_server/utils/task_assignment.py`**
   - Updated `background_poller()` to call `_handle_workflow_sequence()`
   - Added `_handle_workflow_sequence()` method
   - Stores `llm_plan` in metadata (already done)

2. **`it-lead-mcp-server/it_lead_mcp_server/utils/llm_task_planner.py`**
   - Updated `_build_no_match_prompt()` - Added workflow_sequence instructions
   - Updated `_build_low_confidence_prompt()` - Added workflow_sequence instructions
   - Updated `_build_conflict_prompt()` - Already had workflow_sequence
   - Updated `_build_general_prompt()` - Added workflow_sequence instructions
   - Updated `_get_fallback_plan()` - Returns workflow_sequence

## Testing

Submit a task that requires requirements analysis first:
```bash
curl -X POST http://localhost:8000/api/tasks/assign \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test-workflow-001",
    "title": "Test Workflow Sequence",
    "description": "I need help analyzing requirements and then implementing a feature",
    "assignee": "IT Lead",
    "priority": "high"
  }'
```

Expected behavior:
1. LLM planning returns workflow_sequence: ["requirements-engineer", "implementation-engineer"]
2. Task goes to Requirements Engineer first
3. Status shows "step 1/2 in workflow"
4. After Requirements Engineer completes, task auto-forwards to Implementation Engineer
5. Status shows "step 2/2 in workflow"
6. Task marked "done" only after Implementation Engineer completes

## LLM Prompt

The LLM is already prompted to return `workflow_sequence`:

```json
{
    "workflow_sequence": ["requirements-engineer", "implementation-engineer", "code-reviewer"],
    ...
}
```

This is used by the new workflow sequence handler.
