# Dynamic Agent ID Matching - Fix for LLM Routing

## Problem

When LLM recommended an agent like `"Requirement Engineer MCP Server on 0.0.0.0:3062"`, the code tried to match it against hardcoded agent names, failed, and fell back to Implementation Engineer.

### Root Cause

1. **LLM received:** Full server names (e.g., "Requirement Engineer MCP Server on 0.0.0.0:3062")
2. **LLM returned:** That full name in `recommended_agent`
3. **Code tried to match:** Against hardcoded list `["implementation-engineer", "requirements-engineer", ...]`
4. **Match failed:** `"requirement-engineer-mcp-server-on-0.0.0.0:3062"` not in list
5. **Fallback:** Used `"implementation-engineer"` (wrong!)

## Solution

Use **dynamic agent_id** that is:
1. Generated from discovered agent data
2. Shown to LLM in prompt
3. Returned by LLM in response
4. Used directly for endpoint lookup (no hardcoded matching)

## Changes Made

### 1. mcp_registry_client.py

**Added `_generate_agent_id()` method:**
```python
def _generate_agent_id(self, service_name: str) -> str:
    """Generate normalized agent_id from service name."""
    # "Requirement Engineer MCP Server on 0.0.0.0:3062" → "requirements-engineer"
```

**Updated `discover_all_agents_with_tools()`:**
```python
agent_info = {
    "agent_id": agent_id,  # NEW: Normalized ID for LLM matching
    "name": service_name,
    "endpoint": endpoint,
    "description": ...,
    "status": ...,
    "tools": ...
}
```

### 2. llm_task_planner.py

**Updated `_build_agents_section_from_discovery()`:**
```python
# Show agent with its ID for reference
section += f"{i}. **{agent_name}** (ID: `{agent_id}`)\n"
section += f"   - Endpoint: `{endpoint}`\n"
```

**Updated response format instructions:**
```json
{
    "recommended_agent": "agent-id (use the ID shown in the agent list above)"
}
```

### 3. task_assignment.py

**Replaced hardcoded matching with dynamic lookup:**
```python
# OLD (hardcoded):
known_agents = ["implementation-engineer", "requirements-engineer", ...]
if normalized_agent not in known_agents:
    primary_agent = "implementation-engineer"  # WRONG!

# NEW (dynamic):
agents_list = self.routing_engine.mcp_registry_client.discover_all_agents_with_tools()
for agent in agents_list:
    agent_id = agent.get("agent_id")
    if agent_id.lower() == primary_agent.lower():
        agent_endpoint = agent.get("endpoint")  # CORRECT!
        break
```

## Flow Diagram

### Before (Broken)
```
LLM Prompt: "Requirement Engineer MCP Server on 0.0.0.0:3062"
     ↓
LLM Response: {"recommended_agent": "Requirement Engineer MCP Server on 0.0.0.0:3062"}
     ↓
Code normalizes: "requirement-engineer-mcp-server-on-0.0.0.0:3062"
     ↓
Check hardcoded: NOT IN ["implementation-engineer", ...]
     ↓
Fallback: "implementation-engineer" ← WRONG!
     ↓
Endpoint: http://0.0.0.0:3060/mcp ← WRONG PORT!
```

### After (Fixed)
```
LLM Prompt: "Requirement Engineer (ID: `requirements-engineer`)"
     ↓
LLM Response: {"recommended_agent": "requirements-engineer"}
     ↓
Dynamic lookup: Find agent with agent_id="requirements-engineer"
     ↓
Found: {"agent_id": "requirements-engineer", "endpoint": "http://0.0.0.0:3062/mcp"}
     ↓
Endpoint: http://0.0.0.0:3062/mcp ← CORRECT!
```

## Testing

### Test agent_id generation:
```bash
cd /root/qwen/base
python3 -c "
from it_lead_mcp_server.utils.mcp_registry_client import McpRegistryClient
client = McpRegistryClient('http://127.0.0.1:3031/mcp')

test_names = [
    'Requirement Engineer MCP Server on 0.0.0.0:3062',
    'Implementation Engineer: on 0.0.0.0:3060',
    'DevOps Release Engineer Server on 0.0.0.0:3071',
]

for name in test_names:
    agent_id = client._generate_agent_id(name)
    print(f'{name[:50]}... → {agent_id}')
"
```

**Expected output:**
```
Requirement Engineer MCP Server on 0.0.0.0:3062... → requirements-engineer
Implementation Engineer: on 0.0.0.0:3060... → implementation-engineer
DevOps Release Engineer Server on 0.0.0.0:3071... → devops-engineer
```

### Test full discovery:
```bash
python3 -c "
from it_lead_mcp_server.utils.mcp_registry_client import McpRegistryClient
client = McpRegistryClient('http://127.0.0.1:3031/mcp')
agents = client.discover_all_agents_with_tools(use_cache=False)
for agent in agents:
    print(f'agent_id: {agent.get(\"agent_id\")}, endpoint: {agent.get(\"endpoint\")}')
"
```

**Expected output:**
```
agent_id: requirements-engineer, endpoint: http://0.0.0.0:3062/mcp
agent_id: implementation-engineer, endpoint: http://0.0.0.0:3060/mcp
agent_id: devops-engineer, endpoint: http://0.0.0.0:3071/mcp
```

## Files Modified

1. `it-lead-mcp-server/it_lead_mcp_server/utils/mcp_registry_client.py`
   - Added `_generate_agent_id()` method
   - Updated `discover_all_agents_with_tools()` to include `agent_id`

2. `it-lead-mcp-server/it_lead_mcp_server/utils/llm_task_planner.py`
   - Updated `_build_agents_section_from_discovery()` to show `agent_id`
   - Updated response format instructions

3. `it-lead-mcp-server/it_lead_mcp_server/utils/task_assignment.py`
   - Replaced hardcoded agent matching with dynamic lookup
   - Now uses `agent_id` from LLM response to find endpoint

## Benefits

1. **No hardcoded agent names** - All agent info comes from dynamic discovery
2. **Correct routing** - LLM recommendations are matched correctly
3. **Scalable** - New agents automatically supported without code changes
4. **Maintainable** - Single source of truth (MCP Registry)

## Next Steps

1. Restart IT Lead server to load new code
2. Submit test task that should go to Requirements Engineer
3. Verify task is forwarded to correct endpoint (port 3062, not 3060)
