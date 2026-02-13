# Standard-Compliant Model Context Protocol (MCP) Server

This is a fully compliant implementation of the Model Context Protocol (MCP) server in Python. It provides a complete, standard-compliant implementation of the MCP specification with support for both stdio and HTTP transports, including the modern Streamable HTTP transport and legacy HTTP/SSE transport.

## Compliance with MCP Specification

This implementation fully complies with the official MCP specification:
- **STDIO Transport**: Standard input/output stream communication
- **Streamable HTTP Transport**: Modern single `/mcp` endpoint supporting both POST and GET methods
- **Legacy HTTP/SSE Transport**: Backward-compatible `/sse` and `/message` endpoints

## Features

- Full compliance with MCP specification
- Support for stdio, Streamable HTTP, and legacy HTTP/SSE transports
- Implementation of all standard server methods:
  - `initialize`
  - `tools/list`, `tools/call` - Execute operations and actions
  - `resources/list`, `resources/read` - Access static data/content
  - `prompts/list`, `prompts/get` - Retrieve templated instructions
  - `shutdown`
  - `ping` - Health check endpoint (returns timestamp and status)
- Mandatory registry functionality for service discovery (enabled by default and should not be disabled)
- Consistent shell script formatting following the standard provided in the skeleton
- Mixed-mode operation support: server can also act as a client to connect to other MCP servers
- Cross-server task delegation capabilities

### Key Differences:
- **Tools**: Active operations that execute and return results (e.g., calculations, API calls, data transformations)
- **Resources**: Passive data containers accessed by URI that return static content (e.g., files, configurations)
- **Prompts**: Template-based instructions that can be customized with arguments (e.g., LLM prompt templates)
- Implementation of client methods that server can initiate:
  - `sampling/complete`
  - `elicitation/request`
  - `logging/message`
- Notification support for dynamic updates:
  - `notifications/tools/list_changed`
  - `notifications/resources/list_changed`
  - `notifications/prompts/list_changed`
- Optional registry functionality for service discovery (see below)
- Advanced concurrency control with request limiting and monitoring
- Comprehensive metrics and monitoring endpoints
- Mixed-mode operation: server can also act as a client to connect to other MCP servers
- Cross-server task delegation: ability to delegate tasks to other registered MCP servers

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Streamable HTTP Transport (Default & Standard)
```bash
python -m mcp_std_server.server --transport streamable-http --host 127.0.0.1 --port 3030
```

### Stdio Transport
```bash
python -m mcp_std_server.server --transport stdio
```

### Legacy HTTP/SSE Transport (For backward compatibility)
```bash
python -m mcp_std_server.server --transport http --host 127.0.0.1 --port 3030
```

### Mixed-Mode Operation (Server and Client)
Run the server in mixed-mode to act as both server and client:
```bash
python -m mcp_std_server.server --transport streamable-http --port 3030 --enable-client-mode --client-host 127.0.0.1 --client-port 3031
```

### Cross-Server Task Delegation
When registry functionality is enabled, the server can automatically delegate tasks to other registered MCP servers. The delegation logic works as follows:

1. **Service Discovery**: The server queries the registry to discover available services and their capabilities
2. **Capability Matching**: Tasks are matched to servers based on their advertised capabilities
3. **Intelligent Routing**: Requests are forwarded to appropriate servers based on their capabilities
4. **Result Aggregation**: Results from remote servers are returned to the original requester

```bash
python -m mcp_std_server.server --transport streamable-http --port 3030 --enable-registry --enable-client-mode
```

**Delegation Capabilities:**
- `delegate_tool_call()`: Forward tool execution to another server
- `fetch_remote_resource()`: Retrieve resources from other servers  
- `resolve_remote_prompt()`: Get prompt results from other servers
- Automatic service discovery through registry integration
- Load balancing based on server capabilities and availability

## Mandatory Registry Functionality

