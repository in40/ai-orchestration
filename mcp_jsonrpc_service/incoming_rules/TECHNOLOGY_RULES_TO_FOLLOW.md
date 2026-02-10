# Technology and Stack Rules for MCP Server Developers

Based on analysis of the MCP Server Registry, here are the technology and stack requirements that developers must follow when creating MCP servers for seamless integration with the registry:

## 1. MCP Protocol Compliance

- **Mandatory**: Your server must implement the Model Context Protocol (MCP) specification
- Support the three core MCP primitives: tools, resources, and prompts
- Implement proper JSON-RPC 2.0 communication protocol
- Follow the OpenRPC specification pattern for API contracts

## 2. Required Capabilities Structure

Your server must define its capabilities using this exact structure:

```python
{
  "resources": boolean,    # Whether the server supports resources
  "tools": boolean,        # Whether the server supports tools
  "prompts": boolean,      # Whether the server supports prompts
  "roots": boolean,        # Whether the server supports roots
  "sampling": boolean      # Whether the server supports sampling
}
```

## 3. Registration Requirements

Your server must be able to register with the registry using the `registry-register_server` method with this payload structure:

```python
{
  "name": string,                    # Required: Display name of the server
  "description": string,             # Optional: Description of the server
  "endpoint": string,                # Required: Endpoint URL or transport method
  "capabilities": object,            # Required: Capabilities object (see above)
  "metadata": object,                # Optional: Additional metadata (key-value pairs)
  "tags": array[string]              # Optional: Tags for categorization
}
```

## 4. Supported Transport Methods

Your server must support at least one of these transport methods:
- `stdio` - Standard input/output for local communication
- `streamable-http` - HTTP-based transport
- Any other transport compatible with the MCP specification

## 4.1 HTTP Transport Accept Header Requirements

When using HTTP transport (streamable-http), clients must include an Accept header that specifies both required content types:

```
Accept: application/json, text/event-stream
```

This is required because the MCP protocol supports both regular JSON-RPC responses and streaming responses via server-sent events (SSE). Failure to include both content types in the Accept header will result in a 406 Not Acceptable response.

## 5. Technology Stack Requirements

### Python-Based Implementation (Recommended)
- **Python Version**: 3.13 or higher
- **MCP Library**: Use the official `mcp` library (version 1.0.0 or higher)
- **Web Framework**: Compatible with FastAPI-style routing if using HTTP transport
- **Async Support**: Implement asynchronous operations for optimal performance

### Alternative Language Implementation
If implementing in another language:
- Must provide equivalent MCP protocol implementation
- Must support JSON serialization/deserialization matching the registry's expectations
- Must handle the same data models and structures

## 6. Health Monitoring Requirements

- Implement a health check endpoint accessible via HTTP at `/health` (if using HTTP transport)
- Return HTTP 200 status when operational
- Respond to health status updates from the registry via the `registry-update_server_status` method
- Maintain connection availability for the registry's periodic health checks (default interval: 60 seconds)

## 7. Data Model Compliance

Your server must provide the following information when registering:

- **Unique Identifier**: A unique ID for your server instance
- **Endpoint Information**: Properly formatted endpoint URL or transport descriptor
- **Capability Flags**: Boolean values indicating which MCP features your server supports
- **Metadata Support**: Ability to store and retrieve key-value metadata pairs
- **Tagging System**: Support for categorizing your server with searchable tags

## 8. Error Handling Standards

- Implement proper error responses following JSON-RPC 2.0 error format
- Provide meaningful error messages that help with debugging
- Handle registration failures gracefully with appropriate retry mechanisms
- Support timeout configurations (registration timeout defaults to 30 seconds)

## 9. Configuration Requirements

Your server should support configurable settings similar to the registry:
- Database connection parameters (if storing state)
- Transport method selection
- Health check intervals
- Logging levels
- Authentication credentials (if required)

## 10. Security Considerations

