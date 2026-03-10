# Deployment URL Investigation - Root Cause Analysis

## Task Information
- **Task ID**: `task-1773150833618`
- **Status**: `done`
- **Deployment URL**: `http://192.168.51.216:5008/`
- **Git URL**: `ssh://sorokin@192.168.51.187/home/sorokin/mcp-results/tree/main/results/afc3f045-9030-4c31-9942-f91b74c1a7bc/result.py`
- **Issue**: Deployment URL returns "Connection refused" / non-existing resource

---

## Root Cause

### Architecture Mismatch

The system has **TWO SEPARATE SERVERS**:

| Server | IP Address | Purpose |
|--------|------------|---------|
| **Application Server** | `192.168.51.216` | Runs MCP agents, DevOps server, Docker containers, Web UI |
| **Git Server** | `192.168.51.187` | Stores Git repository with generated code |

### The Problem

1. **DevOps Engineer runs on `192.168.51.216`** (Application Server)
2. **Git repository is on `192.168.51.187`** (Git Server)
3. **DevOps deploys Docker container to `192.168.51.216:5008`**
4. **Container crashes immediately** - Python app inside doesn't start

### Container Status

```bash
$ docker ps | grep deploy-task-1773150833618
6a0999f60795   deploy-task-1773150833618   "python result.py"   7 minutes ago   Up 7 minutes   0.0.0.0:5008->5000/tcp   deploy-task-1773150833618
```

Container is **running** but:
- Port 5008 is listening on host
- **Connection is reset** when accessing `http://192.168.51.216:5008/`
- **No logs** from container (app crashed or never started)
- Port 5000 inside container is **free** (not bound by application)

### Why the Container Crashes

The deployed `result.py` is a **Python HTTP server** that should:
1. Import required modules
2. Create HTTP server on port 5000
3. Handle requests

However, the container shows:
- **Port 5000 inside container is CLOSED** (application bound to different port)
- **Port 8080 inside container is OPEN** (app is running on wrong port!)
- **Container is running** but serving on wrong port

### Code Analysis - PORT MISMATCH

The DevOps engineer generates this Dockerfile:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY result.py .
RUN pip install flask
EXPOSE 5000
CMD ["python", "result.py"]
```

And runs the container with:
```bash
docker run -d -p 5008:5000 deploy-task-1773150833618
```

**But the generated `result.py` uses:**
```python
PORT = 8080  # ← MISMATCH! Docker expects 5000

def run_server():
    with socketserver.TCPServer(("", PORT), NexusHandler) as httpd:
        print(f"NexusTech server running at http://localhost:{PORT}")
        httpd.serve_forever()
```

**Result**: 
- App runs on port 8080 inside container
- Docker maps port 5000 to host port 5008
- **Port 5000 has nothing listening** → Connection refused

---

## Secondary Issues

### 1. No SSH Tunnel / Port Forwarding

The deployment URL points to `192.168.51.216:5008`, but:
- No SSH tunnel is configured between servers
- No port forwarding from Git server (187) to App server (216)
- Users accessing from network can't reach the deployment

### 2. Hardcoded Deployment Host

In `devops_release_engineer_mcp_server/handlers/server_handlers.py:518`:
```python
deployment_url = f"http://192.168.51.216:{host_port}/"
```

This is **hardcoded** and should be configurable via `.env`.

### 3. No Health Check

The Docker container has no health check configured, so:
- Container shows "running" even if app crashed
- No automatic restart on failure
- No visibility into actual application health

---

## Evidence

### 1. Container Logs (Empty)
```bash
$ docker logs deploy-task-1773150833618
(empty)
```

### 2. Port Check Inside Container
```bash
$ docker exec deploy-task-1773150833618 python -c "import socket; s=socket.socket(); s.bind(('0.0.0.0', 5000)); print('port 5000 free')"
port 5000 free
```

### 3. Connection Test
```bash
$ curl -v http://192.168.51.216:5008/
curl: (56) Recv failure: Connection reset by peer
```

### 4. Git Repository Location
```bash
$ ssh sorokin@192.168.51.187 "ls /home/sorokin/mcp-results.git"
# Repository exists on 192.168.51.187

$ ls /tmp/mcp-vibe-coding-git/repo/results/afc3f045-9030-4c31-9942-f91b74c1a7bc/
result.py  response.json  # Files exist in local clone
```

### 5. Network Interfaces
```bash
# Application Server (where DevOps runs)
inet 192.168.51.216/24

