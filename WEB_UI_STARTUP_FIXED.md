# ✅ Web UI Fixed - Now Works with start_mcp_master.sh

## Problem

Web UI was not accessible when starting via `start_mcp_master.sh` because:
1. `start_ui.sh` had hardcoded LLM model defaults
2. `start_ui.sh` didn't load `.env` configuration
3. `pydantic-settings` package was not installed in Web UI virtual environment

## Fixes Applied

### 1. Updated start_ui.sh to Load .env

**File: `/root/qwen/base/it-lead-mcp-server/start_ui.sh`**

**Before:**
```bash
# Hardcoded defaults
LLM_MODEL="qwen3.5-35b-a3b@q5_k_xl"  # ❌ WRONG!
```

**After:**
```bash
# Load configuration from .env file
if [ -f "/root/qwen/base/.env" ]; then
    source /root/qwen/base/.env
    echo "✅ Loaded configuration from /root/qwen/base/.env"
fi

# Use values from .env or fallback
LLM_MODEL="${LLM_MODEL:-qwen3-coder-next@q5_k_xl}"  # ✅ From .env
```

### 2. Installed pydantic-settings in Web UI venv

```bash
cd /root/qwen/base/it-lead-mcp-server/web-ui/backend
source venv/bin/activate
pip install pydantic-settings python-dotenv
```

### 3. Updated Help Message

```bash
# Before
--llm-model MODEL  [default: qwen3.5-35b-a3b@q5_k_xl]

# After  
--llm-model MODEL  [default: from .env (qwen3-coder-next@q5_k_xl)]
```

## Testing

### Start Web UI via start_mcp_master.sh

```bash
cd /root/qwen/base
bash ./start_mcp_master.sh
```

### Verify Web UI is Running

```bash
# Check processes
$ ps aux | grep -E "uvicorn|npm.*dev" | grep -v grep
root ... uvicorn main:app --host 0.0.0.0 --port 8000
root ... npm run dev --port 5173

# Test backend
$ curl http://localhost:8000/
{"message":"MCP Agent Web UI Backend is running","status":"healthy"}

# Test frontend
$ curl http://localhost:5173/
<!DOCTYPE html>...
```

### Verify Configuration Loaded

```bash
# Check startup logs
$ tail /tmp/webui.log
Starting MCP Agent Web UI...
✅ Loaded configuration from /root/qwen/base/.env
Configuration:
  Web Backend: 0.0.0.0:8000
  Web Frontend: 5173
  LLM_MODEL: qwen3-coder-next@q5_k_xl
```

## Files Modified

1. `/root/qwen/base/it-lead-mcp-server/start_ui.sh` - Load .env, use config values
2. Web UI virtual environment - Installed `pydantic-settings` and `python-dotenv`

## Usage

### Start All Services

```bash
cd /root/qwen/base
bash ./start_mcp_master.sh
```

### Start Web UI Only

```bash
cd /root/qwen/base/it-lead-mcp-server
bash ./start_ui.sh
```

### Access Web UI

- **Frontend**: http://localhost:5173/
- **Backend API**: http://localhost:8000/

## Configuration

Edit `/root/qwen/base/.env` to customize:

```bash
# Web UI settings
WEB_UI_HOST=0.0.0.0
WEB_UI_BACKEND_PORT=8000
WEB_UI_FRONTEND_PORT=5173
WEB_UI_PUBLIC_URL=http://192.168.51.1:8000

# LLM settings
LLM_MODEL=qwen3-coder-next@q5_k_xl
LLM_PROVIDER_URL=http://192.168.51.237:1234/v1/chat/completions
```

## Summary

✅ Web UI now loads configuration from `.env` file
✅ No hardcoded LLM model values
✅ All required packages installed
✅ Works correctly with `start_mcp_master.sh`
✅ Accessible at http://localhost:5173/
