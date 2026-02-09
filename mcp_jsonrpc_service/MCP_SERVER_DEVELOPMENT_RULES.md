# MCP Server Development Rules and Guidelines

This document defines the mandatory rules and guidelines for developing MCP (Model Context Protocol) servers that integrate with the MCP Server Registry.

## 1. MCP Protocol Compliance

### 1.1 Mandatory Protocol Implementation
- All servers MUST implement the Model Context Protocol (MCP) specification
- All servers MUST support the three core MCP primitives: tools, resources, and prompts
- All servers MUST implement proper JSON-RPC 2.0 communication protocol
- All servers MUST follow the OpenRPC specification pattern for API contracts

### 1.2 Protocol Adherence
- Servers MUST handle all required MCP methods
- Servers MUST use correct JSON-RPC 2.0 format for requests and responses
- Servers MUST implement proper error handling as defined by the MCP specification

## 2. Required Capabilities Structure

### 2.1 Capability Definition
All servers MUST define their capabilities using this exact structure:

```python
{
  "resources": boolean,    # Whether the server supports resources
  "tools": boolean,        # Whether the server supports tools
  "prompts": boolean,      # Whether the server supports prompts
  "roots": boolean,        # Whether the server supports roots
  "sampling": boolean      # Whether the server supports sampling
}
```

### 2.2 Capability Management
- All capability flags MUST be boolean values
- Servers MUST accurately report their actual capabilities
- Capability reporting MUST be consistent with actual server functionality

## 3. Registration Requirements

### 3.1 Registration Payload
Servers MUST be able to register with the registry using the `registry/register_server` method with this exact payload structure:

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

### 3.2 Registration Process
- Servers MUST successfully register with the registry upon startup
- Servers MUST handle registration failures with appropriate retry mechanisms
- Servers MUST store the server ID returned by the registry

## 4. Supported Transport Methods

### 4.1 Transport Support
Servers MUST support at least one of these transport methods:
- `stdio` - Standard input/output for local communication
- `streamable-http` - HTTP-based transport
- Any other transport compatible with the MCP specification

### 4.2 Transport Implementation
- Transport selection MUST be configurable
- All supported transports MUST be reliable and maintain persistent connections when required
- Transport errors MUST be handled gracefully with fallback mechanisms

## 5. Technology Stack Requirements

### 5.1 Python Implementation (Recommended)
When implementing in Python:
- Python version MUST be 3.9 or higher
- The official `mcp` library (version 1.0.0 or higher) MUST be used
- Web framework MUST be compatible with FastAPI-style routing if using HTTP transport
- Async operations MUST be implemented for optimal performance

### 5.2 Alternative Language Implementation
When implementing in other languages:
- MCP protocol implementation MUST be equivalent to the official specification
- JSON serialization/deserialization MUST match the registry's expectations
- Same data models and structures MUST be handled correctly

## 6. Health Monitoring Requirements

### 6.1 Health Check Endpoint
- HTTP transport servers MUST implement a health check endpoint at `/health`
- The endpoint MUST return HTTP 200 status when operational
- Response MUST include current health status and timestamp

### 6.2 Health Status Management
- Servers MUST respond to health status updates from the registry via the `registry/update_server_status` method
- Servers MUST maintain connection availability for the registry's periodic health checks (default interval: 60 seconds)
- Health status MUST accurately reflect server operational state

## 7. Data Model Compliance

### 7.1 Required Information
Servers MUST provide the following information when registering:
- **Unique Identifier**: A unique ID for the server instance
- **Endpoint Information**: Properly formatted endpoint URL or transport descriptor
- **Capability Flags**: Accurate boolean values indicating MCP features supported
- **Metadata Support**: Ability to store and retrieve key-value metadata pairs
- **Tagging System**: Support for categorizing the server with searchable tags

### 7.2 Data Accuracy
- All provided information MUST be accurate and up-to-date
- Servers MUST update registration information when capabilities change
- Metadata and tags MUST be properly maintained

## 8. Error Handling Standards

### 8.1 Error Format Compliance
- All error responses MUST follow JSON-RPC 2.0 error format
- Standard error codes MUST be used appropriately:
  - -32700: Parse error
  - -32600: Invalid Request
  - -32601: Method not found
  - -32602: Invalid params
  - -32603: Internal error

### 8.2 Error Handling Implementation
- All errors MUST provide meaningful messages for debugging
- Registration failures MUST be handled gracefully with retry mechanisms
- Timeout configurations MUST be supported (registration timeout defaults to 30 seconds)

## 9. Configuration Requirements

### 9.1 Configurable Settings
Servers SHOULD support configurable settings:
- Database connection parameters (if storing state)
- Transport method selection
- Health check intervals
- Logging levels
- Authentication credentials (if required)

### 9.2 Configuration Sources
- Configuration MUST be loadable from environment variables
- Configuration MUST be overrideable via command-line arguments
- Default values MUST be provided for all configurable settings

## 10. Security Considerations

### 10.1 Secure Communication
- Production deployments MUST support secure transport (HTTPS/WSS)
- Authentication mechanisms MUST be implemented if required by the registry
- Incoming requests from the registry server MUST be validated

### 10.2 Input Security
- All inputs MUST be protected against injection attacks
- Security headers MUST be implemented for HTTP transport
- Sensitive information MUST NOT be exposed in logs or responses

## 11. Testing and Validation

### 11.1 Testing Requirements
- Servers MUST provide validation for MCP specification compliance
- Integration tests MUST verify registration with the registry
- Health check functionality MUST be tested
- All advertised capabilities MUST be verified to work as expected

### 11.2 Test Coverage
- Unit tests MUST cover core functionality
- Integration tests MUST verify registry interaction
- Error condition tests MUST be included

## 12. Documentation Requirements

### 12.1 Required Documentation
- Server capabilities MUST be documented accurately
- Clear endpoint information MUST be provided for the registry
- Usage examples MUST show how to interact with the server
- Prerequisites and dependencies MUST be specified

### 12.2 Documentation Standards
- Documentation MUST be kept up-to-date with implementation
- API endpoints MUST be documented with request/response formats
- Configuration options MUST be documented with examples

## Enforcement

These rules are mandatory for all MCP server implementations intended for registry integration. Code reviews MUST verify compliance with these rules using the provided checklist. Non-compliant implementations will not be accepted for registry integration.