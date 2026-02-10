# MCP Server Complete Documentation

## Overview

This is a complete implementation of the Model Context Protocol (MCP) server in Python. It provides a fully compliant implementation of the MCP specification with support for both stdio and HTTP/SSE transports, plus an optional registry functionality for service discovery.

## Architecture

The server follows the MCP specification and consists of several key components:

- **JSON-RPC 2.0 Message Handler**: Handles parsing, validation, and routing of JSON-RPC messages
- **Transport Layer**: Supports both stdio and HTTP/SSE transports
- **Request Handlers**: Implements all standard MCP methods
- **Notification Manager**: Handles dynamic updates and notifications
- **Registry System**: Optional service discovery and registration system

## Standard MCP Endpoints

### Server Request Endpoints (Methods the client calls):

1. **Initialization:**
   - `initialize` - Initialize the server and negotiate capabilities
   - `shutdown` - Request server shutdown

2. **Tools:**
   - `tools/list` - List available tools with optional pagination
   - `tools/call` - Execute a specific tool with parameters

3. **Resources:**
   - `resources/list` - List available resources with optional pagination
   - `resources/read` - Read content from a specific resource by URI

4. **Prompts:**
   - `prompts/list` - List available prompts with optional pagination
   - `prompts/get` - Get a specific prompt with resolved arguments

5. **Health Check:**
   - `ping` - Health check endpoint (returns timestamp and status)

### Client Request Endpoints (Methods the server can call back to the client):

1. **Sampling:**
   - `sampling/complete` - Request language model completion from client

2. **Elicitation:**
   - `elicitation/request` - Request user input or confirmation from client

3. **Logging:**
   - `logging/message` - Send log messages to the client

### Notification Endpoints (Asynchronous updates):

1. **Change Notifications:**
   - `notifications/tools/list_changed` - Notify client that tools list has changed
   - `notifications/resources/list_changed` - Notify client that resources list has changed
   - `notifications/prompts/list_changed` - Notify client that prompts list has changed

## Transport-Specific Endpoints

### For HTTP/SSE Transport:

1. **SSE Endpoint:**
   - `/sse` - Server-Sent Events endpoint for receiving server messages
   - Returns an "endpoint" event with the URI for message sending

2. **HTTP POST Endpoint:**
   - `/send` - HTTP POST endpoint for sending messages to the server

## Registry Endpoints (When `--enable-registry` is used)

### Registry Management Endpoints:

1. **Service Registration:**
   - `registry/register` - Register a service with the registry
     - Parameters: service ID, name, description, endpoint, capabilities
     - Allows other MCP servers to register themselves with the registry server

2. **Service Discovery:**
   - `registry/list` - List all registered services in the registry
     - Parameters: optional filter
     - Allows AI agents to discover available services and their capabilities

3. **Service Unregistration:**
   - `registry/unregister` - Remove a service from the registry
     - Parameters: service ID
     - Allows services to deregister when shutting down

## Registration Protocol

When the registry functionality is enabled, MCP servers can participate in a service discovery architecture:

### 1. Service Registration (`registry/register`)

A service registers itself with the registry by sending a JSON-RPC request to the registry's `/send` endpoint:

```json
{
  "jsonrpc": "2.0",
  "id": "req-123",
  "method": "registry/register",
  "params": {
    "id": "service-unique-id",
    "name": "Service Name",
    "description": "Description of the service",
    "endpoint": "http://service-host:port",
    "capabilities": {
      "tools": ["tool1", "tool2"],
      "resources": ["resource1", "resource2"],
      "prompts": ["prompt1", "prompt2"]
    }
  }
}
```

The registry responds with:

```json
{
  "jsonrpc": "2.0",
  "id": "req-123",
  "result": {
    "success": true,
    "service_id": "service-unique-id",
    "message": "Service registered successfully"
  }
}
```

### 2. Service Discovery (`registry/list`)

AI agents or other services can discover available services by sending:

```json
{
  "jsonrpc": "2.0",
  "id": "req-456",
  "method": "registry/list",
  "params": {
    "filter": "database"  // optional
  }
}
```

The registry responds with:

