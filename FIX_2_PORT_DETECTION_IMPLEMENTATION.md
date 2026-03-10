# Fix 2 Implementation: Auto-Detect Port in DevOps Deployment

## Summary

Implemented automatic port detection in DevOps Engineer deployment logic. The system now:
1. Scans generated `result.py` for PORT declarations
2. Uses detected port in Docker configuration
3. Falls back to port 5000 if no custom port found

## Changes Made

### File Modified
`/root/qwen/base/devops-release-engineer-mcp-server/devops_release_engineer_mcp_server/handlers/server_handlers.py`

### Implementation Details

Added port detection logic before creating Dockerfile:

```python
# Detect PORT from generated code
container_port = 5000  # Default fallback
port_patterns = [
    r'PORT\s*=\s*(\d+)',           # PORT = 8080
    r'port\s*=\s*(\d+)',           # port = 8080
    r'PORT\s*=\s*int\(os\.environ\.get\(["\']PORT["\']\s*,\s*(\d+)\)\)',  # PORT = int(os.environ.get("PORT", 8080))
    r'server\.listen\((\d+)\)',    # server.listen(3000) - Node.js style
    r'app\.run\(.*port\s*=\s*(\d+)',  # app.run(port=5000)
]
for pattern in port_patterns:
    port_match = re.search(pattern, content)
    if port_match:
        detected_port = int(port_match.group(1))
        print(f"✅ Detected PORT={detected_port} from pattern: {pattern}")
        container_port = detected_port
        break

if container_port != 5000:
    print(f"⚠️  Non-standard port detected: {container_port} (default is 5000)")
else:
    print(f"ℹ️  Using default PORT=5000 (no custom port detected)")

# Create Dockerfile with detected port
dockerfile_content = f"""FROM python:3.11-slim
WORKDIR /app
COPY result.py .
RUN pip install {' '.join(dependencies)}
EXPOSE {container_port}
CMD ["python", "result.py"]
"""
```

## Test Results

### Unit Tests
All 6 test cases passed:
- ✅ PORT = 8080 → detected 8080
- ✅ PORT = 5000 → detected 5000
- ✅ PORT = int(os.environ.get("PORT", 3000)) → detected 3000
- ✅ No PORT variable → default 5000
- ✅ port = 9000 (lowercase) → detected 9000
- ✅ app.run(port=5000) → detected 5000

### Live Test
Tested on task-1773150833618's result.py:
```
✅ Detected PORT=8080 from pattern: PORT\s*=\s*(\d+)
⚠️  Non-standard port detected: 8080 (default is 5000)
```

## Verification

The DevOps server has been restarted with the new code:
```bash
ps aux | grep devops_release_engineer
# Server running on http://127.0.0.1:3071
```

## Impact

### Before Fix
- DevOps hardcoded `-p {host_port}:5000` for all deployments
- Applications using different ports (8080, 3000, etc.) would fail
- Manual intervention required to fix port mappings

### After Fix
- DevOps auto-detects port from generated code
- Docker mapping uses correct container port
- Deployments work regardless of which port the app uses
- Backward compatible (defaults to 5000 if no port detected)

## Example Deployment Flow

```
1. DevOps receives: git_url with result.py
2. Clones Git repository
3. Reads result.py content
4. Detects PORT = 8080
5. Creates Dockerfile with EXPOSE 8080
6. Runs: docker run -p 5008:8080 ...
7. Application accessible at http://192.168.51.216:5008/
```

## Next Steps

Remaining fixes from investigation:
1. ✅ **Fix 2: Auto-detect port** - COMPLETE
2. ⏳ Fix 1: Enforce PORT=5000 in Implementation Engineer prompts
3. ⏳ Fix 3: Make deployment host configurable via .env
4. ⏳ Fix 4: Add Docker health checks
5. ⏳ Fix 5: Architecture decision documentation

## Files Created

- `test_port_detection.py` - Unit test suite
- `test_port_detection_live.py` - Live test on actual result.py
- `FIX_2_PORT_DETECTION_IMPLEMENTATION.md` - This document

## Status

✅ **Fix 2 COMPLETE** - DevOps now auto-detects port from generated code
