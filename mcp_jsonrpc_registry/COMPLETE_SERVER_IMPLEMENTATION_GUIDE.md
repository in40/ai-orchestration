# Complete Guide: Building MCP Servers to Connect to the Registry

## Overview
This guide provides comprehensive instructions for building MCP (Model Context Protocol) servers that can successfully register with and communicate with the MCP Server Registry.

## Prerequisites

### 1. Required Dependencies
- Python 3.13 or higher
- MCP library (version ≥1.0.0)
- Required packages:
  ```bash
  pip install mcp
  pip install psycopg2-binary  # For registry database connectivity
  ```

### 2. Registry Connection Requirements
- Access to the registry server (typically running on port 6000)
- Proper network connectivity to the registry endpoint
- Understanding of session management requirements

## Server Implementation Guide

### 1. Basic Server Structure

```python
from mcp.server import FastMCP
import asyncio
import logging

class MyMCPServer:
    def __init__(self, server_name: str):
        # Initialize your MCP server with the FastMCP framework
        self.mcp = FastMCP(server_name, streamable_http_path="/mcp")
        self.server_name = server_name
        self.server_id = None  # Will be set after successful registration
        
        # Add your tools, resources, etc.
        self._register_methods()
    
    def _register_methods(self):
        """Register your server's tools and resources."""
        @self.mcp.tool(
            name="my-tool",
            description="Description of your tool"
        )
        def my_tool(param: str) -> dict:
            return {"result": f"Processed {param}"}
    
    def run(self, transport="stdio", **kwargs):
        """Run your server with the specified transport."""
        if transport == "streamable-http":
            # For HTTP transport
            asyncio.run(self.mcp.run_streamable_http_async(**kwargs))
        else:
            # For stdio or other transports
            asyncio.run(self.mcp.run(transport=transport))
```

### 2. Registration Process Implementation

To register with the registry, your server needs to:

1. **Establish a connection to the registry using the proper MCP client**
2. **Create a ClientSession with the connection streams**
3. **Initialize the session to establish proper session context**
4. **Prepare registration parameters with accurate capabilities**
5. **Call the `registry-register_server` method**
6. **Handle the registration response**

```python
import asyncio

async def register_with_registry(self, registry_url: str = "http://localhost:6000/mcp"):
    """Register this server with the registry."""
    try:
        # Connect to the registry using the proper MCP transport
        # For HTTP transport, use streamable_http_client
        from mcp.client.streamable_http import streamable_http_client
        import mcp
        
        # Establish connection to the registry
        async with streamable_http_client(url=registry_url) as (receive_stream, send_stream, get_session_id_callback):
            print("✅ Connected to registry with proper streams")
            
            # Create a ClientSession with the streams
            client_session = mcp.ClientSession(
                read_stream=receive_stream,
                write_stream=send_stream
            )
            
            # Initialize the session (CRITICAL: This establishes proper session context)
            # Without this step, the registry will return "Bad Request: Missing session ID"
            init_result = await client_session.initialize()
            print(f"✅ Session initialized: {init_result}")
            
            # Prepare registration data with accurate information
            registration_data = {
                "name": "my-server-name",
                "description": "Description of my server",
                "endpoint": "http://localhost:8080",  # Your server's endpoint
                "capabilities": {
                    "resources": False,  # Set to True only if your server supports resources
                    "tools": True,       # Set to True only if your server supports tools
                    "prompts": False,    # Set to True only if your server supports prompts
                    "roots": False,      # Set to True only if your server supports roots
                    "sampling": False    # Set to True only if your server supports sampling
                },
                "metadata": {
                    "version": "1.0.0",
                    "author": "Your Name",
                    "category": "service-type"
                },
                "tags": ["custom", "tool-server", "category"]
            }
            
            # Register with the registry
            result = await client_session.call_tool_async(
                "registry-register_server", 
                registration_data
            )
            
            if isinstance(result, dict) and result.get("success"):
                self.server_id = result.get("server_id")
                print(f"✅ Successfully registered with ID: {self.server_id}")
                return self.server_id
            else:
                print(f"❌ Registration failed: {result.get('message', 'Unknown error')}")
                return None
                
    except Exception as e:
        print(f"❌ Error during registration: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
```

### 3. Health Check Endpoint Implementation

Your server must implement a health check endpoint that the registry will call:

```python
from fastapi import FastAPI
import uvicorn
from datetime import datetime

# If using HTTP transport, implement a health endpoint
app = FastAPI()

@app.get("/health")
async def health_check():
    """Health check endpoint for the registry to verify server status."""
    # Perform any necessary health checks
    # Return 200 if healthy, appropriate error code if not
    return {
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat(),
        "details": {
            "uptime": "active",
            "version": "1.0.0"
        }
    }
```

### 4. Complete Example Server Implementation

