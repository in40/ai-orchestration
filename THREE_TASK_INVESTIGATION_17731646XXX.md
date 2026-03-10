# Investigation: Three Tasks Comparison

## Executive Summary

| Task ID | Status | Issue | Root Cause |
|---------|--------|-------|------------|
| **task-1773164616849** | ❌ `in_progress` | Stuck after 1+ hour | Missing async_task_id (Layer 2 issue) |
| **task-1773164623890** | ✅ `done` | Working | LLM planning triggered async processing |
| **task-1773164631668** | ⚠️ `done` (broken) | Deployment URL returns 000 | Flask binds to 127.0.0.1 instead of 0.0.0.0 |

---

## Detailed Analysis

### Task 1: task-1773164616849 ❌ STUCK

**Status**: `in_progress` (stuck since 16:42:57 - over 1 hour)

**Workflow**: `["implementation-engineer", "devops-engineer"]`

**Routing**: 
```json
{
  "confidence": 1.0,
  "matched_rule_id": "rule-1.1",
  "requires_llm_planning": false
}
```

**async_task_id**: ❌ **NULL/Empty**

**Issue**: 
- Matched rule-1.1 (Python implementation) with HIGH confidence (1.0)
- LLM planning was SKIPPED (`requires_llm_planning: false`)
- Implementation Engineer processed as SYNC
- No async_task_id returned
- Background poller NEVER STARTED
- Task stuck in `in_progress` forever

**Evidence**:
```bash
# No poller logs
grep "1773164616849" /tmp/poller_debug.log
# Result: (empty)

# No IT Lead logs
tail -1000 /tmp/it_lead.log | grep "1773164616849"
# Result: (empty)
```

**Root Cause**: **SAME AS task-1773160483045** - Layer 2 issue

**Fix Required**: Manual recovery OR wait for Layer 2 fix to process workflow

---

### Task 2: task-1773164623890 ✅ WORKING

**Status**: `done`

**Workflow**: `["requirements-engineer", "implementation-engineer", "devops-engineer"]`

**Deployment URL**: `http://192.168.51.216:5015/` - **HTTP 200** ✅

**Git UUID**: `974e34c5-6c42-4411-a482-fb0f5b2f3930`

**Code Analysis**:
```python
PORT = 8000
with socketserver.TCPServer(('', PORT), GameHandler) as httpd:
    # '' binds to 0.0.0.0 (all interfaces) ✅
```

**Why It Worked**:
- LLM planning WAS triggered (`requires_llm_planning: true` likely)
- Workflow included requirements-engineer first
- Async processing worked correctly
- Code uses `''` which binds to `0.0.0.0` ✅
- Docker mapped `5015:8000` correctly ✅
- Accessible from outside container ✅

**Container Status**:
```bash
docker ps | grep 1773164623890
# deploy-task-1773164623890   Up 8 minutes   0.0.0.0:5015->8000/tcp
```

---

### Task 3: task-1773164631668 ⚠️ BROKEN DEPLOYMENT

