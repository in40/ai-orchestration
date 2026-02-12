# DNS Resolving MCP Server

This is a specialized Model Context Protocol (MCP) server that provides DNS resolution capabilities. It extends the standard MCP server skeleton to offer DNS-specific tools and functionality.

## Features

- **DNS Resolution**: Resolve various DNS record types (A, AAAA, CNAME, MX, etc.)
- **Reverse DNS Lookup**: Perform reverse DNS lookups for IP addresses
- **Domain Availability Check**: Check if domains are available/resolvable
- **Health Check**: Built-in health check endpoint
- **Registry Integration**: Optional service registry functionality
- **MCP Compliance**: Fully compliant with MCP specification

## Architecture

- **DnsResolvingMcpServer**: Main server class extending McpServer
- **DnsServerHandlers**: Custom handlers for DNS-specific functionality
- **HTTP/SSE Transport**: Communication layer following MCP specification
- **dnspython**: Core DNS resolution engine

## Tools Available

1. **dns_resolve**: Resolve DNS records for a given domain
   - Parameters: `domain` (required), `record_type` (optional, default: "A")
   
2. **dns_reverse_lookup**: Perform reverse DNS lookup for an IP address
   - Parameters: `ip_address` (required)
   
3. **dns_check_domain_availability**: Check if a domain is available
   - Parameters: `domain` (required)

## Usage

### Starting the Server

```bash
# Using the startup script
./start_dns_server.sh --port 3040

# Or directly with Python
python dns_mcp_server.py --transport http --port 3040
```

### With Registry Integration

```bash
# Start registry server
python dns_mcp_server.py --transport http --port 3031 --enable-registry

# Start DNS server and register with registry
python dns_mcp_server.py --transport http --port 3040 --register-with-registry --registry-port 3031
```

### Making Requests

The server accepts MCP-compliant JSON-RPC 2.0 requests:

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "tools/call",
  "params": {
    "name": "dns_resolve",
    "arguments": {
      "domain": "google.com",
      "record_type": "A"
    }
  }
}
```

## Configuration

The server supports various configuration options:
- Transport type (stdio or http)
- Host and port
- Registry integration
- PostgreSQL support for registry (optional)

## Dependencies

- Python 3.9+
- fastapi
- uvicorn
- sse-starlette
- pydantic
- dnspython
- typing-extensions
- requests
- psycopg2-binary

## Testing

The repository includes:
- AI agent simulation tests
- Comprehensive functionality tests
- Registry integration tests

Run tests with:
```bash
python test_dns_server_full.py
./test_dns_ai_agent_simulation.sh
```

## MCP Compliance

This server fully complies with the MCP specification:
- Implements all required server methods
- Supports both stdio and HTTP/SSE transports
- Follows proper JSON-RPC 2.0 messaging patterns
- Supports service registry functionality