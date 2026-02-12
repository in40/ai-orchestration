# MCP Resource Expansion Scripts

This directory contains shell scripts to expand and view detailed information from MCP service resources.

## Available Scripts

### 1. expand_resources.sh
Basic resource expansion script that allows expanding individual resources or multiple resources separately.

**Usage:**
```bash
# List all resources from a service
./expand_resources.sh <service_endpoint> list

# Expand a single resource
./expand_resources.sh <service_endpoint> expand <resource_uri>

# Expand multiple resources (creates separate SSE connections for each)
./expand_resources.sh <service_endpoint> expand-all "resource1,resource2,resource3"
```

**Examples:**
```bash
# List resources from coding agent service
./expand_resources.sh http://127.0.0.1:3050 list

# Expand capabilities resource
./expand_resources.sh http://127.0.0.1:3050 expand "coding-agent://capabilities"

# Expand multiple resources
./expand_resources.sh http://127.0.0.1:3050 expand-all "coding-agent://capabilities,coding-agent://status"
```

### 2. comprehensive_expand_resources.sh
More efficient resource expansion script that uses a single SSE connection for multiple resource requests.

**Usage:**
```bash
# List all resources from a service
./comprehensive_expand_resources.sh <service_endpoint> list

# Expand a single resource
./comprehensive_expand_resources.sh <service_endpoint> expand <resource_uri>

# Expand multiple specific resources using single SSE connection
./comprehensive_expand_resources.sh <service_endpoint> expand-all "resource1,resource2,resource3"

# Expand ALL resources available from a service
./comprehensive_expand_resources.sh <service_endpoint> expand-all-from-service
```

**Examples:**
```bash
# List resources from coding agent service
./comprehensive_expand_resources.sh http://127.0.0.1:3050 list

# Expand all resources from the coding agent service
./comprehensive_expand_resources.sh http://127.0.0.1:3050 expand-all-from-service

# Expand specific resources from DNS service
./comprehensive_expand_resources.sh http://127.0.0.1:3040 expand "dns://resolver/configuration"
```

## How It Works

Both scripts use the underlying Python clients to:
1. Establish an SSE (Server-Sent Events) connection to the target service
2. Send resource requests via the HTTP transport
3. Receive responses through the SSE connection
4. Format and display the resource content

The comprehensive script is more efficient as it reuses the same SSE connection for multiple requests, reducing connection overhead.

## Common Resource URIs

Based on the registry, common resources include:
- `coding-agent://capabilities` - AI coding agent capabilities
- `coding-agent://status` - Current service status
- `coding-agent://health` - Health check information
- `dns://resolver/configuration` - DNS resolver configuration

## Dependencies

- Python 3.x
- requests library (should be installed via requirements.txt)

## Troubleshooting

- Ensure the target service is running and accessible
- Check that the resource URI is correct
- If a resource fails to expand, try expanding it individually
- Increase timeout in the Python scripts if needed for slow responses