```json
{
  "jsonrpc": "2.0",
  "id": "req-456",
  "result": {
    "services": [
      {
        "id": "db-service-1",
        "name": "Database Access Service",
        "description": "Provides database query capabilities",
        "endpoint": "http://localhost:8081",
        "capabilities": {
          "tools": ["query_db", "insert_record"],
          "resources": ["db://users", "db://products"]
        },
        "registered_at": "2023-10-01T10:00:00Z",
        "last_seen": "2023-10-01T12:00:00Z"
      }
    ],
    "total_count": 1
  }
}
```

### 3. Service Deregistration (`registry/unregister`)

Services can deregister themselves when shutting down:

```json
{
  "jsonrpc": "2.0",
  "id": "req-789",
  "method": "registry/unregister",
  "params": {
    "id": "service-unique-id"
  }
}
```

## Usage

### Basic Server (Default - Stdio Transport)

```bash
python -m mcp_server.server --transport stdio
```

### HTTP/SSE Transport

```bash
python -m mcp_server.server --transport http --host 127.0.0.1 --port 3030
```

### Registry Server

```bash
python -m mcp_server.server --transport http --port 3030 --enable-registry
```

### Auto-Registration with Registry

```bash
# Start a server that auto-registers with a registry
python -m mcp_server.server --transport http --port 3032 --register-with-registry --registry-host 127.0.0.1 --registry-port 3031

# Using startup script with auto-registration
./start_mcp_server.sh -R --registry-port 3031 --port 3032
```

### Command Line Options

- `--transport`: Select transport mechanism ('stdio' or 'http')
- `--host`: Host for HTTP transport (default: 127.0.0.1)
- `--port`: Port for HTTP transport (default: 3030)
- `--enable-registry`: Enable registry functionality to track multiple MCP services (optional)
- `--register-with-registry`: Register this server with a registry server (requires --registry-host and --registry-port)
- `--registry-host`: Registry server host to register with (default: 127.0.0.1)
- `--registry-port`: Registry server port to register with (default: 3031)

## Example Usage

### For Stdio Transport:
The server communicates via stdin/stdout as per MCP specification:
```bash
echo '{"jsonrpc": "2.0", "id": "1", "method": "initialize", "params": {"clientInfo": {"name": "test-client", "version": "1.0"}}}' | python -m mcp_server.server
```

### For HTTP/SSE Transport:
The server provides:
1. An SSE endpoint at `/sse` for server messages
2. An HTTP POST endpoint at `/send` for client messages

## Extending the Server

The server is designed to be easily extensible. See `example.py` for examples of:
- Adding custom tools, resources, and prompts
- Creating a registry server for service discovery
- Connecting to databases for persistent storage

## Registry Architecture

The registry functionality enables a distributed architecture:

1. **Registry Server** - Central server that tracks available services
2. **Service Servers** - Individual MCP servers that register their capabilities
3. **AI Agent** - Queries the registry to discover available services

This creates a service-oriented architecture where AI agents can intelligently route requests to the most appropriate server based on capabilities.

## Auto-Registration Feature

The server includes an auto-registration feature that allows servers to automatically register with a registry server upon startup:

### How Auto-Registration Works:
1. Server starts with `--register-with-registry` flag
2. Server contacts the specified registry server
3. Server sends its capabilities (tools, resources, prompts) to the registry
4. Registry stores the server information in its database
5. AI agents can discover the server through the registry

### Auto-Registration Example:
```bash
# Start a registry server
python -m mcp_server.server --transport http --port 3031 --enable-registry

# Start a server that auto-registers with the registry
python -m mcp_server.server --transport http --port 3032 --register-with-registry --registry-port 3031
```

### Service Discovery by AI Agents:
AI agents can discover available services by querying the registry:
```bash
curl -X POST http://localhost:3031/send \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "discover",
    "method": "registry/list",
    "params": {}
  }'
```

## Extending the Server

The MCP server skeleton is designed to be easily extensible. Here are various approaches to add additional functionality:

### 1. Custom Tools, Resources, and Prompts

Extend the server handlers to add custom functionality:

