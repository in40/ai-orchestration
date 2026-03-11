# Deployment Isolation Solution Proposal

## Current Architecture

```
┌─────────────────────────┐         ┌─────────────────────────┐
│   Git Server            │         │   MCP Host              │
│   192.168.51.187        │         │   192.168.51.216        │
│                         │         │                         │
│   - Git Repository      │  SSH    │   - Registry (3031)     │
│   - Code Storage        │◄───────►│   - IT Lead (3061)      │
│   - result.py files     │         │   - Implementation Eng  │
│                         │         │   - Requirements Eng    │
│                         │         │   - DevOps Engineer     │
│                         │         │   - Web UI (8000/5173)  │
└─────────────────────────┘         └─────────────────────────┘
```

## Problem Statement

When deploying multiple generated web applications:
1. **Port conflicts** - Multiple Flask apps default to port 5000
2. **Dependency conflicts** - Different apps may need different package versions
3. **Process management** - Need to start/stop/restart individual deployments
4. **Resource isolation** - Prevent one app from affecting others

## Deployment Location Analysis

### Option A: Deploy on Git Server (192.168.51.187)
| Pros | Cons |
|------|------|
| ✅ Code already there (no transfer) | ❌ Mixed concerns (storage + execution) |
| ✅ Direct file access | ❌ Security risk (user code on storage server) |
| ✅ Simple architecture | ❌ Harder to scale |
| | ❌ Git server becomes single point of failure |

### Option B: Deploy on MCP Host (192.168.51.216) - **RECOMMENDED**
| Pros | Cons |
|------|------|
| ✅ Separation of concerns | ⚠️ Need to pull code from Git |
| ✅ Better security isolation | |
| ✅ Easier to manage deployments | |
| ✅ Can scale independently | |
| ✅ DevOps engineer runs on same host | |

### Option C: Deploy on Separate Host
| Pros | Cons |
|------|------|
| ✅ Maximum isolation | ❌ More infrastructure |
| ✅ Dedicated resources | ❌ Network complexity |
| | ❌ Additional maintenance |

## Recommended Solution: Docker-based Deployment on MCP Host

### Why Docker?

| Requirement | Docker Solution |
|-------------|-----------------|
| Port isolation | Each container gets own port (5001, 5002, ...) |
| Dependency isolation | Each container has own Python env |
| Process isolation | Containers are isolated processes |
| Resource limits | CPU/memory limits per container |
| Easy cleanup | `docker rm` removes everything |
| Reproducibility | Same image every time |

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Host (192.168.51.216)                │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Container 1 │  │ Container 2 │  │ Container 3 │         │
│  │ Port 5001   │  │ Port 5002   │  │ Port 5003   │         │
│  │ task-abc    │  │ task-def    │  │ task-ghi    │         │
│  │ Flask app   │  │ Flask app   │  │ Flask app   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              DevOps Engineer Service                 │   │
│  │  - Creates Dockerfile from result.py                 │   │
│  │  - Builds Docker image                               │   │
│  │  - Runs container with mapped port                   │   │
│  │  - Returns deployment URL to IT Lead                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Deployment Registry                     │   │
│  │  - task_id → container_id mapping                    │   │
│  │  - Port assignments                                  │   │
│  │  - Deployment URLs                                   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Workflow

```
1. Implementation Engineer generates result.py
   └─► Commits to Git repository

2. IT Lead detects workflow completion
   └─► Forwards task to DevOps Engineer (via MCP)
       └─► Includes: task_id, git_url, result.py path

3. DevOps Engineer:
   a) Clones/fetches result.py from Git
   b) Analyzes dependencies (checks imports)
   c) Creates Dockerfile:
      ```dockerfile
      FROM python:3.11-slim
      WORKDIR /app
      COPY result.py .
      RUN pip install flask  # Auto-detected
      EXPOSE 5000
      CMD ["python", "result.py"]
      ```
   d) Builds image: `docker build -t deploy-task-<uuid> .`
   e) Finds available port (5001, 5002, ...)
   f) Runs container: 
      ```bash
      docker run -d \
        --name deploy-task-<uuid> \
        -p <PORT>:5000 \
        --memory="256m" \
        --cpus="0.5" \
        deploy-task-<uuid>
      ```
   g) Returns deployment_url: `http://192.168.51.216:<PORT>/`