- Support secure transport (HTTPS/WSS) for production deployments
- Implement authentication mechanisms if required by the registry
- Validate incoming requests from the registry server
- Protect against injection attacks in all inputs

## 11. Testing and Validation

- Provide a way to validate your server's compliance with the MCP specification
- Include integration tests that verify registration with the registry
- Test health check functionality
- Verify all advertised capabilities actually work as expected

## 12. Documentation Requirements

- Document your server's capabilities accurately
- Provide clear endpoint information for the registry
- Include usage examples showing how to interact with your server
- Specify any prerequisites or dependencies required to run your server

## 13. MCP Standard Endpoint

- The registry follows MCP standards with the `/mcp` endpoint for HTTP transport
- The previous `/rpc` endpoint has been deprecated in favor of the standardized `/mcp` endpoint
- All MCP communications should use the `/mcp` endpoint for compliance with the Model Context Protocol

## 14. Session Management Requirements

- The registry enforces session-based authentication for secure operations
- Registration and update operations require valid session contexts for each RPC call
- Sessions are automatically established when connecting via supported transports
- Session contexts must be maintained and validated for each individual RPC call
- Session timeouts are configurable (default: 1 hour)
- Invalid or expired sessions will result in authentication errors with code -32600
- The error message "Bad Request: Missing session ID" indicates that a valid session context is required but not provided for the specific RPC call
- Session validation occurs at the method level for security-critical operations

## 15. Health Check Implementation Requirements

- The registry performs periodic health checks on registered servers (default interval: 60 seconds)
- Your server must implement a health check endpoint accessible via HTTP at `/health` (if using HTTP transport)
- The health endpoint should return HTTP 200 status when the server is operational
- The registry will call the `registry-update_server_status` method to update your server's status
- Your server should be prepared to receive status updates from the registry
- If your server becomes unavailable, it will be marked as "unhealthy" in the registry

## 16. Session Establishment Process

- When connecting to the registry, sessions are established automatically through the transport layer
- For HTTP transport, ensure your client sends proper headers and maintains connection state
- Session context must be preserved throughout the lifetime of the connection
- When using the `mcp` library, sessions are managed automatically by the framework
- If implementing custom session management, ensure session IDs are properly transmitted with each request

## 17. Registration Process Best Practices

- Before registering, ensure your server is fully operational and ready to serve requests
- Include accurate capability information in your registration request
- Use descriptive names and tags to help clients discover your server
- Monitor your server's status in the registry and respond appropriately to status changes
- Implement retry logic for registration in case of temporary failures
- Handle registration failures gracefully and provide meaningful error messages

## 18. Required Endpoints and Methods

Your server must implement these endpoints/methods to work properly with the registry:
- Registration endpoint: `registry-register_server` method
- Status update endpoint: Must be able to receive `registry-update_server_status` calls
- Health check endpoint: HTTP `/health` (if using HTTP transport)
- Discovery endpoints: Support `rpc.discover` for schema retrieval

## 19. Complete Server Implementation Guide

### 19.1 Basic Server Structure
Your MCP server should implement the following structure:

```python
from mcp.server import FastMCP
import asyncio
import logging

class MyMCPServer:
    def __init__(self):
        # Initialize your MCP server with the FastMCP framework
        self.mcp = FastMCP("my-mcp-server", streamable_http_path="/mcp")
        # Add your tools, resources, etc.
        self._register_methods()
    
    def _register_methods(self):
        # Register your server's tools and resources
        @self.mcp.tool(
            name="my-tool",
            description="Description of your tool"
        )
        def my_tool(param: str) -> dict:
            return {"result": f"Processed {param}"}
    
    def run(self, transport="stdio", **kwargs):
        # Run your server with the specified transport
        if transport == "streamable-http":
            # For HTTP transport
            asyncio.run(self.mcp.run_streamable_http_async(**kwargs))
        else:
            # For stdio or other transports
            asyncio.run(self.mcp.run(transport=transport))
```

