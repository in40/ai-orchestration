# Actual Flow: How the MCP System Works

## System Architecture

The MCP (Model Context Protocol) system consists of **separate services** that communicate via HTTP requests:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           MCP Registry (port 3031)                       │
│  - Service discovery                                                     │
│  - Agent registration                                                    │
│  - Health checks                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                              ↑
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼───────┐  ┌──────────▼──────────┐  ┌─────▼────────┐
│  IT Lead      │  │ Requirements        │  │ DevOps       │
│  (port 3061)  │  │ Engineer            │  │ Engineer     │
│               │  │ (port 3063)         │  │ (port 3064)  │
│ assign_task   │  │ analyze_requirements│  │ orchestrate  │
│ review_code   │  │ resolve_ambiguity   │  │ deployments  │
│ ...           │  │ ...                 │  │ ...          │
└───────────────┘  └─────────────────────┘  └──────────────┘
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Web UI (port 3000)│
                    │  - Submit tasks    │
                    │  - View results    │
                    └─────────────────────┘
```

## Step-by-Step: Task Submission Flow

### Step 1: User submits task via Web UI
```
User -> Web UI (http://localhost:3000)
```

**Web UI Backend** (`it-lead-mcp-server/web-ui/backend/main.py`):
```python
# Web UI receives task submission
await handle_task_assignment_via_it_lead(task_data)

# Calls IT Lead server
response = await client.post(
    f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
    json={
        "jsonrpc": "2.0",
        "id": "task-123",
        "method": "tools/call",
        "params": {
            "name": "assign_task",
            "arguments": {
                "task_id": "task-123",
                "task_description": "Build a login feature",
                "assignee": "IT Lead",
                "priority": "medium"
            }
        }
    }
)
```

### Step 2: IT Lead receives task
```
IT Lead server (port 3061) receives HTTP request
```

**Handler chain:**
1. `ExtendedItLeadServerHandlers.handle_tools_call()` - Main entry point
2. Routes to `AdvancedAssignmentHandlers.handle_tools_call()`
3. Eventually reaches `TaskAssignmentManager.assign_and_forward_task()`

### Step 3: IT Lead routes task to appropriate agent
```
TaskAssignmentManager.assign_and_forward_task()
```

**Logic flow:**
```python
# 1. Check if assignee is "IT Lead" - if so, determine specialized agent
if assignee in ('it-lead', 'it lead', 'itlead'):
    effective_assignee = None  # Let routing rules determine

# 2. Evaluate task against routing rules
routing_decision = routing_engine.evaluate_task(
    task_description, effective_assignee, routing_context
)

# 3. Determine which agent should handle it
# Rules check for keywords:
# - "requirement", "specification", "analyze" → Requirements Engineer
# - "code", "implement", "feature", "build" → Implementation Engineer
# - "deploy", "infrastructure", "server" → DevOps Engineer

primary_agent = routing_decision.assign_to  # e.g., "implementation-engineer"
```

**Example routing:**
```
Task: "Build a login feature with email/password authentication"

→ Routing Engine detects keywords: "build", "feature"
→ Assigns to: "implementation-engineer"
```

### Step 4: IT Lead forwards task to Implementation Engineer agent
```
IT Lead → Implementation Engineer (port 3062)
```

**HTTP call to agent:**
```python
# Forward task to agent via MCP
response = requests.post(
    "http://localhost:3062/mcp",
    json={
        "jsonrpc": "2.0",
        "id": "forward-task-123",
        "method": "tools/call",
        "params": {
            "name": "vibe_code_async",
            "arguments": {
                "task_description": "Build a login feature with email/password authentication",
                "language": "python",
                "vibe_level": 5,
                "style_guide": "PEP 8"
            }
        }
    },
    timeout=120.0
)
```

### Step 5: Implementation Engineer executes task
```
Implementation Engineer agent (port 3062)
```

**Current implementation** (from `mcp-vibe-coding-agent`):
```python
# server_handlers.py
def vibe_code_async(self, task_description, language, vibe_level, style_guide):
    # 1. Call LLM to generate code
    code = self._call_llm_to_generate_code(task_description, language)
    
    # 2. Return result (currently just returns the code)
    return {
        "status": "success",
        "code": code,  # ← Code is returned inline, NOT stored in Git yet
        "message": "Code generated"
    }
```

**This is the KEY difference:**
- **Current**: Agent returns code content directly
- **With agent-driven Git push**: Agent would store code in Git first, then return Git URL

### Step 6: IT Lead receives agent response
```
IT Lead receives response from Implementation Engineer
```

**Current implementation** (from `task_assignment.py`):
```python
forward_result = self._forward_task_to_agent(
    task_id, task_description, primary_agent, tool,
    priority, deadline, metadata
)

# Current flow: ResultRouter classifies and stores result
if self.result_router:
    agent_response = forward_result.get("response", {})
    result_data = agent_response.get("result", {})
    
    # ResultRouter classifies content type
    storage_ref = self.result_router.route_result(
        task_id=task_id,
        result_data=result_data,  # ← The code content
        agent=primary_agent,
        tool=tool
    )
    
    # Store in Git or File storage
    # Returns: {"storage_type": "git", "path": "/results/task-123/main.py"}
    
    # Update task with storage reference
    self.task_storage.update_task_result_reference(
        task_id=task_id,
        storage_ref=storage_ref
    )
```

### Step 7: Result stored via centralized ResultRouter
```
ResultRouter routes based on content:
```

**Classification logic** (from `result_router.py`):
```python
def _classify_result(self, result_data):
    if isinstance(result_data, str):
        content = result_data
        
        # Detect code patterns
        if "import " in content or "#!/usr/bin/env python" in content:
            return {"type": "code", "to_git": True}
        
        # Detect markdown
        if "```" in content:
            return {"type": "document", "to_git": True}
        
        return {"type": "document", "to_git": True}
    
    elif isinstance(result_data, bytes):
        # Binary → File Storage
        return {"type": "binary", "to_git": False}
```

**Storage decision:**
| Content | Storage |
|---------|---------|
| Code (< 100KB) | Git Storage |
| Documentation (< 100KB) | Git Storage |
| Large files (> 100KB) | File Storage |
| Binary (images, PDFs) | File Storage |

## The Proposed Change: Agent-Driven Git Push

### New Flow:
```
Step 1-4: Same as before (Web UI → IT Lead → Routing → Agent)

Step 5 (NEW): Implementation Engineer pushes to Git FIRST
```

**New agent implementation:**
```python
def vibe_code_async(self, task_description, language, vibe_level, style_guide):
    # 1. Call LLM to generate code
    code = self._call_llm_to_generate_code(task_description, language)
    
    # 2. PUSH TO GIT FIRST (NEW)
    result = self.git_helper.store_code_result(
        task_id=self.current_task_id,
        code=code,
        language=language
    )
    
    # 3. Return Git URL instead of code (NEW)
    if result["success"]:
        return {
            "status": "success",
            "code_url": result["git_url"],  # ← Git URL returned
            "message": "Code generated and stored in Git"
        }
    else:
        return {
            "status": "error",
            "message": f"Failed to store code: {result.get('error')}"
        }
```

### Step 6 (NEW): IT Lead receives Git URL
```
IT Lead receives: {"code_url": "git://.../results/task-123/main.py"}
```

**Simplified handling:**
```python
# Instead of ResultRouter routing
agent_response = forward_result.get("response", {})
git_url = agent_response.get("code_url")

# Just store the URL in task metadata
self.task_storage.update_task_result_reference(
    task_id=task_id,
    storage_ref={
        "storage_type": "git",
        "git_url": git_url,
        "storage_path": git_url
    }
)
```

### Benefits of New Flow:
| Aspect | Current (Centralized) | New (Agent-Driven) |
|--------|----------------------|-------------------|
| Code passes through | IT Lead → ResultRouter → Git | Agent → Git directly |
| IT Lead processing | Classifies content, routes to storage | Just stores URL |
| Agent responsibility | Return code | Store code AND return URL |
| ResultRouter needed | Yes | No (can be removed) |
| Agent identity | Lost in routing | Preserved in commit |
| Complexity | Medium | Lower |

## Summary

### Current Flow (7 steps):
1. Web UI submits task
2. IT Lead receives task
3. IT Lead routes to appropriate agent
4. IT Lead forwards task to agent
5. Agent executes and returns **code content**
6. IT Lead routes result to storage via ResultRouter
7. ResultRouter classifies and stores in Git/File

**Problem**: IT Lead has to handle all storage logic, agents lose ownership of their results

---

### NEW Flow (5 steps): Agent-Driven Git Push
1. Web UI submits task
2. IT Lead receives task
3. IT Lead routes to appropriate agent
4. IT Lead forwards task to agent
5. Agent executes, **pushes to Git**, returns **Git URL**
6. IT Lead stores Git URL in task metadata (simpler!)

**Benefits**:
- ✅ Agents own their results
- ✅ Direct Git history under agent identity
- ✅ No ResultRouter needed
- ✅ Lower latency (no intermediate routing)
- ✅ Simpler architecture