The server includes mandatory registry functionality that enables a service discovery architecture (this functionality should not be disabled by default). The server can operate in two distinct registry modes:

### Registry Server Mode
Act as a central registry server to track available services:
```bash
python -m mcp_std_server.server --transport streamable-http --port 3030 --enable-registry
```

### Registry Client Mode  
Register this server with an external registry server:
```bash
python -m mcp_std_server.server --transport streamable-http --port 3031 --register-with-registry --registry-host 127.0.0.1 --registry-port 3030
```

### Registry Endpoints (when --enable-registry is used):
- `registry/register` - Register a service with the registry
- `registry/list` - List all registered services
- `registry/unregister` - Remove a service from the registry

### Registry Architecture:
1. **Registry Server** - Central server that tracks available services (use `--enable-registry`)
2. **Service Servers** - Individual MCP servers that register their capabilities
3. **Registry Clients** - MCP servers that register with an external registry (use `--register-with-registry`)
4. **AI Agent** - Queries the registry to discover available services

### How to Use Registry:
1. **As Registry Server**: Start the server with `--enable-registry` flag to accept registrations from other servers
2. **As Registry Client**: Start the server with `--register-with-registry` flag to register with an external registry server
3. Other MCP servers can register with the registry via the `/mcp` endpoint (for Streamable HTTP) or `/send` endpoint (for legacy)
4. AI agents can discover services by querying the registry's `registry/list` method
5. Services can deregister via the `registry/unregister` method

### Auto-Registration and Heartbeat Monitoring:
- Servers can auto-register with a registry using `--register-with-registry` flag
- Registered services send periodic heartbeats (every 30 seconds) to maintain registration
- Services not seen within 10 minutes are automatically removed from the registry
- Services automatically deregister when shutting down cleanly
- Remote heartbeat manager maintains registration status for auto-registered services

## Architecture

The server is organized into several modules:

- `utils/json_rpc.py`: JSON-RPC 2.0 message handling with concurrency control
- `transports/streamable_http.py`: Modern Streamable HTTP transport implementation
- `transports/http_sse.py`: Legacy HTTP/SSE transport implementation with session correlation
- `transports/stdio.py`: STDIO transport implementation
- `handlers/server_handlers.py`: Standard server method handlers
- `handlers/client_handlers.py`: Client method handlers
- `utils/notifications.py`: Notification management
- `utils/service_registry_db.py`: Optional database integration for registry functionality
- `utils/postgres_registry_db.py`: PostgreSQL database integration for registry functionality
- `utils/heartbeat_manager.py`: Service heartbeat and health monitoring
- `server.py`: Main server implementation

## Configuration

The server can be configured via command-line arguments:
- `--transport`: Select transport mechanism ('stdio', 'http', or 'streamable-http')
- `--host`: Host for HTTP transport (default: 127.0.0.1)
- `--port`: Port for HTTP transport (default: 3030)
- `--max-concurrent-requests`: Maximum number of concurrent requests (default: 10)
- `--enable-registry`: Enable registry functionality to track multiple MCP services (mandatory and enabled by default)
- `--register-with-registry`: Register this server with a registry server (requires --registry-host and --registry-port)
- `--registry-host`: Registry server host to register with (default: 127.0.0.1)
- `--registry-port`: Registry server port to register with (default: 3031)
- `--use-postgres`: Use PostgreSQL for registry storage instead of SQLite (optional)
- `--postgres-host`: PostgreSQL host (default: 127.0.0.1)
- `--postgres-port`: PostgreSQL port (default: 5432)
- `--postgres-db`: PostgreSQL database name (default: mcp_registry)
- `--postgres-user`: PostgreSQL username (default: postgres)
- `--postgres-password`: PostgreSQL password (default: empty)
- `--enable-client-mode`: Enable client mode to connect to another MCP server (default: False)
- `--client-transport`: Transport mechanism for client connection ('stdio', 'http', or 'streamable-http') (default: 'streamable-http')
- `--client-host`: Host of the remote MCP server to connect to (default: 127.0.0.1)
- `--client-port`: Port of the remote MCP server to connect to (default: 3030)
- `--client-endpoint`: Specific endpoint of the remote MCP server (overrides host:port)

