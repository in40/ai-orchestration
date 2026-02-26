# MCP System - Complete Workflow Demonstration

## Overview
This document describes the complete workflow demonstration for the Model Context Protocol (MCP) system.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Registry Server (port 3031)                │
│           Central service discovery and coordination         │
└──────────────────┬──────────────────────────────────────────┘
                   │
          ┌────────┼───────────────┬──────────┐
          │        │               │          │
    ┌─────▼────┐ ┌─▼─────┐    ┌──▼────┐ ┌──▼────────┐
    |IT Lead   | │Imp.     |    |Req.   | |Team       |
    |Server    | │Engineer|    |Engineer| |Management  |
    |3061      | │3060     |    |3062    | |3063        |
    └──────────┘ └─────────┘    └───────┘ └───────────┘
```

## Starting the System

### Option 1: Master Startup Script (Recommended)

```bash
cd /root/qwen/base && ./start_mcp_master.sh
```

This starts all servers in dependency order:
1. Registry Server (3031)
2. Requirements Engineer (3062)
3. IT Lead Server (3061)
4. Team Management (3063)

### Option 2: Start Manually

```bash
# Terminal 1: Start Registry
cd /root/qwen/base/mcp-std-skeleton && ./start_registry_server.sh --port 3031

# Terminal 2: Start Implementation Engineer (vibe coding)
cd /root/qwen/base/mcp-std-coder/mcp-vibe-coding-agent && bash start_mcp_server.sh --port 3060

# Terminal 3: Start IT Lead
cd /root/qwen/base/it-lead-mcp-server && ./start_it_lead_server.sh

# Terminal 4: Start Requirements Engineer (if needed)
cd /root/qwen/base/requirements-engineer-mcp-server/requirement-engineer-mcp-server && ./start_requirement_engineer_server.sh

# Terminal 5: Start Team Management
cd /root/qwen/base/team-management-ui/team-management-mcp-server && ./start_team_management_server.sh
```

## Running the Workflow Demo

### Using the Shell Script (Recommended)

```bash
/root/qwen/base/run_workflow.sh
```

This will:
1. Show all registered services in the registry
2. Submit tasks for processing
3. Display task status and results

### Using Python Script

```bash
python3 /root/qwen/base/run_mcp_workflow_demo.py
```

## Task Types Supported

### 1. Architecture Analysis (`analyze_architecture`)
- Analyzes current system architecture
- Identifies scalability, performance, security issues
- Provides recommendations for improvements

**Example:**
```bash
curl -X POST http://localhost:3061/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"analyze_architecture","arguments':{"current_architecture":"Flask monolith","requirements":"Add CI/CD and Dockerize"}},"id":"1"}'
```

### 2. Task Assignment (`assign_task`)
- Assign tasks to specific agents
- Track task status through the registry
- Support for priority levels and deadlines

**Example:**
```bash
curl -X POST http://localhost:3061/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"assign_task","arguments':{"task_id":"task-001","task_description":"Create REST API","assignee":"requirement-engineer","priority":"high"}}},"id":"1"}'
```

### 3. Project Planning (`generate_project_plan`)
- Create project plans with timelines
- Allocate resources
- Define milestones

**Example:**
```bash
curl -X POST http://localhost:3061/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"generate_project_plan","arguments":{'requirements':'Build e-commerce platform','team_size':5,'timeline_weeks':12}}},"id":"1"}'
```

## Service Registry Endpoints

### List All Services
```bash
curl -X POST http://localhost:3031/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"registry/list","params":{},"id":"list"}'
```

### Register a Service
```bash
curl -X POST http://localhost:3031/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"registry/register","params":{"service_id":"my-service","endpoint":"http://localhost:4000/mcp"},"id":"register"}'
```

### Unregister a Service
```bash
curl -X POST http://localhost:3031/mCP \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"registry/unregister","params":{"service_id":"my-service"},"id":"unregister"}'
```

## Task Workflow

1. **Submit**: Client submits a task to IT Lead Server
2. **Analyze**: IT Lead analyzes requirements and determines best agent
3. **Assign**: IT Lead forwards task to appropriate agent (Requirements/Implementation)
4. **Execute**: Agent completes the task
5. **Report**: Results are stored in the registry for client access

## Files

- `/root/qwen/base/start_mcp_master.sh` - Master startup script
- `/root/qwen/base/run_workflow.sh` - Workflow demonstration script
- `/root/qwen/base/run_mcp_workflow_demo.py` - Python workflow demo
- `/tmp/mcp_registry.log` - Registry logs
- `/tmp/it_lead.log` - IT Lead server logs

## Monitoring

### Check Service Health
```bash
# Check registry
curl http://localhost:3031/

# Check IT Lead
curl http://localhost:3061/
```

### View Logs
```bash
tail -f /tmp/mcp_registry.log
tail -f /tmp/it_lead.log
```

## Stopping the System

Press `Ctrl+C` in the terminal where the master script is running, or:

```bash
pkill -f "mcp_std_server" || true
pkill -f it_lead_mcp_server || true
pkill -f team_management || true
```