4. IT Lead:
   a) Updates task status to "deployed"
   b) Stores deployment_url in task metadata
   c) Updates status_history
   d) Returns result to user via Web UI
```

### Database Schema Addition

```sql
-- Add deployment tracking table
CREATE TABLE task_deployments (
    task_id VARCHAR(255) PRIMARY KEY,
    container_id VARCHAR(255) NOT NULL,
    container_port INTEGER NOT NULL,
    host_port INTEGER NOT NULL,
    deployment_url VARCHAR(512) NOT NULL,
    status VARCHAR(50) DEFAULT 'running',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    stopped_at TIMESTAMP NULL,
    git_commit_sha VARCHAR(64),
    docker_image VARCHAR(255)
);

-- Add to task_registry metadata
-- deployment_url: "http://192.168.51.216:5001/"
-- container_id: "deploy-task-32705e02"
```

### DevOps Engineer MCP Tools

```python
tools = [
    {
        "name": "deploy_web_application",
        "description": "Deploy a Python web application from Git repository",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "git_url": {"type": "string"},
                "result_path": {"type": "string"},
                "memory_limit": {"type": "string", "default": "256m"},
                "cpu_limit": {"type": "string", "default": "0.5"}
            },
            "required": ["task_id", "git_url", "result_path"]
        }
    },
    {
        "name": "stop_deployment",
        "description": "Stop a deployed application",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"}
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "list_deployments",
        "description": "List all active deployments",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_deployment_status",
        "description": "Get status of a specific deployment",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"}
            },
            "required": ["task_id"]
        }
    }
]
```

### Port Management

```python
# Simple port allocation strategy
USED_PORTS = {5000}  # Web UI backend
MIN_PORT = 5001
MAX_PORT = 5100

def get_available_port():
    for port in range(MIN_PORT, MAX_PORT):
        if port not in USED_PORTS and not is_port_in_use(port):
            USED_PORTS.add(port)
            return port
    raise Exception("No available ports")
```

### Alternative: If Docker Not Available

**Fallback: Python venv + systemd user services**

```bash
# Create isolated environment
python3 -m venv /opt/deployments/task-<uuid>/venv
source /opt/deployments/task-<uuid>/venv/bin/activate
pip install flask

# Create systemd user service
cat > ~/.config/systemd/user/deploy-task-<uuid>.service << EOF
[Unit]
Description=Deployment for task-<uuid>

[Service]
ExecStart=/opt/deployments/task-<uuid>/venv/bin/python /opt/deployments/task-<uuid>/result.py
Environment=PORT=5001
Restart=always

[Install]
WantedBy=default.target
EOF

systemctl --user start deploy-task-<uuid>
```

## Implementation Priority

1. **Phase 1**: Basic Docker deployment (single app)
   - Add `deploy_web_application` tool to DevOps Engineer
   - Update IT Lead workflow to include DevOps step
   - Store deployment URL in task metadata

2. **Phase 2**: Multi-app support
   - Port management system
   - Deployment registry (PostgreSQL table)
   - Container naming convention

3. **Phase 3**: Operations
   - `stop_deployment` tool
   - `list_deployments` tool
   - Health check endpoint

4. **Phase 4**: Advanced features
   - Dependency auto-detection (parse imports)
   - Resource limits
   - Deployment logs
   - Auto-cleanup of stopped containers

## Recommendation

**Deploy on MCP Host (192.168.51.216) using Docker containers.**

This provides:
- ✅ Clean separation from Git storage
- ✅ Full isolation (ports, dependencies, processes)
- ✅ Easy management via Docker CLI/API
- ✅ Scalability (up to 100 concurrent deployments)
- ✅ Security (container isolation)
- ✅ Resource control (memory/CPU limits)
