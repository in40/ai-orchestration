# AI Coding Agent MCP Server

MCP server that provides AI coding assistance using a local LLM (LM Studio). Accepts coding tasks, manages their lifecycle asynchronously via a task queue, and returns generated code or explanations. Supports concurrent processing of multiple tasks with a configurable number of worker coroutines.

## Features

- **Asynchronous Task Processing**: Submit coding tasks and receive a task ID immediately while processing happens in the background
- **Configurable Concurrency**: Adjust the number of parallel task processors via environment variable
- **LM Studio Integration**: Connects to local LM Studio instance for code generation
- **Prompt Template System**: Flexible prompt templates for different coding scenarios
- **Task Management**: Create, monitor, list, and cancel coding tasks
- **Registry Integration**: Optionally register with MCP registry for service discovery

## Architecture

The server implements an asynchronous task queue architecture:

1. **Task Submission**: Clients submit coding tasks via `submit_coding_task` tool
2. **Queue Management**: Tasks are queued for asynchronous processing
3. **Worker Pool**: Configurable number of concurrent workers process tasks from the queue
4. **LM Studio Integration**: Workers call LM Studio API to generate code/explanations
5. **Result Storage**: Completed tasks are stored with their results
6. **Task Status**: Clients can poll for task status and retrieve results

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd ai-coding-agent-mcp

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Create a `.env` file based on `.env.example`:

```bash
LMSTUDIO_HOST=asus-tus
LMSTUDIO_PORT=1234
CONCURRENT_WORKERS=2
DEBUG=false
```

- `LMSTUDIO_HOST`: Host of your LM Studio instance
- `LMSTUDIO_PORT`: Port of your LM Studio instance  
- `CONCURRENT_WORKERS`: Number of parallel task processors (default: 2)
- `DEBUG`: Enable debug logging (default: false)

## Usage

### Start the Server

```bash
# Using the startup script
./start_ai_coding_agent.sh

# Or directly with Python
python -m mcp_server.server --transport http --port 3050
```

### Stop the Server

```bash
./stop_ai_coding_agent.sh
```

## MCP Tools

The server provides the following MCP tools:

### `lmstudio_health`
Check connectivity to LM Studio and return model list.

Input:
```json
{}
```

Output:
```json
{
  "status": "ok",
  "models": ["qwen3-4b", ...],
  "reachable": true
}
```

### `submit_coding_task`
Submit a coding task; enqueues for asynchronous processing. Returns task ID.

Input:
```json
{
  "task": "string",
  "language": "string?",
  "max_tokens": "integer?"
}
```

Output:
```json
{
  "task_id": "uuid-string"
}
```

### `get_task_status`
Retrieve current status and result (if completed) of a task.

Input:
```json
{
  "task_id": "string"
}
```

Output:
```json
{
  "id": "string",
  "status": "pending|processing|completed|failed|cancelled",
  "task_description": "string",
  "parameters": "object",
  "result": "string?",
  "error": "string?",
  "created_at": "float",
  "updated_at": "float"
}
```

### `list_tasks`
List all tasks, optionally filtered by status.

Input:
```json
{
  "status": "string?"
}
```

Output:
```json
[
  {
    "id": "string",
    "status": "string",
    "created_at": "float",
    "updated_at": "float"
  }
]
```

### `cancel_task`
Cancel a pending task.

Input:
```json
{
  "task_id": "string"
}
```

Output:
```json
{
  "success": true
}
```

### `render_prompt`
Render a prompt template with given variables.

Input:
```json
{
  "template_name": "string",
  "variables": "object"
}
```

Output:
```json
{
  "rendered_prompt": "string"
}
```

## MCP Resources

The server provides the following MCP resources:

### `prompts/list`
List all available prompt templates in the `./prompts/` directory.

### `prompts/get`
Get the content of a specific prompt template using URI format: `file://prompts/{name}.txt`

## Adjusting Concurrency

The number of concurrent workers can be adjusted by setting the `CONCURRENT_WORKERS` environment variable:

```bash
# Start with 4 concurrent workers
CONCURRENT_WORKERS=4 ./start_ai_coding_agent.sh
```

More workers allow for more simultaneous task processing but consume more system resources.

## Registry Integration

The server can register with an MCP registry for service discovery:

```bash
# Start and register with registry
python -m mcp_server.server --transport http --port 3050 --register-with-registry --registry-host 127.0.0.1 --registry-port 3031
```

## Health Checks

The server provides health check information through the `ping` method, which includes LM Studio connectivity status, queue information, and worker pool status.

## Development

To run the server in development mode:

```bash
# Activate virtual environment
source venv/bin/activate

# Run with debug output
DEBUG=true python -m mcp_server.server --transport http --port 3050
```

## Testing

See the test scripts in the root directory for examples of how to interact with the server programmatically.