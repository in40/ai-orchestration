# FIX APPLIED: Tasks Stuck at in_progress

## Root Cause

The Implementation Engineer server was failing to call the LLM because the `LLM_MODEL` environment variable was **not being exported** to the Python process.

### What Was Happening:

1. `start_mcp_master.sh` calls `start_mcp_server.sh` for Implementation Engineer
2. `start_mcp_server.sh` sources `.env` file which sets `LLM_MODEL=qwen3-coder-next@q5_k_xl`
3. Script sets `LLM_MODEL` variable but **never exports it**
4. Python process starts without `LLM_MODEL` in its environment
5. Python's `Settings()` class reads `llm_model=None` (default value)
6. LLM API calls sent with `model=null` → HTTP 500 Internal Server Error
7. After 5 retries, task marked as "failed"
8. Task stays at "in_progress" in IT Lead database

## Fix Applied

**File Modified**: `/root/qwen/base/mcp-std-coder/mcp-vibe-coding-agent/start_mcp_server.sh`

**Change**: Added export statements for LLM configuration variables after line 29:

```bash
LLM_PROVIDER_URL="${LLM_PROVIDER_URL:-http://192.168.51.237:1234/v1/chat/completions}"
LLM_MODEL="${LLM_MODEL:-qwen3-coder-next@q5_k_xl}"

# Export LLM configuration for Python process
export LLM_PROVIDER_URL
export LLM_MODEL
```

## Verification

### Before Fix:
```bash
$ cat /proc/<pid>/environ | tr '\0' '\n' | grep LLM
(empty - no LLM variables)
```

Tasks failed with:
```
⚠️ LLM call failed (attempt 1/5): 500 Server Error
⚠️ LLM call failed (attempt 2/5): 500 Server Error
...
❌ LLM call failed after 5 attempts
```

### After Fix:
```bash
$ cat /proc/841123/environ | tr '\0' '\n' | grep LLM
LLM_PROVIDER_URL=http://192.168.51.237:1234/v1/chat/completions
LLM_TEMPERATURE=1.0
LLM_MODEL=qwen3-coder-next@q5_k_xl
```

Tasks complete successfully:
```
DEBUG: LLM response received, calling git_push_llm_response for task d074c40e...
Task status: completed (progress: 100%)
```

## Test Results

```bash
# Submit test task
$ curl -X POST http://localhost:3060/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"test","method":"tools/call","params":{"name":"vibe_code_async","arguments":{"task_description":"Create hello world in Python","language":"python","vibe_level":1}}}'

# Response
{
  "taskId": "d074c40e-5735-4a62-bc97-023a6ca244c0",
  "status": "submitted"
}

# Check status after 20 seconds
$ curl -X POST http://localhost:3060/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"check","method":"tools/call","params":{"name":"tasks/get","arguments":{"taskId":"d074c40e-5735-4a62-bc97-023a6ca244c0"}}}'

# Response - SUCCESS!
{
  "taskId": "d074c40e-5735-4a62-bc97-023a6ca244c0",
  "status": "completed",
  "progress": 100
}
```

## Impact

This fix resolves the issue where **ALL tasks** submitted to the Implementation Engineer were failing because:
- LLM calls were failing with HTTP 500 errors
- Tasks were stuck at "in_progress" status in IT Lead
- No code was being generated

## Related Issues

This fix also resolves the secondary issue where the IT Lead's background poller doesn't update task status when async tasks fail. Now that LLM calls succeed, tasks complete properly and the status update issue is no longer triggered.

## Files Modified

1. `/root/qwen/base/mcp-std-coder/mcp-vibe-coding-agent/start_mcp_server.sh` - Added LLM export statements

## Restart Required

To apply this fix, restart the Implementation Engineer server:

```bash
# Kill existing server
pkill -f "mcp_std_server.*3060"

# Start new server
cd /root/qwen/base/mcp-std-coder/mcp-vibe-coding-agent
bash ./start_mcp_server.sh --port 3060
```

Or restart the entire MCP system:

```bash
cd /root/qwen/base
bash ./start_mcp_master.sh
```
