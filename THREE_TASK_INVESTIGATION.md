# Investigation: Three Tasks Comparison

## Tasks Analyzed

| Task ID | Status | Expected | Actual | Issue |
|---------|--------|----------|--------|-------|
| `task-1773160492410` | ✅ `done` | Working deployment | Working | **NONE - Working as expected** |
| `task-1773160511616` | ❌ `done` | Working deployment | Connection refused | Flask binds to localhost |
| `task-1773160483045` | ⏳ `in_progress` | Complete deployment | Stuck at implementation | Implementation not completed |

---

## Detailed Analysis

### Task 1: task-1773160492410 ✅ WORKING

**Status**: `done`  
**Deployment URL**: `http://192.168.51.216:5012/` - **HTTP 200** ✅

**Workflow**: `["requirements-engineer", "implementation-engineer", "devops-engineer"]`

**Git UUID**: `ac5145ff-d5c9-487f-9a30-67737bc68cf4`

**Code Analysis**:
```python
PORT = 8000
with socketserver.TCPServer(("", PORT), GameServerHandler) as httpd:
    print(f"Serving at port {PORT}")
```

**Why It Works**:
- ✅ Uses `TCPServer(("", PORT), ...)` - empty string `""` binds to `0.0.0.0` (all interfaces)
- ✅ Port 8000 correctly detected by DevOps
- ✅ Docker mapped: `5012:8000`
- ✅ Accessible from outside container

**Container Logs**:
```
192.168.51.216 - - [10/Mar/2026 16:46:01] "GET / HTTP/1.1" 200 -
```

---

### Task 2: task-1773160511616 ❌ NOT WORKING

**Status**: `done` (but deployment broken)  
**Deployment URL**: `http://192.168.51.216:5013/` - **Connection refused** ❌

**Workflow**: `["requirements-engineer", "implementation-engineer", "devops-engineer"]`

**Git UUID**: `5d38c47c-5cf4-48d2-8c11-df828d2e344c`

**Code Analysis**:
```python
from flask import Flask
app = Flask(__name__)
# ... routes ...
app.run(debug=True, port=5000)  # ❌ Flask defaults to 127.0.0.1
```

**Why It Fails**:
- ❌ Flask's `app.run()` defaults to `127.0.0.1` (localhost only)
- ✅ Port 5000 correctly detected by DevOps
- ✅ Docker mapped: `5013:5000`
- ❌ App binds to `127.0.0.1:5000` inside container - not accessible from host

**Container Logs**:
```
 * Running on http://127.0.0.1:5000  ← ❌ localhost only!
```

**Fix Required**:
```python
# Should be:
app.run(host='0.0.0.0', debug=True, port=5000)
```

---

### Task 3: task-1773160483045 ⏳ STUCK IN PROGRESS

**Status**: `in_progress`  
**Deployment URL**: None (not deployed yet)

**Workflow**: `["implementation-engineer", "devops-engineer"]`

**Git UUID**: None (code not generated yet)

**Routing Decision**:
```json
{
  "confidence": 1.0,
  "matched_rule_id": "rule-1.1",  // Python implementation
  "requires_llm_planning": false
}
```

**LLM Plan** (from Option 3 post-processing):
```json
{
  "workflow_sequence": ["implementation-engineer", "devops-engineer"],
  "tools": {
    "implementation-engineer": "vibe_code_async",
    "devops-engineer": "deploy_web_application"
  },
  "reasoning": "Rule-based routing with auto-detected deployment requirement"
}
```

**Why It's Stuck**:
- ✅ Matched rule-1.1 (Python implementation) with high confidence
- ✅ Option 3 added `devops-engineer` to workflow
- ❌ Implementation Engineer hasn't completed code generation
- ❌ No git commit found
- ❌ No poller logs (task never reached polling stage)

**Investigation**:
- No logs in `/tmp/implementation_engineer.log`
- No logs in `/tmp/poller_debug.log`
- No container deployed

**Likely Cause**: Implementation Engineer is still processing or encountered an error during code generation.

---

## Root Cause Summary

### Common Issue: Flask/Server Binding to localhost

| Task | Framework | Binding | Result |
|------|-----------|---------|--------|
| 1773160492410 | socketserver | `""` → `0.0.0.0` | ✅ Works |
| 1773160511616 | Flask | `127.0.0.1` (default) | ❌ Fails |
| 1773160483045 | N/A (not generated) | N/A | ⏳ Pending |

### Why LLM Generates Different Code

The LLM generates code based on:
1. **Task description** - may or may not specify deployment requirements
2. **Vibe coding prompt** - currently has instructions to use `0.0.0.0` (just added)
3. **Randomness** - LLM may choose different frameworks (Flask vs socketserver)

**Before our fix**: No instructions about binding to `0.0.0.0`
**After our fix**: LLM instructed to use `host='0.0.0.0'` for web servers

---

## Fixes Applied

### Fix 1: Port Detection Patterns ✅
Added patterns for HTTPServer, TCPServer, Flask, uvicorn, etc.

### Fix 2: LLM Instructions ✅
Added to vibe coding prompt:
```
8. **For web servers/APIs: Use PORT environment variable or port 5000**:
   - Python: `PORT = int(os.environ.get("PORT", 5000))`
   - Always bind to `0.0.0.0` not `localhost` for Docker compatibility
   - Example: `HTTPServer(('0.0.0.0', PORT), Handler)` or `app.run(host='0.0.0.0', port=PORT)`
```

### Fix 3: Option 3 Deployment Detection ✅
Rule-based routing now auto-adds `devops-engineer` when:
- Deployment keywords detected in task description
- `deploy_after_implementation` flag set in metadata

---

## Recommended Actions

### For task-1773160511616 (broken deployment)

**Option A**: Redeploy with host binding fix
```bash
docker stop deploy-task-1773160511616
docker rm deploy-task-1773160511616

# Manually fix the code to use host='0.0.0.0'
# Then redeploy
```

**Option B**: Regenerate code with new LLM instructions
- Re-submit task with same description
- New code will use `host='0.0.0.0'`

### For task-1773160483045 (stuck)

**Investigate Implementation Engineer**:
```bash
# Check if Implementation Engineer is running
ps aux | grep implementation

# Check recent logs
tail -100 /tmp/implementation_engineer.log

# Check IT Lead logs for task forwarding
tail -500 /tmp/it_lead.log | grep 1773160483045
```

**If stuck**: Restart Implementation Engineer or re-submit task.

---

## Verification Commands

```bash
# Check all three tasks
PGPASSWORD=postgres psql -h 127.0.0.1 -U postgres -d mcp_registry \
  -c "SELECT task_id, status, metadata->>'deployment_url' as url FROM task_registry \
   WHERE task_id IN ('task-1773160511616', 'task-1773160492410', 'task-1773160483045');"

# Test deployment URLs
curl -s -o /dev/null -w "%{http_code}" http://192.168.51.216:5012/  # Expected: 200
curl -s -o /dev/null -w "%{http_code}" http://192.168.51.216:5013/  # Expected: 000 (broken)

# Check containers
docker ps | grep -E "1773160511616|1773160492410"
```

---

## Status Summary

| Task | Status | Issue | Fix Status |
|------|--------|-------|------------|
| 1773160492410 | ✅ Working | None | N/A |
| 1773160511616 | ❌ Broken | Flask binds to localhost | LLM instructions added |
| 1773160483045 | ⏳ Stuck | Implementation not completed | Needs investigation |

**Overall**: 1/3 working, 1/3 broken (fixable), 1/3 stuck (needs investigation)
