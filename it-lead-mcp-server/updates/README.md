# Async Task Management Implementation - Updates Directory

## Overview

This directory contains implementation specifications for adding **asynchronous task management** support to all MCP agents in the IT Lead ecosystem.

## Background

The IT Lead MCP Server has been enhanced to support asynchronous task assignment via MCP notifications. This allows:

- **Non-blocking task assignment** - IT Lead doesn't wait for agent to complete tasks
- **Background processing** - Agents process tasks in background workers
- **Status tracking** - Real-time status updates via notifications
- **Resource-based queries** - Check task status via `it-lead://resource/task-status/{task_id}`

## Documents in This Directory

| Document | Description | Target Audience |
|----------|-------------|-----------------|
| `00_COMMON_BASE_IMPLEMENTATION.md` | Common base implementation for all agents | All agent developers |
| `01_IMPLEMENTATION_ENGINEER_ASYNC.md` | Detailed Implementation Engineer guide | Implementation Engineer developer |
| `02_ALL_OTHER_AGENTS_ASYNC.md` | Guides for all other agents | Other agent developers |

## Implementation Order

### Phase 1: IT Lead Server (Completed ✅)

The IT Lead server has been updated with:

1. **Extended MCP Client** (`client.py`)
   - `send_notification()` - Send MCP notifications
   - `send_task_notification()` - Assign tasks to agents
   - `send_task_status_notification()` - Report status updates

2. **Extended NotificationManager** (`utils/notifications.py`)
   - `notify_task_assigned()` - Notify agents of new tasks
   - `notify_task_status_update()` - Send status updates
   - `notify_task_acknowledged()` - Handle acknowledgments

3. **Async Task Handlers** (`handlers/async_task_handlers.py`)
   - `assign_task_async` - Non-blocking task assignment
   - `get_async_task_status` - Query task status
   - `list_async_tasks` - List all async tasks
   - `cancel_async_task` - Cancel running tasks

4. **Extended Server Handlers** (`handlers/extended_server_handlers.py`)
   - Integrated async task handlers
   - Added task status resources
   - Routing for async tool calls

### Phase 2: Agent Implementation (In Progress)

Each agent needs to implement:

1. **MCP Client Extension** - Add notification sending capability
2. **Notification Handlers** - Handle incoming task notifications
3. **Task Queue** - Background worker for async processing
4. **Tool Executor** - Map tool names to handlers
5. **Server Integration** - Initialize and start components

## Quick Start Guide

### For IT Lead Server Users

```bash
# 1. Start IT Lead server
./start_it_lead_server.sh

# 2. Assign async task
curl -X POST http://localhost:3061/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "tools/call",
    "params": {
      "name": "assign_task_async",
      "arguments": {
        "task_id": "my-async-task-001",
        "task_description": "Create a REST API endpoint",
        "assignee": "implementation-engineer"
      }
    }
  }'

# 3. Check task status
curl -X POST http://localhost:3061/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "2",
    "method": "resources/read",
    "params": {
      "uri": "it-lead://resource/task-status/my-async-task-001"
    }
  }'
```

### For Agent Developers

1. **Read the common base implementation** - `00_COMMON_BASE_IMPLEMENTATION.md`
2. **Find your agent's document** - See table above
3. **Follow the implementation checklist** - Each document has a checklist
4. **Test with IT Lead** - Use the quick start commands

## Architecture Diagram

```
┌─────────────────┐                          ┌─────────────────┐
│   IT Lead       │                          │   Agent         │
│   (Server)      │                          │   (Server)      │
└────────┬────────┘                          └────────┬────────┘
         │                                            │
         │ 1. assign_task_async (tools/call)          │
         │◀───────────────────────────────────────────│ Client
         │                                            │
         │ 2. Store task in IT Lead DB                │
         │                                            │
         │ 3. notifications/tasks/new                 │
         │────────────────────────────────────────────▶
         │                                            │
         │ 4. Store task in Agent DB                  │
         │                                            │
         │ 5. notifications/tasks/ack                 │
         │◀────────────────────────────────────────────│
         │                                            │
         │ 6. Queue task for background processing    │
         │                                            │
         │ 7. notifications/tasks/status (in_progress)│
         │◀────────────────────────────────────────────│
         │                                            │
         │ 8. Process task (background worker)        │
         │                                            │
         │ 9. notifications/tasks/completed           │
         │◀────────────────────────────────────────────│
         │                                            │
         │ 10. Update IT Lead DB                      │
         │                                            │
         │ 11. resources/read task-status/{id}        │
         │◀───────────────────────────────────────────│ Client
         │                                            │
```

## Notification Types

| Notification | Direction | Purpose |
|--------------|-----------|---------|
| `notifications/tasks/new` | IT Lead → Agent | Assign new task |
| `notifications/tasks/ack` | Agent → IT Lead | Acknowledge receipt |
| `notifications/tasks/status` | Agent → IT Lead | Status update |
| `notifications/tasks/cancelled` | IT Lead → Agent | Cancel task |
| `notifications/tasks/completed` | Agent → IT Lead | Task completed |

## Task Status Values

| Status | Description |
|--------|-------------|
| `queued` | Task received, waiting in queue |
| `in_progress` | Task is being processed |
| `completed` | Task completed successfully |
| `failed` | Task failed with error |
| `cancelled` | Task was cancelled |

## Testing

### Prerequisites

- IT Lead server running on port 3061
- At least one agent server running (e.g., Implementation Engineer on 3060)

### Test Commands

```bash
# Test 1: Assign async task
python3 test_async_assignment.py

# Test 2: Check task status
python3 test_task_status.py

# Test 3: List all async tasks
python3 test_list_tasks.py

# Test 4: Cancel a task
python3 test_cancel_task.py
```

### Expected Results

1. **Task Assignment** - Returns immediately with `task_id` and `status: "forwarded"`
2. **Status Updates** - Agent sends periodic status updates
3. **Task Completion** - Final status update with result
4. **Resource Query** - Returns full task history and status

## Troubleshooting

| Issue | Possible Cause | Solution |
|-------|----------------|----------|
| Agent doesn't receive task | Notification handler not registered | Check `register_handlers()` call |
| Task stays in "queued" | Worker not started | Check `start_worker()` call |
| Status not updating | MCP client disconnected | Check `mcp_client.connect()` |
| Task fails immediately | Tool not found | Check tool name mapping |

## Migration Path

### From Sync to Async

Existing synchronous task assignment (`assign_task`) continues to work. New async tools run in parallel:

| Feature | Sync (`assign_task`) | Async (`assign_task_async`) |
|---------|---------------------|----------------------------|
| **Response Time** | Blocks until complete | Returns immediately |
| **Use Case** | Quick operations | Long-running tasks |
| **Status Tracking** | Poll agent directly | Resource-based queries |
| **Error Handling** | Immediate error return | Status = "failed" |

### Backward Compatibility

- Existing `assign_task` tool: **No changes required**
- Existing agent tools: **Continue to work**
- New `assign_task_async` tool: **Optional, opt-in**

## Next Steps

1. **Implement agents** - Follow documents in this directory
2. **Test end-to-end** - Verify full async flow
3. **Monitor performance** - Track task completion times
4. **Gather feedback** - Improve based on usage patterns

## Support

For questions or issues:
1. Check the troubleshooting tables in each document
2. Review the common base implementation
3. Examine IT Lead server logs for notification flow
4. Check agent logs for task processing

---

**Last Updated**: 2026-02-16
**Version**: 1.0.0
**Status**: IT Lead implementation complete, Agent implementation in progress