### PostgreSQL Authentication Security
When using PostgreSQL, ensure secure authentication by:
- Setting strong passwords via `--postgres-password` parameter
- Using dedicated database users with minimal required privileges
- Storing credentials in environment variables when possible rather than command line
- Ensuring the PostgreSQL server is properly secured and accessible only from authorized networks

### Port Configuration Clarification
Understanding the difference between server and client ports:
- `--port`: The port that this server listens on for incoming connections (server port)
- `--client-port`: The port that this server connects to when acting as a client to other servers
- When using `--register-with-registry`, the server acts as a client to connect to the registry server
- Default server port is 3030, default registry client port is 3031
- These ports can be configured independently to avoid conflicts

## Example Usage

For stdio transport, the server communicates via stdin/stdout as per MCP specification:
```bash
echo '{"jsonrpc": "2.0", "id": "1", "method": "initialize", "params": {"clientInfo": {"name": "test-client", "version": "1.0"}}}' | python -m mcp_std_server.server
```

For Streamable HTTP transport, the server provides:
1. A bidirectional endpoint at `/mcp` that supports both POST (client-to-server) and GET (server-to-client via SSE) methods
2. A metrics endpoint at `/metrics` for performance monitoring

## Advanced Features

### Concurrency Control
The server implements sophisticated concurrency control to limit the number of simultaneous requests:
- Configurable maximum concurrent requests (default: 10)
- Semaphore-based request limiting
- Performance monitoring and metrics tracking

### Session Correlation (HTTP Transports)
The HTTP transports support session correlation for proper request/response routing:
- MCP-Session-Id header for client identification
- Request-to-client mapping for accurate response delivery
- Automatic session management

### Health Monitoring
- Built-in `ping` endpoint for health checks
- `/metrics` endpoint for detailed performance metrics
- Concurrency monitoring with request tracking
- Detailed logging and error reporting

### Signal Handling
- Graceful shutdown on SIGINT and SIGTERM signals
- Proper cleanup of resources and connections
- Automatic deregistration from registries during shutdown

## Starting the Server

### Using Python Directly
```bash
# Start with default settings (Streamable HTTP on port 3030)
python -m mcp_std_server.server --transport streamable-http

# Start with custom port
python -m mcp_std_server.server --transport streamable-http --port 9000

# Start registry server
python -m mcp_std_server.server --transport streamable-http --port 3030 --enable-registry

# Start with concurrency limits
python -m mcp_std_server.server --transport streamable-http --max-concurrent-requests 20

# Start with PostgreSQL registry backend
python -m mcp_std_server.server --transport streamable-http --port 3030 --enable-registry --use-postgres
```

## Database Support

The MCP server includes support for multiple database backends:

### SQLite (Default)
- Built-in support for registry functionality
- Stores data in `mcp_registry.db` file
- No configuration required - ready to use out of the box
- Automatic table creation and schema management
- Separate TaskStorage class available for storing received and submitted tasks in addition to registry data

### PostgreSQL (Optional)
- Production-ready database solution
- High availability and scalability
- Requires PostgreSQL installation and configuration
- Connection pooling and reconnection logic
- Advanced error handling and transaction management
- Separate TaskStorage class available for storing received and submitted tasks in addition to registry data

**PostgreSQL Usage:**
```bash
# Start registry server with PostgreSQL backend
python -m mcp_std_server.server --transport streamable-http --port 3030 --enable-registry --use-postgres

# With custom PostgreSQL parameters
python -m mcp_std_server.server --transport streamable-http --port 3030 --enable-registry --use-postgres \
  --postgres-host localhost --postgres-port 5432 \
  --postgres-db mcp_registry --postgres-user postgres \
  --postgres-password ''
```

