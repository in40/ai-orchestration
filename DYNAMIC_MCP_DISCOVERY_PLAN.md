# Dynamic MCP Agent & Tool Discovery for LLM Planning

## Problem Statement

Currently, the IT Lead's LLM planner uses **hardcoded agent descriptions and tool lists** instead of discovering actual registered MCP servers and their capabilities via MCP protocol. This means:

1. ❌ New MCP servers are invisible to LLM
2. ❌ Tool names are hardcoded, not discovered
3. ❌ No tool schemas sent to LLM (input/output structure unknown)
4. ❌ Server capabilities not reflected in planning
5. ❌ LLM may assign tasks to unavailable agents

## Current Architecture Analysis

### Current Flow (Static)

```
IT Lead LLM Planner
    ↓
_hardcoded_agents = ["implementation-engineer", "requirements-engineer", ...]
_hardcoded_tools = {
    "implementation-engineer": ["vibe_code_async", "vibe_code", ...],
    "requirements-engineer": ["analyze_requirements", ...]
}
    ↓
LLM Prompt (static agent list)
    ↓
LLM Decision (based on outdated info)
```

### Current Code Issues

**File**: `it-lead-mcp-server/it_lead_mcp_server/utils/llm_task_planner.py`

```python
def _get_available_tools(self) -> Dict[str, List[str]]:
    """Get available tools for each agent from the service registry"""
    available_tools = {}

    if self.agent_registry:
        try:
            services = self.agent_registry.list_services()
            # ... tries to map services to tools ...
        except Exception as e:
            print(f"⚠️ Error getting available tools: {e}")

    # FALLBACK: Hardcoded defaults (ALWAYS USED if registry fails)
    if not available_tools:
        available_tools = {
            "implementation-engineer": ["vibe_code_async", "vibe_code", "implement_feature"],
            "requirements-engineer": ["analyze_requirements"],
            # ... hardcoded for all 6 agents
        }
    return available_tools
```

**Problem**: Registry lookup often fails or returns incomplete data, so hardcoded defaults are used.

### Existing MCP Registry Client

**File**: `it-lead-mcp-server/it_lead_mcp_server/utils/mcp_registry_client.py`

```python
class McpRegistryClient:
    def list_services(self) -> List[Dict[str, Any]]:
        # Calls registry/list via MCP protocol
        # Returns: [{"name": "implementation-engineer", "endpoint": "...", "capabilities": {...}}, ...]
        
    def get_available_tools(self, agent_name: str) -> List[str]:
        # Returns tools from capabilities.tools field
        # BUT: Doesn't call tools/list on agent server - just returns cached list from registry
```

**Problem**: The client gets tool **names** from registry metadata, but doesn't introspect actual tool **schemas** from each agent.

## Proposed Architecture (Dynamic)

### New Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    IT Lead LLM Planner                          │
│                                                                 │
│  1. Call McpRegistryClient.list_services()                     │
│     → Returns: List of registered agents with endpoints        │
│                                                                 │
│  2. For each agent, call AgentMcpClient.list_tools()           │
│     → Calls POST {agent_endpoint}/mcp {method: "tools/list"}   │
│     → Returns: Full tool schemas (name, description, inputSchema) │
│                                                                 │
│  3. Build dynamic prompt with:                                 │
│     - Agent names & descriptions                               │
│     - Tool names, descriptions, input schemas                  │
│     - Real-time availability status                            │
│                                                                 │
│  4. Call LLM with complete, accurate information               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Registry Server (:3031)                  │
│  - Maintains list of registered agents                         │
│  - Each agent registered via: registry/register                │
│  - Returns: [{name, endpoint, description, capabilities}, ...] │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓ (for each agent)
┌─────────────────────────────────────────────────────────────────┐
│              Agent MCP Servers (3060, 3062, 3063, ...)          │
│  Implementation Engineer (:3060)                               │
│    POST /mcp {method: "tools/list"}                            │
│    → Returns: [{name: "vibe_code_async", description: "...",  │
│                inputSchema: {...}}, ...]                       │
│                                                                 │
│  Requirements Engineer (:3062)                                 │
│    POST /mcp {method: "tools/list"}                            │
│    → Returns: [{name: "analyze_requirements", ...}, ...]       │
│                                                                 │
│  (Same for all registered agents)                              │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Plan

### Phase 1: Enhanced MCP Registry Client

**File**: `it-lead-mcp-server/it_lead_mcp_server/utils/mcp_registry_client.py`

**New Methods**:

