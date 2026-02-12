# MCP Resource Expansion Guide

This guide explains how to expand and view detailed information from MCP service resources.

## Available Scripts

### 1. Basic Resource Expansion
- **Script**: `expand_resources.sh`
- **Purpose**: Expand individual resources or multiple resources separately
- **Usage**:
  ```bash
  # List all resources from a service
  ./expand_resources.sh http://localhost:3030 list
  
  # Expand a single resource
  ./expand_resources.sh http://localhost:3030 expand "coding-agent://capabilities"
  
  # Expand multiple resources (creates separate SSE connections)
  ./expand_resources.sh http://localhost:3030 expand-all "resource1,resource2,resource3"
  ```

### 2. Comprehensive Resource Expansion
- **Script**: `comprehensive_expand_resources.sh`
- **Purpose**: More efficient resource expansion using a single SSE connection
- **Usage**:
  ```bash
  # List all resources from a service
  ./comprehensive_expand_resources.sh http://localhost:3030 list
  
  # Expand a single resource
  ./comprehensive_expand_resources.sh http://localhost:3030 expand "coding-agent://capabilities"
  
  # Expand multiple specific resources using single SSE connection
  ./comprehensive_expand_resources.sh http://localhost:3030 expand-all "resource1,resource2,resource3"
  
  # Expand ALL resources available from a service
  ./comprehensive_expand_resources.sh http://localhost:3030 expand-all-from-service
  ```

## Example: Expanding Coding Agent Resources

From the registry, we know that the coding agent service at `http://127.0.0.1:3050` has these resources:
- `coding-agent://capabilities` - Information about the agent's capabilities
- `coding-agent://status` - Current status of the service
- `coding-agent://health` - Health check information

### To expand all coding agent resources:
```bash
./comprehensive_expand_resources.sh http://127.0.0.1:3050 expand-all "coding-agent://capabilities,coding-agent://status,coding-agent://health"
```

### To expand all resources from the service:
```bash
./comprehensive_expand_resources.sh http://127.0.0.1:3050 expand-all-from-service
```

## Example: Expanding DNS Service Resources

The DNS service at `http://127.0.0.1:3040` has:
- `dns://resolver/configuration` - DNS resolver configuration details

### To expand the DNS configuration:
```bash
./comprehensive_expand_resources.sh http://127.0.0.1:3040 expand "dns://resolver/configuration"
```

## Understanding the Output

Resource contents are typically returned as JSON strings. For example, the capabilities resource contains:
- Name and version of the service
- Available capabilities/tools
- Supported languages
- Description

The status and health resources contain:
- Online/offline status
- Model information
- LLM endpoint details
- Timestamps

## Troubleshooting

- If a resource fails to expand, try expanding it individually
- Ensure the target service is running and accessible
- Check that the resource URI is correct
- Increase timeout if needed: modify the --timeout parameter in the Python scripts