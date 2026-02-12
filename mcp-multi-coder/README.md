# Vibe Coding AI Agent - MCP Server

A production-ready, secure, and observable AI Coding Agent MCP server that connects to LM Studio for autonomous coding tasks.

## Features

- **MCP 2025 Compliant**: Full compliance with MCP protocol specification using Streamable HTTP transport
- **LM Studio Integration**: Connects to LM Studio (qwen3-4b model) for AI-powered coding
- **12 Core Tools**: Complete set of coding agent tools for planning, generation, analysis, and execution
- **Security Hardened**: Path traversal prevention, input validation, and safe execution
- **Observable**: Structured logging, OpenTelemetry integration, and health monitoring
- **Governance Compliant**: AGENTS.md governance with security policies and tool-use policies

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   AI Agent      │◄──►│   MCP Server    │◄──►│   LM Studio     │
│   (Client)      │    │   (Streamable   │    │   (Backend)     │
│                 │    │   HTTP 3050)    │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                       ┌──────────────────┐
                       │   Tools Layer    │
                       │  (Planning, Gen, │
                       │   Analysis, etc) │
                       └──────────────────┘
```

## Prerequisites

- Python 3.8+
- LM Studio running at `http://asus-tus:1234/v1` with `qwen3-4b` model
- Linux/macOS environment

## Quick Start

1. **Setup Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start Server**:
   ```bash
   chmod +x start_server.sh
   ./start_server.sh
   ```

4. **Server will be available at**: `http://localhost:3050/mcp`

## Core Tools

### Task Management
- `accept_task`: Accept and plan development tasks
- `get_plan_status`: Check status of ongoing plans

### Code Analysis
- `analyze_code`: Find bugs, optimizations, refactoring opportunities
- `explain_code`: Detailed code explanations

### Code Generation
- `generate_code`: Generate code from specifications
- `write_file_content`: Secure file writing with validation
- `read_file_content`: Safe file reading with range support

### Execution & Testing
- `execute_code`: Sandboxed code execution
- `run_tests`: Test execution and reporting

### Memory & Context
- `store_memory`: Persistent memory storage
- `retrieve_memory`: Semantic memory retrieval

### Debugging
- `debug_error`: Error analysis and fix suggestions

### Health & Monitoring
- `health`: Server and LM Studio connectivity check

## Configuration

### Environment Variables
- `LM_STUDIO_URL`: LM Studio API endpoint (default: `http://asus-tus:1234/v1`)
- `LM_STUDIO_MODEL`: Model name (default: `qwen3-4b`)
- `MCP_PORT`: Server port (default: `3050`)
- `OTEL_ENABLED`: Enable OpenTelemetry (default: `false`)

### Security Settings
- `CIRCUIT_BREAKER_THRESHOLD`: Failure threshold (default: `5`)
- `CIRCUIT_BREAKER_TIMEOUT`: Recovery timeout in seconds (default: `60`)

## Testing

Run simulation tests to verify functionality:

```bash
# Test task planning
./simulate_task_planning.sh

# Test code generation and execution
./simulate_code_gen_and_exec.sh

# Test memory operations
./simulate_memory_retrieval.sh

# Test health monitoring
./simulate_health_check.sh

# Validate catalog entry
python validate_catalog.py
```

## Governance & Security

### AGENTS.md Compliance
The server follows the AGENTS.md standard for AI agent governance with:
- Security-first approach
- Token efficiency optimization
- Input validation and sanitization
- Safe execution practices

### Security Features
- Path traversal prevention
- Input size limits (100k characters)
- Sandboxed code execution
- Confirmation for destructive operations
- Secret leakage prevention

## Production Deployment

### Recommended Setup
- Use PostgreSQL for registry storage
- Configure proper logging and monitoring
- Set up reverse proxy for SSL termination
- Implement rate limiting at infrastructure level

### Monitoring
- Health check endpoint: `/mcp` with `health` tool
- Structured logs in `./logs/server.log`
- OpenTelemetry metrics when enabled

## Project Structure

```
├── vibe_coding_agent/          # Main server implementation
│   ├── mcp_server.py          # MCP server with all tools
│   ├── lmstudio_client.py     # Hardened LM Studio client
│   ├── tools.py               # All 12 coding agent tools
│   └── __init__.py
├── start_server.sh            # Startup script
├── simulate_*.sh              # Test simulation scripts
├── AGENTS.md                  # Governance policies
├── .cursorrules               # Editor rules
├── catalog_entry.yaml         # Service catalog entry
├── validate_catalog.py        # Catalog validation
├── INVESTIGATION.md           # Research documentation
├── TECH_RULES_COPY.md         # Technical decisions
├── TEST_REPORT.md             # Test results
├── requirements.txt           # Dependencies
└── .env.example              # Environment configuration
```

## License

This project follows the governance policies outlined in AGENTS.md and is intended for use in accordance with MCP protocol standards.