```python
from mcp_server.handlers.server_handlers import McpServerHandlers

class CustomMcpServerHandlers(McpServerHandlers):
    def __init__(self):
        super().__init__()
        
        # Add custom tools
        self.tools.extend([
            {
                "name": "custom_database_query",
                "description": "Execute custom database queries",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "SQL query to execute"}
                    },
                    "required": ["query"]
                }
            }
        ])
        
        # Add custom resources
        self.resources.extend([
            {
                "uri": "custom://database/config",
                "name": "Database Configuration",
                "description": "Database connection configuration"
            }
        ])
        
        # Add custom prompts
        self.prompts.extend([
            {
                "name": "sql_generation_prompt",
                "description": "Generate SQL queries from natural language",
                "arguments": [
                    {
                        "name": "natural_language",
                        "type": "string",
                        "description": "Natural language description of the query"
                    }
                ]
            }
        ])
    
    def handle_custom_database_query(self, params, request_id):
        """Handle custom database query tool"""
        query = params.get("query")
        # Execute query and return results
        return {"result": f"Executed query: {query}"}
```

### 2. Database Integration

Connect to external databases for persistent storage:

```python
import sqlite3
import psycopg2  # For PostgreSQL
from typing import Dict, Any

class DatabaseIntegration:
    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config
        self.connection = None
    
    def connect(self):
        """Establish database connection"""
        # Implementation depends on database type
        pass
    
    def execute_query(self, query: str, params=None):
        """Execute a database query"""
        # Implementation
        pass
```

### 3. Authentication and Authorization

Add security layers:

```python
from functools import wraps

def require_auth(func):
    """Decorator to require authentication"""
    @wraps(func)
    def wrapper(self, params, request_id):
        auth_token = params.get("auth_token")
        if not self.validate_token(auth_token):
            raise ValueError("Invalid or missing authentication token")
        return func(self, params, request_id)
    return wrapper

class SecureMcpServerHandlers(McpServerHandlers):
    def __init__(self):
        super().__init__()
        self.auth_tokens = set()  # Valid tokens
    
    def validate_token(self, token: str) -> bool:
        """Validate authentication token"""
        return token in self.auth_tokens
    
    @require_auth
    def handle_secure_tool(self, params, request_id):
        """Secure tool that requires authentication"""
        return {"result": "Secure operation completed"}
```

### 4. Caching Layer

Add caching for improved performance:

```python
import redis
from functools import lru_cache

class CachedMcpServerHandlers(McpServerHandlers):
    def __init__(self):
        super().__init__()
        self.cache = redis.Redis(host='localhost', port=6379, db=0)
    
    def handle_resource_read(self, params, request_id):
        """Override to add caching"""
        uri = params.get('uri')
        
        # Check cache first
        cached_content = self.cache.get(uri)
        if cached_content:
            return {"uri": uri, "contents": cached_content.decode()}
        
        # If not in cache, call parent method and cache result
        result = super().handle_resource_read(params, request_id)
        self.cache.setex(uri, 3600, str(result))  # Cache for 1 hour
        return result
```

### 5. Monitoring and Logging

Add comprehensive monitoring:

```python
import logging
from datetime import datetime

class MonitoredMcpServerHandlers(McpServerHandlers):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.metrics = {}
    
    def handle_tools_call(self, params, request_id):
        """Monitor tool calls"""
        start_time = datetime.now()
        tool_name = params.get('name')
        
        try:
            result = super().handle_tools_call(params, request_id)
            
            # Log successful call
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"Tool '{tool_name}' executed successfully in {duration}s")
            
            # Update metrics
            self.update_metrics(tool_name, duration, success=True)
            
            return result
        except Exception as e:
            # Log error
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Tool '{tool_name}' failed after {duration}s: {str(e)}")
            
            # Update metrics
            self.update_metrics(tool_name, duration, success=False)
            
            raise
    
    def update_metrics(self, tool_name, duration, success):
        """Update performance metrics"""
        if tool_name not in self.metrics:
            self.metrics[tool_name] = {
                "calls": 0,
                "errors": 0,
                "avg_duration": 0
            }
        
        stats = self.metrics[tool_name]
        stats["calls"] += 1
        if not success:
            stats["errors"] += 1
        stats["avg_duration"] = (
            (stats["avg_duration"] * (stats["calls"] - 1) + duration) / stats["calls"]
        )
```

