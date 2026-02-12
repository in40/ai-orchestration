# Investigation Report: Vibe Coding AI Agent MCP Server

## MCP Protocol Standards

### Streamable HTTP Transport
- **Status**: Confirmed as the modern standard for remote MCP server communication
- **Specification**: Replaced the deprecated HTTP+SSE transport from protocol version 2024-11-05 (as of specification version 2025-03-26)
- **Advantages**: Operates over a single `/mcp` endpoint supporting both POST (client-to-server) and GET (server-to-client) methods
- **Port**: Will use port 3050 as specified in requirements

### MCP Transport Mechanisms
- **STDIO**: Traditional transport, forbidden for this implementation
- **Streamable HTTP**: Modern standard, required for this implementation
- **HTTP+SSE**: Legacy transport, deprecated

## Agentic Coding Rulebook 2025

### AGENTS.md Standard
- **Purpose**: Neutral standard for AI coding agents, gaining traction by July 2025
- **Function**: Enables interoperable, auditable, and secure AI agents
- **Format**: Simple and open format designed to assist AI coding agents
- **Adoption**: Supported by tools like Codex, OpenCode, Gemini CLI, Jules, and Factory AI

### Core Principles
- Simplicity First
- Readability Priority
- Dependency Minimalism
- Security First
- Test-Driven Thinking
- Token Efficiency

## LM Studio API Compatibility

### OpenAI Compatible Endpoints
- **Endpoint**: `http://asus-tus:1234/v1/chat/completions` (as specified in requirements)
- **Model**: `qwen3-4b` (no authentication required)
- **Compatibility**: LM Studio exposes OpenAI-compatible API, allowing use of OpenAI SDK
- **Method**: POST requests to `/v1/chat/completions` endpoint

## MCP Standard Skeleton Analysis

### Repository Location
- **Source**: `https://github.com/in40/ai-orchestration/tree/main/mcp-std-skeleton`
- **Features**: Full MCP specification compliance with support for stdio, Streamable HTTP, and legacy HTTP/SSE transports

### Architecture
- **Transports**: Three mechanisms supported (stdio, streamable-http, http-sse)
- **Core Components**: JSON-RPC handler, server handlers, client handlers, notification manager
- **Standard Methods**: `initialize`, `tools/list`, `tools/call`, `resources/list`, `resources/read`, `prompts/list`, `prompts/get`, `shutdown`, `ping`
- **Registry Functionality**: Optional service discovery with SQLite/PostgreSQL backends

### Key Files Identified
- `mcp_std_server/server.py`: Main server implementation
- `mcp_std_server/handlers/server_handlers.py`: Standard server method handlers
- `mcp_std_server/transports/streamable_http.py`: Streamable HTTP transport implementation
- `requirements.txt`: Dependencies
- `README.md`: Documentation and usage instructions

## Implementation Requirements Summary

### Mandatory Features
1. **Transport**: Streamable HTTP only (port 3050)
2. **Forbidden**: STDIO transport
3. **LM Studio Integration**: Connect to `http://asus-tus:1234/v1/chat/completions`, model `qwen3-4b`
4. **Tools**: At least 12 coding agent tools as specified
5. **Governance**: AGENTS.md file with security guardrails
6. **Observability**: Health checks, structured logging, OpenTelemetry support

### Security Considerations
- Path traversal prevention
- Input size limits (reject prompts > 100k chars)
- Safe subprocess execution
- No secrets in code (use .env files)
- Human confirmation for destructive operations

### Testing Requirements
- Simulation scripts for task planning, code generation, memory retrieval, health checks
- Zero warnings/errors in server logs
- Successful registry registration