**Status**: `done` (but deployment doesn't work)

**Workflow**: `["requirements-engineer", "implementation-engineer", "devops-engineer"]`

**Deployment URL**: `http://192.168.51.216:5014/` - **HTTP 000** ❌

**Git UUID**: `1b7fa333-4c95-40b2-a6d8-8d5f5d84c3ba`

**Code Analysis**:
```python
from flask import Flask
app = Flask(__name__)
# ...
app.run(debug=True)  # ❌ Defaults to 127.0.0.1:5000
```

**Issue**:
- Flask's `app.run()` defaults to `127.0.0.1:5000` (localhost only)
- Docker mapped `5014:5000` ✅
- But app only listens on `127.0.0.1` inside container ❌
- Not accessible from outside container ❌

**Evidence**:
```bash
# Container is running
docker ps | grep 1773164631668
# deploy-task-1773164631668   Up 9 minutes   0.0.0.0:5014->5000/tcp

# Port 5000 is open inside container
docker exec deploy-task-1773164631668 python -c "
  import socket
  s=socket.socket()
  r=s.connect_ex(('localhost', 5000))
  s.close()
  print(f'Port 5000: {\"OPEN\" if r==0 else \"CLOSED\"}')"
# Port 5000: OPEN

# But container logs show binding to localhost
docker logs deploy-task-1773164631668
# * Running on http://127.0.0.1:5000  ← ❌ localhost only!

# Connection refused from host
curl -v http://192.168.51.216:5014/
# curl: (7) Failed to connect to 192.168.51.216 port 5014: Connection refused
```

**Root Cause**: **LLM generated code with Flask binding to localhost**

**Fix Required**: 
1. Regenerate code with instruction to use `host='0.0.0.0'`
2. OR manually fix container:
```bash
docker stop deploy-task-1773164631668
docker rm deploy-task-1773164631668
# Manually edit result.py to use: app.run(host='0.0.0.0', debug=True)
# Rebuild and redeploy
```

---

## Comparison Table

| Aspect | task-1773164616849 | task-1773164623890 | task-1773164631668 |
|--------|-------------------|-------------------|-------------------|
| **Status** | `in_progress` | `done` | `done` |
| **Workflow** | 2 agents | 3 agents | 3 agents |
| **LLM Planning** | ❌ Skipped | ✅ Triggered | ✅ Triggered |
| **async_task_id** | ❌ NULL | ✅ Present | ✅ Present |
| **Poller Started** | ❌ No | ✅ Yes | ✅ Yes |
| **Git URL** | ❌ None | ✅ Generated | ✅ Generated |
| **Deployment** | ❌ None | ✅ Working | ⚠️ Broken |
| **Port Binding** | N/A | ✅ `''` → `0.0.0.0` | ❌ `127.0.0.1` |
| **HTTP Status** | N/A | 200 ✅ | 000 ❌ |

---

## Root Causes Identified

### Issue 1: Layer 2 Problem (task-1773164616849)

**Same as previous investigation**:
- High confidence rule match → LLM planning skipped
- Implementation Engineer processed as sync
- No async_task_id returned
- Poller never started
- Task stuck

**Status**: ✅ **Layer 2 fix deployed** - should prevent future occurrences

### Issue 2: Flask Localhost Binding (task-1773164631668)

**New issue discovered**:
- LLM generated Flask code with `app.run(debug=True)`
- Flask defaults to `127.0.0.1` (localhost)
- Docker can't access localhost binding from outside container
- Deployment URL returns connection refused

**Status**: ❌ **Not fixed by Layer 2** - requires LLM instruction fix

---

## Recommended Actions

### Immediate (Now)

1. **Recover task-1773164616849** (Layer 2 issue):
```bash
# Task should be processed by Layer 2 fix now
# Check if it completed
PGPASSWORD=postgres psql -h 127.0.0.1 -U postgres -d mcp_registry \
  -c "SELECT task_id, status FROM task_registry WHERE task_id='task-1773164616849';"
```

2. **Fix task-1773164631668** (localhost binding):
```bash
# Option A: Redeploy with fixed code
docker stop deploy-task-1773164631668
docker rm deploy-task-1773164631668

# Option B: Manually fix in container (temporary)
docker exec deploy-task-1773164631668 sed -i \
  's/app.run(debug=True)/app.run(host="0.0.0.0", debug=True)/' \
  /app/result.py
docker restart deploy-task-1773164631668
```

### Short-term (Today)

1. **Add LLM instruction** to always use `host='0.0.0.0'` for Flask:
```python
# In vibe_coder.py prompt
"For Flask apps: app.run(host='0.0.0.0', port=PORT)"
```

2. **Add port detection** for Flask apps in DevOps:
```python
# Detect app.run() without host parameter
if 'app.run(' in content and 'host=' not in content:
    print("⚠️ Flask app missing host='0.0.0.0' - deployment will fail")
```

### Long-term (This week)

1. **Implement Layer 3 fix** (Implementation Engineer always async)
2. **Add health checks** to detect localhost binding issues
3. **Add monitoring** for tasks stuck > 5 minutes

---

## Files Created

- `THREE_TASK_INVESTIGATION_17731646XXX.md` - This report

---

## Status Summary

| Task | Issue | Status | Fix Status |
|------|-------|--------|------------|
| 1773164616849 | Layer 2 (missing async_task_id) | ❌ Stuck | ✅ Layer 2 deployed |
| 1773164623890 | None | ✅ Working | N/A |
| 1773164631668 | Flask localhost binding | ⚠️ Broken | ❌ Needs LLM fix |

---

**Investigation Complete**: ✅  
**New Issues Found**: 1 (Flask localhost binding)  
**Action Required**: Fix LLM instructions for Flask host binding
