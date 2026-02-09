# Base MCP Server

This is a base skeleton for MCP (Model Context Protocol) servers that can be extended with specific functionality depending on the use case. The server follows the specifications outlined in the MCP Server Registry and is designed to seamlessly integrate with the registry system.

## Features

- Configurable transport methods (stdio, HTTP)
- MCP protocol compliance
- Registry registration capabilities
- Health monitoring
- Extensible architecture
- OpenRPC schema discovery via `rpc.discover` method
- Complete HTTP transport with GET/POST support for `/rpc` endpoint
- Enhanced stdio communication with registry

## Prerequisites

- Python 3.9 or higher
- MCP library (version 1.0.0 or higher)

## Installation

```bash
pip install -r requirements.txt
```

Or install directly from the pyproject.toml:

```bash
pip install .
```

## Usage

### Running with stdio transport (default)

```bash
python -m src.main
```

### Running with HTTP transport

```bash
python -m src.main --transport http --port 8080
```

### With custom configuration

```bash
# Set environment variables
export LOG_LEVEL=DEBUG

python -m src.main --transport http --host 0.0.0.0 --port 8080 --log-level DEBUG
```

## Configuration

The server can be configured via command-line arguments or environment variables:

- `--transport`: Transport method (`stdio` or `http`) [default: stdio]
- `--host`: Host for HTTP transport [default: 0.0.0.0]
- `--port`: Port for HTTP transport [default: 8080]
- `--log-level`: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) [default: INFO]

## Developing a New MCP Server

To develop a new MCP server based on this skeleton, follow these steps:

### 1. Set Up the Development Environment
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .  # Install in development mode
```

### 2. Create Your Server Class
Extend the `BaseMCPServer` or implement the `MCPServerExtension` interface:

```python
# Example: Creating a custom server
from src.server import BaseMCPServer

