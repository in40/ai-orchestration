# Async Task Management - Common Base Implementation for All Agents

## Overview

This document describes the **common base implementation** required for all team member agents to support **asynchronous task management** via MCP notifications. The IT Lead server has been updated to support async task assignment, and each agent needs to implement the corresponding handlers.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   IT Lead       │     │   Agent          │     │   Agent         │
│   (Server)      │     │   (Server)       │     │   (Background)  │
└────────┬────────┘     └────────┬─────────┘     └────────┬────────┘
         │                       │                        │
         │ notifications/        │                        │
         │ tasks/new             │                        │
         │──────────────────────▶│                        │
         │                       │                        │
         │                       │ Store in local DB      │
         │                       │ Queue for processing   │
         │                       │                        │
         │ notifications/        │                        │
         │ tasks/ack             │                        │
         │◀──────────────────────│                        │
         │                       │                        │
         │                       │ Process task           │
         │                       │ (background worker)    │
         │                       │────────────────────────│
         │                       │                        │
         │ notifications/        │                        │
         │ tasks/status          │                        │
         │◀──────────────────────│                        │
         │                       │                        │
         │                       │ Complete task          │
         │                       │────────────────────────│
         │                       │                        │
         │ notifications/        │                        │
         │ tasks/completed       │                        │
         │◀──────────────────────│                        │
