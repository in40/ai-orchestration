# MCP Server Registry - Usage Examples

This document provides practical examples of how to use the MCP Server Registry.

## Table of Contents
1. [Running the Registry Server](#running-the-registry-server)
2. [Registering an MCP Server](#registering-an-mcp-server)
3. [Discovering Registered Servers](#discovering-registered-servers)
4. [Searching for Specific Servers](#searching-for-specific-servers)
5. [Accessing Registry Resources](#accessing-registry-resources)

## Running the Registry Server

### Local Development (stdio transport)
```bash
python -m src.registry.main
```

### HTTP Transport
```bash
python -m src.registry.main --transport streamable-http --port 8080
```

### With Custom Configuration
```bash
# Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost/mcp_registry"
export HEALTH_CHECK_INTERVAL=30

python -m src.registry.main --transport streamable-http --port 8080
```

## Registering an MCP Server

Once the registry is running, other MCP servers can register themselves using the `registry_register_server` tool:

```python
from mcp.client import Client

# Connect to the registry (assuming it's available via stdio)
client = Client.connect_stdio()

# Register your server
result = client.call_tool("registry_register_server", {
    "name": "my-data-access-server",
    "description": "Server for accessing internal data sources",
    "endpoint": "http://localhost:9000",
    "capabilities": {
        "resources": True,
        "tools": True,
        "prompts": False,
        "roots": False,
        "sampling": False
    },
    "metadata": {
        "version": "1.0.0",
        "author": "Your Organization",
        "category": "data-access"
    },
    "tags": ["database", "sql", "internal"]
})

print(f"Registration result: {result}")
# Output: {'success': True, 'server_id': 'abc123...', 'message': 'Server \'my-data-access-server\' registered successfully...'}
```

## Discovering Registered Servers

Clients can discover all registered servers using the `registry_list_servers` tool:

```python
from mcp.client import Client

client = Client.connect_stdio()  # or appropriate transport

# List all registered servers
servers = client.call_tool("registry_list_servers", {})

for server in servers["servers"]:
    print(f"Server: {server['name']}")
    print(f"  ID: {server['id']}")
    print(f"  Endpoint: {server['endpoint']}")
    print(f"  Health: {server['health_status']}")
    print(f"  Capabilities: {server['capabilities']}")
    print(f"  Tags: {server['tags']}")
    print("---")
```

## Searching for Specific Servers

Use the `registry_search_servers` tool to find servers by name, description, or tags:

```python
from mcp.client import Client

client = Client.connect_stdio()

# Search for servers with "database" in name/description
database_servers = client.call_tool("registry_search_servers", {
    "query": "database"
})

# Search for servers with specific tags
sql_servers = client.call_tool("registry_search_servers", {
    "tags": ["sql", "database"]
})

# Combined search
combined_results = client.call_tool("registry_search_servers", {
    "query": "analytics",
    "tags": ["data", "warehouse"]
})

print(f"Found {len(combined_results['servers'])} analytics servers with data warehouse capabilities")
```

## Accessing Registry Resources

The registry exposes several resources that provide structured information:

### All Servers Resource
```python
from mcp.client import Client

client = Client.connect_stdio()

# Access the servers resource
servers_resource = client.read_resource("registry://servers")

print(f"Total servers: {servers_resource['total_count']}")
print(f"Fetched at: {servers_resource['fetched_at']}")

for server in servers_resource["servers"]:
    print(f"- {server['name']} ({server['health_status']})")
```

### Capabilities Summary Resource
```python
# Get collective capabilities of all servers
capabilities_resource = client.read_resource("registry://capabilities")

print("Collective capabilities:")
for capability, supported in capabilities_resource["collective_capabilities"].items():
    print(f"  {capability}: {'✓' if supported else '✗'}")

print(f"Total servers contributing capabilities: {capabilities_resource['server_count']}")
```

### Health Status Resource
```python
# Get health status summary
health_resource = client.read_resource("registry://health-status")

print(f"Health Summary:")
print(f"  Total: {health_resource['total_servers']}")
print(f"  Healthy: {health_resource['healthy']}")
print(f"  Unhealthy: {health_resource['unhealthy']}")
print(f"  Unknown: {health_resource['unknown']}")

for detail in health_resource["details"]:
    print(f"  {detail['name']}: {detail['status']}")
```

## Updating Server Status

Servers can update their health status if they detect issues:

```python
# Update server status (typically done automatically by the health monitor, 
# but can be called manually if needed)
result = client.call_tool("registry_update_server_status", {
    "server_id": "your-server-id",
    "health_status": "unhealthy"  # or "healthy", "unknown"
})

print(result)
```

## Complete Example: MCP Client Using Registry

Here's a complete example of an MCP client that uses the registry to find and connect to appropriate servers:

```python
from mcp.client import Client
import asyncio

class MCPClientWithRegistry:
    def __init__(self):
        # Connect to the registry
        self.registry_client = Client.connect_stdio()  # Adjust transport as needed
    
    async def find_and_use_database_server(self, query):
        """Find a database server and execute a query."""
        # Search for database servers
        db_servers = self.registry_client.call_tool("registry_search_servers", {
            "tags": ["database", "sql"],
            "query": "postgres"  # Look for PostgreSQL servers
        })
        
        if not db_servers["servers"]:
            raise Exception("No database servers found")
        
        # Pick the first healthy server
        target_server = None
        for server in db_servers["servers"]:
            if server["health_status"] == "healthy":
                target_server = server
                break
        
        if not target_server:
            raise Exception("No healthy database servers available")
        
        print(f"Using server: {target_server['name']} at {target_server['endpoint']}")
        
        # In a real implementation, you would now connect to the target server
        # and execute your query. This is just a conceptual example.
        return {
            "server_used": target_server["name"],
            "query_executed": query,
            "result": "Query result would go here"
        }

# Usage
async def main():
    client = MCPClientWithRegistry()
    result = await client.find_and_use_database_server("SELECT * FROM users LIMIT 10")
    print(result)

# asyncio.run(main())  # Uncomment to run
```

## Environment Variables

The registry can be configured using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://mcp_user:mcp_password@localhost/mcp_registry` | Database connection string |
| `REDIS_URL` | `redis://localhost:6379` | Redis URL for caching |
| `HTTP_HOST` | `0.0.0.0` | Host for HTTP transport |
| `HTTP_PORT` | `8080` | Port for HTTP transport |
| `LOG_LEVEL` | `INFO` | Logging level |
| `HEALTH_CHECK_INTERVAL` | `60` | Interval for health checks in seconds |
| `JWT_SECRET` | `dev-secret-change-in-production` | Secret for JWT tokens |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
| `MAX_REGISTRATION_ATTEMPTS` | `3` | Max attempts for server registration |
| `REGISTRATION_TIMEOUT` | `30` | Timeout for registration in seconds |

## Troubleshooting

### Common Issues

1. **Database Connection Errors**: Ensure PostgreSQL is running and accessible at the configured DATABASE_URL
2. **Server Registration Failures**: Check that the server endpoint is reachable and properly formatted
3. **Health Check Failures**: Verify that registered servers are actually running and accessible

### Debugging Tips

- Set `LOG_LEVEL=DEBUG` for more detailed logs
- Check the health status resource to see which servers are marked as unhealthy
- Verify that the registry server is accessible via the expected transport method