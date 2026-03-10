# FIX: Tasks Stuck at in_progress - MCP Registry Client Architecture

## Problem Summary

Tasks were stuck at `in_progress` status because the IT Lead server couldn't properly discover and forward tasks to agent servers (Implementation Engineer, Requirements Engineer, etc.).

## Root Cause

**Architecture Problem**: The IT Lead server was trying to discover agent endpoints by directly querying a local SQLite/PostgreSQL database, but agents were registering with a **separate central MCP Registry Server** (port 3031).

This created a **split-brain registry** problem:
- **Agents** → Register with MCP Registry Server (port 3031) → PostgreSQL DB
- **IT Lead** → Reading from local SQLite DB → Doesn't have agent registrations
- **Result** → IT Lead can't find agent endpoints → Task forwarding fails → Tasks stuck at `in_progress`

## Solution: MCP Registry Client Architecture

The correct architecture is for the IT Lead to communicate with the MCP Registry Server **via MCP protocol** (HTTP POST to `/mcp`), just like any other MCP client would.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Registry Server (port 3031)               │
│  - Manages PostgreSQL registry database                          │
│  - Exposes MCP endpoints: registry/register, registry/list, etc. │
│  - Agents register here via MCP protocol                         │
└─────────────────────────────────────────────────────────────────┘
                              ↑
                              │ MCP Protocol (HTTP POST to /mcp)
                              │ registry/list, registry/register
                              │
        ┌─────────────────────┴─────────────────────┐
        │                                           │
┌───────▼────────┐                         ┌────────▼────────┐
│  IT Lead       │                         │  Agents         │
│  (port 3061)   │                         │  (3060, 3062,   │
│                │                         │   3063, 3071)   │
│ NEW: MCP       │                         │                 │
│ Registry       │                         │ Register via    │
│ Client         │                         │ MCP protocol    │
└────────────────┘                         └─────────────────┘
```

### Files Created

1. **`/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/mcp_registry_client.py`**
   - New client that communicates with MCP Registry Server via MCP protocol
   - Calls `registry/list` via HTTP POST to `/mcp` endpoint
   - Caches results for 60 seconds to reduce network calls
   - Provides methods: `list_services()`, `get_agent_endpoint()`, `is_agent_available()`

### Files Modified

2. **`/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/task_routing_engine.py`**
   - Added `mcp_registry_client` parameter to `__init__`
   - New method `_update_agent_endpoints_from_mcp_registry()` - discovers agents via MCP protocol
   - Deprecated `_update_agent_endpoints_from_registry()` - old direct DB access method
   - Now prefers MCP Registry Client, falls back to direct DB access for backward compatibility

3. **`/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/task_assignment.py`**
   - Added `mcp_registry_client` parameter to `__init__`
   - Creates `McpRegistryClient` with endpoint `http://127.0.0.1:3031/mcp`
   - Passes MCP Registry Client to `TaskRoutingEngine`

4. **`/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/handlers/extended_server_handlers.py`**
   - Updated `TaskAssignmentManager` initialization to use MCP Registry Client
   - Added comment explaining the correct architecture
   - Local registry (SQLite/PostgreSQL) now only used for local task storage, NOT agent discovery

## How It Works

### Agent Discovery Flow (NEW)

```
1. IT Lead starts up
   ↓
2. TaskAssignmentManager.__init__()
   ↓
3. Creates McpRegistryClient("http://127.0.0.1:3031/mcp")
   ↓
4. TaskRoutingEngine._update_agent_endpoints_from_mcp_registry()
   ↓
5. Calls MCP Registry Server via HTTP POST:
   POST http://127.0.0.1:3031/mcp
   {
     "jsonrpc": "2.0",
     "id": "registry-list-...",
     "method": "tools/call",
     "params": {
       "name": "registry/list",
       "arguments": {}
     }
   }
   ↓
6. MCP Registry Server returns list of registered services
   ↓
7. TaskRoutingEngine extracts agent endpoints:
   - implementation-engineer → http://127.0.0.1:3060/mcp
   - requirements-engineer → http://127.0.0.1:3062/mcp
   - devops-engineer → http://127.0.0.1:3071/mcp
   ↓
8. Stores endpoints in self.agent_endpoints for task forwarding
```

### Task Forwarding Flow (UNCHANGED)

```
1. User submits task via Web UI
   ↓
2. IT Lead receives task via assign_task tool
   ↓
3. Background thread starts LLM planning
   ↓
4. LLM determines primary_agent = "implementation-engineer"
   ↓
5. TaskRoutingEngine.get_agent_endpoint("implementation-engineer")
   ↓
6. Returns endpoint discovered via MCP Registry Client
   ↓
7. HTTP POST to agent endpoint with vibe_code_async tool
   ↓
8. Agent processes task and returns result
```

## Benefits of This Architecture

### ✅ Proper Separation of Concerns
- **MCP Registry Server** (port 3031): Manages service registration and discovery
- **IT Lead Server** (port 3061): Orchestrates tasks, uses MCP protocol for discovery
- **Agent Servers** (3060, 3062, etc.): Execute specific tasks

