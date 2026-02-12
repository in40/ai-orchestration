# AI Coding Agent MCP Server - Technology Rules and Implementation Scenarios

## Overview
This document outlines the technology rules, architecture, and implementation scenarios for the AI Coding Agent MCP Server.

## Architecture

### Core Components
1. **MCP Server Base Class**: Inherits from the standard MCP server implementation
2. **AI Coding Agent Server**: Specialized server for handling coding tasks
3. **LM Studio Integration**: Connects to LM Studio endpoint for LLM processing
4. **Custom Handlers**: Specialized handlers for coding-related tools, resources, and prompts

### Technology Stack
- Python 3.9+
- FastAPI for HTTP transport
- SSE (Server-Sent Events) for bidirectional communication
- OpenAI library for LM Studio integration
- psutil for system monitoring
- Standard MCP protocol compliance

## Implementation Scenarios

### 1. Execute Coding Task
- **Tool Name**: `execute_coding_task`
- **Purpose**: Execute a coding task using the AI coding agent
- **Parameters**:
  - `task_description`: Detailed description of the coding task
  - `context`: Additional context or requirements
  - `file_path`: Path to file if modifying existing file

### 2. Generate Code Solution
- **Tool Name**: `generate_code_solution`
- **Purpose**: Generate a complete code solution based on requirements
- **Parameters**:
  - `requirements`: Requirements for the code to be generated
  - `language`: Programming language for the solution
  - `constraints`: Any constraints or limitations

### 3. Review Code
- **Tool Name**: `review_code`
- **Purpose**: Review code for quality, efficiency, and best practices
- **Parameters**:
  - `code`: Code to be reviewed
  - `review_criteria`: Specific criteria to focus on during review

### 4. Health Check
- **Tool Name**: `health_check`
- **Purpose**: Perform a health check on the AI coding agent service
- **Parameters**:
  - `detailed`: Whether to return detailed health information

## MCP Protocol Compliance

### Standard Endpoints Implemented
- `initialize`: Server initialization and capability negotiation
- `tools/list`: List available tools
- `tools/call`: Execute a specific tool
- `resources/list`: List available resources
- `resources/read`: Read content from a specific resource
- `prompts/list`: List available prompts
- `prompts/get`: Get a specific prompt with resolved arguments
- `shutdown`: Request server shutdown

### Custom Endpoints
- `execute_coding_task`: Custom tool for coding tasks
- `generate_code_solution`: Custom tool for code generation
- `review_code`: Custom tool for code review
- `health_check`: Custom tool for health checks

## LM Studio Integration

### Connection Details
- **Endpoint**: http://asus-tus:1234/v1
- **Model**: qwen3-4b
- **Authentication**: None required
- **Library**: OpenAI Python library with custom base URL

### Error Handling
- Connection timeouts are handled gracefully
- LLM unavailability is reported in health checks
- Fallback responses are provided when LLM is inaccessible

## Security Considerations
- No authentication required for this implementation
- Input validation is performed on all parameters
- Rate limiting is implemented via concurrent request limits

## Performance Monitoring
- Concurrent request limiting (default: 10)
- Health check endpoints for monitoring
- Detailed metrics available via `/metrics` endpoint

## Configuration Options
- Transport type: stdio or http
- Host and port configuration
- Concurrent request limits
- Registry functionality (optional)

## Deployment Notes
- Virtual environment recommended
- Dependencies managed via requirements.txt
- Startup scripts provided for easy deployment
- Logging configured for debugging and monitoring