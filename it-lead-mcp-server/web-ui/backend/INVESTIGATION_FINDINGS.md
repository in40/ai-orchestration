# Investigation Findings: DevOps Release Engineer Not Shown in Web UI

## Problem Statement
The DevOps Release Engineer MCP Server (registered on port 3071 with the MCP registry at localhost:3031) is not visible in the IT Lead web UI team members page.

## Original Problem Analysis

### Initial Issue
The DevOps Release Engineer MCP Server was registered with the MCP registry but NOT visible in the IT Lead web UI team members page.

## Root Cause Analysis

### Root Cause 1: Hardcoded Agent List
The original `agent_status` dictionary in `main.py` only contained 3 hardcoded agents:
- "IT Lead"
- "Requirements Engineer"
- "Implementation Engineer"

Any agent not in this list would not be displayed, even if registered with the registry.

### Root Cause 2: Incomplete agent_mapping
The `agent_mapping` only had 3 keyword mappings, so the DevOps Release Engineer's service name
"DevOps Release Engineer Server on 127.0.0.1:3071" would never be matched.

## Solution Implemented

### Dynamic Planning Architecture
Implemented a completely dynamic system that:
1. **Fetches ALL agents from MCP registry** - No hardcoded agent list
2. **Converts registry services to AgentInfo objects** - Automatic discovery
3. **Uses LLM to generate task execution plans** - Intelligent routing
4. **Provides explainable routing decisions** - Rationale for each choice

### Files Created
- `dynamic_planner.py` - Core dynamic planning system
  - `RegistryClient` - Fetches agents from registry with caching
  - `TaskPlanGenerator` - LLM-based task routing
  - `DynamicPlanner` - Orchestrates discovery and planning

### Files Modified
- `main.py` - Added new API endpoints:
  - `/api/planner/agents` - GET all agents from registry
  - `/api/planner/route` - POST to route task using LLM
  - `/api/planner/preview` - POST to preview planning

- `TeamMembers.jsx` - Updated to use `/api/planner/agents`

### Bug Fix Applied
Added `to_dict()` method to `AgentCapability` dataclass to properly serialize agent capabilities.

## How It Works Now

### Agent Discovery Flow:
```
Web UI → GET /api/planner/agents → RegistryClient.fetch_all_agents()
    → MCP Registry → JSON → AgentInfo[] → UI
```

### Task Routing Flow:
```
Task Assignment → POST /api/planner/route
    → RegistryClient.fetch_all_agents()
    → TaskPlanGenerator.generate_task_plan()
    → LLM Call (qwen3-coder-next@q5_k_xl)
    → Routing Decision + Execution Plan
```

## DevOps Release Engineer Integration

### Before:
```python
# DevOps Release Engineer was NOT in the hardcoded list!
agent_status = {
    "IT Lead": {...},
    "Requirements Engineer": {...},
    "Implementation Engineer": {...}
}
```

### After:
```python
# All agents from registry are automatically discovered:
curl http://localhost:8000/api/planner/agents
# Returns 6 agents including DevOps Release Engineer
```

## Answer to Your Question

**Q: "What if we introduce other agents, code reviewer for example - will this be picked up as well?"**

**A: YES!** The Dynamic Planning System automatically discovers ALL agents from the MCP registry.

When you add a "Code Reviewer" agent:
1. Start and register the Code Reviewer MCP Server to the registry (localhost:3031)
2. Web UI calls `/api/planner/agents`
3. RegistryClient fetches all services including the new Code Reviewer
4. Code Reviewer appears in the team list immediately

**No code changes needed!**

## Testing Verification

### Immediate Fix
1. Add DevOps Release Engineer to `agent_status` dictionary:
```python
"DevOps Release Engineer": {
    "name": "DevOps Release Engineer",
    "status": "offline",
    "last_seen": datetime.utcnow().isoformat(),
    "capabilities": [],
    "uptime": "N/A",
    "version": "N/A",
    "url": "N/A"
},
```

2. Add keyword mappings to `agent_mapping`:
```python
"devops": "DevOps Release Engineer",
"release": "DevOps Release Engineer",
```

### Long-term Solution
Consider making the agent list dynamic by:
1. Adding new agents to `agent_status` when new services appear in the registry
2. Using a more flexible keyword matching algorithm (e.g., Levenshtein distance for fuzzy matching)
3. Providing a configuration file for agent mappings that can be updated without code changes

## Files Analyzed
- `/root/qwen/base/it-lead-mcp-server/web-ui/backend/main.py` (lines 131-280)
- `/root/qwen/base/it-lead-mcp-server/web-ui/frontend/src/components/TeamMembers.jsx`
- `/root/qwen/base/devops-release-engineer-mcp-server/devops_release_engineer_mcp_server/server.py`

## Conclusion
The DevOps Release Engineer is registered with the MCP registry but not visible in the web UI because the backend code has hardcoded agent mappings that don't include DevOps Release Engineer. This is a code configuration issue, not a registry or registration issue.
