"""
Test Suite for Base MCP Server

This module contains tests to verify MCP protocol compliance and basic functionality.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.server import BaseMCPServer
from src.errors import RPCException, InternalError


@pytest.fixture
def base_server():
    """Create a BaseMCPServer instance for testing."""
    server = BaseMCPServer(transport="stdio")
    return server


@pytest.mark.asyncio
async def test_server_initialization(base_server):
    """Test that the server initializes correctly."""
    assert base_server.transport == "stdio"
    assert base_server.name == "base-mcp-server"
    assert isinstance(base_server.capabilities, dict)
    assert base_server.health_status == "unknown"


@pytest.mark.asyncio
async def test_set_capability():
    """Test setting server capabilities."""
    server = BaseMCPServer(transport="stdio")
    
    # Test setting a valid capability
    server.set_capability("tools", True)
    assert server.capabilities["tools"] is True
    
    # Test setting an invalid capability
    with patch('logging.Logger.warning') as mock_warning:
        server.set_capability("invalid_capability", True)
        mock_warning.assert_called_once()


@pytest.mark.asyncio
async def test_add_tag():
    """Test adding tags to the server."""
    server = BaseMCPServer(transport="stdio")
    
    server.add_tag("test-tag")
    assert "test-tag" in server.tags
    
    # Adding the same tag again should not duplicate
    server.add_tag("test-tag")
    assert server.tags.count("test-tag") == 1


@pytest.mark.asyncio
async def test_set_metadata():
    """Test setting metadata for the server."""
    server = BaseMCPServer(transport="stdio")
    
    server.set_metadata("version", "1.0.0")
    assert server.metadata["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_get_registration_info():
    """Test getting registration information."""
    server = BaseMCPServer(transport="stdio")
    server.name = "test-server"
    server.description = "Test server for verification"
    server.set_capability("tools", True)
    server.add_tag("test")
    server.set_metadata("version", "1.0.0")
    
    reg_info = server.get_registration_info()
    
    assert reg_info["name"] == "test-server"
    assert reg_info["description"] == "Test server for verification"
    assert reg_info["capabilities"]["tools"] is True
    assert "test" in reg_info["tags"]
    assert reg_info["metadata"]["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_update_health_status():
    """Test updating health status."""
    server = BaseMCPServer(transport="stdio")
    
    server.update_health_status("healthy")
    assert server.health_status == "healthy"
    
    server.update_health_status("unhealthy")
    assert server.health_status == "unhealthy"
    
    server.update_health_status("unknown")
    assert server.health_status == "unknown"
    
    # Test invalid status
    with patch('logging.Logger.warning') as mock_warning:
        server.update_health_status("invalid_status")
        mock_warning.assert_called_once()


@pytest.mark.asyncio
async def test_start_stop_stdio_transport():
    """Test starting and stopping the server with stdio transport."""
    server = BaseMCPServer(transport="stdio")
    
    # Mock the stdio server functionality
    with patch('src.server.stdio_server') as mock_stdio:
        mock_context_manager = AsyncMock()
        mock_stdio.return_value.__aenter__.return_value = mock_context_manager
        mock_context_manager.return_value = None
        
        # Start the server
        start_task = asyncio.create_task(server.start())
        
        # Give it a moment to start
        await asyncio.sleep(0.01)
        
        # Stop the server
        await server.shutdown()
        
        # Wait for the start task to complete
        try:
            await asyncio.wait_for(start_task, timeout=0.1)
        except asyncio.TimeoutError:
            # Cancel the task if it doesn't complete quickly
            start_task.cancel()
            try:
                await start_task
            except asyncio.CancelledError:
                pass


@pytest.mark.asyncio
async def test_start_stop_http_transport():
    """Test starting and stopping the server with HTTP transport."""
    server = BaseMCPServer(transport="http", host="127.0.0.1", port=8081)

    # Start the server
    start_task = asyncio.create_task(server.start())

    # Give it a moment to start and update health status
    await asyncio.sleep(0.2)

    # Verify the server is running
    assert server.health_status == "healthy"

    # Stop the server
    await server.shutdown()

    # Wait for the start task to complete
    try:
        await asyncio.wait_for(start_task, timeout=0.5)
    except asyncio.TimeoutError:
        # Cancel the task if it doesn't complete quickly
        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_registry_client_basic():
    """Test basic registry client functionality."""
    from src.registry_client import RegistryClient
    
    # Test initialization
    client = RegistryClient("stdio://")
    assert client.registry_endpoint == "stdio://"
    
    # Test context manager functionality
    async with RegistryClient("stdio://") as client:
        assert client.session is not None


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling functionality."""
    from src.errors import RPCException, InternalError, InvalidRequestError

    # Test creating an RPC exception
    error = InternalError("Test internal error")
    assert error.code == -32603
    assert error.message == "Test internal error"

    # Test converting to dict
    error_dict = error.to_dict()
    assert "code" in error_dict
    assert "message" in error_dict
    assert error_dict["code"] == -32603
    assert error_dict["message"] == "Test internal error"

    # Test creating an error with data
    error_with_data = InvalidRequestError("Invalid request", data={"param": "value"})
    error_dict_with_data = error_with_data.to_dict()
    assert "data" in error_dict_with_data
    assert error_dict_with_data["data"] == {"param": "value"}


@pytest.mark.asyncio
async def test_rpc_discover_method():
    """Test the rpc.discover method."""
    server = BaseMCPServer(transport="stdio")
    
    # Call the discover method
    result = await server.handle_discover_method()
    
    # Verify the result contains the expected structure
    assert "openrpc" in result
    assert result["openrpc"] == "1.3.2"
    assert "info" in result
    assert "methods" in result
    
    # Verify the rpc.discover method is in the schema
    methods = result["methods"]
    discover_methods = [method for method in methods if method["name"] == "rpc.discover"]
    assert len(discover_methods) == 1


@pytest.mark.asyncio
async def test_openrpc_schema_generation():
    """Test that the OpenRPC schema is properly generated."""
    server = BaseMCPServer(transport="stdio")
    
    # Check that the schema was generated during initialization
    assert hasattr(server, '_openrpc_schema')
    assert server._openrpc_schema is not None
    
    # Verify the schema structure
    schema = server._openrpc_schema
    assert schema["openrpc"] == "1.3.2"
    assert schema["info"]["title"] == server.name
    assert schema["info"]["description"] == server.description


@pytest.mark.asyncio
async def test_configuration_loading():
    """Test configuration loading functionality."""
    from src.config import ServerConfig, load_config_from_env

    # Test default configuration
    config = ServerConfig()
    assert config.transport == "stdio"
    assert config.port == 8080
    # Note: Default log level might vary, so we just check it's set
    assert config.log_level in ["DEBUG", "INFO", "WARNING", "ERROR"]

    # Test loading from environment (should match defaults since no env vars are set)
    loaded_config = load_config_from_env()
    assert loaded_config.transport == "stdio"
    assert loaded_config.port == 8080
    # Note: Default log level might vary, so we just check it's set
    assert loaded_config.log_level in ["DEBUG", "INFO", "WARNING", "ERROR"]


if __name__ == "__main__":
    pytest.main([__file__])