# Git Server (where code is stored)
inet 192.168.51.187/24
```

---

## Proposed Fixes

### Fix 1: Enforce Standard Port in Generated Code (CRITICAL)

**Problem**: Generated `result.py` files use arbitrary ports (8080, 3000, etc.) instead of standard port 5000

**Root Cause**: LLM generates code with hardcoded port that doesn't match Docker expectation

**Solution**: Update the Implementation Engineer's code generation prompt to ALWAYS:
1. Use `PORT = 5000` (or read from `PORT` environment variable)
2. Include proper `if __name__ == "__main__"` block

**Example template**:
```python
import os
PORT = int(os.environ.get("PORT", 5000))

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), NexusHandler) as httpd:
        print(f"Serving on port {PORT}")
        httpd.serve_forever()
```

**Files to modify**:
- `mcp-std-coder/mcp-vibe-coding-agent/prompts/` - Add port requirement to system prompt
- `mcp-std-coder/mcp-vibe-coding-agent/implementation_engineer.py` - Add port validation

### Fix 2: Update DevOps to Use Environment Variable for Port

**Problem**: DevOps Dockerfile hardcodes `EXPOSE 5000` but app might use different port

**Solution**: Make DevOps detect port from generated code or use environment variable:

```python
# Detect port from result.py
import re
with open(os.path.join(deploy_dir, "result.py"), 'r') as f:
    content = f.read()
    port_match = re.search(r'PORT\s*=\s*(\d+)', content)
    container_port = int(port_match.group(1)) if port_match else 5000

# Use detected port in Docker run
subprocess.run([
    "docker", "run", "-d",
    "--name", container_name,
    "-p", f"{host_port}:{container_port}",
    # ... rest of options
])
```

**Files to modify**:
- `devops-release-engineer-mcp-server/devops_release_engineer_mcp_server/handlers/server_handlers.py` - Add port detection

---

## Immediate Action Required

### To fix the current deployment (task-1773150833618):

**Option A - Restart container with correct port mapping**:
```bash
# Stop current container
docker stop deploy-task-1773150833618
docker rm deploy-task-1773150833618

# Restart with correct port mapping (8080 instead of 5000)
docker run -d \
  --name deploy-task-1773150833618 \
  -p 5008:8080 \
  --restart unless-stopped \
  deploy-task-1773150833618

# Test
curl http://192.168.51.216:5008/
```

**Option B - Access on correct port** (if container can't be restarted):
```bash
# The app is running on port 8080 inside container
# But there's no way to access it without restarting
# Container would need to be recreated with correct port mapping
```

### To prevent future occurrences:

1. **Update Implementation Engineer prompt** to require `PORT = 5000` or `PORT = int(os.environ.get("PORT", 5000))`
2. **Update DevOps deployment** to detect port from generated code
3. **Add Docker health check** to detect crashed/misconfigured containers
4. **Add container restart policy** (`--restart unless-stopped`)

---

## Verification

### Fix Applied

Restarted container with correct port mapping:
```bash
docker stop deploy-task-1773150833618
docker rm deploy-task-1773150833618
docker run -d --name deploy-task-1773150833618 -p 5008:8080 --restart unless-stopped deploy-task-1773150833618
```

### Result

```bash
$ curl http://192.168.51.216:5008/
<!DOCTYPE html>
<html lang="en">
<head>
    <title>NexusTech | Modern Innovation Solutions</title>
...
```

**Deployment URL is now accessible!**

---

## Summary

| Issue | Root Cause | Fix Priority |
|-------|------------|--------------|
| Deployment URL not working | **Port mismatch**: App runs on 8080, Docker maps 5000 | **CRITICAL** |
| Container shows running but not serving | App bound to wrong port inside container | **CRITICAL** |
| Hardcoded deployment host | `192.168.51.216` hardcoded in DevOps code | HIGH |
| No health monitoring | Docker container has no health check | MEDIUM |
| Two-server architecture confusion | Git on 187, Deploy on 216, no tunnel | MEDIUM |

---

## Next Steps

1. **Immediate**: ✅ **DONE** - Restarted container with correct port mapping (`-p 5008:8080`)
2. **Short-term**: Update Implementation Engineer to use `PORT = 5000` or `PORT = int(os.environ.get("PORT", 5000))`
3. **Medium-term**: Update DevOps to detect port from generated code
4. **Long-term**: Add Docker health checks and decide on deployment architecture (single server vs remote deployment)
