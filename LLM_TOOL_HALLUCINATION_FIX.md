# LLM Tool Hallucination Fix

## Problem Identified
When the LLM was asked to plan task assignments, it was **hallucinating tool names** that don't exist in the system.

### Example:
**Task**: "Create a Flappy Bird game in HTML"

**LLM Response**:
```json
{
  "primary_agent": "implementation-engineer",
  "tools": {
    "implementation-engineer": "code-editor"  ❌ WRONG! This tool doesn't exist
  }
}
```

**Result**: Task failed with error `"Internal error: Tool 'code-editor' not found"` and was stored inline instead of in Git.

## Root Cause
The LLM prompt included **available agents** but **NOT available tools** for each agent. Without this information, the LLM made up tool names based on its training data rather than using the actual tools available in the system.

## Solution Implemented

### 1. Added `_get_available_tools()` Method
```python
def _get_available_tools(self) -> Dict[str, List[str]]:
    """Get available tools for each agent from the service registry"""
    available_tools = {}
    
    # Map service names to agents and their tools
    if "implementation" in service_name:
        available_tools["implementation-engineer"] = [
            "vibe_code_async",
            "vibe_code",
            "implement_feature",
            "generate_code_from_spec",
            "generate_unit_tests"
        ]
    # ... other agents
```

### 2. Updated LLM Prompts to Include Tools
Added a new section to all LLM planning prompts:

```
## Available Tools
- **implementation-engineer**: `vibe_code_async`, `vibe_code`, `implement_feature`, ...
- **requirements-engineer**: `analyze_requirements`, ...
- **code-reviewer**: `review_code`, ...
- **qa-test-engineer**: `test_execution_suite`, ...
```

### 3. Added Critical Instructions
```
## CRITICAL INSTRUCTION: 
- ALL coding, development, implementation, frontend, web, JavaScript, Python, React, HTML, CSS tasks MUST go to implementation-engineer
- ONLY use tools listed under "Available Tools" above - DO NOT invent tool names
- For implementation-engineer coding tasks, use `vibe_code_async`
```

## Files Modified

1. `/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/llm_task_planner.py`
   - Added `_get_available_tools()` method
   - Updated `plan_task_assignment()` to fetch and pass available tools
   - Updated `_build_conflict_prompt()` to include tools section
   - Updated all prompt builders to include available tools

## Expected Outcome

Now when the LLM plans task assignments:
1. ✅ It receives the list of actual available tools for each agent
2. ✅ It will only recommend tools that exist in the system
3. ✅ Tasks will be successfully forwarded to agents
4. ✅ Results will be stored in Git (not inline)
5. ✅ No more "Tool not found" errors

## Testing

To verify the fix:
1. Submit a coding task: "Create a Python script that calculates Fibonacci"
2. Check logs for "Available tools:" message
3. Verify LLM response uses `vibe_code_async` (not "code-editor")
4. Task should complete with Git storage

## Key Takeaway

**Always provide the LLM with the actual available options** when asking it to make decisions. Without this context, it will hallucinate based on its training data rather than using the real system capabilities.
