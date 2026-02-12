# MCP Standard Server

This is a standard implementation of the Model Context Protocol (MCP) server in Python. It provides a complete, compliant implementation of the MCP specification with support for both stdio and HTTP/SSE transports.

## Compliance Requirements

**IMPORTANT: All implementations based on this skeleton must 100% comply with the specifications documented in README.md and DOCUMENTATION.md.**

### Mandatory Compliance Rules:

1. **MCP Specification Compliance**: All implementations must fully comply with the official MCP specification
2. **Interface Compatibility**: All standard MCP methods must be implemented as documented
3. **Transport Standards**: Both stdio and HTTP/SSE transports must follow MCP specification exactly
4. **Registry Protocol**: If implementing registry functionality, it must follow the documented protocols
5. **Documentation Adherence**: All implementations must maintain compatibility with the documented interfaces and behaviors
6. **Extension Points**: When extending functionality, ensure that core MCP interfaces remain unchanged and compliant
7. **Dependencies Management**: Any additional packages/libraries required for the implementation must be added to requirements.txt following the format: `package-name>=version`

**Failure to comply with these requirements means the implementation is not a valid MCP server based on this skeleton.**

## Features

- Full compliance with MCP specification
- Support for stdio and HTTP/SSE transports
- Implementation of all standard server methods:
  - `initialize`
  - `tools/list`, `tools/call` - Execute operations and actions
  - `resources/list`, `resources/read` - Access static data/content
  - `prompts/list`, `prompts/get` - Retrieve templated instructions
  - `shutdown`
  - `ping` - Health check endpoint (returns timestamp and status)

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

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Stdio Transport (Default)
```bash
python -m mcp_server.server --transport stdio
```

### HTTP/SSE Transport
```bash
python -m mcp_server.server --transport http --host 127.0.0.1 --port 3030
```

## Optional Registry Functionality

The server includes optional registry functionality that enables a service discovery architecture:

### Enabling Registry Mode
```bash
python -m mcp_server.server --transport http --port 3030 --enable-registry
```

### Registry Endpoints (when enabled):
- `registry/register` - Register a service with the registry
- `registry/list` - List all registered services
- `registry/unregister` - Remove a service from the registry

### Registry Architecture:
1. **Registry Server** - Central server that tracks available services
2. **Service Servers** - Individual MCP servers that register their capabilities
3. **AI Agent** - Queries the registry to discover available services

### How to Use Registry:
1. Start the registry server with `--enable-registry` flag
2. Other MCP servers can register with the registry via the `/send` endpoint
3. AI agents can discover services by querying the registry's `registry/list` method
4. Services can deregister via the `registry/unregister` method

### Auto-Registration and Heartbeat Monitoring:
- Servers can auto-register with a registry using `--register-with-registry` flag
- Registered services send periodic heartbeats (every 30 seconds) to maintain registration
- Services not seen within 10 minutes are automatically removed from the registry
- Services automatically deregister when shutting down cleanly
- Remote heartbeat manager maintains registration status for auto-registered services

## Architecture

The server is organized into several modules:

- `utils/json_rpc.py`: JSON-RPC 2.0 message handling with concurrency control
- `transports/stdio.py`: Stdio transport implementation
- `transports/http_sse.py`: HTTP/SSE transport implementation with session correlation
- `handlers/server_handlers.py`: Standard server method handlers
- `handlers/client_handlers.py`: Client method handlers
- `utils/notifications.py`: Notification management
- `utils/service_registry_db.py`: Optional database integration for registry functionality
- `utils/postgres_registry_db.py`: PostgreSQL database integration for registry functionality
- `utils/heartbeat_manager.py`: Service heartbeat and health monitoring
- `utils/concurrency_monitor.py`: Concurrency and performance monitoring
- `server.py`: Main server implementation

## Configuration

The server can be configured via command-line arguments:
- `--transport`: Select transport mechanism ('stdio' or 'http')
- `--host`: Host for HTTP transport (default: 127.0.0.1)
- `--port`: Port for HTTP transport (default: 3030)
- `--max-concurrent-requests`: Maximum number of concurrent requests (default: 10)
- `--enable-registry`: Enable registry functionality to track multiple MCP services (optional)
- `--register-with-registry`: Register this server with a registry server (requires --registry-host and --registry-port)
- `--registry-host`: Registry server host to register with (default: 127.0.0.1)
- `--registry-port`: Registry server port to register with (default: 3031)
- `--use-postgres`: Use PostgreSQL for registry storage instead of SQLite (optional)
- `--postgres-host`: PostgreSQL host (default: 127.0.0.1)
- `--postgres-port`: PostgreSQL port (default: 5432)
- `--postgres-db`: PostgreSQL database name (default: mcp_registry)
- `--postgres-user`: PostgreSQL username (default: postgres)
- `--postgres-password`: PostgreSQL password (default: empty)

## Example Usage