### 6. Plugin System

Create a plugin architecture:

```python
from abc import ABC, abstractmethod
import importlib

class Plugin(ABC):
    @abstractmethod
    def get_tools(self) -> list:
        pass
    
    @abstractmethod
    def get_resources(self) -> list:
        pass
    
    @abstractmethod
    def handle_custom_method(self, params, request_id):
        pass

class PluginManager:
    def __init__(self):
        self.plugins = []
    
    def load_plugin(self, module_name: str):
        """Load a plugin from a module"""
        module = importlib.import_module(module_name)
        plugin_class = getattr(module, 'PluginImpl')  # Assuming PluginImpl is the class name
        plugin = plugin_class()
        self.plugins.append(plugin)
    
    def get_all_tools(self) -> list:
        """Aggregate tools from all plugins"""
        tools = []
        for plugin in self.plugins:
            tools.extend(plugin.get_tools())
        return tools
```

### 7. Event System

Add event-driven architecture:

```python
from typing import Callable, List
from dataclasses import dataclass
from enum import Enum

class EventType(Enum):
    TOOL_CALLED = "tool_called"
    RESOURCE_ACCESSED = "resource_accessed"
    CLIENT_CONNECTED = "client_connected"
    CLIENT_DISCONNECTED = "client_disconnected"

@dataclass
class Event:
    type: EventType
    data: dict
    timestamp: float

class EventEmitter:
    def __init__(self):
        self.listeners: dict[EventType, List[Callable]] = {}
    
    def on(self, event_type: EventType, callback: Callable):
        """Register an event listener"""
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)
    
    def emit(self, event: Event):
        """Emit an event to all listeners"""
        if event.type in self.listeners:
            for callback in self.listeners[event.type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Error in event listener: {e}")

class EventDrivenMcpServerHandlers(McpServerHandlers):
    def __init__(self):
        super().__init__()
        self.event_emitter = EventEmitter()
        
        # Register event handlers
        self.event_emitter.on(EventType.TOOL_CALLED, self.on_tool_called)
    
    def handle_tools_call(self, params, request_id):
        """Emit event when tool is called"""
        result = super().handle_tools_call(params, request_id)
        
        # Emit event
        event = Event(
            type=EventType.TOOL_CALLED,
            data={
                "tool_name": params.get("name"),
                "arguments": params.get("arguments", {}),
                "result": result
            },
            timestamp=datetime.now().timestamp()
        )
        self.event_emitter.emit(event)
        
        return result
    
    def on_tool_called(self, event: Event):
        """Handle tool called event"""
        print(f"Tool {event.data['tool_name']} was called")
```

### 8. Configuration Management

Add flexible configuration:

```python
import yaml
import json
from pathlib import Path

class ConfigManager:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config = self.load_config()
    
    def load_config(self):
        """Load configuration from file"""
        if self.config_path.exists():
            with open(self.config_path) as f:
                if self.config_path.suffix in ['.yaml', '.yml']:
                    return yaml.safe_load(f)
                else:
                    return json.load(f)
        return {}
    
    def get(self, key: str, default=None):
        """Get configuration value with dot notation"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value

# Usage in server
class ConfigurableMcpServer(McpServer):
    def __init__(self, config_path="config.yaml", **kwargs):
        self.config_manager = ConfigManager(config_path)
        
        # Override defaults with config values
        transport_type = self.config_manager.get("server.transport", kwargs.get("transport_type", "stdio"))
        host = self.config_manager.get("server.host", kwargs.get("host", "127.0.0.1"))
        port = self.config_manager.get("server.port", kwargs.get("port", 3030))
        
        super().__init__(transport_type=transport_type, host=host, port=port, **kwargs)
```

### 9. Health Checks and Diagnostics

Add system health monitoring:

