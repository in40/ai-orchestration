# MCP Server Registry

An MCP (Model Context Protocol) server registry that itself implements the MCP protocol, allowing LLM models to discover registered MCP servers through the standard MCP protocol.

## Overview

The MCP Server Registry is a centralized service that maintains a catalog of available MCP servers. It implements the MCP protocol itself, enabling LLM models and other clients to discover, query, and manage registered MCP servers using standard MCP primitives (tools, resources, and prompts).

## Features

- **MCP Protocol Compliance**: Implements the Model Context Protocol as both a client and server
- **Server Registration**: Allows MCP servers to register their capabilities and endpoints
- **Session Management**: Enforces session-based authentication for secure operations
- **Discovery Tools**: Provides tools for discovering registered servers by capabilities, tags, or search terms
- **Health Monitoring**: Automatically monitors the health status of registered servers
- **Rich Metadata**: Stores detailed information about registered servers including capabilities, metadata, and tags
- **Standardized Contract**: Implements OpenRPC specification for clear API contracts

## Architecture

The registry implements the following MCP primitives:

### HTTP Transport Endpoints
The registry supports HTTP transport for MCP protocol communication:

- **POST `/mcp`**: Handle MCP JSON-RPC requests over HTTP (STANDARD)
  - Accepts JSON-RPC 2.0 requests for all registry methods
  - Request format: `{"jsonrpc": "2.0", "method": "<method_name>", "params": {...}, "id": "<request_id>"}`
  - Response format: `{"jsonrpc": "2.0", "result": {...}, "id": "<request_id>"}` or `{"jsonrpc": "2.0", "error": {...}, "id": "<request_id>"}`
  - NOTE: Previously, `/rpc` was used as the endpoint, but this has been removed as it does not follow MCP standards. The `/mcp` endpoint follows the Model Context Protocol convention.

- **GET `/mcp`**: MCP Protocol Info Endpoint (STANDARD)
  - Provides information about the MCP server capabilities
  - Returns server information in JSON format
  - NOTE: The `/rpc` endpoint was previously used but has been removed as non-standard.

### Tools
- `registry/list_servers`: List all registered MCP servers
- `registry/get_server_details`: Get details for a specific server
- `registry/search_servers`: Search servers by name, description, or tags
- `registry/register_server`: Register a new MCP server
- `registry/update_server_status`: Update server health status
- `rpc.discover`: Return the OpenRPC schema for this service

### Resources
- `registry://servers`: Provides all registered servers in structured format
- `registry://capabilities`: Shows collective capabilities of all servers
- `registry://health-status`: Provides current health status summary

## Prerequisites

- Python 3.13+
- PostgreSQL 12+ with the following:
  - Database: `mcp_registry`
  - User: `mcp_user` with password `mcp_password`
  - Proper permissions granted to the user
- Redis (for caching, optional)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd mcp-jsonrpc-registry
   ```

2. Set up PostgreSQL database:
   
   **Option 1: Using the initialization script**
   ```bash
   # Make sure PostgreSQL server is running
   sudo systemctl start postgresql  # On Debian/Ubuntu systems
   
   # Run the database initialization script
   ./init_database.sh
   ```
   
   **Option 2: Manual setup**
   ```bash
   # Switch to postgres user and access PostgreSQL
   sudo -u postgres psql
   
   # In PostgreSQL prompt, run these commands:
   CREATE USER mcp_user WITH PASSWORD 'mcp_password';
   CREATE DATABASE mcp_registry OWNER mcp_user;
   GRANT ALL PRIVILEGES ON DATABASE mcp_registry TO mcp_user;
   \q  # Exit PostgreSQL prompt
   ```

3. Set up the virtual environment:
   
   **On Linux/Mac:**
   ```bash
   ./setup_env.sh
   ```
   
   **On Windows:**
   ```cmd
   setup_env.bat
   ```

   Or set up manually:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Linux/Mac
   # or
   venv\Scripts\activate     # On Windows
   
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

## Configuration

The registry can be configured using environment variables:

- `DATABASE_URL`: PostgreSQL database URL (default: `postgresql://mcp_user:mcp_password@localhost/mcp_registry`)
- `REDIS_URL`: Redis URL (default: `redis://localhost:6379`)
- `HTTP_HOST`: Host for HTTP transport (default: `0.0.0.0`)
- `HTTP_PORT`: Port for HTTP transport (default: `6000` as configured in .env)
- `LOG_LEVEL`: Logging level (default: `INFO`)
- `HEALTH_CHECK_INTERVAL`: Interval for health checks in seconds (default: `60`)
- `JWT_SECRET`: Secret for JWT tokens (default: `dev-secret-change-in-production`)
- `SESSION_TIMEOUT`: Session timeout in seconds (default: `3600`)
- `REQUIRE_SESSION_FOR_REGISTRATION`: Require session for registration (default: `true`)
- `REQUIRE_SESSION_FOR_UPDATES`: Require session for updates (default: `true`)