### 19.2 Registration Process Implementation
To register with the registry, your server needs to:

1. Establish a connection to the registry using the proper MCP client initialization sequence
2. Prepare registration parameters with accurate capabilities
3. Call the `registry-register_server` method
4. Handle the registration response

The proper MCP client initialization sequence is critical and consists of:
1. Establish connection via `streamable_http_client`
2. Create `ClientSession` with the returned streams
3. Call `initialize()` on the session to establish proper session context
4. Then make the registration call

Without this proper initialization sequence, the registry will return "Bad Request: Missing session ID".

```python
import asyncio

async def register_with_registry(self):
    """Register this server with the registry."""
    try:
        # Connect to the registry using the proper MCP transport
        # For HTTP transport, use streamable_http_client
        from mcp.client.streamable_http import streamable_http_client
        import mcp
        
        registry_url = "http://localhost:6000/mcp"  # Adjust as needed
        
        # Establish connection to the registry using proper MCP sequence
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
                server_id = result.get("server_id")
                print(f"✅ Successfully registered with ID: {server_id}")
                return server_id
            else:
                print(f"❌ Registration failed: {result.get('message', 'Unknown error')}")
                return None
                
    except Exception as e:
        print(f"❌ Error during registration: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
```

### 19.3 Health Check Endpoint Implementation
Your server must implement a health check endpoint that the registry will call:

```python
from fastapi import FastAPI
import uvicorn

# If using HTTP transport, implement a health endpoint
app = FastAPI()

@app.get("/health")
async def health_check():
    """Health check endpoint for the registry to verify server status."""
    # Perform any necessary health checks
    # Return 200 if healthy, appropriate error code if not
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
```

### 19.4 Session Management from Client Perspective
When connecting to the registry, sessions are established at the transport level, but individual RPC calls require proper session context validation. You should be aware of:

- Transport sessions are created automatically when establishing a connection
- Individual RPC calls (like registry-register_server and registry-update_server_status) require proper session context validation
- Sessions are tied to the transport connection but must be maintained for each RPC call
- Long-lived connections maintain transport session state
- If connections are dropped, new sessions may need to be established
- Session timeouts are configurable (default 1 hour)
- The registry will return error code -32600 with message "Bad Request: Missing session ID" if individual RPC calls lack proper session context

### 19.5 Error Handling and Recovery

- Implement proper error handling for registration failures
- Retry registration with exponential backoff if initial registration fails
- Handle session expiration by re-establishing connections when needed
- Log registration and health check failures for debugging purposes
- Gracefully handle situations where the registry becomes temporarily unavailable
- Implement circuit breaker patterns for registry communication
- Have fallback strategies when registry is unreachable

### 19.6 Transport Configuration
Configure your server to work with different transport methods:
- For `stdio`: Use standard input/output for local communication
- For `streamable-http`: Configure HTTP endpoints and ensure proper headers
- Ensure your server can accept both `application/json` and `text/event-stream` content types

### 19.7 Capability Reporting Accuracy
Report your server's actual capabilities accurately:
- Only set `resources` to `True` if your server actually implements resources
- Only set `tools` to `True` if your server actually implements tools
- Similarly for `prompts`, `roots`, and `sampling`
- Mismatched capabilities will lead to errors when clients try to use unimplemented features

### 19.8 Connection Establishment Process
When connecting to the registry, follow these steps:

1. **Transport Selection**: Choose the appropriate transport method:
   - `stdio`: For local communication between processes
   - `streamable-http`: For network-based communication

2. **Connection Initialization**:
   ```python
   from mcp.client import Client
   
   # For stdio transport (local communication)
   client = Client.connect_stdio()
   
   # For HTTP transport (network communication)
   client = Client.connect_http("http://registry-host:port")
   ```

3. **Connection Validation**: Verify the connection is working before attempting registration

