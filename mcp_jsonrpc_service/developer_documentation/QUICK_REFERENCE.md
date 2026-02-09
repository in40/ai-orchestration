# MCP Server Development Quick Reference

## Common Commands

### Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Install development tools
pip install -r requirements-dev.txt
```

### Running the Server
```bash
# Stdio transport (default)
python -m src.main

# HTTP transport
python -m src.main --transport http --port 8080

# With custom configuration
MCP_TRANSPORT=http MCP_PORT=9000 python -m src.main
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_specific.py

# Run with verbose output
pytest -v
```

### Formatting and Linting
```bash
# Format code with Black
black src/

# Lint with Flake8
flake8 src/

# Type check with MyPy
mypy src/
```

## Key Imports

```python
# Server base class
from src.server import BaseMCPServer, MCPServerExtension

# Error handling
from src.errors import (
    RPCException, 
    InvalidParamsError, 
    InternalError, 
    handle_rpc_error
)

# Configuration
from src.config import ServerConfig, load_config_from_env

# Registry client
from src.registry_client import RegistryClient
```

## Common Patterns

### Creating a Custom Server
```python
from src.server import BaseMCPServer

class MyCustomServer(BaseMCPServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Enable capabilities as needed
        self.set_capability("tools", True)
        self.set_capability("resources", True)
        
    async def _perform_health_check(self):
        # Custom health check logic
        pass
```

### Adding Error Handling
```python
from src.errors import handle_rpc_error, InvalidParamsError

@handle_rpc_error
async def my_handler(params):
    if not validate_params(params):
        raise InvalidParamsError("Invalid parameters provided")
    
    # Handler implementation
    return result
```

### Creating an Extension
```python
from src.server import MCPServerExtension

class MyExtension(MCPServerExtension):
    async def initialize(self, server):
        # Add functionality to server
        server.set_capability("tools", True)
    
    def get_name(self):
        return "my-extension"
    
    def get_description(self):
        return "My custom extension"
```

### Configuration Loading
```python
from src.config import load_config_from_env, merge_config_with_args

def main():
    config = load_config_from_env()
    # Use config values
    server = BaseMCPServer(
        transport=config.transport,
        host=config.host,
        port=config.port
    )
```

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `MCP_TRANSPORT` | `stdio` | Transport method |
| `MCP_HOST` | `0.0.0.0` | HTTP host |
| `MCP_PORT` | `8080` | HTTP port |
| `MCP_LOG_LEVEL` | `INFO` | Logging level |
| `MCP_REGISTRY_ENDPOINT` | `stdio://` | Registry endpoint |
| `MCP_HEALTH_CHECK_INTERVAL` | `60` | Health check interval (seconds) |

## Error Codes

| Code | Meaning |
|------|---------|
| -32700 | Parse error |
| -32600 | Invalid Request |
| -32601 | Method not found |
| -32602 | Invalid params |
| -32603 | Internal error |

## Testing Patterns

### Async Tests
```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await my_async_function()
    assert result is not None
```

### Fixture Pattern
```python
@pytest.fixture
async def my_server():
    server = BaseMCPServer(transport="stdio")
    yield server
    # Cleanup if needed
```

## Logging

```python
import logging

logger = logging.getLogger(__name__)

logger.debug("Detailed debug info")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred", exc_info=True)
```

## Common Validations

```python
from pydantic import BaseModel, validator

class MyParams(BaseModel):
    required_field: str
    optional_field: int = 0
    
    @validator('required_field')
    def validate_required_field(cls, v):
        if not v:
            raise ValueError('Field cannot be empty')
        return v
```

## Async Best Practices

```python
import asyncio

# Concurrent execution
results = await asyncio.gather(
    task1(),
    task2(),
    task3()
)

# With timeouts
try:
    result = await asyncio.wait_for(long_running_task(), timeout=10.0)
except asyncio.TimeoutError:
    # Handle timeout
    pass

# Background tasks
task = asyncio.create_task(background_work())
# Later, if needed:
# await task
```

## Git Workflow

```bash
# Create feature branch
git checkout -b feature/my-feature

# Commit changes
git add .
git commit -m "Add my feature"

# Push and create PR
git push origin feature/my-feature
```

## Docker Commands

```bash
# Build image
docker build -t my-mcp-server .

# Run container
docker run -p 8080:8080 my-mcp-server

# Run with environment variables
docker run -e MCP_PORT=9000 -p 9000:9000 my-mcp-server
```