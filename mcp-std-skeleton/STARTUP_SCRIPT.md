# MCP System Startup Scripts

This directory contains several scripts for starting individual and multiple servers.

## Master Startup Script

**`start_mcp_master.sh`** - Starts the complete MCP system with all agents:

```
Usage: ./mcp_std_skeleton/start_mcp_master.sh
       cd /root/qwen/base && ./start_mcp_master.sh
```

This script starts in order:
1. **Registry Server** (port 3031) - Central service discovery
2. **Requirements Engineer** (port 3062) - Requirements management agent
3. **IT Lead Server** (port 3061) - IT leadership and coordination agent
3. **Team Management** (port 3063) - Team/task management UI

## Individual Start Scripts

### Registry Server
```bash
cd /root/qwen/base/mcp-std-skeleton && ./start_registry_server.sh --port 3031
```

### Requirements Engineer
```bash
cd /root/qwen/base/requirements-engineer-mcp-server/requirement-engineer-mcp-server && ./start_requirement_engineer_server.sh
```

### IT Lead Server
```bash
cd /root/qwen/base/it-lead-mcp-server && ./start_it_lead_server.sh
```

### Team Management
```bash
cd /root/qwen/base/team-management-ui/team-management-mcp-server && ./start_team_management_server.sh
```

## Stopping the System

The master startup script can be stopped with Ctrl+C, which gracefully shuts down all servers.

To stop individual servers:

```bash
# Registry server
./stop_registry_server.sh --port 3031

# IT Lead server  
./stop_it_lead_server.sh --port 3061

# Team Management
./stop_team_management_server.sh --port 3041
```