```python
class McpRegistryClient:
    # ... existing methods ...
    
    def discover_all_agents_with_tools(self) -> List[Dict[str, Any]]:
        """
        Discover all registered agents and introspect their tools via MCP protocol.
        
        Returns:
            List of agent info with full tool schemas:
            [
                {
                    "name": "implementation-engineer",
                    "endpoint": "http://0.0.0.0:3060/mcp",
                    "description": "AI coding agent...",
                    "status": "online",
                    "tools": [
                        {
                            "name": "vibe_code_async",
                            "description": "Submit coding task asynchronously",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "task_description": {"type": "string", ...},
                                    "language": {"type": "string", ...}
                                },
                                "required": ["task_description"]
                            }
                        },
                        ...
                    ]
                },
                ...
            ]
        """
        agents = []
        services = self.list_services()
        
        for service in services:
            agent_info = {
                "name": service.get("name"),
                "endpoint": service.get("endpoint"),
                "description": service.get("description"),
                "status": "unknown",
                "tools": []
            }
            
            # Call tools/list on agent's MCP endpoint
            if agent_info["endpoint"]:
                try:
                    tools = self._introspect_agent_tools(agent_info["endpoint"])
                    agent_info["tools"] = tools
                    agent_info["status"] = "online"
                except Exception as e:
                    agent_info["status"] = "offline"
                    agent_info["error"] = str(e)
            
            agents.append(agent_info)
        
        return agents
    
    def _introspect_agent_tools(self, agent_endpoint: str) -> List[Dict[str, Any]]:
        """
        Call tools/list on an agent's MCP endpoint to get full tool schemas.
        
        Args:
            agent_endpoint: Agent's MCP endpoint (e.g., "http://0.0.0.0:3060/mcp")
        
        Returns:
            List of tool schemas from tools/list response
        """
        response = requests.post(
            agent_endpoint,
            json={
                "jsonrpc": "2.0",
                "id": f"tools-list-{int(time.time() * 1000)}",
                "method": "tools/list",
                "params": {}
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("result", {}).get("tools", [])
        else:
            raise Exception(f"Agent returned status {response.status_code}")
```

### Phase 2: Update LLM Planner

**File**: `it-lead-mcp-server/it_lead_mcp_server/utils/llm_task_planner.py`

**Changes**:

```python
class LLMTaskPlanner:
    def __init__(self, llm_client, agent_registry=None, mcp_registry_client=None):
        self.llm_client = llm_client
        self.agent_registry = agent_registry  # Deprecated
        self.mcp_registry_client = mcp_registry_client  # NEW: Use this
    
    def plan_task_assignment(self, task_description: str, routing_context: Dict[str, Any]) -> Dict[str, Any]:
        # NEW: Get dynamic agent & tool info
        agents_with_tools = self.mcp_registry_client.discover_all_agents_with_tools()
        
        # Build prompt with REAL data
        prompt = self._build_dynamic_prompt(task_description, agents_with_tools)
        
        # Call LLM
        response = self.llm_client.generate(prompt, temperature=0.3)
        return self._parse_llm_response(response, task_description, routing_context)
    
    def _build_dynamic_prompt(self, task_description: str, agents: List[Dict[str, Any]]) -> str:
        """Build prompt with dynamically discovered agents and tools"""
        
        # Build agent list with full tool schemas
        agents_section = "## Available Agents and Their Tools\n\n"
        for agent in agents:
            if agent["status"] != "online":
                continue  # Skip offline agents
            
            agents_section += f"### {agent['name']}\n"
            agents_section += f"**Description**: {agent['description']}\n\n"
            agents_section += "**Tools**:\n"
            
            for tool in agent["tools"]:
                tool_name = tool.get("name")
                tool_desc = tool.get("description", "No description")
                input_schema = tool.get("inputSchema", {})
                
                # Format tool info
                agents_section += f"- **`{tool_name}`**: {tool_desc}\n"
                
                # Show required parameters
                required = input_schema.get("required", [])
                properties = input_schema.get("properties", {})
                if required:
                    agents_section += f"  - Required: {', '.join(required)}\n"
                if properties:
                    for param_name, param_info in properties.items():
                        param_type = param_info.get("type", "any")
                        param_desc = param_info.get("description", "")
                        agents_section += f"  - `{param_name}` ({param_type}): {param_desc}\n"
            
            agents_section += "\n"
        
        return f"""You are an IT Lead Agent responsible for task assignment.

## Task Description
{task_description}

{agents_section}

## Your Task
Analyze the task and determine:
1. Which agent should handle this task?
2. What specific tool should be used? (MUST be from the list above)
3. What parameters should be passed to the tool?
4. What is the reasoning for this assignment?

## Response Format
Respond in valid JSON format:
{{
    "primary_agent": "agent-name",
    "tool": "tool-name",
    "tool_arguments": {{...}},
    "reasoning": "...",
    "confidence": 0.0-1.0
}}
"""
```

### Phase 3: Update Task Assignment Manager

**File**: `it-lead-mcp-server/it_lead_mcp_server/utils/task_assignment.py`

**Changes**:

