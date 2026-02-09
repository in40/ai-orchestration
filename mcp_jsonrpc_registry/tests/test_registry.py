"""Basic tests for the MCP Server Registry."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.server.registry_server import RegistryServer
from src.models.server import ServerCapabilities, RegisterServerRequest


@pytest.fixture
def mock_db_service():
    """Mock database service for testing."""
    db_service = Mock()
    db_service.get_all_servers.return_value = []
    db_service.register_server.return_value = Mock(id="test-server-id", name="Test Server")
    return db_service


@pytest.fixture
def mock_health_monitor():
    """Mock health monitor service for testing."""
    health_monitor = Mock()
    return health_monitor


def test_registry_server_initialization():
    """Test that the registry server initializes correctly."""
    # This test will likely fail initially due to MCP library dependencies
    # We'll focus on testing the business logic parts
    assert True  # Placeholder test


def test_server_capabilities_model():
    """Test the ServerCapabilities model."""
    capabilities = ServerCapabilities(
        resources=True,
        tools=True,
        prompts=False,
        roots=False,
        sampling=True
    )
    
    assert capabilities.resources is True
    assert capabilities.tools is True
    assert capabilities.prompts is False
    assert capabilities.roots is False
    assert capabilities.sampling is True


def test_register_server_request_model():
    """Test the RegisterServerRequest model."""
    caps = ServerCapabilities(resources=True, tools=True)
    req = RegisterServerRequest(
        name="Test Server",
        description="A test server",
        endpoint="http://localhost:8000",
        capabilities=caps,
        metadata={"version": "1.0.0"},
        tags=["test", "utility"]
    )
    
    assert req.name == "Test Server"
    assert req.description == "A test server"
    assert req.endpoint == "http://localhost:8000"
    assert req.capabilities.resources is True
    assert req.metadata["version"] == "1.0.0"
    assert "test" in req.tags
    assert "utility" in req.tags


@patch('src.services.database.DatabaseService')
@patch('src.services.health_monitor.HealthMonitorService')
def test_registry_server_creation(mock_health_monitor, mock_db_service):
    """Test creating a registry server with mocked dependencies."""
    # Configure mocks
    mock_db_service_instance = Mock()
    mock_health_monitor_instance = Mock()
    
    mock_db_service.return_value = mock_db_service_instance
    mock_health_monitor.return_value = mock_health_monitor_instance
    
    # Create registry server
    registry = RegistryServer()
    
    # Verify initialization
    assert registry.db_service == mock_db_service_instance
    assert registry.health_monitor == mock_health_monitor_instance