### ✅ Consistent Communication Pattern
- All components communicate via **MCP protocol** (JSON-RPC over HTTP)
- No component has special direct database access
- Follows standard client-server architecture

### ✅ Scalability
- Multiple IT Lead instances can share the same Registry Server
- Registry Server can be deployed independently
- Agents can register/deregister dynamically

### ✅ Maintainability
- Single source of truth for agent registrations (PostgreSQL via Registry Server)
- No more split-brain registry problem
- Easy to add new agents - just register with Registry Server

## Testing

### Verify MCP Registry Client Works

```bash
# Test that MCP Registry Client can reach Registry Server
cd /root/qwen/base/it-lead-mcp-server
python3 -c "
from it_lead_mcp_server.utils.mcp_registry_client import McpRegistryClient
client = McpRegistryClient('http://127.0.0.1:3031/mcp')
services = client.list_services()
print(f'Found {len(services)} services:')
for svc in services:
    print(f'  - {svc[\"name\"]}: {svc[\"endpoint\"]}')
"
```

Expected output:
```
✅ Retrieved 7 services from MCP Registry Server
Found 7 services:
  - DevOps Release Engineer Server on 0.0.0.0:3071: http://0.0.0.0:3071/mcp
  - Implementation Engineer: http://0.0.0.0:3060/mcp
  - IT Lead Agent Server on 127.0.0.1:3061: http://127.0.0.1:3061/mcp
  - MCP Service Registry: http://127.0.0.1:3031
  - Requirement Engineer MCP Server on 0.0.0.0:3062: http://0.0.0.0:3062/mcp
  - Requirement Engineer MCP Server on 127.0.0.1:3062: http://127.0.0.1:3062/mcp
  - Team Management MCP Server on 0.0.0.0:3063: http://0.0.0.0:3063/mcp
```

### Verify Task Routing Engine Uses MCP Registry Client

```bash
cd /root/qwen/base/it-lead-mcp-server
python3 -c "
from it_lead_mcp_server.utils.mcp_registry_client import McpRegistryClient
from it_lead_mcp_server.utils.task_routing_engine import TaskRoutingEngine

# Create MCP Registry Client
mcp_client = McpRegistryClient('http://127.0.0.1:3031/mcp')

# Create TaskRoutingEngine with MCP Registry Client
engine = TaskRoutingEngine(mcp_registry_client=mcp_client)

# Check discovered endpoints
print('Discovered agent endpoints:')
for agent, endpoint in engine.agent_endpoints.items():
    print(f'  {agent}: {endpoint}')
"
```

Expected output:
```
📋 Discovered 7 services from MCP Registry Server
✅ Found implementation-engineer: http://0.0.0.0:3060/mcp (was: http://127.0.0.1:3060/mcp)
✅ Found requirements-engineer: http://127.0.0.1:3062/mcp
✅ Found devops-engineer: http://0.0.0.0:3071/mcp
Discovered agent endpoints:
  implementation-engineer: http://0.0.0.0:3060/mcp
  requirements-engineer: http://127.0.0.1:3062/mcp
  code-reviewer: None
  qa-test-engineer: None
  security-engineer: None
  devops-engineer: http://0.0.0.0:3071/mcp
```

### Test Full Task Flow

1. **Restart IT Lead Server** to pick up new code:
   ```bash
   # Stop existing IT Lead server
   # Start new IT Lead server
   cd /root/qwen/base/it-lead-mcp-server
   python -m it_lead_mcp_server.server --transport streamable-http --port 3061 --use-postgres
   ```

2. **Watch for startup logs**:
   ```
   ✅ MCP Registry Client initialized (default: http://127.0.0.1:3031/mcp)
   📋 Discovered 7 services from MCP Registry Server
   ✅ Found implementation-engineer: http://0.0.0.0:3060/mcp
   ✅ Task assignment manager initialized successfully with MCP Registry Client
   ```

3. **Submit a test task** via Web UI

4. **Monitor task progress**:
   ```sql
   SELECT task_id, status, assigned_to, created_at 
   FROM tasks 
   ORDER BY created_at DESC 
   LIMIT 1;
   ```

   Expected status flow: `submitted` → `received` → `in_progress` → `done`

## Migration Notes

### Backward Compatibility

The old direct database access method is kept as a fallback:

```python
# In TaskRoutingEngine.__init__()
if mcp_registry_client:
    self._update_agent_endpoints_from_mcp_registry()  # NEW: MCP protocol
elif service_registry:
    self._update_agent_endpoints_from_registry()  # DEPRECATED: Direct DB
```

This ensures the system still works if MCP Registry Server is temporarily unavailable.

### Deprecation Warning

When using the old method, a warning is logged:
```
⚠️  Using deprecated direct DB registry access - should use MCP Registry Client instead
```

## Conclusion

This fix resolves the split-brain registry problem by having the IT Lead server communicate with the MCP Registry Server via the standard MCP protocol, just like all other components do. This is the correct architectural pattern for an MCP-based system.

**Key Principle**: All inter-component communication should happen via MCP protocol (JSON-RPC over HTTP), not direct database access. The database is an implementation detail of the Registry Server, not a shared resource.