```python
from mcp.server import FastMCP
from mcp.client.streamable_http import streamable_http_client
import mcp
import asyncio
import logging
from datetime import datetime

class CompleteMCPServer:
    def __init__(self, server_name: str, server_port: int = 8080):
        self.mcp = FastMCP(server_name, streamable_http_path="/mcp")
        self.server_name = server_name
        self.server_port = server_port
        self.server_id = None
        self.registry_url = f"http://localhost:{server_port}/mcp"
        
        # Register methods
        self._register_methods()
    
    def _register_methods(self):
        """Register server tools."""
        @self.mcp.tool(
            name="example-tool",
            description="An example tool for demonstration"
        )
        def example_tool(input_param: str) -> dict:
            return {
                "result": f"Processed input: {input_param}",
                "processed_at": datetime.utcnow().isoformat()
            }
    
    async def register_with_registry(self):
        """Register the server with the registry."""
        try:
            async with streamable_http_client(url=self.registry_url) as (receive_stream, send_stream, get_session_id_callback):
                client_session = mcp.ClientSession(
                    read_stream=receive_stream,
                    write_stream=send_stream
                )
                
                # Initialize session
                await client_session.initialize()
                
                # Prepare registration data
                registration_data = {
                    "name": self.server_name,
                    "description": f"MCP Server: {self.server_name}",
                    "endpoint": f"http://localhost:{self.server_port}",
                    "capabilities": {
                        "resources": False,
                        "tools": True,
                        "prompts": False,
                        "roots": False,
                        "sampling": False
                    },
                    "metadata": {
                        "version": "1.0.0",
                        "author": "Server Developer",
                        "startup_time": datetime.utcnow().isoformat()
                    },
                    "tags": ["mcp-server", "example", "demo"]
                }
                
                # Register with registry
                result = await client_session.call_tool(
                    "registry-register_server",
                    registration_data
                )
                
                if isinstance(result, dict) and result.get("success"):
                    self.server_id = result.get("server_id")
                    print(f"✅ Server registered successfully with ID: {self.server_id}")
                    return True
                else:
                    print(f"❌ Registration failed: {result}")
                    return False
                    
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return False
    
    def run(self):
        """Run the server."""
        # First register with registry
        registration_success = asyncio.run(self.register_with_registry())
        
        if registration_success:
            print(f"Server {self.server_name} running and registered with ID: {self.server_id}")
            # Run the server
            asyncio.run(self.mcp.run_streamable_http_async(host="0.0.0.0", port=self.server_port))
        else:
            print("Failed to register with registry, exiting...")
            return

# Usage
if __name__ == "__main__":
    server = CompleteMCPServer("my-example-server", 8080)
    server.run()
```

## Session Management Requirements

### 1. Session Establishment Process
- Sessions are automatically established when connecting via supported transports
- For HTTP transport, ensure your client sends proper headers and maintains connection state
- Session context must be preserved throughout the lifetime of the connection
- When using the `mcp` library, sessions are managed automatically by the framework

### 2. Session Validation
- Registration and update operations require valid session contexts
- Session timeouts are configurable (default: 1 hour)
- Invalid or expired sessions will result in authentication errors with code -32600

## Transport Configuration

### HTTP Transport Requirements
When using HTTP transport (streamable-http), clients must include an Accept header that specifies both required content types:

```
Accept: application/json, text/event-stream
```

This is required because the MCP protocol supports both regular JSON-RPC responses and streaming responses via server-sent events (SSE).

## Error Handling and Recovery

### 1. Registration Failures
- Implement proper error handling for registration failures
- Retry registration with exponential backoff if initial registration fails
- Handle session expiration by re-establishing connections when needed
- Log registration and health check failures for debugging purposes

### 2. Common Error Responses
- Error code -32600: "Bad Request: Missing session ID" - Indicates session context is required
- Network errors: Handle connection timeouts and retries appropriately
- Validation errors: Ensure all registration parameters are valid

## Configuration Requirements

Your server should support configurable settings:
- Transport method selection (stdio, streamable-http)
- Health check intervals
- Logging levels
- Connection timeouts

## Testing and Validation

### 1. Registration Test
```python
async def test_registration():
    """Test server registration with the registry."""
    server = CompleteMCPServer("test-server", 9000)
    success = await server.register_with_registry()
    assert success, "Registration should succeed"
    assert server.server_id is not None, "Server should have an ID after registration"
    print("✅ Registration test passed")
```

### 2. Health Check Test
```python
import requests

def test_health_check():
    """Test the health check endpoint."""
    response = requests.get("http://localhost:9000/health")
    assert response.status_code == 200, "Health check should return 200"
    data = response.json()
    assert data["status"] == "healthy", "Status should be healthy"
    print("✅ Health check test passed")
```

## Security Considerations

- Support secure transport (HTTPS/WSS) for production deployments
- Validate incoming requests from the registry server
- Protect against injection attacks in all inputs
- Implement proper authentication if required by your deployment

## Deployment Considerations

### Production Deployment
- Use HTTPS for secure communication
- Implement proper logging and monitoring
- Configure appropriate timeouts and retry mechanisms
- Set up health check endpoints properly

### Scaling Considerations
- Design for multiple concurrent connections if needed
- Implement connection pooling if needed
- Consider load balancing for high-traffic scenarios

## Troubleshooting

### Common Issues
1. **"Missing session ID" errors**: Ensure proper session establishment using the MCP client library
2. **Connection timeouts**: Verify network connectivity and firewall settings
3. **Registration failures**: Check that all required fields are provided and capabilities are accurate
4. **Health check failures**: Ensure the /health endpoint is accessible and returns proper status

### Debugging Tips
- Enable debug logging to see detailed communication
- Verify that the registry server is accessible at the configured endpoint
- Check that session context is properly established before making RPC calls
- Validate that all registration parameters match the expected schema

This guide provides a complete reference for building MCP servers that can successfully connect to and register with the MCP Server Registry.