```python
import psutil
import time
from datetime import datetime

class HealthCheckMixin:
    def __init__(self):
        self.start_time = time.time()
    
    def handle_health_check(self, params, request_id):
        """Provide system health information"""
        uptime = time.time() - self.start_time
        
        return {
            "status": "healthy",
            "uptime": uptime,
            "timestamp": datetime.now().isoformat(),
            "system_stats": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent,
                "active_connections": self.get_active_connections_count()
            }
        }
    
    def get_active_connections_count(self):
        """Get count of active connections"""
        # Implementation depends on transport
        return 0
```

## Best Practices for Extensions:

1. **Follow MCP Standards**: Always maintain compliance with MCP specification
2. **Modular Design**: Keep extensions modular and loosely coupled
3. **Error Handling**: Implement proper error handling and logging
4. **Performance**: Consider performance implications of new features
5. **Security**: Add authentication and authorization where needed
6. **Testing**: Write tests for new functionality
7. **Documentation**: Document new features and APIs

The skeleton is designed to be easily extensible while maintaining MCP compliance and following best practices for maintainable code.

## Code Reusability & Component Architecture

The MCP server is built with reusability in mind, allowing components to be leveraged when building additional servers:

### 1. **Reusable Components**

#### Transport Layer
- HTTP/stdio transport abstractions
- JSON-RPC request/response handling
- Error handling and validation utilities
- Request routing mechanisms

#### Database Abstraction Layer
- PostgreSQL connection management
- Connection pooling and reconnection logic
- Base database operations (CRUD)
- Error handling and transaction management

#### Registry System
- Service registration and discovery patterns
- Health check implementations
- Service metadata storage and retrieval
- Service lifecycle management

#### Configuration Management
- Command-line argument parsing
- Environment variable handling
- Configuration file loading
- Default value management

#### Logging & Debugging Infrastructure
- Comprehensive logging setup
- Debug mode configurations
- Structured logging patterns
- Performance monitoring hooks

#### Server Lifecycle Management
- Graceful startup/shutdown procedures
- Signal handling
- Resource cleanup routines
- Health check endpoints

### 2. **Reusability Patterns**

#### Modular Architecture
- Separate concerns into distinct modules
- Use dependency injection for flexibility
- Implement interfaces for easy swapping
- Follow SOLID principles

#### Template-Based Extension
- Use the current server as a template
- Extend specific classes with new functionality
- Override only necessary methods
- Maintain backward compatibility

#### Plugin Architecture
- Design for pluggable components
- Use hooks and callbacks for customization
- Implement middleware patterns
- Support dynamic module loading

### 3. **Extending for New Servers**

The architecture allows you to build new servers by:
- Inheriting from base server classes
- Reusing transport and database layers
- Extending registry functionality
- Leveraging existing configuration and logging
- Building on the proven error handling patterns

This makes the codebase a robust foundation for multiple server implementations with minimal duplication.

## Database Support

The MCP server includes support for multiple database backends:

### 1. SQLite (Default)
- **Built-in**: Used by default for registry functionality
- **File-based**: Stores data in `mcp_registry.db`
- **No configuration**: Ready to use out of the box
- **Use case**: Development, testing, lightweight deployments

### 2. PostgreSQL (Optional)
- **Production-ready**: Robust, scalable database solution
- **Configuration required**: Connection parameters needed
- **High availability**: Supports clustering and replication
- **Use case**: Production deployments, high-concurrency scenarios

**PostgreSQL Configuration:**
```bash
# Start registry server with PostgreSQL backend
./start_mcp_server.sh --port 3031 --enable-registry --use-postgres

# With custom PostgreSQL parameters
./start_mcp_server.sh --port 3031 --enable-registry --use-postgres \
  --postgres-host db.example.com --postgres-port 5432 \
  --postgres-db mcp_production --postgres-user mcp_user \
  --postgres-password secret123
```

**PostgreSQL Options:**
- `--use-postgres`: Enable PostgreSQL for registry storage instead of SQLite
- `--postgres-host`: PostgreSQL host (default: 127.0.0.1)
- `--postgres-port`: PostgreSQL port (default: 5432)
- `--postgres-db`: PostgreSQL database name (default: mcp_registry)
- `--postgres-user`: PostgreSQL username (default: postgres)
- `--postgres-password`: PostgreSQL password (default: empty)

