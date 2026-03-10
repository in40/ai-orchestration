# Investigation: task-1773158728213 - Deployment URL Not Working

## Task Information

| Field | Value |
|-------|-------|
| **Task ID** | `task-1773158728213` |
| **Status** | `done` |
| **Assigned To** | `devops-engineer` |
| **Git URL** | `ssh://sorokin@192.168.51.187/.../results/f8b0f931-f4ca-4161-bba2-80bc15f0ada1/result.py` |
| **Deployment URL** | `http://192.168.51.216:5011/` |
| **Workflow** | `["requirements-engineer", "implementation-engineer", "devops-engineer"]` |

## Issue

**"View Deployed App" button points to `http://192.168.51.216:5011/` but connection is refused.**

## Root Cause Analysis

### 1. Container Status
```bash
$ docker ps | grep task-1773158728213
7ad08dd67944   deploy-task-1773158728213   "python result.py"   17 minutes ago   Up 17 minutes   0.0.0.0:5011->5000/tcp
```
✅ Container is running

### 2. Port Mapping
- **Host port**: 5011
- **Container port**: 5000 (Docker expects app to listen on 5000)
- **Actual app port**: 8000 (hardcoded in result.py)

### 3. Generated Code Issue
```python
# From result.py line 209:
server = HTTPServer(('localhost', 8000), GameHandler)
print('Game server running on http://localhost:8000')
```

**Problem**: The generated code hardcodes port 8000, but:
1. DevOps expects app to use port 5000 (default)
2. Our port detection regex didn't catch `HTTPServer(('localhost', 8000)`
3. Docker maps `5011:5000`, but app listens on 8000

### 4. Port Detection Failure

Our port detection patterns (from `server_handlers.py`):
```python
port_patterns = [
    r'PORT\s*=\s*(\d+)',           # PORT = 8080
    r'port\s*=\s*(\d+)',           # port = 8080
    r'PORT\s*=\s*int\(os\.environ\.get\(["\']PORT["\']\s*,\s*(\d+)\)\)',
    r'server\.listen\((\d+)\)',    # Node.js style
    r'app\.run\(.*port\s*=\s*(\d+)',  # Flask style
]
```

**Missing pattern**: `HTTPServer\([^,]+,\s*(\d+)\)` or similar for Python http.server

### 5. Connection Test
```bash
$ curl -v http://192.168.51.216:5011/
curl: (7) Failed to connect to 192.168.51.216 port 5011: Connection refused

$ docker exec deploy-task-1773158728213 python -c "
  import socket
  s=socket.socket()
  r=s.connect_ex(('localhost', 5000))
  s.close()
  print(f'Port 5000: {\"OPEN\" if r==0 else \"CLOSED\"}')"
Port 5000: CLOSED

$ docker exec deploy-task-1773158728213 python /app/result.py
OSError: [Errno 98] Address already in use
```

**App crashed on startup** because:
1. It tried to bind to port 8000
2. Port 8000 was already in use (or binding failed)
3. Container shows "running" but app process died

## Timeline

```
1. Task submitted via Web UI with deploy checkbox ✓
2. Workflow: requirements → implementation → devops ✓
3. Implementation Engineer generated code with hardcoded port 8000 ✗
4. DevOps port detection didn't catch HTTPServer(('localhost', 8000) ✗
5. DevOps created Docker with EXPOSE 5000, mapped 5011:5000 ✗
6. Container started, app tried to bind to 8000, failed ✗
7. Container shows "running" but app is dead ✗
8. Deployment URL returns "Connection refused" ✗
```

## Why This Happened

### Issue 1: Incomplete Port Detection

Our regex patterns only catch:
- `PORT = 8080`
- `port = 3000`
- `app.run(port=5000)`
- `server.listen(3000)`

**But NOT**:
- `HTTPServer(('localhost', 8000), Handler)`
- `socketserver.TCPServer(("0.0.0.0", 9000), ...)`
- `run_simple('0.0.0.0', 5000, app)`

### Issue 2: App Crash Not Detected

Docker container shows "running" even though the Python app crashed immediately. No health check configured.

## Solutions

### Fix 1: Improve Port Detection Patterns

Add patterns for Python http.server and socketserver:

```python
port_patterns = [
    r'PORT\s*=\s*(\d+)',
    r'port\s*=\s*(\d+)',
    r'PORT\s*=\s*int\(os\.environ\.get\(["\']PORT["\']\s*,\s*(\d+)\)\)',
    r'server\.listen\((\d+)\)',
    r'app\.run\(.*port\s*=\s*(\d+)',
    # NEW: Python http.server and socketserver
    r'HTTPServer\([^,]+,\s*(\d+)',
    r'TCPServer\([^,]+,\s*(\d+)',
    r'UDPServer\([^,]+,\s*(\d+)',
    r'serve_forever\([^)]*port\s*=\s*(\d+)',
    r'run_simple\([^,]+,\s*(\d+)',  # Werkzeug
]
```

### Fix 2: Add Container Health Check

In DevOps deployment:
```python
subprocess.run([
    "docker", "run", "-d",
    "--name", container_name,
    "-p", f"{host_port}:{container_port}",
    "--health-cmd", f"curl -f http://localhost:{container_port}/ || exit 1",
    "--health-interval", "10s",
    "--health-retries", "3",
    "--health-start-period", "5s",
    "--restart", "unless-stopped",
    image_name
])
```

### Fix 3: Detect App Crash and Restart

Monitor container health and restart if app crashes:
```python
# After deployment, verify app is responding
import time
import httpx

time.sleep(5)  # Wait for app to start
try:
    response = httpx.get(f"http://localhost:{host_port}", timeout=5)
    if response.status_code != 200:
        print(f"⚠️ App returned status {response.status_code}, restarting...")
        # Restart container
except Exception as e:
    print(f"❌ App not responding: {e}, restarting container...")
    # Restart container
```

## Immediate Fix for task-1773158728213

```bash
# Stop current container
docker stop deploy-task-1773158728213
docker rm deploy-task-1773158728213

# Redeploy with correct port (8000)
docker run -d \
  --name deploy-task-1773158728213 \
  -p 5011:8000 \
  --restart unless-stopped \
  deploy-task-1773158728213

# Test
curl http://192.168.51.216:5011/
```

## Files to Modify

1. **`devops-release-engineer-mcp-server/devops_release_engineer_mcp_server/handlers/server_handlers.py`**
   - Add more port detection patterns
   - Add health check to docker run
   - Add post-deployment verification

2. **`it-lead-mcp-server/it_lead_mcp_server/utils/llm_task_planner.py`**
   - Add instruction to LLM: "Use PORT = int(os.environ.get('PORT', 5000)) for web servers"

## Status

**Investigation Complete** ✅

**Root Cause**: Port detection regex didn't catch `HTTPServer(('localhost', 8000)` pattern

**Fix Required**: Add more port detection patterns + health checks