```python
class TaskAssignmentManager:
    def __init__(self, task_storage, routing_engine, llm_client, mcp_registry_client=None):
        self.task_storage = task_storage
        self.routing_engine = routing_engine
        self.llm_client = llm_client
        self.mcp_registry_client = mcp_registry_client  # NEW
    
    def assign_and_forward_task(self, task_id: str, task_description: str, ...) -> Dict[str, Any]:
        # Pass MCP registry client to routing engine
        if self.mcp_registry_client:
            self.routing_engine.mcp_registry_client = self.mcp_registry_client
        
        # ... rest of assignment logic ...
```

### Phase 4: Update IT Lead Server Initialization

**File**: `it-lead-mcp-server/it_lead_mcp_server/server.py`

**Changes**:

```python
class McpServer:
    def __init__(self, ...):
        # ... existing initialization ...
        
        # Create MCP Registry Client
        from .utils.mcp_registry_client import McpRegistryClient
        self.mcp_registry_client = McpRegistryClient(
            registry_endpoint=f"http://{REGISTRY_HOST}:{REGISTRY_PORT}/mcp"
        )
        
        # Pass to task assignment manager
        self.task_assignment_manager = TaskAssignmentManager(
            task_storage=self.task_storage,
            routing_engine=self.routing_engine,
            llm_client=self.llm_client,
            mcp_registry_client=self.mcp_registry_client  # NEW
        )
        
        # Pass to LLM planner
        self.llm_planner = LLMTaskPlanner(
            llm_client=self.llm_client,
            mcp_registry_client=self.mcp_registry_client  # NEW
        )
```

## Testing Strategy

### Test 1: Verify Tool Discovery

```python
# Test script: test_dynamic_discovery.py
from it_lead_mcp_server.utils.mcp_registry_client import McpRegistryClient

client = McpRegistryClient("http://127.0.0.1:3031/mcp")
agents = client.discover_all_agents_with_tools()

print(f"Discovered {len(agents)} agents:")
for agent in agents:
    print(f"\n{agent['name']} ({agent['status']}):")
    print(f"  Endpoint: {agent['endpoint']}")
    print(f"  Tools: {len(agent['tools'])}")
    for tool in agent['tools'][:3]:  # Show first 3 tools
        print(f"    - {tool['name']}: {tool['description'][:50]}...")
```

### Test 2: Verify LLM Planning with Dynamic Data

```python
# Test script: test_llm_planning.py
from it_lead_mcp_server.utils.llm_task_planner import LLMTaskPlanner
from it_lead_mcp_server.utils.mcp_registry_client import McpRegistryClient

# Setup
registry_client = McpRegistryClient("http://127.0.0.1:3031/mcp")
llm_planner = LLMTaskPlanner(llm_client=..., mcp_registry_client=registry_client)

# Test task
result = llm_planner.plan_task_assignment(
    task_description="Create a Flappy Bird game in HTML",
    routing_context={}
)

print(f"Primary agent: {result['primary_agent']}")
print(f"Tool: {result['tool']}")
print(f"Reasoning: {result['reasoning']}")
```

### Test 3: End-to-End Task Flow

1. Start all MCP servers (Registry, IT Lead, Implementation Engineer, etc.)
2. Submit task via Web UI
3. Verify LLM planning uses discovered tools (check logs)
4. Verify task is forwarded to correct agent
5. Verify completion and git storage

## Migration Path

### Backward Compatibility

- Keep existing hardcoded fallback for when registry/tools/list fails
- Log warnings when using fallback vs dynamic discovery
- Add config option to force dynamic discovery: `USE_DYNAMIC_DISCOVERY=true`

### Rollout Steps

1. **Week 1**: Implement Phase 1 (MCP Registry Client enhancement)
2. **Week 2**: Implement Phase 2 (LLM Planner update)
3. **Week 3**: Implement Phase 3-4 (Integration)
4. **Week 4**: Testing and bug fixes
5. **Week 5**: Deploy to production, monitor logs

## Benefits

| Aspect | Before | After |
|--------|--------|-------|
| Agent Discovery | Hardcoded 6 agents | Dynamic from registry |
| Tool Discovery | Hardcoded names | Full schemas via MCP |
| New Agent Support | Requires code change | Auto-discovered |
| LLM Accuracy | Limited info | Complete tool capabilities |
| Availability Check | None | Real-time status |
| Maintenance | Manual updates | Automatic |

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Tool introspection slow | LLM planning delay | Cache results for 5 min |
| Agent server unavailable | Missing tools in prompt | Mark as offline, use fallback |
| Registry server down | No agent discovery | Use cached data, degrade gracefully |
| LLM context limit | Too many tools | Summarize tools, group by category |

## Success Metrics

1. ✅ All registered agents appear in LLM prompt
2. ✅ All tool schemas included (name, description, inputSchema)
3. ✅ LLM assigns tasks using discovered tools (not hardcoded)
4. ✅ New agents auto-discovered without code changes
5. ✅ Offline agents excluded from planning
6. ✅ Planning latency < 30 seconds (including discovery)
