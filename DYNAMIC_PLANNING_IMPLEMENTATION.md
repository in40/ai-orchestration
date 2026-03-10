# Dynamic Planning System Implementation

## Overview

Implemented a flexible, dynamic task routing system that discovers and plans based on all available MCP agents without hardcoded agent mappings.

## Architecture Components

### 1. Dynamic Planner (`dynamic_planner.py`)

**Location**: `/root/qwen/base/it-lead-mcp-server/web-ui/backend/dynamic_planner.py`

**Key Classes**:

#### `RegistryClient`
- Fetches all registered agents from MCP registry
- Caches agent information for 5 minutes
- Converts registry service entries to `AgentInfo` objects
- Handles network errors gracefully with fallback

#### `TaskPlanGenerator`
- Generates execution plans using LLM
- Formats agent capabilities for LLM consumption
- Creates routing decisions with rationale
- Returns confidence scores and complexity assessments

#### `DynamicPlanner` (Orchestrator)
- Combines registry fetching and LLM planning
- Provides `route_task()` method for end-to-end routing
- Exposes `get_available_agents()` for UI display

### 2. Backend API Endpoints (`main.py`)

**New Endpoints Added**:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/planner/agents` | GET | Get all agents from registry |
| `/api/planner/route` | POST | Route task using dynamic planning |
| `/api/planner/preview` | POST | Preview dynamic plan without execution |

## How It Works

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

### LLM Prompt Structure:
```
Available Agents:
## DevOps Release Engineer
Tools: git_commit_and_push, configure_ci_cd_pipeline, ...
## Implementation Engineer  
Tools: vibe_code, implement_feature, ...
## Requirements Engineer
Tools: analyze_requirements, resolve_ambiguity, ...

Task:
Title: Deploy feature to staging
Description: ...
Context: {...}

Output: JSON with primary_agent, execution_plan, confidence
```

## Features

### 1. Dynamic Agent Discovery
- No hardcoded agent list
- Auto-discovers any new MCP server registered to the registry
- Caches results to reduce registry load

### 2. LLM-Based Routing
- Understands context and capabilities
- Generates detailed execution plans
- Provides confidence scores
- Explains routing decisions

### 3. Task Complexity Classification
- `simple`: Single agent, straightforward
- `moderate`: 2-3 agents, some coordination
- `complex`: Multiple agents, complex workflow
- `cross_cutting`: Requires multiple domains

### 4. Planning Output
```json
{
  "primary_agent": "DevOps Release Engineer",
  "secondary_agents": [],
  "execution_plan": ["Step 1", "Step 2", ...],
  "rationale": "Explanation of why this agent was selected",
  "confidence": 0.92,
  "complexity": "moderate",
  "estimated_duration": "5-10 minutes",
  "required_capabilities": ["tool1", "tool2"]
}
```

## DevOps Release Engineer Integration

### Before (Hardcoded):
```python
agent_mapping = {
    "requirement": "Requirements Engineer",
    "implementation engineer": "Implementation Engineer"
}
# DevOps Release Engineer was NOT in the list!
```

### After (Dynamic):
```python
# All agents from registry are automatically included:
# - DevOps Release Engineer (8 tools, 4 resources, 3 prompts)
# - Implementation Engineer (13 tools)
# - Requirements Engineer (5 tools, 3 resources)
# - IT Lead (31 tools!)
# - Team Management (16 tools)
# - Registry Server
```

## Web UI Updates

### TeamMembers Component
- Now uses `/api/planner/agents` endpoint
- Shows ALL agents from registry
- Displays capabilities for each agent

### AgentDetail Component
- Can route tasks via `/api/planner/route`
- Shows planning rationale

## Benefits

| Benefit | Before | After |
|---------|--------|-------|
| New Agent Discovery | Manual code update | Automatic |
| Agent List Maintenance | Update hardcoded dict | None needed |
| Task Routing | Fixed rules | LLM context-aware |
| Explainability | None | Detailed rationale |
| Flexibility | Low | High |
| Multi-Agent Support | Limited | Full support |

## Configuration

### Environment Variables (Optional)
```python
_planner = DynamicPlanner(
    registry_host="127.0.0.1",      # Default: 127.0.0.1
    registry_port=3031,             # Default: 3031
    llm_provider_url="http://192.168.51.237:1234/v1/chat/completions",
    llm_model="qwen3-coder-next@q5_k_xl"
)
```

## Performance Considerations

### Caching
- Agent list cached for 5 minutes
- Reduces registry queries
- Cache invalidates on network errors

### LLM Latency
- Planning call: ~2-5 seconds
- Consider adding async caching for frequently routed task types
- Can pre-compute common routing patterns

### Optimization Opportunities
1. **Task Type Cache**: Cache plans for recurring task patterns
2. **Agent Priority**: Pre-select top-N most capable agents
3. **Fallback Rules**: If LLM fails, use keyword-based routing

## Testing

### Verify Dynamic Discovery:
```bash
curl http://localhost:8000/api/planner/agents
```

### Test Task Routing:
```bash
curl -X POST http://localhost:8000/api/planner/route \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test-123",
    "title": "Deploy to staging",
    "description": "Deploy the new feature to staging environment",
    "context": {"environment": "staging"}
  }'
```

## Future Enhancements

1. **Async Task Execution**: Start tasks asynchronously
2. **Task History**: Learn from past routing decisions
3. **Agent Performance**: Track agent success rates
4. **A/B Testing**: Compare routing strategies
5. **Multi-Step Plans**: Handle complex workflows with checkpoints

## Files Modified

| File | Changes |
|------|---------|
| `it-lead-mcp-server/web-ui/backend/main.py` | Added dynamic planner imports, new API endpoints |
| `it-lead-mcp-server/web-ui/backend/dynamic_planner.py` | NEW: Dynamic planning system |
| `it-lead-mcp-server/web-ui/frontend/src/components/TeamMembers.jsx` | Updated to use `/api/planner/agents` |

## Migration Notes

### Backward Compatibility
- Old `/api/agents` endpoint still works
- New `/api/planner/*` endpoints are additive
- No breaking changes to existing functionality

### Rollout Strategy
1. ✅ Deploy backend with dynamic planner
2. ✅ Update frontend to use new endpoints
3. ✅ Verify DevOps Release Engineer appears in UI
4. ✅ Test task routing with LLM

## Conclusion

The Dynamic Planning System provides a flexible, maintainable architecture that:
- Automatically discovers all MCP agents
- Uses LLM for intelligent task routing
- Provides explainable routing decisions
- Supports complex multi-agent workflows
- Requires no code changes when adding new agents