### PostgreSQL Setup Requirements

When using PostgreSQL backend, ensure the following setup is completed:

#### 1. PostgreSQL Configuration
The server requires proper PostgreSQL authentication configuration:

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

#### 2. Database Creation
The server will automatically create the registry database and tables if they don't exist:
- Database: `mcp_registry` (by default)
- Table: `services` with columns for service ID, name, description, endpoint, capabilities, etc.

#### 3. Connection Parameters
- **Host**: Use `127.0.0.1` instead of `localhost` to avoid IPv6 resolution issues
- **Port**: Default is `5432`
- **Database**: Default is `mcp_registry`
- **User**: Default is `postgres`
- **Password**: Must match the password set in PostgreSQL

### Troubleshooting PostgreSQL Connections

If experiencing connection issues:

1. **Verify PostgreSQL service is running**:
   ```bash
   sudo systemctl status postgresql
   ```

2. **Test direct connection**:
   ```bash
   psql -h 127.0.0.1 -U postgres -d mcp_registry
   ```

3. **Check authentication configuration**:
   ```bash
   sudo cat /etc/postgresql/*/main/pg_hba.conf
   ```

4. **Verify user password is set**:
   ```bash
   sudo -u postgres psql -c "SELECT usename, passwd FROM pg_shadow WHERE usename = 'postgres';"
   ```

5. **Check server logs** for specific error messages about connection failures

## Startup and Testing Scripts

The MCP server includes several utility scripts to simplify startup, management, and testing:

### 1. Basic Startup Scripts

#### `start_mcp_server.sh` - Main Startup Script
The primary script for starting MCP servers with various configurations.

**Features:**
- Supports all server options (transport, host, port, registry, etc.)
- Validates inputs and provides helpful error messages
- Shows configuration summary before starting
- Supports both foreground and background operation
- Supports both SQLite and PostgreSQL backends

**Usage:**
```bash
# Start with defaults (HTTP on port 3030)
./start_mcp_server.sh

# Start registry server
./start_mcp_server.sh --port 3031 --enable-registry

# Start server that auto-registers with registry
./start_mcp_server.sh -R --registry-port 3031 --port 3032

# Start with custom host and port
./start_mcp_server.sh --host 0.0.0.0 --port 9000

# Start registry server with PostgreSQL backend
./start_mcp_server.sh --port 3031 --enable-registry --use-postgres

# Show help
./start_mcp_server.sh --help
```

**Options:**
- `--transport`: Transport type ('stdio' or 'http')
- `--host`: Host to bind to (default: 127.0.0.1)
- `--port`: Port to listen on (default: 3030)
- `--enable-registry`: Enable registry functionality
- `--register-with-registry`: Register with a registry server
- `--registry-host`: Registry host to register with
- `--registry-port`: Registry port to register with
- `--use-postgres`: Use PostgreSQL for registry storage instead of SQLite
- `--postgres-host`: PostgreSQL host (default: 127.0.0.1)
- `--postgres-port`: PostgreSQL port (default: 5432)
- `--postgres-db`: PostgreSQL database name (default: mcp_registry)
- `--postgres-user`: PostgreSQL username (default: postgres)
- `--postgres-password`: PostgreSQL password (default: empty)
- `--python`: Python command to use
- `--log-to-file`: Redirect all output to log file instead of console
- `--log-file`: Specify log file name (default: mcp_server_YYYYMMDD_HHMMSS.log)
- `--background`: Run server in background (implies --log-to-file)

#### `start_mcp_default.sh` - Simple Startup Script
A simplified script that starts the server with default settings.

**Usage:**
```bash
# Start with all defaults
./start_mcp_default.sh
```

**Features:**
- Starts HTTP transport on port 3030
- No registry functionality
- Minimal configuration options
- Good for quick testing

#### `start_registry_server.sh` - Registry Server Startup Script
A dedicated script for starting an MCP registry server with default settings optimized for registry functionality.

**Usage:**
```bash
# Start registry server on default port 3031
./start_registry_server.sh

# Start registry server on custom port
./start_registry_server.sh -p 4000

# Start registry server with PostgreSQL backend
./start_registry_server.sh --use-postgres

# Start registry server in background with logging
./start_registry_server.sh --background --log-file registry.log
```

