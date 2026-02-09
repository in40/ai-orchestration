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

Your server must be able to register with the registry using the `registry/register_server` method with this payload structure:

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

## 5. Technology Stack Requirements

### Python-Based Implementation (Recommended)
- **Python Version**: 3.9 or higher
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
- Respond to health status updates from the registry via the `registry/update_server_status` method
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

These rules ensure that your MCP server will integrate smoothly with the registry and be discoverable by clients using the standard MCP protocol.