4. **Error Handling**: Implement connection retry logic with exponential backoff:
   - Initial delay: 1 second
   - Maximum delay: 60 seconds
   - Maximum attempts: Defined by `MAX_REGISTRATION_ATTEMPTS` (default: 3)

### 19.9 Complete Registration Lifecycle
Follow this complete registration process:

1. **Pre-Registration Validation**:
   - Verify your server is fully operational
   - Confirm all advertised capabilities are working
   - Ensure health check endpoint is accessible

2. **Registration Attempt**:
   - Prepare registration data with accurate information
   - Call `registry-register_server` method
   - Handle the response appropriately

3. **Post-Registration Validation**:
   - Verify registration was successful
   - Store the returned server ID for future reference
   - Update your server's internal state to reflect registration

4. **Failure Handling**:
   - If registration fails, analyze the error response
   - Implement retry logic with exponential backoff
   - Consider fallback strategies if registry remains unavailable

### 19.10 Session Management Details
Understanding session lifecycle is critical:

1. **Session Creation**: Sessions are automatically created when establishing a transport connection
2. **Session Duration**: Sessions remain valid for the duration of the connection (default timeout: 1 hour)
3. **Session Renewal**: Sessions are renewed automatically with continued activity
4. **Session Expiration**: When sessions expire, establish a new connection to create a new session
5. **Session Validation**: Some operations require active sessions; check session status before critical operations

### 19.11 Health Check Implementation Requirements
Your server must implement health checks with these specifications:

1. **Endpoint Path**: `/health` (for HTTP transport)
2. **Response Format**:
   ```json
   {
     "status": "healthy",
     "timestamp": "2023-12-01T10:00:00Z",
     "details": {
       // Optional: additional health details
     }
   }
   ```
3. **Status Codes**:
   - 200 OK: Server is healthy and operational
   - 4xx/5xx: Server is unhealthy or experiencing issues
4. **Response Time**: Health checks should complete within 10 seconds (timeout used by registry)
5. **Content Type**: Respond with `application/json` content type

### 19.12 Error Recovery Procedures
Implement comprehensive error recovery:

1. **Network Interruption Handling**:
   - Detect connection drops promptly
   - Implement reconnection logic
   - Preserve important state during reconnects

2. **Registry Unavailability**:
   - Continue operating normally when registry is unavailable
   - Queue important registry updates for when registry becomes available
   - Log registry unavailability for monitoring

3. **Capability Mismatch Handling**:
   - Validate capabilities before advertising them
   - Gracefully handle requests for unimplemented capabilities
   - Provide meaningful error messages for unsupported operations

4. **Status Update Failures**:
   - Continue operating even if status updates to registry fail
   - Log status update failures for diagnostics
   - Retry status updates with appropriate backoff

### 19.13 Configuration Requirements
Ensure your server meets these configuration requirements:

1. **Environment Variables**:
   - Set appropriate timeout values (`REGISTRATION_TIMEOUT`, `SESSION_TIMEOUT`)
   - Configure retry attempts (`MAX_REGISTRATION_ATTEMPTS`)
   - Set proper logging levels for debugging

2. **Dependencies**:
   - Use compatible versions of the `mcp` library (≥1.0.0)
   - Ensure async/await support in your runtime environment
   - Include necessary transport libraries (aiohttp for HTTP transport)

3. **Compatibility**:
   - Support Python 3.13+ (minimum requirement)
   - Implement proper JSON-RPC 2.0 protocol handling
   - Support both `application/json` and `text/event-stream` content types

### 19.14 Operational Considerations
For production environments, consider:

1. **Monitoring**: Implement proper logging and metrics for registration and health check operations
2. **Security**: Use TLS for production deployments, validate certificates, implement proper authentication
3. **Scalability**: Design for multiple concurrent connections if needed
4. **Graceful Shutdown**: Properly deregister from the registry when shutting down

These rules ensure that your MCP server will integrate smoothly with the registry and be discoverable by clients using the standard MCP protocol.