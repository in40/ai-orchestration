# DevOps Release Engineer MCP Server

An AI agent serving as a DevOps Release Engineer for software delivery pipelines, handling CI/CD configuration, infrastructure provisioning, deployment orchestration, and build optimization.

## Overview

The DevOps Release Engineer MCP Server is an AI-powered agent that acts as a specialized DevOps engineer for software development teams. It accepts DevOps tasks via MCP (Model Context Protocol) endpoints and provides expert-level assistance with CI/CD pipelines, infrastructure provisioning, deployment orchestration, and build optimization.

## Features

- **CI/CD Pipeline Configuration**: Configure and maintain CI/CD pipelines for various platforms (GitHub Actions, GitLab CI, Jenkins)
- **Infrastructure Provisioning**: Manage infrastructure using Infrastructure as Code (Terraform, CloudFormation)
- **Deployment Orchestration**: Orchestrate deployments across environments (dev, staging, prod) with blue-green, rolling, and canary strategies
- **Deployment Health Monitoring**: Monitor deployment health and perform automatic rollbacks on failures
- **Build Optimization**: Optimize build times and resource utilization
- **Git Operations**: Handle Git commit and push operations
- **LLM Integration**: Integrated with LM Studio for AI-powered decision making
- **Registry Integration**: Automatically registers with MCP registry for service discovery

## Prerequisites

- Python 3.7+
- LM Studio with qwen3-coder-next model running at http://192.168.51.237:1234/v1/chat/completions
- MCP Registry server running on localhost:3031 (optional, for service discovery)

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

The server can be configured via command-line arguments:

- `--port`: Port to run the server on (default: 3071)
- `--llm-provider-url`: URL for the LLM provider (default: http://192.168.51.237:1234/v1/chat/completions)
- `--llm-model`: LLM model name (default: qwen3-coder-next@q5_k_xl)
- `--registry-host`: Registry server host (default: 127.0.0.1)
- `--registry-port`: Registry server port (default: 3031)

## Usage

### Starting the Server

Use the provided startup script:

```bash
./start_devops_release_engineer_server.sh --port 3071
```

### Available Tools

The DevOps Release Engineer server provides the following tools:

1. **git_commit_and_push**: Perform Git commit and push operations for code changes
2. **configure_ci_cd_pipeline**: Configure and maintain CI/CD pipelines for automated software delivery
3. **manage_infrastructure_provisioning**: Manage infrastructure provisioning using Infrastructure as Code (IaC)
4. **orchestrate_deployments**: Orchestrate deployments across different environments
5. **monitor_deployment_health**: Monitor deployment health and perform rollbacks on failures
6. **optimize_build_processes**: Optimize build times and resource utilization
7. **generate_terraform_config**: Generate Terraform configuration files for infrastructure provisioning
8. **generate_pipeline_config**: Generate CI/CD pipeline configuration for various platforms

### Available Resources

1. **devops://resource/deployment-status**: Current deployment status across all environments
2. **devops://resource/build-metrics**: Build performance metrics and statistics
3. **devops://resource/infrastructure-status**: Current infrastructure provisioning status
4. **devops://resource/deployment-history**: Historical deployment records with status and timestamps

### Available Prompts

1. **deployment_prompt**: Prompt for orchestrating deployments with LLM assistance
2. **pipeline_config_prompt**: Prompt for generating CI/CD pipeline configurations
3. **infrastructure_prompt**: Prompt for generating infrastructure provisioning configurations

## MCP Protocol Compliance

This server fully complies with the Model Context Protocol (MCP) specification:

- STDIO Transport: Standard input/output stream communication
- Streamable HTTP Transport: Modern single `/mcp` endpoint supporting both POST and GET methods
- Legacy HTTP/SSE Transport: Backward-compatible `/sse` and `/message` endpoints

## Registry Integration

The server automatically registers with the MCP registry server at startup and maintains its registration through periodic heartbeats. This enables service discovery by other MCP clients and servers.

## Architecture

The server follows a modular architecture with clear separation of concerns:

- **Transports**: Handle communication via stdio, HTTP/SSE, or Streamable HTTP
- **Handlers**: Process MCP requests and responses
- **Utils**: Provide common functionality like JSON-RPC handling and notifications
- **Registry**: Manage service registration and discovery

## Project Structure

```
devops-release-engineer-mcp-server/
├── devops_release_engineer_mcp_server/
│   ├── __init__.py
│   ├── server.py                  # Main server implementation
│   ├── client.py                  # MCP client implementation
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── server_handlers.py     # DevOps Release Engineer handlers
│   │   └── client_handlers.py     # Client handlers
│   ├── transports/
│   │   ├── __init__.py
│   │   ├── stdio.py               # STDIO transport
│   │   ├── http_sse.py            # Legacy HTTP/SSE transport
│   │   ├── streamable_http.py     # Streamable HTTP transport
│   │   ├── client_stdio.py        # Client stdio transport
│   │   ├── client_http_sse.py     # Client HTTP/SSE transport
│   │   └── client_streamable_http.py  # Client streamable HTTP
│   └── utils/
│       ├── __init__.py
│       ├── json_rpc.py            # JSON-RPC handler
│       ├── notifications.py       # Notification manager
│       ├── heartbeat_manager.py   # Heartbeat management
│       ├── service_registry_db.py # SQLite registry
│       └── postgres_registry_db.py # PostgreSQL registry
├── venv/                          # Python virtual environment
├── start_devops_release_engineer_server.sh  # Start script
├── stop_devops_release_engineer_server.sh   # Stop script
├── test_devops_release_engineer_simulation.sh  # Test script
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

## Development

### Running Tests

```bash
source venv/bin/activate
bash test_devops_release_engineer_simulation.sh
```

### Development Server

```bash
source venv/bin/activate
python devops_release_engineer_mcp_server/server.py --port 3071 --llm-provider-url http://192.168.51.237:1234/v1/chat/completions --llm-model qwen3-coder-next@q5_k_xl
```

##停止 Server

```bash
./stop_devops_release_engineer_server.sh --port 3071
```

## License

MIT License

## Author

DevOps Release Engineer MCP Server Implementation
