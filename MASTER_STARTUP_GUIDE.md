# Master Startup Script - Complete Documentation

## Overview

The **Master Startup Script** (`start_mcp_master.sh`) starts the complete MCP system with all components in the correct dependency order.

## Files Created

### `/root/qwen/base/start_mcp_master.sh`
Master startup script that coordinates all server startups.

## What It Starts

| Step | Service | Port | Purpose |
|------|---------|------|---------|
| 1 | Registry Server | 3031 | Central service discovery |
| 2 | Requirements Engineer | 3062 | Requirements management |
| 3 | IT Lead Server | 3061 | Leadership and coordination |
| 4 | Team Management | 3063 | Task/team management |
| 5 | **Web UI** | 8000/5173 | **New! Web interface** |

## Usage

```bash
# Start the complete system
/root/qwen/base/start_mcp_master.sh

# Or from any directory:
cd /root/qwen && ./start_mcp_master.sh
```

## How It Works

### Step-by-Step Startup Sequence:

1. **Registry Server (3031)** - Starts first, must be available for other services to register
2. **Requirements Engineer (3062)** - Registers with registry on startup
3. **IT Lead Server (3061)** - Registers with registry, also starts internal task tracking
4. **Team Management (3063)** - Registers with registry
5. **Web UI (8000/5173)** - Backend (FastAPI) and Frontend (Vite/React) servers

## Service Discovery Flow

```
┌─────────────┐
│ Registry    │──┐
│ (3031)      │  │ registers itself
└─────────────┘  │
                 │
           ┌─────┴─────┐
           │           │
       ┌───▼───┐   ┌───▼───┐
       │ IT    │   │ Team  │   (registered services)
       │ Lead  │   │ Mgmt  │
       │ 3061  │   │ 3063  │
       └───────┘   └───────┘

All services use the registry to discover each other's endpoints.
Registry ONLY provides discovery - it does NOT track tasks!
```

## Task Tracking (Separate from Registry!)

Tasks are tracked LOCALLY by IT Lead, not in the registry:

1. Client submits task to IT Lead
2. IT Lead stores in local database with status="received"
3. IT Lead forwards to appropriate agent using registry for endpoint discovery
4. Progress is tracked locally by IT Lead only

## Stopping the System

Press `Ctrl+C` in the terminal where the script is running.

The cleanup function will:
- Stop all MCP servers
- Kill any remaining processes
- Show shutdown confirmation

## Verification

After startup, verify services:

```bash
# Check registry
curl http://localhost:3031/mcp -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"registry/list","params":{},"id":"check"}'

# Check IT Lead tasks
curl http://localhost:3061/mcp -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_all_tasks","arguments":{}},"id":"tasks"}'

# Access Web UI
open http://localhost:5173/
```

## Web Interface

### Backend (Port 8000)
- FastAPI application serving as the REST API layer
- Endpoint: `http://localhost:8000`
- Health check: `/` or `/health`

### Frontend (Port 5173)
- React + Vite single-page application
- Provides web UI for task management
- Access: `http://localhost:5173`

## Configuration

The script uses default ports. To change them, edit the script's port numbers in these sections:

- **Registry**: Change `--port 3031` to desired value
- **Web UI Backend**: Modify line with `--web-backend-port`
- **Web UI Frontend**: Modify line with `--web-frontend-port`

## Troubleshooting

### Server won't start
- Check logs: `/tmp/mcp_registry.log`, `/tmp/it_lead.log`, etc.
- Ensure port is not already in use: `lsof -i :3031`

### Service not registering
- Make sure the previous service started successfully first
- Check registry logs for error messages

### Web UI won't start
- Ensure Node.js dependencies are installed in frontend directory
- Check if ports 8000 or 5173 are already in use

## Log Files

| Service | Log File |
|---------|----------|
| Registry | `/tmp/mcp_registry.log` |
| IT Lead | `/tmp/it_lead.log` |
| Requirements | `/tmp/req_eng.log` |
| Team Mgmt | `/tmp/team_management.log` |
| Web UI Backend | `/tmp/webui.log` |

## Next Steps

After the system is running:

1. Access the Web UI at `http://localhost:5173/`
2. Submit your first task
3. Monitor progress through the registry
4. Check IT Lead's local database for detailed status

---

**Note**: The registry should ONLY be used for service discovery (finding which endpoints provide what services). Task tracking is handled locally by IT Lead.
