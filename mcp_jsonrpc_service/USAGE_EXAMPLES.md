# Base MCP Server - Usage Examples

This document provides practical examples of how to use the Base MCP Server skeleton to create your own MCP-compliant servers.

## Table of Contents
1. [Basic Usage](#basic-usage)
2. [Extending the Server](#extending-the-server)
3. [Configuration Options](#configuration-options)
4. [Transport Methods](#transport-methods)
5. [Health Monitoring](#health-monitoring)
6. [Registry Integration](#registry-integration)

## Basic Usage

### Running the Server

#### With stdio transport (default)
```bash
python -m src.main
```

#### With HTTP transport
```bash
python -m src.main --transport http --port 8080
```

#### With custom configuration
```bash
# Using environment variables
export MCP_NAME="my-custom-server"
export MCP_TRANSPORT="http"
export MCP_PORT=9000

python -m src.main
```

## Extending the Server

To create a custom server based on this skeleton, extend the `BaseMCPServer` class or implement the `MCPServerExtension` interface:

### Example: Creating a Custom Extension

```python
from src.server import MCPServerExtension, BaseMCPServer
from src.errors import handle_rpc_error

class DataQueryExtension(MCPServerExtension):
    def get_name(self) -> str:
        return "data-query-extension"
    
    def get_description(self) -> str:
        return "Provides data querying capabilities"
    
    async def initialize(self, server: BaseMCPServer):
        # Enable the tools capability since we'll be providing tools
        server.set_capability("tools", True)
        
        # Add custom functionality to the server
        self._add_data_query_tools(server)
    
    def _add_data_query_tools(self, server: BaseMCPServer):
        # Add your custom tools to the server
        # This is a simplified example
        pass

# To use the extension, you would integrate it with your server implementation
```

### Example: Overriding Health Checks

```python
from src.server import BaseMCPServer
import asyncio

class CustomHealthServer(BaseMCPServer):
    async def _perform_health_check(self):
        # Perform custom health checks
        try:
            # Check database connectivity
            # Check external service availability
            # Check resource usage
            
            # Update status based on checks
            self.update_health_status("healthy")
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            self.update_health_status("unhealthy")
```

## Configuration Options

The server supports configuration through both command-line arguments and environment variables:

### Command-Line Arguments

| Argument | Description |
|----------|-------------|
| `--transport` | Transport method (`stdio` or `http`) |
| `--host` | Host for HTTP transport |
| `--port` | Port for HTTP transport |
| `--log-level` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `--registry-endpoint` | Registry endpoint to register with |
| `--disable-health-monitoring` | Disable automatic health monitoring |
| `--health-interval` | Health check interval in seconds |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | `stdio` | Transport method for the server |
| `MCP_HOST` | `0.0.0.0` | Host for HTTP transport |
| `MCP_PORT` | `8080` | Port for HTTP transport |
| `MCP_NAME` | `base-mcp-server` | Name of the server |
| `MCP_DESCRIPTION` | `Base MCP server skeleton` | Description of the server |
| `MCP_REGISTRY_ENDPOINT` | `stdio://` | Registry endpoint to register with |
| `MCP_HEALTH_CHECK_INTERVAL` | `60` | Health check interval in seconds |
| `MCP_ENABLE_HEALTH_MONITORING` | `True` | Enable automatic health monitoring |
| `MCP_LOG_LEVEL` | `INFO` | Logging level |
| `MCP_DATABASE_URL` | `sqlite:///./mcp_server.db` | Database connection string |
| `MCP_REDIS_URL` | `redis://localhost:6379` | Redis URL for caching |
| `MCP_JWT_SECRET` | `dev-secret-change-in-production` | Secret for JWT tokens |
| `MCP_CORS_ORIGINS` | `*` | Allowed CORS origins |
| `MCP_MAX_REGISTRATION_ATTEMPTS` | `3` | Max attempts for server registration |
| `MCP_REGISTRATION_TIMEOUT` | `30` | Timeout for registration in seconds |

## Transport Methods

The server supports multiple transport methods:

### Stdio Transport
```bash
python -m src.main --transport stdio
```

Stdio transport is the default and most common method for local MCP servers. It communicates with clients through standard input and output streams.

### HTTP Transport
```bash
python -m src.main --transport http --host 0.0.0.0 --port 8080
```

HTTP transport allows the server to communicate over HTTP. The server will expose a health check endpoint at `/health`.

## Health Monitoring

The server includes built-in health monitoring that can be customized:

### Enabling Health Monitoring
Health monitoring is enabled by default. To disable it:
```bash
python -m src.main --disable-health-monitoring
```

### Custom Health Check Interval
```bash
python -m src.main --health-interval 30
```

Or via environment variable:
```bash
export MCP_HEALTH_CHECK_INTERVAL=30
python -m src.main
```

## Registry Integration

The server automatically registers with the MCP registry:

### Default Registration
By default, the server registers with the registry at `stdio://`:
```bash
python -m src.main
```

### Custom Registry Endpoint
```bash
python -m src.main --registry-endpoint http://registry.example.com:8080
```

### Registration Information
The server registers with the following information:
- Name: Configured server name
- Description: Server description
- Endpoint: The server's own endpoint
- Capabilities: Boolean flags for resources, tools, prompts, roots, and sampling
- Metadata: Key-value pairs with additional information
- Tags: Categorization tags

### Health Status Reporting
When health monitoring is enabled and a registry endpoint is provided, the server automatically reports its health status to the registry at regular intervals.

## Error Handling

The server implements JSON-RPC 2.0 compliant error handling:

### Standard Error Codes
- `-32700`: Parse error
- `-32600`: Invalid Request
- `-32601`: Method not found
- `-32602`: Invalid params
- `-32603`: Internal error
- `-32099` to `-32000`: Server error range

### Using Error Handlers
For custom methods, use the provided decorators:
```python
from src.errors import handle_rpc_error

@handle_rpc_error
async def my_custom_method(params):
    # Your implementation
    pass
```

## Testing

Run the test suite to verify MCP protocol compliance:
```bash
pytest tests/
```

Or run specific tests:
```bash
pytest tests/test_base_mcp_server.py
```

## Development

To extend this server skeleton:

1. Create a new class that extends `BaseMCPServer` or implements `MCPServerExtension`
2. Add your custom functionality
3. Update capabilities as needed using `server.set_capability()`
4. Add any required configuration options
5. Write tests for your new functionality
6. Update documentation as needed