**Features:**
- Starts HTTP transport on port 3031 (default registry port)
- Registry functionality enabled by default
- Optimized for registry server use cases
- Supports PostgreSQL backend
- Supports background operation and logging
- Includes PID file support for process management

#### Logging Options

Both startup scripts support comprehensive logging options:

**Console vs File Logging:**
- By default, servers output to console for real-time monitoring
- Use `--log-to-file` to redirect all output to a timestamped log file
- Use `--log-file filename.log` to specify a custom log file name
- Use `--background` to run the server in the background with automatic logging

**Examples:**
```bash
# Start with automatic timestamped log file
./start_mcp_server.sh --log-to-file

# Start with custom log file
./start_mcp_server.sh --log-file myserver.log

# Start in background (automatically logs to file)
./start_mcp_server.sh --background

# Start registry in background with custom log
./start_mcp_server.sh --background --log-file registry.log --port 3031 --enable-registry
```

**Log File Management:**
- Timestamped log files follow the format: `mcp_server_YYYYMMDD_HHMMSS.log`
- All stdout and stderr are captured in the log file
- Background processes automatically redirect output to prevent terminal detachment issues

#### `start_mcp_server_bg.sh` - Enhanced Background Startup Script
An advanced script with built-in background operation support.

**Features:**
- All features of the main startup script
- Built-in background operation (`-b` flag)
- Log file support (`-l` flag)
- PID file support (`--pid-file` flag)
- Input validation and error handling

**Usage:**
```bash
# Start in background
./start_mcp_server_bg.sh -b --port 3031 --enable-registry

# Start with logging
./start_mcp_server_bg.sh -b -l registry.log --port 3031 --enable-registry

# Start with PID file
./start_mcp_server_bg.sh -b --pid-file registry.pid --port 3031 --enable-registry
```

### 2. Testing Scripts

#### `test_registry_simple.sh` - Registry Verification Script
Tests the registry functionality and provides detailed output.

**Features:**
- Verifies registry server is running
- Shows server process information
- Explains HTTP/SSE transport behavior
- Provides example commands for interaction
- Color-coded output for readability

**Usage:**
```bash
# Run registry verification
./test_registry_simple.sh
```

#### `query_registry.sh` - Registry Query Test
Simulates how an AI agent would query the registry server using proper MCP protocol.

**Features:**
- Sends `registry/list` requests to registry via MCP protocol
- Parses service information from registry response
- Simulates AI agent discovery workflow
- Uses only MCP-compliant communication methods

**Usage:**
```bash
# Query registry as AI agent would
./query_registry.sh
```

#### `query_registry_client_proper.py` - Advanced Registry Client
Advanced Python client that properly implements the MCP HTTP/SSE protocol to query the registry.

**Features:**
- Opens SSE connection first, then sends requests (proper MCP pattern)
- Retrieves complete service information including capabilities
- Shows detailed service metadata (ID, name, endpoint, description)
- Supports querying specific services by ID (if supported by registry)
- Real-time response handling through SSE

**Usage:**
```bash
# Query all registered services
python query_registry_client_proper.py

# Query specific service by ID
python query_registry_client_proper.py --service-id "server-127.0.0.1-3030"

# Use custom registry URL and timeout
python query_registry_client_proper.py --registry-url "http://localhost:3031" --timeout 20
```

#### `query_registry_sse.sh` - Shell Wrapper for Registry Client
Shell script wrapper that provides a convenient interface to query the registry using the proper HTTP/SSE protocol.

**Features:**
- Simple shell interface to the Python registry client
- Proper MCP HTTP/SSE protocol implementation
- Automatic detection of Python client
- Configurable registry URL and timeout
- Complete service information display

**Usage:**
```bash
# Query all registered services
./query_registry_sse.sh

# Query with custom registry URL
./query_registry_sse.sh "http://localhost:3031"

# Query specific service (if registry supports it)
./query_registry_sse.sh "http://localhost:3031" "server-127.0.0.1-3030"

# Query with custom timeout
./query_registry_sse.sh "http://localhost:3031" "" 20
```