## Usage

### Running the Registry Server

For local development with stdio transport:
```bash
python -m src.registry.main
```

For HTTP transport:
```bash
python -m src.registry.main --transport streamable-http --port 6000
```

### Registering an MCP Server

MCP servers can register themselves with the registry using the `registry_register_server` tool:

```python
from mcp.client import Client

# Connect to the registry
client = Client.connect("stdio")  # or appropriate transport

# Register your server
result = client.call_tool("registry_register_server", {
    "name": "my-awesome-server",
    "description": "An awesome MCP server",
    "endpoint": "http://localhost:8000",
    "capabilities": {
        "resources": True,
        "tools": True,
        "prompts": False,
        "roots": False,
        "sampling": False
    },
    "metadata": {
        "version": "1.0.0",
        "author": "Your Name"
    },
    "tags": ["utility", "data-access"]
})
```

### Session Management

The registry enforces session-based authentication for secure operations. When connecting to the registry:

- Sessions are automatically established when connecting via supported transports
- Registration and update operations require valid session contexts
- Session timeouts are configurable (default: 1 hour)
- Invalid or expired sessions will result in authentication errors

### Discovering MCP Servers

Clients can discover registered servers using the registry tools:

```python
# List all servers
servers = client.call_tool("registry_list_servers", {})

# Search for servers with specific capabilities
results = client.call_tool("registry_search_servers", {
    "query": "database",
    "tags": ["database", "sql"]
})

# Get details for a specific server
details = client.call_tool("registry_get_server_details", {
    "server_id": "some-server-id"
})
```

## Complete Usage Examples

See [docs/usage_examples.md](docs/usage_examples.md) for comprehensive usage examples and advanced patterns.

## API Documentation

The registry implements the OpenRPC specification for MCP servers. See [docs/openrpc.yml](docs/openrpc.yml) for the complete API specification.

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black src/
```

### Type Checking

```bash
mypy src/
```

### Running the Development Server

```bash
# Activate the virtual environment first
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate     # On Windows

# Then run the server
python -m src.registry.main
```

Or use the convenience script to run the server directly:
```bash
# On Linux/Mac
source venv/bin/activate && python -m src.registry.main --transport streamable-http --port 6000

# On Windows
venv\Scripts\activate && python -m src.registry.main --transport streamable-http --port 6000
```

Or use the automated startup scripts:
```bash
# On Linux/Mac
./start_registry.sh

# On Windows
start_registry.bat
```

To stop the registry server:
```bash
# On Linux/Mac
./stop_registry.sh

# On Windows (just press Ctrl+C in the terminal where it's running)
```

## Project Structure

```
mcp-jsonrpc-registry/
├── src/
│   ├── registry/          # Main registry package
│   ├── server/            # MCP server implementation
│   ├── models/            # Data models
│   ├── services/          # Business logic services
│   └── utils/             # Utility functions
├── docs/                  # Documentation
│   ├── openrpc.yml        # API specification
│   └── usage_examples.md  # Usage examples
├── tests/                 # Test suite
├── config/                # Configuration
├── requirements.txt       # Dependencies
├── pyproject.toml         # Poetry configuration
└── README.md
```

## Database Schema

The registry uses PostgreSQL to store information about registered MCP servers. The following database objects are created automatically when the application starts:

### Database Requirements
- Database name: `mcp_registry`
- Database user: `mcp_user` with password `mcp_password`
- User permissions: Full access to the `mcp_registry` database

### Tables
- `registered_servers`: Stores information about registered MCP servers including name, description, endpoint, capabilities, metadata, registration timestamp, last seen timestamp, health status, and tags.

### Automatic Setup
When the registry server starts, it will automatically create the required tables if they don't exist.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Update documentation as needed
6. Submit a pull request

## License

MIT