For stdio transport, the server communicates via stdin/stdout as per MCP specification:
```bash
echo '{"jsonrpc": "2.0", "id": "1", "method": "initialize", "params": {"clientInfo": {"name": "test-client", "version": "1.0"}}}' | python -m mcp_server.server
```

For HTTP/SSE transport, the server provides:
1. An SSE endpoint at `/sse` for server messages
2. An HTTP POST endpoint at `/send` for client messages
3. A metrics endpoint at `/metrics` for performance monitoring

## Advanced Features

### Concurrency Control
The server implements sophisticated concurrency control to limit the number of simultaneous requests:
- Configurable maximum concurrent requests (default: 10)
- Semaphore-based request limiting
- Performance monitoring and metrics tracking

### Session Correlation (HTTP/SSE)
The HTTP/SSE transport supports session correlation for proper request/response routing:
- X-MCP-Session-ID header for client identification
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
# Start with default settings (HTTP on port 3030)
python -m mcp_server.server --transport http

# Start with custom port
python -m mcp_server.server --transport http --port 9000

# Start registry server
python -m mcp_server.server --transport http --port 3030 --enable-registry

# Start with concurrency limits
python -m mcp_server.server --transport http --max-concurrent-requests 20

# Start with PostgreSQL registry backend
python -m mcp_server.server --transport http --port 3030 --enable-registry --use-postgres
```

### Using Startup Scripts

Two convenient shell scripts are provided:

1. **Simple startup script** (starts with defaults):
```bash
./start_mcp_default.sh
```

2. **Configurable startup script** (supports all options):
```bash
./start_mcp_server.sh --help
./start_mcp_server.sh --port 9000
./start_mcp_server.sh --enable-registry --port 5000
./start_mcp_server.sh --register-with-registry --registry-port 3031
```

### Auto-Registration with Registry

Servers can automatically register with a registry server:

```bash
# Start a server and register it with the registry at localhost:3031
./start_mcp_server.sh --port 3032 --register-with-registry

# Start a server and register it with a registry at a custom host/port
./start_mcp_server.sh --port 3032 --register-with-registry --registry-host registry.example.com --registry-port 8080
```

### Running in Background

Servers can be started in the background using several methods:

#### Method 1: Standard Backgrounding
```bash
# Start in background using &
./start_mcp_server.sh --port 3031 --enable-registry --use-postgres --postgres-user postgres --postgres-password postgres &
echo "Registry server started in background"
```

#### Method 2: Using nohup for Persistence
```bash
# Start with nohup to persist after terminal closes
nohup ./start_mcp_server.sh --port 3031 --enable-registry --use-postgres --postgres-user postgres --postgres-password postgres > registry.log 2>&1 &
```

#### Method 3: Using Screen or Tmux
```bash
# Using screen
screen -dmS mcp-registry './start_mcp_server.sh --port 3031 --enable-registry --use-postgres --postgres-user postgres --postgres-password postgres'

# Using tmux
tmux new-session -d -s mcp-registry './start_mcp_server.sh --port 3031 --enable-registry --use-postgres --postgres-user postgres --postgres-password postgres'
```

### Testing the Registry

A test script is provided to verify registry functionality:

```bash
# First start a registry server
./start_mcp_server.sh --port 3031 --enable-registry

# Then run the test script in another terminal
./test_registry_simple.sh
```

### Testing Auto-Registration

Test scripts are provided to verify auto-registration functionality:

```bash
# Start registry server
./start_mcp_server.sh --port 3031 --enable-registry &

# Start server that auto-registers with registry
./start_mcp_server.sh -R --registry-port 3031 --port 3032 &

# Query registry as an AI agent would
./query_registry.sh

# Or run complete AI agent workflow simulation
./ai_agent_workflow.sh
```

### Database Support

The MCP server includes support for multiple database backends:

#### SQLite (Default)
- Built-in support for registry functionality
- Stores data in `mcp_registry.db` file
- No configuration required - ready to use out of the box
- Automatic table creation and schema management

#### PostgreSQL (Optional)
- Production-ready database solution
- High availability and scalability
- Requires PostgreSQL installation and configuration
- Connection pooling and reconnection logic
- Advanced error handling and transaction management

**PostgreSQL Usage:**
```bash
# Start registry server with PostgreSQL backend
./start_mcp_server.sh --port 3031 --enable-registry --use-postgres

# With custom PostgreSQL parameters
./start_mcp_server.sh --port 3031 --enable-registry --use-postgres \
  --postgres-host localhost --postgres-port 5432 \
  --postgres-db mcp_registry --postgres-user postgres \
  --postgres-password ''
