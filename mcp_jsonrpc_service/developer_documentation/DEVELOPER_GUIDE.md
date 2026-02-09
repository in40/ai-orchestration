# MCP Server Development Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Architecture Overview](#architecture-overview)
3. [Development Environment Setup](#development-environment-setup)
4. [Project Structure](#project-structure)
5. [Core Concepts](#core-concepts)
6. [Implementation Guidelines](#implementation-guidelines)
7. [Testing Strategy](#testing-strategy)
8. [Deployment Guidelines](#deployment-guidelines)
9. [Security Best Practices](#security-best-practices)
10. [Performance Considerations](#performance-considerations)
11. [Troubleshooting](#troubleshooting)
12. [Versioning and Release Process](#versioning-and-release-process)

## Introduction

This document serves as a comprehensive guide for developers working on MCP (Model Context Protocol) servers. It covers everything from initial setup to advanced implementation patterns, ensuring consistency and quality across all MCP server implementations.

The Model Context Protocol (MCP) enables AI systems to securely access external tools, resources, and prompts. This guide will help you build robust, scalable, and compliant MCP servers that integrate seamlessly with the broader ecosystem.

## Architecture Overview

### High-Level Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   AI System     │◄──►│   MCP Server     │◄──►│ External Systems│
│                 │    │                  │    │                 │
│ (LSP, IDE, etc.)│    │ • Transport Layer│    │ • Databases     │
│                 │    │ • Protocol Layer │    │ • APIs          │
│                 │    │ • Business Logic │    │ • Files         │
└─────────────────┘    │ • Security Layer │    │ • Services      │
                       └──────────────────┘    └─────────────────┘
                                │
                       ┌──────────────────┐
                       │   MCP Registry   │
                       │ • Discovery      │
                       │ • Health Checks  │
                       │ • Monitoring     │
                       └──────────────────┘
```

### Component Layers
1. **Transport Layer**: Handles communication protocols (stdio, HTTP, WebSocket)
2. **Protocol Layer**: Implements MCP specification and JSON-RPC 2.0
3. **Business Logic Layer**: Core functionality and domain logic
4. **Integration Layer**: Connects to external systems and services
5. **Security Layer**: Authentication, authorization, and validation
6. **Monitoring Layer**: Health checks, metrics, and logging

## Development Environment Setup

### Prerequisites
- Python 3.9 or higher
- pip package manager
- Git version control
- Docker (optional, for containerized deployments)
- Virtual environment tool (venv or conda)

### Initial Setup
```bash
# Clone the repository
git clone <repository-url>
cd <project-name>

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Recommended IDE Extensions
- Python extension for VS Code
- Black formatter
- Flake8 linter
- Pylint
- GitLens (for Git integration)

### Development Dependencies
```bash
# Install development tools
pip install pytest pytest-asyncio pytest-cov black flake8 mypy pre-commit
```

## Project Structure

The standard MCP server project follows this structure:

```
project-root/
├── src/
│   ├── __init__.py
│   ├── main.py                 # Entry point
│   ├── server.py               # Core server implementation
│   ├── config.py               # Configuration management
│   ├── errors.py               # Error handling
│   ├── registry_client.py      # Registry interaction
│   └── extensions/             # Server extensions
│       ├── __init__.py
│       └── base_extension.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Pytest configuration
│   ├── test_base_mcp_server.py # Core functionality tests
│   └── integration/            # Integration tests
├── docs/                       # Documentation
├── developer_documentation/    # Developer guidelines
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development dependencies
├── pyproject.toml            # Package configuration
├── README.md                 # Project overview
├── USAGE_EXAMPLES.md         # Usage examples
├── .gitignore               # Git ignore patterns
├── .pre-commit-config.yaml  # Pre-commit hooks
├── .env.example             # Environment variable template
└── Dockerfile               # Container configuration (optional)
```

## Core Concepts

### MCP Protocol Fundamentals
The Model Context Protocol defines standardized ways for AI systems to interact with external tools and resources. Key concepts include:

- **Tools**: Callable functions that perform specific actions
- **Resources**: Accessible data that can be read or monitored
- **Prompts**: Templates for generating AI instructions
- **Connections**: Persistent connections to external services

### Server Capabilities
Each MCP server must declare its capabilities:
- `resources`: Whether the server supports resources
- `tools`: Whether the server supports tools
- `prompts`: Whether the server supports prompts
- `roots`: Whether the server supports roots
- `sampling`: Whether the server supports sampling

### Transport Methods
MCP servers support multiple transport methods:
- `stdio`: Standard input/output for local communication
- `http`: HTTP-based communication
- `websocket`: Real-time bidirectional communication

## Implementation Guidelines

### 1. Following the Base Server Pattern
Always extend the base server implementation provided in this skeleton:

```python
from src.server import BaseMCPServer

class MyCustomServer(BaseMCPServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize custom functionality
        self.setup_custom_handlers()

    def setup_custom_handlers(self):
        # Add custom functionality
        pass
```

### 2. Registry Registration Requirement
**CRITICAL: Every MCP server MUST register with the local MCP registry on startup.** This is a mandatory requirement for all MCP server implementations:

- The server must automatically register with the local MCP registry when it starts up
- The server must continuously send health checks to the registry at regular intervals
- The server must update its health status in the registry when its status changes
- The server must deregister from the registry when shutting down gracefully

This ensures proper service discovery, monitoring, and orchestration within the MCP ecosystem.

### 3. Implementing Extensions
Use the extension pattern for modular functionality:

```python
from src.server import MCPServerExtension

class MyCustomExtension(MCPServerExtension):
    async def initialize(self, server: BaseMCPServer):
        # Add custom functionality to the server
        server.set_capability("tools", True)
        self._add_custom_tools(server)
    
    def get_name(self) -> str:
        return "my-custom-extension"
    
    def get_description(self) -> str:
        return "Description of the extension"
```

### 3. Error Handling
Follow JSON-RPC 2.0 error standards:

```python
from src.errors import InvalidParamsError, InternalError, handle_rpc_error

@handle_rpc_error
async def my_handler(params):
    if not validate_params(params):
        raise InvalidParamsError("Invalid parameters provided")
    
    try:
        # Implementation
        pass
    except Exception as e:
        raise InternalError(f"Internal error: {str(e)}")
```

### 4. Configuration Management
Use the configuration system consistently:

```python
from src.config import load_config_from_env, merge_config_with_args

def main():
    config = load_config_from_env()
    # Use config values
    server = MyServer(
        host=config.host,
        port=config.port,
        log_level=config.log_level
    )
```

### 5. Health Monitoring
Implement proper health checks:

```python
async def _perform_health_check(self):
    # Check internal components
    # Check external dependencies
    # Update health status accordingly
    if all_systems_operational:
        self.update_health_status("healthy")
    else:
        self.update_health_status("unhealthy")
```

### 6. Async Programming
Use async/await consistently:

```python
import asyncio

async def async_operation():
    # Perform async operations
    result = await some_async_function()
    return result

# Use asyncio for concurrent operations
async def multiple_operations():
    results = await asyncio.gather(
        operation1(),
        operation2(),
        operation3()
    )
    return results
```

### 7. Logging Standards
Follow consistent logging patterns:

```python
import logging

logger = logging.getLogger(__name__)

def my_function():
    logger.info("Starting operation")
    try:
        # Operation
        logger.debug("Operation step completed")
    except Exception as e:
        logger.error(f"Operation failed: {e}", exc_info=True)
        raise
    logger.info("Operation completed successfully")
```

## Testing Strategy

### Unit Testing
Write unit tests for individual components:

```python
import pytest
from src.my_component import MyComponent

@pytest.fixture
def my_component():
    return MyComponent()

def test_component_initialization(my_component):
    assert my_component is not None

@pytest.mark.asyncio
async def test_async_method(my_component):
    result = await my_component.async_method()
    assert result is not None
```

### Integration Testing
Test component interactions:

```python
@pytest.mark.asyncio
async def test_server_integration():
    server = BaseMCPServer(transport="stdio")
    await server.start()
    
    # Test server functionality
    assert server.health_status == "healthy"
    
    await server.shutdown()
```

### Test Coverage
Maintain high test coverage (>80%):

```bash
# Run tests with coverage
pytest --cov=src --cov-report=html
```

### Property-Based Testing
For complex logic, use property-based testing:

```python
from hypothesis import given, strategies as st

@given(st.text())
def test_input_validation(input_text):
    result = validate_input(input_text)
    assert isinstance(result, bool)
```

## Deployment Guidelines

### Containerization
Use Docker for consistent deployments:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "-m", "src.main"]
```

### Configuration Management
Use environment variables for configuration:

```bash
# Example .env file
MCP_TRANSPORT=http
MCP_HOST=0.0.0.0
MCP_PORT=8080
MCP_LOG_LEVEL=INFO
MCP_REGISTRY_ENDPOINT=http://registry:8080
```

### Health Checks
Implement readiness and liveness probes:

```python
# Health check endpoint is automatically provided
# GET /health returns server status
```

### Scaling Considerations
Design for horizontal scaling:

- Statelessness where possible
- External session storage
- Distributed caching
- Database connection pooling

## Security Best Practices

### Input Validation
Always validate and sanitize inputs:

```python
from pydantic import BaseModel, ValidationError

class MyRequest(BaseModel):
    param1: str
    param2: int

def handler(raw_params):
    try:
        validated_params = MyRequest(**raw_params)
    except ValidationError as e:
        raise InvalidParamsError(f"Validation error: {e}")
```

### Authentication and Authorization
Implement appropriate security measures:

```python
# Example authentication middleware
async def authenticate_request(request):
    token = request.headers.get("Authorization")
    if not token or not is_valid_token(token):
        raise UnauthorizedError("Invalid or missing authentication token")
```

### Secure Communication
Use HTTPS/TLS for production deployments:

```python
# Configuration for secure communication
SECURE_TRANSPORT = True
TLS_CERT_PATH = "/path/to/cert.pem"
TLS_KEY_PATH = "/path/to/key.pem"

# Environment variables for security
ENVIRONMENT=production
FORCE_HTTPS=true  # Forces HTTPS redirects in production
```

### Security Headers
The server automatically includes security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`

### Rate Limiting
Implement rate limiting to prevent abuse:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
```

## Performance Considerations

### Async Operations
Maximize concurrency with async operations:

```python
import asyncio

async def process_multiple_requests(requests):
    # Process requests concurrently
    results = await asyncio.gather(
        *[process_single_request(req) for req in requests],
        return_exceptions=True
    )
    return results
```

### Caching Strategies
Implement appropriate caching:

```python
import aiocache

@aiocache.cached(ttl=60)
async def expensive_operation(param):
    # Expensive operation
    return result
```

### Memory Management
Monitor and optimize memory usage:

```python
import tracemalloc

def start_tracing():
    tracemalloc.start()

def get_memory_stats():
    current, peak = tracemalloc.get_traced_memory()
    return {"current": current, "peak": peak}
```

### Connection Pooling
Use connection pooling for databases and external services:

```python
import asyncpg

async def get_db_pool():
    return await asyncpg.create_pool(
        "postgresql://user:pass@localhost/db",
        min_size=10,
        max_size=20
    )
```

## Troubleshooting

### Common Issues

#### Server Won't Start
- Check if the port is already in use
- Verify configuration values
- Check logs for specific error messages

#### Registration Fails
- Verify registry endpoint is accessible
- Check network connectivity
- Ensure server capabilities are properly set

#### Health Checks Failing
- Check dependent services are running
- Verify external connections
- Review health check implementation

### Debugging Tips

#### Enable Verbose Logging
```bash
export MCP_LOG_LEVEL=DEBUG
python -m src.main
```

#### Use Interactive Debugging
```python
import pdb; pdb.set_trace()  # Breakpoint
```

#### Monitor Resource Usage
```bash
# Monitor CPU and memory
top -p $(pgrep -f "python.*mcp")
```

### Diagnostic Tools
Include diagnostic endpoints in your server:

```python
@app.get("/diagnostics")
async def diagnostics():
    return {
        "health_status": server.health_status,
        "uptime": get_uptime(),
        "active_connections": len(connections),
        "memory_usage": get_memory_stats()
    }
```

## Versioning and Release Process

### Versioning Scheme
Follow semantic versioning (MAJOR.MINOR.PATCH):

- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes (backward compatible)

### Release Process
1. Update version in `pyproject.toml`
2. Update changelog
3. Run full test suite
4. Create release branch
5. Tag release in Git
6. Build distribution packages
7. Deploy to package repository

### Changelog Format
Maintain a changelog with this format:

```
# Changelog

## [Unreleased]

## [1.2.0] - 2023-12-01
### Added
- New feature X
- New configuration option Y

### Changed
- Updated dependency Z to version 2.0

### Fixed
- Bug in health check logic
```

### Continuous Integration
Implement CI pipeline with:
- Automated testing
- Code quality checks
- Security scanning
- Automated releases for tagged commits

---
This guide should be updated as new patterns and best practices emerge in MCP server development.