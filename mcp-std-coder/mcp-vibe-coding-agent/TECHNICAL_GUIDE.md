# Technical Guide: Vibe Coding MCP Server

## Project Overview
This project implements a production-ready Model Context Protocol (MCP) server for a vibe coding AI agent. The server exposes an MCP tool that accepts natural language coding tasks, sends them to a local LLM (LM Studio), and returns generated code.

## Architecture

### Components
- **Server**: Main MCP server implementation using FastAPI and Streamable HTTP transport
- **Configuration**: Pydantic-based settings in `config.py`
- **Vibe Coder**: Core functionality in `dependencies/vibe_coder.py` that integrates with LM Studio
- **Transport**: Streamable HTTP transport with health check endpoint

### File Structure
```
mcp-vibe-coding-agent/
├── config.py                 # Server configuration
├── dependencies/
│   └── vibe_coder.py       # Core vibe coding functionality
├── mcp_std_server/
│   ├── server.py           # Main server implementation
│   ├── handlers/
│   │   └── server_handlers.py
│   ├── transports/
│   │   └── streamable_http.py  # With health check endpoint
│   └── utils/
├── tests/
│   ├── simulate_agent.py   # AI agent simulation tests
│   └── run_simulation.sh
├── requirements.txt
└── start_mcp_server.sh     # Startup script
```

## MCP Tool Design Patterns

### Vibe Code Tool
- **Name**: `vibe_code`
- **Arguments**:
  - `task_description` (required): Natural language description of the code to generate
  - `language` (optional): Programming language (default: "python")
  - `vibe_level` (optional): Creativity level 1-10 (default: 5)
  - `style_guide` (optional): Additional style hints

### Tool Registration
The vibe coding tool is registered dynamically using the `register_vibe_coding_tool()` function which extends the server's existing tool handling capabilities.

## Environment Setup

### Prerequisites
- Python 3.9+
- LM Studio running with a compatible model (e.g., qwen3-4b)

### Installation
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install openai pydantic-settings
```

### Configuration
Update `config.py` with your LM Studio settings:
```python
llm_base_url: str = "http://your-lm-studio-host:1234/v1"
llm_model: str = "your-model-name"
```

## Adding New Tools

To add a new tool:
1. Create a new module in `dependencies/`
2. Implement the tool function with proper schema
3. Register it in the server initialization

## Changing LLM Provider

To switch to a different LLM provider:
1. Update the `llm_base_url` and `llm_model` in `config.py`
2. Ensure the provider supports the OpenAI-compatible API
3. Adjust the system prompt in `call_llm()` if needed

## Vibe Coding Best Practices

### Temperature Mapping
- Vibe level 1 → Temperature 0.1 (more deterministic)
- Vibe level 10 → Temperature 1.0 (more creative/random)

### System Prompt Engineering
The system prompt sets the assistant's persona as a "vibe coding assistant" that generates clean, working code with brief explanations.

## Health Check Implementation

The server includes a `/health` endpoint that:
- Checks if the server is running
- Verifies connectivity to the LLM (LM Studio)
- Returns appropriate status codes

## Testing Methodology

### Simulation Tests
The `tests/simulate_agent.py` script:
- Lists available tools
- Calls the vibe_code tool with sample parameters
- Validates responses

### Manual Testing
Use the startup script to run the server and test with the simulation script:
```bash
./start_mcp_server.sh
# In another terminal:
python tests/simulate_agent.py
```

## Production Deployment

### Port Configuration
The server runs on port 3050 by default. This can be changed in `config.py`.

### Registry Integration
Registry functionality is disabled by default for local deployment. Enable it by setting `registry_url` in `config.py`.

### Security Considerations
- The server validates origin headers to prevent DNS rebinding attacks
- Session IDs are used for connection tracking
- Input validation occurs through JSON Schema definitions

## Troubleshooting

### Common Issues
- **Connection refused**: Ensure the server is running and listening on the correct port
- **LLM unreachable**: Verify LM Studio is running and accessible at the configured URL
- **Tool not found**: Check that the vibe_code tool is properly registered

### Debugging
Enable debug logging by modifying the server startup parameters or checking the console output for error messages.