```

#### PostgreSQL Setup Requirements

When using PostgreSQL backend, ensure the following setup is completed:

1. **Set up PostgreSQL user password**:
   ```bash
   sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
   ```

2. **Configure pg_hba.conf** for proper authentication:
   - The default `pg_hba.conf` uses `peer` authentication for local connections, which may not work with the server
   - Change authentication method to `md5` or `scram-sha-256` for the postgres user
   - Example configuration:
     ```
     local   all             postgres                                md5
     host    all             all             127.0.0.1/32            md5
     host    all             all             ::1/128                 md5
     ```

3. **Restart PostgreSQL** after configuration changes:
   ```bash
   sudo systemctl restart postgresql
   ```

4. **Use 127.0.0.1 instead of localhost** to avoid IPv6 resolution issues

### Running in Background

Servers can be started in the background using several methods:

#### Method 1: Standard Backgrounding
```bash
# Start in background using &
./start_mcp_server.sh --port 3031 --enable-registry &
echo "Registry server started in background"

# Start auto-registering server in background
./start_mcp_server.sh -R --registry-port 3031 --port 3032 &
echo "Auto-registering server started in background"
```

#### Method 2: Using Enhanced Script with Background Options
```bash
# Start in background with the enhanced script
./start_mcp_server_bg.sh -b --port 3031 --enable-registry

# Start with logging
./start_mcp_server_bg.sh -b -l registry.log --port 3031 --enable-registry

# Start with PID file
./start_mcp_server_bg.sh -b --pid-file registry.pid --port 3031 --enable-registry

# Start registry with PostgreSQL in background
./start_mcp_server_bg.sh -b --port 3031 --enable-registry --use-postgres
```

#### Method 3: Using nohup for Persistence
```bash
# Start with nohup to persist after terminal closes
nohup ./start_mcp_server.sh --port 3031 --enable-registry > registry.log 2>&1 &
```

#### Method 4: Using Screen or Tmux
```bash
# Using screen
screen -dmS mcp-registry ./start_mcp_server.sh --port 3031 --enable-registry

# Using tmux
tmux new-session -d -s mcp-registry './start_mcp_server.sh --port 3031 --enable-registry'
```

#### Managing Background Processes
```bash
# Check running processes
ps aux | grep "python -m mcp_server.server"

# Kill specific process
pkill -f "python -m mcp_server.server"

# Or using PID if saved to file
kill $(cat registry.pid)
```

### Stopping Servers

Three stop scripts are provided to terminate MCP and registry server instances:

1. **Stop MCP Server Only**:
```bash
./stop_mcp_server.sh
```

2. **Stop Registry Server Only**:
```bash
./stop_registry_server.sh
```

3. **Stop All Servers (Recommended)**:
```bash
./stop_all_servers.sh
```

The `stop_all_servers.sh` script is the most comprehensive and will:
- Terminate any registry server processes (those with `--enable-registry` flag or running on ports 3031/3032)
- Terminate any remaining MCP server processes
- Force kill any processes that don't respond to graceful termination
- Clean up any leftover PID files

## Extending the Server

The server is designed to be easily extensible. See `example.py` for examples of:
- Adding custom tools, resources, and prompts
- Creating a registry server for service discovery
- Connecting to databases for persistent storage

### Code Reusability

The server architecture promotes code reuse when building additional servers:
- **Transport Layer**: HTTP/stdio transport abstractions can be reused
- **Database Integration**: PostgreSQL and SQLite connection management is reusable
- **Registry System**: Service discovery and registration patterns can be extended
- **Configuration Management**: Command-line parsing and configuration loading
- **Lifecycle Management**: Startup/shutdown procedures and signal handling
- **Logging Infrastructure**: Comprehensive logging setup and debug utilities
- **Concurrency Control**: Request limiting and performance monitoring systems
- **Session Management**: HTTP/SSE session correlation and request routing

This modular design allows you to build new servers by inheriting from base classes and reusing existing components with minimal duplication.

## Complete Script Reference

The MCP server project includes multiple shell scripts for different purposes:

### Startup Scripts
- `./start_mcp_default.sh` - Simple startup with default settings
- `./start_mcp_server.sh` - Full-featured startup with all configuration options
- `./start_mcp_server_bg.sh` - Enhanced startup with built-in background operation
- `./start_registry_server.sh` - Dedicated registry server startup with optimized defaults

### Testing Scripts
- `./test_registry_simple.sh` - Basic registry functionality test
- `./test_registry.sh` - Comprehensive registry functionality test
- `./test_auto_registration.sh` - Auto-registration functionality test
- `./test_postgres_integration.sh` - PostgreSQL integration test

### Utility Scripts
- `./query_registry.sh` - Query registered services from registry using MCP protocol
- `./query_registry_client_proper.py` - Advanced registry client with full service details via HTTP/SSE
- `./query_registry_client_proper_fixed.py` - Improved registry client with better reliability and synchronization
- `./query_registry_sse.sh` - Shell wrapper for registry client with full service details
- `./query_registry_sse_improved.sh` - Improved shell wrapper using the fixed Python client for better reliability
- `./test_registry_client_reliability.sh` - Test script to compare original vs improved client reliability
- `./ai_agent_workflow.sh` - Complete AI agent workflow simulation using MCP protocol
- `./final_verification.sh` - Complete system verification using MCP protocol