```

## Common Components (Required for All Agents)

### 1. MCP Client Extension

**File**: `client.py` (same as IT Lead's client.py)

All agents need the `send_notification` method in their MCP client:

```python
def send_notification(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Send an MCP notification (fire-and-forget, no response expected)"""
    if not self.connected:
        return {"success": False, "error": "Client not connected"}
    
    notification = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params
    }
    
    import requests
    response = requests.post(self.endpoint, json=notification, timeout=10.0)
    
    if response.status_code in [200, 202, 204]:
        return {"success": True, "method": method}
    else:
        return {"success": False, "error": f"HTTP {response.status_code}"}

def send_task_status_notification(self, task_id: str, status: str, 
                                   progress: int = 0, 
                                   result: dict = None,
                                   error: str = None) -> Dict[str, Any]:
    """Send task status update to IT Lead"""
    params = {
        "task_id": task_id,
        "status": status,
        "progress": progress,
        "timestamp": time.time()
    }
    if result: params["result"] = result
    if error: params["error"] = error
    
    return self.send_notification("notifications/tasks/status", params)
```

### 2. Notification Handler

**File**: `handlers/notification_handlers.py` (new file per agent)

```python
"""
Async Task Notification Handlers
Handles incoming task notifications from IT Lead
"""
import asyncio
import time
from typing import Dict, Any
from ..utils.json_rpc import JsonRpcHandler


class NotificationHandlers:
    """Handles incoming MCP notifications for async tasks"""

    def __init__(self, task_storage, mcp_client, task_queue):
        self.task_storage = task_storage
        self.mcp_client = mcp_client
        self.task_queue = task_queue
        self.it_lead_endpoint = None  # Set during initialization

    def register_handlers(self, rpc_handler: JsonRpcHandler):
        """Register notification handlers"""
        rpc_handler.register_notification_handler(
            'notifications/tasks/new',
            self.handle_task_assignment
        )
        rpc_handler.register_notification_handler(
            'notifications/tasks/cancelled',
            self.handle_task_cancellation
        )

    async def handle_task_assignment(self, message: Dict[str, Any]):
        """Handle notifications/tasks/new from IT Lead"""
        params = message.get('params', {})
        task_id = params.get('task_id')
        tool = params.get('tool')
        arguments = params.get('arguments', {})
        callback_url = params.get('callback_url')

        print(f"📨 Received async task: {task_id} - Tool: {tool}")

        # Store task in agent's LOCAL database
        if self.task_storage:
            self.task_storage.store_received_task(
                task_id=task_id,
                title=f"Async Task: {task_id}",
                description=arguments.get('description', str(arguments)),
                assigned_to="self",  # This agent
                priority="medium",
                source_server="it-lead",
                metadata={
                    "tool_to_execute": tool,
                    "tool_arguments": arguments,
                    "callback_url": callback_url,
                    "async_mode": True,
                    "received_via": "notification"
                },
                status="queued"
            )

        # Queue for background processing
        if self.task_queue:
            await self.task_queue.enqueue(task_id, tool, arguments)

        # Acknowledge receipt to IT Lead
        if self.mcp_client and self.mcp_client.connected:
            await self.mcp_client.send_notification(
                "notifications/tasks/ack",
                {
                    "task_id": task_id,
                    "status": "received",
                    "timestamp": time.time()
                }
            )

    async def handle_task_cancellation(self, message: Dict[str, Any]):
        """Handle notifications/tasks/cancelled from IT Lead"""
        params = message.get('params', {})
        task_id = params.get('task_id')
        reason = params.get('reason', 'No reason provided')

        print(f"❌ Task cancelled: {task_id} - Reason: {reason}")

        # Update task status in local DB
        if self.task_storage:
            self.task_storage.store_received_task(
                task_id=task_id,
                title=f"Async Task: {task_id}",
                description=f"Cancelled: {reason}",
                assigned_to="self",
                priority="medium",
                source_server="it-lead",
                metadata={"cancellation_reason": reason},
                status="cancelled"
            )

        # Remove from queue if pending
        if self.task_queue:
            await self.task_queue.cancel(task_id)
```

### 3. Background Task Queue

**File**: `utils/task_queue.py` (new file per agent)

```python
"""
Async Task Queue for Background Processing
"""
import asyncio
import time
from typing import Dict, Any, Optional


class AsyncTaskQueue:
    """Background task queue for async task processing"""

    def __init__(self, task_storage, mcp_client, tool_executor):
        self.task_storage = task_storage
        self.mcp_client = mcp_client
        self.tool_executor = tool_executor
        self.queue = asyncio.Queue()
        self.running = False
        self.worker_task = None

    async def enqueue(self, task_id: str, tool: str, arguments: Dict[str, Any]):
        """Add task to queue"""
        await self.queue.put((task_id, tool, arguments))
        print(f"📥 Task queued: {task_id}")

    async def cancel(self, task_id: str):
        """Cancel a queued task (best effort)"""
        # Note: This is best-effort; asyncio.Queue doesn't support removal
        print(f"⚠️  Cancel requested for: {task_id}")

    async def start_worker(self):
        """Start background worker"""
        self.running = True
        self.worker_task = asyncio.create_task(self._process_loop())
        print("✅ Task queue worker started")

    async def stop_worker(self):
        """Stop background worker"""
        self.running = False
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        print("🛑 Task queue worker stopped")

    async def _process_loop(self):
        """Process tasks from queue"""
        while self.running:
            try:
                task_id, tool, arguments = await self.queue.get()
                await self._process_task(task_id, tool, arguments)
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Error in task queue: {e}")
                await asyncio.sleep(1)

    async def _process_task(self, task_id: str, tool: str, arguments: Dict[str, Any]):
        """Process a single task"""
        print(f"🔧 Processing task: {task_id} - Tool: {tool}")

        # Update status: in_progress
        await self._report_status(task_id, "in_progress", progress=0)

        try:
            # Execute the tool
            result = await self.tool_executor.execute_tool(tool, arguments)

            # Update status: completed
            await self._report_status(task_id, "completed", progress=100, result=result)
            print(f"✅ Task completed: {task_id}")

        except Exception as e:
            # Update status: failed
            await self._report_status(task_id, "failed", error=str(e))
            print(f"❌ Task failed: {task_id} - Error: {e}")

    async def _report_status(self, task_id: str, status: str, 
                              progress: int = 0, result: dict = None, 
                              error: str = None):
        """Report task status to IT Lead"""
        # Update local database
        if self.task_storage:
            self.task_storage.store_received_task(
                task_id=task_id,
                title=f"Async Task: {task_id}",
                description=f"Status: {status}",
                assigned_to="self",
                priority="medium",
                source_server="it-lead",
                metadata={"last_reported_status": status},
                status=status
            )

        # Send notification to IT Lead
        if self.mcp_client and self.mcp_client.connected:
            await self.mcp_client.send_task_status_notification(
                task_id=task_id,
                status=status,
                progress=progress,
                result=result,
                error=error
            )
```

### 4. Tool Executor Interface

**File**: `utils/tool_executor.py` (new file per agent)

```python
"""
Tool Executor Interface
Executes tools based on tool name and arguments
"""
from typing import Dict, Any


class ToolExecutor:
    """Executes tools by name"""

    def __init__(self, available_tools: Dict[str, callable]):
        """
        Initialize with available tools
        
        Args:
            available_tools: Dict mapping tool names to async functions
        """
        self.available_tools = available_tools

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by name
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        if tool_name not in self.available_tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        tool_func = self.available_tools[tool_name]
        return await tool_func(arguments)
```

### 5. Server Integration

**File**: `server.py` (modify existing server file)

Add the following to the server initialization:

```python
# In server __init__ or startup:

# 1. Initialize MCP client for sending notifications
from .client import McpClient
self.mcp_client = McpClient()
# Get IT Lead endpoint from registry or config
self.mcp_client.endpoint = "http://localhost:3061/mcp"
self.mcp_client.connect()

# 2. Initialize task queue
from .utils.task_queue import AsyncTaskQueue
from .utils.tool_executor import ToolExecutor

# Define available tools for this agent
available_tools = {
    "implement_feature": self.handle_implement_feature,
    "generate_code_from_spec": self.handle_generate_code_from_spec,
    # ... add other tools specific to this agent
}

self.tool_executor = ToolExecutor(available_tools)
self.task_queue = AsyncTaskQueue(
    task_storage=self.task_storage,
    mcp_client=self.mcp_client,
    tool_executor=self.tool_executor
)

# 3. Initialize notification handlers
from .handlers.notification_handlers import NotificationHandlers
self.notification_handlers = NotificationHandlers(
    task_storage=self.task_storage,
    mcp_client=self.mcp_client,
    task_queue=self.task_queue
)
self.notification_handlers.register_handlers(self.rpc_handler)

# 4. Start background worker
asyncio.create_task(self.task_queue.start_worker())
```

## Notification Types

| Notification | Direction | Purpose | Payload |
|--------------|-----------|---------|---------|
| `notifications/tasks/new` | IT Lead → Agent | Assign new task | `{task_id, tool, arguments}` |
| `notifications/tasks/ack` | Agent → IT Lead | Acknowledge receipt | `{task_id, status}` |
| `notifications/tasks/status` | Agent → IT Lead | Status update | `{task_id, status, progress, result?, error?}` |
| `notifications/tasks/cancelled` | IT Lead → Agent | Cancel task | `{task_id, reason}` |
| `notifications/tasks/completed` | Agent → IT Lead | Task completed | `{task_id, result}` |

## Task Status Values

| Status | Description |
|--------|-------------|
| `queued` | Task received, waiting in queue |
| `in_progress` | Task is being processed |
| `completed` | Task completed successfully |
| `failed` | Task failed with error |
| `cancelled` | Task was cancelled by IT Lead |

## Implementation Checklist (Per Agent)

- [ ] **Extend MCP Client** (`client.py`)
  - [ ] Add `send_notification()` method
  - [ ] Add `send_task_status_notification()` method

- [ ] **Create Notification Handlers** (`handlers/notification_handlers.py`)
  - [ ] Implement `handle_task_assignment()`
  - [ ] Implement `handle_task_cancellation()`
  - [ ] Register handlers with RPC handler

- [ ] **Create Task Queue** (`utils/task_queue.py`)
  - [ ] Implement `AsyncTaskQueue` class
  - [ ] Implement background worker loop
  - [ ] Implement status reporting

- [ ] **Create Tool Executor** (`utils/tool_executor.py`)
  - [ ] Implement `ToolExecutor` class
  - [ ] Map tool names to handler functions

- [ ] **Update Server** (`server.py`)
  - [ ] Initialize MCP client
  - [ ] Initialize task queue
  - [ ] Initialize notification handlers
  - [ ] Start background worker on startup
  - [ ] Stop worker on shutdown

## Testing

After implementation, test the async flow:

1. **Start IT Lead server**
2. **Start agent server**
3. **Call `assign_task_async`** on IT Lead:
   ```json
   {
     "task_id": "test-async-001",
     "task_description": "Test async task",
     "assignee": "implementation-engineer"
   }
   ```
4. **Verify agent receives notification** (check agent logs)
5. **Verify agent sends ack** (check IT Lead logs)
6. **Verify task is processed** (check both logs)
7. **Verify status updates** (check IT Lead receives `notifications/tasks/status`)
8. **Read task status resource**:
   ```
   it-lead://resource/task-status/test-async-001
   ```

## Migration from Sync to Async

Agents can support **both** sync and async modes:

- **Sync**: Existing `tools/call` pattern (blocking)
- **Async**: New `notifications/tasks/new` pattern (non-blocking)

The IT Lead will determine which mode to use based on the tool called:
- `assign_task` → Sync mode (existing behavior)
- `assign_task_async` → Async mode (new behavior)

## Troubleshooting

| Issue | Possible Cause | Solution |
|-------|----------------|----------|
| Agent doesn't receive task | Notification handler not registered | Check `register_handlers()` call |
| Task stays in "queued" status | Worker not started | Check `start_worker()` call |
| Status updates not received | MCP client not connected | Check `mcp_client.connect()` |
| Task fails immediately | Tool not found in executor | Check tool name mapping |

---

**Next Steps**: See agent-specific implementation docs in this directory for role-specific tool mappings.