class MyCustomMCPServer(BaseMCPServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set your server's identity
        self.name = "my-custom-server"
        self.description = "Description of my custom server"
        
        # Enable required capabilities
        self.set_capability("tools", True)      # If your server provides tools
        self.set_capability("resources", True)  # If your server provides resources
        self.set_capability("prompts", False)   # If your server doesn't provide prompts
        
        # Add tags for categorization
        self.add_tag("custom")
        self.add_tag("data-processing")
        
        # Add custom metadata
        self.set_metadata("version", "1.0.0")
        self.set_metadata("author", "Your Name")
        
        # Initialize your custom functionality
        self.setup_custom_functionality()
    
    def setup_custom_functionality(self):
        # Add your server-specific functionality here
        pass
    
    async def _perform_health_check(self):
        # Override to add custom health checks
        try:
            # Check your specific dependencies
            # database connectivity, external services, etc.
            self.update_health_status("healthy")
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            self.update_health_status("unhealthy")
```

### 3. Alternative: Create Server Extensions
If you prefer to use the extension pattern:

```python
from src.server import MCPServerExtension, BaseMCPServer

class MyCustomExtension(MCPServerExtension):
    def get_name(self) -> str:
        return "my-custom-extension"
    
    def get_description(self) -> str:
        return "Description of my custom extension"
    
    async def initialize(self, server: BaseMCPServer):
        # Enable capabilities
        server.set_capability("tools", True)
        server.set_capability("resources", True)
        
        # Add tags and metadata
        server.add_tag("custom-extension")
        server.set_metadata("extension-version", "1.0.0")
        
        # Add your custom functionality to the server
        self._add_custom_tools(server)
        self._add_custom_resources(server)
    
    def _add_custom_tools(self, server):
        # Add your custom tools to the server
        pass
    
    def _add_custom_resources(self, server):
        # Add your custom resources to the server
        pass
```

### 4. Update the Main Entry Point (if using custom server class)
Modify `src/main.py` to use your custom server:

```python
# Option 1: If using custom server class
from .my_custom_server import MyCustomMCPServer

async def main():
    # ... existing config loading ...
    
    # Initialize your custom server instead of BaseMCPServer
    server = MyCustomMCPServer(
        transport=config.transport,
        host=config.host,
        port=config.port
    )
    # ... rest of the code remains the same
```

### 5. Configure Your Server
Use environment variables or command-line arguments:

```bash
# Environment variables
export MCP_NAME="my-custom-server"
export MCP_DESCRIPTION="My awesome custom server"
export MCP_TRANSPORT="stdio"  # or "http"
export MCP_PORT=8080
export MCP_REGISTRY_ENDPOINT="stdio://"  # or "http://registry:8080"

# Or use command-line arguments
python -m src.main --transport http --port 9000 --registry-endpoint http://registry:8080
```

### 6. Implement Your Core Functionality
- Add your tools, resources, or prompts as needed
- Implement the business logic for your specific use case
- Ensure proper error handling using the provided error classes
- Add proper logging throughout your implementation

### 7. Add Custom Health Checks
Override the `_perform_health_check` method to check your specific dependencies:

```python
async def _perform_health_check(self):
    # Check database connectivity
    # Check external API availability
    # Check resource availability
    # Update health status accordingly
    pass
```

### 8. Write Tests for Your Implementation
Create tests in the `tests/` directory:

```python
# tests/test_my_custom_server.py
import pytest
from src.my_custom_server import MyCustomMCPServer

@pytest.mark.asyncio
async def test_my_custom_server_initialization():
    server = MyCustomMCPServer(transport="stdio")
    assert server.name == "my-custom-server"
    assert server.capabilities["tools"] is True

@pytest.mark.asyncio
async def test_my_custom_functionality():
    # Test your custom functionality
    pass
```

### 9. Run and Test Your Server
```bash
# Run with stdio transport (recommended for local development)
python -m src.main

# Run with HTTP transport
python -m src.main --transport http --port 8080

# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

### Key Points to Remember:
- Always extend from `BaseMCPServer` or implement `MCPServerExtension`
- Use the provided configuration system (`src/config.py`)
- Implement proper error handling with the provided error classes
- Ensure your server can register with the registry
- Implement health checks appropriate for your server's dependencies
- Follow the JSON-RPC 2.0 protocol standards
- Use async/await consistently throughout your implementation
- Follow the security best practices outlined in the developer documentation

### New Functionality Added for Compliance:

#### OpenRPC Schema Discovery
The server now implements the `rpc.discover` method as required by the OpenRPC specification. This method returns the complete OpenRPC schema describing the server's capabilities:

```python
# Example of calling the discover method
result = await server.handle_discover_method()
print(result['openrpc'])  # Should output "1.3.2"
```

#### HTTP Transport Enhancement
The HTTP transport now fully supports both GET and POST methods for the `/rpc` endpoint:
- GET `/rpc`: Returns server information and capabilities
- POST `/rpc`: Accepts JSON-RPC 2.0 requests for MCP protocol communication

#### Improved Registry Communication
The registry client now has enhanced stdio communication capabilities, allowing for proper communication with the registry server via stdio transport.

## Architecture

The base server follows the MCP protocol specification and includes:

- A base server class (`BaseMCPServer`) that handles core functionality
- Support for different transport methods
- Capability definitions matching the registry requirements
- Health monitoring and status reporting
- Configuration system supporting environment variables and command-line options
- Error handling following JSON-RPC 2.0 standards

## Integration with Registry

The server is designed to register with the MCP Server Registry and includes methods for:

- Registering the server with the registry
- Updating health status
- Providing required server information (capabilities, metadata, tags)

## Testing

Run the test suite to verify MCP protocol compliance:
```bash
pytest tests/
```

Or run specific tests:
```bash
pytest tests/test_base_mcp_server.py
```

## Usage Examples

See [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) for detailed examples of how to use and extend the base server.

## License

This project is licensed under the MIT License.