#### `ai_agent_workflow.sh` - Complete AI Agent Simulation
Runs a complete simulation of the AI agent service discovery workflow using MCP protocol calls.

**Features:**
- Complete 4-step workflow simulation
- Queries registry for services via MCP protocol
- Uses only MCP-compliant communication methods
- Shows service selection process based on capabilities
- Comprehensive verification via proper channels

**Usage:**
```bash
# Run complete AI agent workflow simulation
./ai_agent_workflow.sh
```

#### `test_auto_registration.sh` - Auto-Registration Test
Tests the auto-registration functionality.

**Features:**
- Starts registry and auto-registering servers
- Verifies registration process
- Tests server connectivity
- Cleans up processes automatically

**Usage:**
```bash
# Test auto-registration functionality
./test_auto_registration.sh
```

#### `test_registry.sh` - Advanced Registry Test
Comprehensive test of all registry functionality (if present).

**Features:**
- Tests registration, listing, and deregistration
- Verifies all registry methods
- Shows formatted output
- Tests filtering capabilities

#### `test_postgres_integration.sh` - PostgreSQL Integration Test
Tests the PostgreSQL database integration functionality.

**Features:**
- Verifies PostgreSQL connection
- Tests registry operations with PostgreSQL backend
- Validates data persistence in PostgreSQL
- Checks authentication and connection pooling

**Usage:**
```bash
# Test PostgreSQL integration
./test_postgres_integration.sh

# Test with specific PostgreSQL parameters
./test_postgres_integration.sh --postgres-host localhost --postgres-port 5432 --postgres-db mcp_registry
```

#### `final_verification.sh` - Complete System Verification
Performs a comprehensive verification of all MCP server functionality using MCP protocol calls.

**Features:**
- Tests all major components and integrations
- Verifies startup scripts functionality
- Validates registry and auto-registration via MCP protocol
- Checks service discovery functionality
- Runs complete workflow simulation
- Provides detailed verification report
- Uses only MCP-compliant communication methods

**Usage:**
```bash
# Run complete system verification
./final_verification.sh
```

### 3. Background Operation Methods

All startup scripts can be run in the background using various methods:

#### Standard Backgrounding
```bash
# Using & operator
./start_mcp_server.sh --port 3031 --enable-registry &
```

#### Using nohup for Persistence
```bash
# Persist after terminal closes
nohup ./start_mcp_server.sh --port 3031 --enable-registry > registry.log 2>&1 &
```

#### Using Screen or Tmux
```bash
# Using screen
screen -dmS mcp-registry ./start_mcp_server.sh --port 3031 --enable-registry

# Using tmux
tmux new-session -d -s mcp-registry './start_mcp_server.sh --port 3031 --enable-registry'
```

### 4. Process Management

#### Checking Running Processes
```bash
# Find MCP server processes
ps aux | grep "python -m mcp_server.server"
```

#### Killing Processes
```bash
# Kill all MCP server processes
pkill -f "python -m mcp_server.server"

# Kill specific process by PID
kill <PID>

# Kill using PID file
kill $(cat registry.pid)
```

### 5. Typical Usage Scenarios

#### Scenario 1: Development Setup
```bash
# Start registry server
./start_mcp_server.sh --port 3031 --enable-registry &

# Start service server that registers with registry
./start_mcp_server.sh -R --registry-port 3031 --port 3032 &

# Verify setup
./test_registry_simple.sh
```

#### Scenario 2: Production Deployment
```bash
# Start with logging and PID file
./start_mcp_server_bg.sh -b -l registry.log --pid-file registry.pid --port 3031 --enable-registry

# Monitor logs
tail -f registry.log
```

#### Scenario 3: Testing Auto-Registration
```bash
# Run complete test
./test_auto_registration.sh

# Or manual test
./start_mcp_server.sh --port 3031 --enable-registry &
sleep 3
./start_mcp_server.sh -R --registry-port 3031 --port 3032 &
sleep 5
./query_registry.sh
```

These scripts provide a complete toolkit for deploying, managing, and testing MCP servers with various configurations and use cases.