### Task Storage
- The server includes a separate TaskStorage class for persisting received and submitted tasks
- Tasks are stored separately from registry data to maintain clear separation of concerns
- Both SQLite and PostgreSQL backends support persistent task storage with status tracking
- Tasks survive server restarts and maintain their state in the database

## Extending the Server

The server is designed to be easily extensible. See the source code for examples of:
- Adding custom tools, resources, and prompts
- Creating a registry server for service discovery
- Connecting to databases for persistent storage

### Customizing Tools for Specific Domains

The server provides a flexible framework for implementing domain-specific tools. When extending the server for specific use cases (e.g., IT leadership, project management, etc.), consider implementing specialized tools that align with the domain requirements:

- **Domain-Specific Tools**: Implement tools tailored to your specific use case (e.g., assign_task, review_code, generate_project_plan for IT leadership)
- **Tool Input Validation**: Define appropriate input schemas for each tool to ensure proper validation
- **Status Tracking**: Implement proper status tracking for long-running operations
- **Integration Points**: Connect tools with external systems as needed for your domain

Example domain-specific tools might include:
- Task assignment and management tools
- Code review and quality assurance tools
- Project planning and scheduling tools
- Team communication and coordination tools
- Progress tracking and reporting tools

### Code Reusability

The server architecture promotes code reuse when building additional servers:
- **Transport Layer**: Multiple transport implementations can be reused
- **Database Integration**: PostgreSQL and SQLite connection management is reusable
- **Registry System**: Service discovery and registration patterns can be extended
- **Configuration Management**: Command-line parsing and configuration loading
- **Lifecycle Management**: Startup/shutdown procedures and signal handling
- **Logging Infrastructure**: Comprehensive logging setup and debug utilities
- **Concurrency Control**: Request limiting and performance monitoring systems
- **Session Management**: HTTP session correlation and request routing

This modular design allows you to build new servers by inheriting from base classes and reusing existing components with minimal duplication.

## Shell Script Variables

The MCP server comes with several shell scripts for different deployment scenarios. Each script supports various environment variables and command-line parameters:

### `start_mcp_server.sh`
Comprehensive script with all configuration options.

**Environment Variables and Parameters:**
- `TRANSPORT` (default: "streamable-http"): Transport type (stdio, http, streamable-http)
- `HOST` (default: "127.0.0.1"): Host for HTTP transport
- `PORT` (default: 3030): Port for HTTP transport
- `ENABLE_REGISTRY` (default: false): Enable registry functionality to track multiple MCP services
- `REGISTER_WITH_REGISTRY` (default: true): Register this server with a registry server
- `REGISTRY_HOST` (default: "127.0.0.1"): Registry server host to register with
- `REGISTRY_PORT` (default: 3031): Registry server port to register with
- `USE_POSTGRES` (default: false): Use PostgreSQL for registry storage instead of SQLite
- `MAX_CONCURRENT_REQUESTS` (default: 10): Maximum number of concurrent requests

### `start_registry_server.sh`
Specifically configured for registry servers.

**Environment Variables and Parameters:**
- `TRANSPORT` (default: "streamable-http"): Transport type (http, streamable-http)
- `HOST` (default: "127.0.0.1"): Host for HTTP transport
- `PORT` (default: 3031): Port for HTTP transport (registry default)
- `USE_POSTGRES` (default: false): Use PostgreSQL for registry storage instead of SQLite
- `MAX_CONCURRENT_REQUESTS` (default: 10): Maximum number of concurrent requests
- `BACKGROUND` (default: false): Run server in background
- `LOG_FILE`: Redirect output to log file
- `PID_FILE`: Write process ID to file

### `start_mcp_default.sh`
Quick start with default settings.

**Environment Variables and Parameters:**
- Uses default settings: Streamable HTTP transport on port 3030