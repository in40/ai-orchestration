# DevOps Release Engineer MCP Server - Technology Rules and Implementation Scenarios

## Overview

This document captures the technology rules, implementation patterns, and scenarios used for the DevOps Release Engineer MCP Server implementation.

## Technology Stack

### Core Framework
- **Python 3.7+** - Primary programming language
- **FastAPI** - Web framework for HTTP transport
- **Uvicorn** - ASGI server for FastAPI
- **SSE Starlette** - Server-Sent Events support
- **Requests** - HTTP client for LLM API integration

### Communication Protocol
- **MCP (Model Context Protocol)** - Standard protocol for AI agent communication
- **Streamable HTTP Transport** - Default transport with bidirectional `/mcp` endpoint
- **JSON-RPC 2.0** - Message format for all communications

### External Services
- **LM Studio** - Local LLM provider
- **LLM Model**: `qwen3-coder-next@q5_k_xl`
- **LLM URL**: `http://192.168.51.237:1234/v1/chat/completions`

### Database (Optional)
- **PostgreSQL** - Production database for service registry
- **SQLite** - Development database for service registry

## Implementation Rules

### 1. MCP Protocol Compliance
- All implementations must fully comply with MCP specification v2024-11-05
- Support Streamable HTTP transport as default
- Support stdio and legacy HTTP/SSE transports for compatibility
- Implement all standard MCP methods: `initialize`, `tools/list`, `tools/call`, `resources/list`, `resources/read`, `prompts/list`, `prompts/get`, `shutdown`, `ping`

### 2. Tool Naming Convention
- Use snake_case for tool names (e.g., `git_commit_and_push`)
- Use descriptive names that clearly indicate the tool's purpose
- Follow domain-specific naming patterns for consistency

### 3. Input Validation
- Define `inputSchema` for all tools with proper types
- Mark required fields explicitly in the schema
- Provide sensible defaults where applicable

### 4. LLM Integration
- All DevOps tools leverage LLM via HTTP API calls to LM Studio
- System prompt establishes the DevOps Release Engineer persona
- User prompt contains tool name and arguments
- Results returned as structured JSON with tool name and original arguments

### 5. Server Configuration
- Port 3071 is reserved for DevOps Release Engineer server
- Auto-registration with MCP registry at `localhost:3031`
- Client mode enabled by default for cross-server task delegation
- PostgreSQL support for production deployments

## DevOps Release Engineer Tool Categories

### 1. Git Operations
- **`git_commit_and_push`** - Git commit and push operations
- **Input**: Repository path, files to commit, commit message
- **Output**: LLM-generated commit verification and suggestions

### 2. CI/CD Pipeline Management
- **`configure_ci_cd_pipeline`** - Configure and maintain CI/CD pipelines
- **Input**: Source repository, target platform, build requirements, deployment targets
- **Output**: Complete pipeline configuration (GitHub Actions, GitLab CI, Jenkins)

### 3. Infrastructure as Code
- **`manage_infrastructure_provisioning`** - Manage IaC provisioning
- **Input**: Infrastructure requirements, target platform, IaC tool
- **Output**: Complete IaC templates (Terraform, CloudFormation)

### 4. Deployment Orchestration
- **`orchestrate_deployments`** - Orchestrate deployments across environments
- **Input**: Application artifacts, target environments, deployment strategy
- **Output**: Complete deployment plan with rollback procedures

### 5. Deployment Monitoring
- **`monitor_deployment_health`** - Monitor deployment health and trigger rollbacks
- **Input**: Deployed application, target environment, health metrics
- **Output**: Health monitoring plan with threshold configurations

### 6. Build Optimization
- **`optimize_build_processes`** - Optimize build times and resource utilization
- **Input**: Build configuration, build metrics, optimization goals
- **Output**: Optimization recommendations and configurations

### 7. Template Generation
- **`generate_terraform_config`** - Generate Terraform configurations
- **`generate_pipeline_config`** - Generate CI/CD pipeline configurations

## Resource URIs

| URI | Description |
|-----|-------------|
| `devops://resource/deployment-status` | Current deployment status across all environments |
| `devops://resource/build-metrics` | Build performance metrics and statistics |
| `devops://resource/infrastructure-status` | Current infrastructure provisioning status |
| `devops://resource/deployment-history` | Historical deployment records with timestamps |

## Prompt Templates

| Prompt Name | Description |
|-------------|-------------|
| `deployment_prompt` | For orchestrating deployments with LLM assistance |
| `pipeline_config_prompt` | For generating CI/CD pipeline configurations |
| `infrastructure_prompt` | For generating infrastructure provisioning configurations |

## Communication with Other Agents

### With IT Lead Agent
- Receives deployment tasks via `orchestrate_deployments`
- Provides deployment status updates via resources
- Handles Git operations via `git_commit_and_push`

### With Implementation Engineers
- Coordinates artifact deployment via `orchestrate_deployments`
- Manages Git operations via `git_commit_and_push`

### With QA/Test Engineers
- Coordinates deployment timing via `monitor_deployment_health`
- Provides deployment health information

### With Security Engineers
- Ensures security in deployment via tool arguments
- Provides security configurations

### With Human Stakeholders
- Reports deployment health via resources
- Provides optimization metrics

## Testing Strategy

### Unit Tests
- Verify tool schemas are correctly defined
- Test MCP protocol compliance
- Validate input/output handling

### Integration Tests
- Test server startup and registration
- Verify LLM API integration
- Test cross-server communication

### Simulation Tests
- Run full agent workflow simulations
- Test error handling and recovery
- Verify registry integration

## Deployment Scenarios

### Development
- Use SQLite for registry (no configuration required)
- Run server on default port 3071
- Client mode enabled for testing

### Production
- Use PostgreSQL for registry
- Configure appropriate concurrency limits
- Set up proper logging and monitoring

### High Availability
- Deploy multiple instances behind load balancer
- Use external PostgreSQL for shared registry
- Implement health checks and auto-recovery

## Security Considerations

### Network Security
- Use HTTPS for external API calls
- Validate Origin headers for HTTP transports
- Implement rate limiting for production

### Authentication
- LLM API uses local network access (no auth required)
- PostgreSQL requires password authentication
- Consider API keys for external access

### Data Security
- LLM prompts may contain sensitive code
- Consider encryption for sensitive data
- Implement access controls for production

## Monitoring and Logging

### Health Endpoints
- `ping` - Returns server status and timestamp
- `registry/list` - Shows all registered services

### Metrics
- Request count and latency
- Concurrency levels
- Failed requests

## Future Enhancements

### Planned Features
1. Pipeline caching strategies
2. Multi-cloud deployment support
3. Kubernetes-native deployment tools
4. Advanced rollback scenarios
5. Cost optimization recommendations

### Potential Integrations
1. GitHub/GitLab API for repo management
2. Docker Hub/ECR for image management
3. Prometheus/Grafana for metrics
4. Slack/Teams for notifications

## Implementation Checklist

- [x] Clone and extend MCP skeleton
- [x] Implement DevOps-specific tools
- [x] Add custom resources and prompts
- [x] Configure LLM integration
- [x] Set up port 3071
- [x] Register with MCP registry
- [x] Create startup scripts
- [x] Create stop scripts
- [x] Write simulation tests
- [x] Document implementation scenarios
- [x] Configure PostgreSQL support
- [x] Test server registration
- [x] Verify LLM integration

## References

- [MCP Specification](https://modelcontextprotocol.io/specification)
- [LM Studio API Documentation](https://lmstudio.ai/docs)
- [Terraform Documentation](https://developer.hashicorp.com/terraform/docs)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
