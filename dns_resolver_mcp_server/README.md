# DNS Resolver MCP Server

This is an MCP (Model Context Protocol) server that provides DNS resolution services. It allows clients to resolve hostnames to IP addresses and vice versa through the MCP protocol.

## Features

- Resolve hostnames to IP addresses (forward DNS lookup)
- Resolve IP addresses to hostnames (reverse DNS lookup)
- Support for multiple DNS record types (A, AAAA, CNAME, MX, NS, TXT, PTR, SRV, SOA, ANY)
- Check domain availability
- Health monitoring and reporting

## Installation

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Running the Server

```bash
# Run with HTTP transport
python -m dns_resolver_server.src.main --transport http --port 8080

# Run with stdio transport (default)
python -m dns_resolver_server.src.main
```

### Using the Startup Scripts

The server includes convenient startup scripts:

```bash
# Start the server (logs will be shown after startup)
./start_server.sh

# Start the server and tail logs continuously
./start_server.sh --tail-logs
# or
./start_server.sh -t
```

### Viewing Server Logs

The server writes logs to files in the project directory:
- HTTP transport: `dns_resolver_server_http.log`
- Stdio transport: `dns_resolver_server_stdio.log`

To view recent logs after startup:
```bash
tail -n 20 dns_resolver_server_http.log
```

To continuously monitor logs:
```bash
tail -f dns_resolver_server_http.log
```

### Configuration

The server can be configured using command-line arguments or environment variables:

| Command-line Argument | Environment Variable | Default | Description |
|----------------------|---------------------|---------|-------------|
| `--transport` | `MCP_TRANSPORT` | `stdio` | Transport method (`stdio` or `http`) |
| `--host` | `MCP_HOST` | `0.0.0.0` | Host for HTTP transport |
| `--port` | `MCP_PORT` | `8080` | Port for HTTP transport |
| `--log-level` | `MCP_LOG_LEVEL` | `INFO` | Logging level |
| `--registry-endpoint` | `MCP_REGISTRY_ENDPOINT` | `stdio://` | Registry endpoint to register with |

## API

The server exposes the following tools via the MCP protocol:

### `resolve_dns`

Resolve a hostname to IP address or vice versa.

**Parameters:**
- `hostname` (optional): Hostname to resolve to IP address
- `ip_address` (optional): IP address to resolve to hostname (reverse lookup)
- `record_type` (optional): DNS record type to query (default: "A")

**Example:**
```json
{
  "name": "resolve_dns",
  "arguments": {
    "hostname": "example.com",
    "record_type": "A"
  }
}
```

### `check_domain_availability`

Check if a domain is available by attempting to resolve it.

**Parameters:**
- `domain`: Domain name to check for availability

**Example:**
```json
{
  "name": "check_domain_availability",
  "arguments": {
    "domain": "mydomain.com"
  }
}
```

## Health Checks

The server exposes a health check endpoint at `/health` when running in HTTP mode:

```bash
curl http://localhost:8080/health
```

## Architecture

The DNS Resolver MCP Server extends the BaseMCPServer class and implements:

- Tool definitions for DNS resolution operations
- HTTP transport with JSON-RPC 2.0 endpoint
- Health monitoring and reporting
- Registry integration for service discovery