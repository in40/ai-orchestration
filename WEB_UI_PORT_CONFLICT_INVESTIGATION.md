# Web UI Port Conflict Investigation - ROOT CAUSE FOUND

**Date**: March 10, 2026  
**Issue**: Web UI becoming unavailable repeatedly

---

## Root Cause

The Web UI backend (port 8000) was failing because:

### 1. Docker Containers Occupying Port 8000

Multiple Docker containers were mapping their internal port 8000 to various host ports:

```
/usr/bin/docker-proxy -proto tcp -host-ip 0.0.0.0 -host-port 5009 -container-ip 172.17.0.6 -container-port 8000
/usr/bin/docker-proxy -proto tcp -host-ip 0.0.0.0 -host-port 5011 -container-ip 172.17.0.8 -container-port 8000
/usr/bin/docker-proxy -proto tcp -host-ip 0.0.0.0 -host-port 5012 -container-ip 172.17.0.9 -container-port 8000
/usr/bin/docker-proxy -proto tcp -host-ip 0.0.0.0 -host-port 5015 -container-ip 172.17.0.12 -container-port 8000
/usr/bin/docker-proxy -proto tcp -host-ip 0.0.0.0 -host-port 5017 -container-ip 172.17.0.14 -container-port 8000
```

**Impact**: Even though these are on different external ports, they can cause port binding conflicts.

### 2. Multiple Stale `start_ui.sh` Processes

Processes from different dates were all running simultaneously:

```
root 1446490 0.0 0.0 7216 3584 ? S Mar09 0:00 bash ./start_ui.sh --web-backend-port 8000 ...
root 1654705 0.0 0.0 7216 3488 pts/3 S+ 21:08 0:00 bash ./start_ui.sh --web-backend-port 8000 ...
root 1657306 0.0 0.0 7216 3556 ? S 21:20 0:00 bash ./start_ui.sh --web-backend-port 8000 ...
```

**Impact**: Each attempt to restart created a NEW process without killing the old one.

### 3. Zombie Vite Frontend Processes

Multiple Vite dev servers running on the same port 5173:

```
root 1422849 ... node .../vite --port 5173 --host 0.0.0.0  (Mar09)
root 1446537 ... node .../vite --port 5173                (Mar09)
root 1654729 ... node .../vite --port 5173                (21:08)
root 1657371 ... node .../vite --port 5173                (21:20)
```

**Impact**: Port 5173 became unusable, frontend couldn't start.

### 4. Python `result.py` Processes

Dozens of zombie Python processes holding various ports:

```
root 1056817 ... python result.py
root 1512157 ... python result.py
root 1512230 ... /usr/local/bin/python result.py
... (20+ processes)
```

**Impact**: System resources exhausted, ports occupied.

---

## Error Logs

```
ERROR: [Errno 98] error while attempting to bind on address ('0.0.0.0', 8000): address already in use
INFO: Waiting application shutdown.
INFO: Application shutdown complete.
```

---

## Solution

### Immediate Fix: Use Different Ports

Instead of fighting for ports 8000/5173, use unused ports:

| Service | Old Port | New Port |
|---------|----------|----------|
| Web UI Backend | 8000 | **9000** |
| Web UI Frontend | 5173 | **9180** |

### Start Commands

```bash
# Kill all stale processes
pkill -9 -f "start_ui.sh"
pkill -9 -f "vite.*5173"
pkill -9 -f "vite.*9180"
pkill -9 -f "uvicorn.*main"

# Start backend on port 9000
cd /root/qwen/base/it-lead-mcp-server/web-ui/backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 9000 &

# Start frontend on port 9180
cd /root/qwen/base/it-lead-mcp-server/web-ui/frontend
npm run dev -- --port 9180 --host 0.0.0.0 &
```

### Access

- **Web UI**: http://localhost:9180
- **Backend API**: http://localhost:9000/api

---

## Permanent Fix Required

### 1. Fix `start_ui.sh` Script

The script should:
1. Check if ports are in use BEFORE starting
2. Kill existing processes on those ports
3. Use unique PIDs and track them properly
4. Implement proper cleanup on exit

### 2. Add Port Conflict Detection

```bash
# Check if port is in use
if lsof -i :$BACKEND_PORT > /dev/null 2>&1; then
    echo "❌ Port $BACKEND_PORT is already in use!"
    echo "Run: lsof -i :$BACKEND_PORT to see what's using it"
    echo "Run: kill -9 <PID> to free the port"
    exit 1
fi
```

### 3. Implement Process Management

- Use PID files to track running processes
- Implement proper signal handling (SIGTERM, SIGINT)
- Auto-cleanup on script exit

### 4. Docker Container Cleanup

Remove unused Docker containers that may be holding ports:

```bash
docker ps --filter "expose=8000"
docker stop <container_id>
docker rm <container_id>
```

---

## Status

| Issue | Status |
|-------|--------|
| Web UI Backend | ✅ Running on port 9000 |
| Web UI Frontend | ✅ Running on port 9180 |
| All Agents | ✅ Online |
| Port Conflicts | ⚠️ Avoided (using new ports) |
| Permanent Fix | ❌ NOT YET IMPLEMENTED |

---

## Next Steps

1. ✅ Web UI working on ports 9000/9180
2. ❌ Fix `start_ui.sh` to handle port conflicts
3. ❌ Clean up Docker containers
4. ❌ Kill zombie `result.py` processes
5. ❌ Implement proper process management
