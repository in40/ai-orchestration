# Fix Summary: Frontend Developer Agent Issue

## Problem Description

Some jobs were being assigned to `frontend-developer-agent` which doesn't exist in the registry, causing the message:
```
Task assigned to frontend-developer-agent (agent offline)
```

## Root Cause

The LLM task planner was returning `frontend-developer-agent` as the primary agent when it should have been routing to `implementation-engineer`. This happened because:

1. The LLM prompts mentioned agents but didn't explicitly state that coding tasks MUST go to `implementation-engineer`
2. The fallback plan was using `implement_feature` instead of `vibe_code_async` for coding tasks
3. No validation was in place to reject unknown agent names

## Changes Made

### 1. Updated LLM Task Planner Prompts (`llm_task_planner.py`)

**Before:**
```
Note: Implementation tasks should be handled by requirements-engineer for task decomposition.
```

**After:**
```
## CRITICAL INSTRUCTION: ALL coding, development, implementation, frontend, web, JavaScript, Python, React, HTML, CSS tasks MUST go to implementation-engineer. Do NOT use requirements-engineer for coding tasks.
```

This was applied to:
- `_build_no_match_prompt()` 
- `_build_low_confidence_prompt()`
- `_build_conflict_prompt()`
- `_build_general_prompt()`

### 2. Updated Fallback Plan (`llm_task_planner.py`)

**Before:**
```python
if any(kw in description_lower for kw in ["python", "code", "implement", "create"]):
    agent = "implementation-engineer"
    tool = "implement_feature"
```

**After:**
```python
if any(kw in description_lower for kw in ["python", "code", "implement", "create"]):
    agent = "implementation-engineer"
    tool = "vibe_code_async"
elif any(kw in description_lower for kw in ["javascript", "js", "react", "frontend", "html", "css"]):
    agent = "implementation-engineer"
    tool = "vibe_code_async"
```

### 3. Added Agent Validation (`task_assignment.py`)

Added validation to reject unknown agent names and fall back to `implementation-engineer`:

```python
known_agents = ["implementation-engineer", "requirements-engineer", "code-reviewer", 
               "qa-test-engineer", "security-engineer", "devops-engineer", "it-lead"]

if normalized_agent not in known_agents:
    print(f"⚠️  Warning: Unknown agent '{primary_agent}' - falling back to implementation-engineer")
    primary_agent = "implementation-engineer"
    tool = "vibe_code_async"
```

### 4. Updated Routing Rules (`task_routing_rules.py`)

1. **rule-1.0b (Web Page Implementation)**: Reduced confidence threshold from 0.6 to 0.5

2. **Added new rule-1.0c (Frontend Implementation Request)**: More specific rule for frontend tasks with confidence 0.6

3. **Added new rule-1.0d (JavaScript/Node.js Implementation)**: New rule for JS/TS tasks with confidence 0.7

## Expected Outcome

After these fixes:

1. All coding/frontend tasks will be routed to `implementation-engineer`
2. LLM planning will never return invalid agent names
3. Unknown agent names are rejected and fall back to `implementation-engineer`
4. All async coding tasks use `vibe_code_async` for Git-based result storage

## Files Modified

1. `/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/llm_task_planner.py`
2. `/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/task_assignment.py`
3. `/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/task_routing_rules.py`
