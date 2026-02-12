# Vibe Coding AI Agent - Task Management Utilities

This repository contains the complete Vibe Coding AI Agent MCP Server and associated task management utilities.

## 🚀 Quick Start

### 1. Start the Server
```bash
./start_server.sh
```

The server will start on `http://localhost:3050/mcp` with Streamable HTTP transport.

### 2. Submit Coding Tasks
```bash
./task_manager.sh submit "Create a Python function to calculate fibonacci numbers"
```

### 3. Check Queue Status
```bash
./task_manager.sh list
```

### 4. Check Specific Task
```bash
./task_manager.sh check <plan_id>
```

## 🛠️ Available Utilities

### 1. `task_manager.sh` - Complete Task Management Suite
Full-featured utility for submitting tasks, managing queues, and tracking completion.

**Commands:**
- `submit "task"` - Submit a new coding task
- `list` - Show queue status and all tasks
- `check <plan_id>` - Check status of specific task
- `health` - Check server health
- `analyze "code"` - Analyze code for issues
- `generate "spec"` - Generate code from specification
- `clear` - Clear local task storage
- `logs` - Show recent operation logs

### 2. `task_queue_manager.sh` - Queue-Focused Manager
Simple utility focused on task queuing and management.

**Commands:**
- `submit "task"` - Submit a new task to queue
- `list` - Show current queue status
- `check <plan_id>` - Check specific task status
- `health` - Check server health
- `clear` - Clear local queue tracking

### 3. `advanced_task_utility.sh` - Advanced Features
Extended utility with additional development tools.

**Commands:**
- `submit "task"` - Submit a new coding task
- `list` - List all tracked tasks
- `check <plan_id>` - Check specific task status
- `health` - Check server health
- `analyze "code"` - Analyze code for issues
- `generate "spec"` - Generate code from specification

### 4. `task_utility.sh` - Basic Task Submission
Simple utility for basic task submission.

**Commands:**
- `submit "task"` - Submit a new coding task
- `list` - List active tasks
- `health` - Check server health

## 📋 Example Workflows

### Submit a Development Task
```bash
./task_manager.sh submit "Create a Python Flask API with CRUD operations for a todo list"
```

### Analyze Code for Issues
```bash
./task_manager.sh analyze "def divide(a, b): return a / b"
```

### Generate Code from Specification
```bash
./task_manager.sh generate "Create a JavaScript function that sorts an array of objects by a specific property"
```

### Monitor Task Progress
```bash
# Submit task
./task_manager.sh submit "Create a React component for a counter"

# Check queue status
./task_manager.sh list

# Check specific task once you have the plan ID
./task_manager.sh check plan_a1b2c3d4
```

## 🏗️ Server Architecture

The Vibe Coding AI Agent is built on the MCP Standard Skeleton with:

- **Streamable HTTP Transport** on port 3050
- **Registry functionality** enabled by default
- **12 core coding tools**:
  - `accept_task`, `get_plan_status` (Task Management)
  - `analyze_code`, `explain_code` (Code Analysis)
  - `generate_code`, `write_file_content`, `read_file_content` (Code Generation)
  - `execute_code`, `run_tests` (Execution & Testing)
  - `store_memory`, `retrieve_memory` (Memory & Context)
  - `debug_error` (Debugging)
  - `health` (Monitoring)

## 🔧 Configuration

The server connects to LM Studio at `http://asus-tus:1234/v1` with the `qwen3-4b` model by default.

To customize, set environment variables:
```bash
export LM_STUDIO_URL="http://your-lm-studio:1234/v1"
export LM_STUDIO_MODEL="your-model-name"
./start_server.sh
```

## 📊 Task Management Features

- **Local task tracking** with JSON storage
- **Queue management** with pending/processing/completed states
- **Status monitoring** for individual tasks
- **Operation logging** for audit trail
- **Health monitoring** of server and LM Studio connection

## 🚀 Advanced Usage

### Submit with Registration to External Registry
```bash
./start_server.sh --register-with-registry --registry-host your-registry.com --registry-port 3031
```

### Custom Server Configuration
```bash
./start_server.sh --port 3060 --host 0.0.0.0 --enable-registry
```

## 🛡️ Security Features

- Path traversal prevention
- Input validation and sanitization
- Safe code execution with timeouts
- Confirmation required for file writes
- Secret leakage prevention

## 📄 Files Structure

```
├── start_server.sh                 # Main server startup script
├── task_manager.sh                 # Complete task management suite
├── task_queue_manager.sh           # Queue-focused manager
├── advanced_task_utility.sh        # Advanced features utility
├── task_utility.sh                 # Basic task submission
├── vibe_coding_agent/             # Server implementation
│   ├── mcp_server.py              # Main server with all tools
│   ├── lmstudio_client.py         # Hardened LM Studio client
│   ├── tools.py                   # All 12 coding agent tools
│   └── ...
├── AGENTS.md                      # Governance policies
├── catalog_entry.yaml             # Service catalog entry
├── README.md                      # This file
└── ...
```

The Vibe Coding AI Agent is ready for production use with full MCP compliance, security hardening, and comprehensive task management capabilities.