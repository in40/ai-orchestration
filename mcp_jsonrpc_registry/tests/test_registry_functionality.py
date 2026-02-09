"""Comprehensive tests for the MCP Server Registry functionality."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from src.server.registry_server import RegistryServer
from src.models.server import ServerCapabilities, RegisterServerRequest, UpdateServerStatusRequest
from src.services.database import DatabaseService
from src.services.health_monitor import HealthMonitorService


class TestRegistryServer:
    """Test cases for the RegistryServer class."""
    
    @pytest.fixture
    def mock_db_service(self):
        """Mock database service for testing."""
        db_service = Mock(spec=DatabaseService)
        db_service.get_all_servers.return_value = []
        db_service.register_server.return_value = Mock(
            id="test-server-id",
            name="Test Server",
            description="A test server",
            endpoint="http://localhost:8000",
            capabilities=ServerCapabilities(resources=True, tools=True),
            metadata={"version": "1.0.0"},
            registered_at=datetime.now(),
            last_seen=None,
            health_status="healthy",
            tags=["test"]
        )
        return db_service
    
    @pytest.fixture
    def mock_health_monitor(self):
        """Mock health monitor service for testing."""
        health_monitor = Mock(spec=HealthMonitorService)
        return health_monitor
    
    @pytest.fixture
    def registry_server(self, mock_db_service, mock_health_monitor):
        """Create a registry server instance with mocked dependencies."""
        registry = RegistryServer.__new__(RegistryServer)  # Create without calling __init__
        registry.mcp = Mock()
        registry.db_service = mock_db_service
        registry.health_monitor = mock_health_monitor
        registry._register_mcp_methods = Mock()  # Skip method registration in tests
        return registry
    
    def test_registry_server_initialization(self):
        """Test that the registry server can be initialized."""
        # Mock the database service to avoid needing a real database connection
        with patch('src.server.registry_server.DatabaseService') as mock_db_service_class, \
             patch('src.server.registry_server.HealthMonitorService') as mock_health_monitor_class, \
             patch('src.server.registry_server.Server'):
            
            # Create mock instances
            mock_db_service = Mock()
            mock_health_monitor = Mock()
            
            mock_db_service_class.return_value = mock_db_service
            mock_health_monitor_class.return_value = mock_health_monitor
            
            registry = RegistryServer()
            assert registry.db_service is mock_db_service
            assert registry.health_monitor is mock_health_monitor
    
    def test_registry_list_servers(self, registry_server, mock_db_service):
        """Test the _registry_list_servers method."""
        # Setup mock return value
        mock_server = Mock()
        mock_server.id = "test-id"
        mock_server.name = "Test Server"
        mock_server.description = "A test server"
        mock_server.endpoint = "http://localhost:8000"
        mock_server.capabilities = ServerCapabilities(resources=True, tools=True)
        mock_server.metadata = {"version": "1.0.0"}
        mock_server.registered_at = datetime.now()
        mock_server.last_seen = None
        mock_server.health_status = "healthy"
        mock_server.tags = ["test"]
        
        mock_db_service.get_all_servers.return_value = [mock_server]
        
        # Call the method
        result = registry_server._registry_list_servers()
        
        # Assertions
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == "test-id"
        assert result[0]["name"] == "Test Server"
        assert result[0]["description"] == "A test server"
        assert result[0]["endpoint"] == "http://localhost:8000"
        assert result[0]["metadata"]["version"] == "1.0.0"
        assert result[0]["health_status"] == "healthy"
        assert "test" in result[0]["tags"]
    
    def test_registry_get_server_details_found(self, registry_server, mock_db_service):
        """Test the _registry_get_server_details method when server is found."""
        # Setup mock return value
        mock_server = Mock()
        mock_server.id = "found-server-id"
        mock_server.name = "Found Server"
        mock_server.description = "A found server"
        mock_server.endpoint = "http://localhost:8001"
        mock_server.capabilities = ServerCapabilities(resources=False, tools=True)
        mock_server.metadata = {"version": "2.0.0"}
        mock_server.registered_at = datetime.now()
        mock_server.last_seen = datetime.now()
        mock_server.health_status = "unhealthy"
        mock_server.tags = ["found", "test"]
        
        mock_db_service.get_server_by_id.return_value = mock_server
        
        # Call the method
        result = registry_server._registry_get_server_details("found-server-id")
        
        # Assertions
        assert result["id"] == "found-server-id"
        assert result["name"] == "Found Server"
        assert result["health_status"] == "unhealthy"
        assert "found" in result["tags"]
    
    def test_registry_get_server_details_not_found(self, registry_server, mock_db_service):
        """Test the _registry_get_server_details method when server is not found."""
        mock_db_service.get_server_by_id.return_value = None
        
        # Call the method
        result = registry_server._registry_get_server_details("non-existent-id")
        
        # Assertions
        assert "error" in result
        assert "non-existent-id" in result["error"]
    
    def test_registry_search_servers(self, registry_server, mock_db_service):
        """Test the _registry_search_servers method."""
        # Setup mock return value
        mock_server = Mock()
        mock_server.id = "search-result-id"
        mock_server.name = "Search Result Server"
        mock_server.description = "A search result server"
        mock_server.endpoint = "http://localhost:8002"
        mock_server.capabilities = ServerCapabilities(resources=True, tools=False)
        mock_server.metadata = {"version": "3.0.0"}
        mock_server.registered_at = datetime.now()
        mock_server.last_seen = None
        mock_server.health_status = "unknown"
        mock_server.tags = ["search", "result"]
        
        mock_db_service.search_servers.return_value = [mock_server]
        
        # Call the method
        result = registry_server._registry_search_servers(query="search", tags=["result"])
        
        # Verify the search method was called with correct parameters
        mock_db_service.search_servers.assert_called_once_with(query="search", tags=["result"])
        
        # Assertions
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == "search-result-id"
        assert result[0]["name"] == "Search Result Server"
    
    def test_registry_register_server_success(self, registry_server, mock_db_service):
        """Test the _registry_register_server method for successful registration."""
        # Setup mock return value
        registered_mock = Mock()
        registered_mock.id = "new-server-id"
        registered_mock.name = "New Server"
        
        mock_db_service.register_server.return_value = registered_mock
        
        # Call the method
        result = registry_server._registry_register_server(
            name="New Server",
            description="A new server",
            endpoint="http://localhost:8003",
            capabilities={"resources": True, "tools": True, "prompts": False, "roots": False, "sampling": False},
            metadata={"version": "1.0.0"},
            tags=["new", "test"]
        )
        
        # Assertions
        assert result["success"] is True
        assert result["server_id"] == "new-server-id"
        assert "registered successfully" in result["message"]
    
    def test_registry_register_server_exception(self, registry_server, mock_db_service):
        """Test the _registry_register_server method when an exception occurs."""
        # Setup mock to raise an exception
        mock_db_service.register_server.side_effect = Exception("Registration failed")
        
        # Call the method
        result = registry_server._registry_register_server(
            name="Failing Server",
            description="A failing server",
            endpoint="http://localhost:8004",
            capabilities={"resources": False, "tools": True, "prompts": False, "roots": False, "sampling": False},
            metadata={},
            tags=[]
        )
        
        # Assertions
        assert result["success"] is False
        assert "Registration failed" in result["error"]
        assert "Failed to register" in result["message"]
    
    def test_registry_update_server_status_valid(self, registry_server, mock_db_service):
        """Test the _registry_update_server_status method with valid status."""
        mock_db_service.update_server_status.return_value = True
        
        # Call the method
        result = registry_server._registry_update_server_status("test-server-id", "healthy")
        
        # Verify the update method was called
        mock_db_service.update_server_status.assert_called_once()
        
        # Assertions
        assert result["success"] is True
        assert "updated to healthy" in result["message"]
    
    def test_registry_update_server_status_invalid(self, registry_server, mock_db_service):
        """Test the _registry_update_server_status method with invalid status."""
        # Call the method with invalid status
        result = registry_server._registry_update_server_status("test-server-id", "invalid-status")
        
        # Verify the update method was NOT called
        mock_db_service.update_server_status.assert_not_called()
        
        # Assertions
        assert result["success"] is False
        assert "Invalid health status" in result["error"]
    
    def test_registry_update_server_status_not_found(self, registry_server, mock_db_service):
        """Test the _registry_update_server_status method when server is not found."""
        mock_db_service.update_server_status.return_value = False
        
        # Call the method
        result = registry_server._registry_update_server_status("non-existent-id", "healthy")
        
        # Assertions
        assert result["success"] is False
        assert result["error"] == "Server not found"
    
    def test_get_all_servers_resource(self, registry_server, mock_db_service):
        """Test the _get_all_servers_resource method."""
        # Setup mock return value
        mock_server = Mock()
        mock_server.id = "resource-server-id"
        mock_server.name = "Resource Server"
        mock_server.description = "A resource server"
        mock_server.endpoint = "http://localhost:8005"
        mock_server.capabilities = ServerCapabilities(resources=True, tools=True)
        mock_server.metadata = {"version": "4.0.0"}
        mock_server.registered_at = datetime.now()
        mock_server.last_seen = None
        mock_server.health_status = "healthy"
        mock_server.tags = ["resource"]
        
        mock_db_service.get_all_servers.return_value = [mock_server]
        
        # Call the method
        result = registry_server._get_all_servers_resource()
        
        # Assertions
        assert "servers" in result
        assert "total_count" in result
        assert "fetched_at" in result
        assert result["total_count"] == 1
        assert result["servers"][0]["id"] == "resource-server-id"
        assert result["servers"][0]["name"] == "Resource Server"
    
    def test_get_all_capabilities_resource(self, registry_server, mock_db_service):
        """Test the _get_all_capabilities_resource method."""
        # Setup mock return value
        mock_server1 = Mock()
        mock_server1.capabilities = ServerCapabilities(resources=True, tools=False, prompts=False, roots=False, sampling=False)
        mock_server1.health_status = "healthy"
        
        mock_server2 = Mock()
        mock_server2.capabilities = ServerCapabilities(resources=False, tools=True, prompts=False, roots=False, sampling=False)
        mock_server2.health_status = "unhealthy"
        
        mock_db_service.get_all_servers.return_value = [mock_server1, mock_server2]
        
        # Call the method
        result = registry_server._get_all_capabilities_resource()
        
        # Assertions
        assert "collective_capabilities" in result
        assert "server_count" in result
        assert "fetched_at" in result
        assert result["server_count"] == 2
        assert result["collective_capabilities"]["resources"] is True
        assert result["collective_capabilities"]["tools"] is True
    
    def test_get_health_status_resource(self, registry_server, mock_db_service):
        """Test the _get_health_status_resource method."""
        # Setup mock return values
        mock_server1 = Mock()
        mock_server1.id = "server1"
        mock_server1.name = "Server 1"
        mock_server1.health_status = "healthy"
        
        mock_server2 = Mock()
        mock_server2.id = "server2"
        mock_server2.name = "Server 2"
        mock_server2.health_status = "unhealthy"
        
        mock_server3 = Mock()
        mock_server3.id = "server3"
        mock_server3.name = "Server 3"
        mock_server3.health_status = "healthy"
        
        mock_db_service.get_all_servers.return_value = [mock_server1, mock_server2, mock_server3]
        
        # Call the method
        result = registry_server._get_health_status_resource()
        
        # Assertions
        assert "total_servers" in result
        assert "healthy" in result
        assert "unhealthy" in result
        assert "unknown" in result
        assert "details" in result
        assert "fetched_at" in result
        
        assert result["total_servers"] == 3
        assert result["healthy"] == 2  # Two healthy servers
        assert result["unhealthy"] == 1  # One unhealthy server
        assert result["unknown"] == 0  # No unknown servers
        
        # Check details
        detail_ids = [detail["id"] for detail in result["details"]]
        assert "server1" in detail_ids
        assert "server2" in detail_ids
        assert "server3" in detail_ids


class TestServerCapabilities:
    """Test cases for ServerCapabilities model."""
    
    def test_server_capabilities_creation(self):
        """Test creating ServerCapabilities instances."""
        caps = ServerCapabilities(
            resources=True,
            tools=False,
            prompts=True,
            roots=False,
            sampling=True
        )
        
        assert caps.resources is True
        assert caps.tools is False
        assert caps.prompts is True
        assert caps.roots is False
        assert caps.sampling is True
    
    def test_server_capabilities_defaults(self):
        """Test ServerCapabilities default values."""
        caps = ServerCapabilities()
        
        # Assuming defaults are False based on the model definition
        assert caps.resources is False
        assert caps.tools is False
        assert caps.prompts is False
        assert caps.roots is False
        assert caps.sampling is False


class TestRegisterServerRequest:
    """Test cases for RegisterServerRequest model."""
    
    def test_register_server_request_creation(self):
        """Test creating RegisterServerRequest instances."""
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


if __name__ == "__main__":
    pytest.main([__file__])