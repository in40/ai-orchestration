"""MCP Server implementation for the Registry."""

from mcp.server import FastMCP
from typing import List, Dict, Any
import asyncio
from datetime import datetime

from src.services.database import DatabaseService
from src.services.health_monitor import HealthMonitorService
from src.models.server import RegisteredServer, RegisterServerRequest, UpdateServerStatusRequest
from config.settings import settings


class RegistryServer:
    def __init__(self):
        self.mcp = FastMCP("mcp-registry-server")
        self.db_service = DatabaseService()
        self.health_monitor = HealthMonitorService(self.db_service)

        # Register MCP methods
        self._register_mcp_methods()
    
    def _register_mcp_methods(self):
        """Register all MCP methods for the registry server."""

        # Registry tools - using decorators with proper names (compliant with MCP standard)
        @self.mcp.tool(
            name="registry-list_servers",
            description="List all registered MCP servers with their capabilities"
        )
        def list_servers() -> List[Dict[str, Any]]:
            return self._registry_list_servers()

        @self.mcp.tool(
            name="registry-get_server_details",
            description="Retrieve detailed information about a specific registered server"
        )
        def get_server_details(server_id: str) -> Dict[str, Any]:
            return self._registry_get_server_details(server_id)

        @self.mcp.tool(
            name="registry-search_servers",
            description="Search for servers by name, description, or tags"
        )
        def search_servers(query: str = "", tags: List[str] = []) -> List[Dict[str, Any]]:
            return self._registry_search_servers(query, tags)

        @self.mcp.tool(
            name="registry-register_server",
            description="Register a new MCP server with the registry"
        )
        def register_server(
            name: str,
            description: str = "",
            endpoint: str = "",
            capabilities: Dict[str, bool] = {},
            metadata: Dict[str, str] = {},
            tags: List[str] = []
        ) -> Dict[str, Any]:
            return self._registry_register_server(name, description, endpoint, capabilities, metadata, tags)

        @self.mcp.tool(
            name="registry-update_server_status",
            description="Update the health status of a registered server"
        )
        def update_server_status(server_id: str, health_status: str) -> Dict[str, Any]:
            return self._registry_update_server_status(server_id, health_status)

        # Registry resources - using decorators
        @self.mcp.resource(
            "registry://servers",
            description="Provides all registered servers in structured format"
        )
        def get_all_servers_resource() -> Dict[str, Any]:
            return self._get_all_servers_resource()

        @self.mcp.resource(
            "registry://capabilities",
            description="Shows collective capabilities of all registered servers"
        )
        def get_all_capabilities_resource() -> Dict[str, Any]:
            return self._get_all_capabilities_resource()

        @self.mcp.resource(
            "registry://health-status",
            description="Provides current health status of registered servers"
        )
        def get_health_status_resource() -> Dict[str, Any]:
            return self._get_health_status_resource()
    
    def _registry_list_servers(self) -> List[Dict[str, Any]]:
        """
        List all registered MCP servers with their capabilities.
        
        Returns:
            List of server information dictionaries
        """
        servers = self.db_service.get_all_servers()
        return [
            {
                "id": server.id,
                "name": server.name,
                "description": server.description,
                "endpoint": server.endpoint,
                "capabilities": server.capabilities.model_dump(),
                "metadata": server.metadata,
                "registered_at": server.registered_at.isoformat(),
                "last_seen": server.last_seen.isoformat() if server.last_seen else None,
                "health_status": server.health_status,
                "tags": server.tags
            }
            for server in servers
        ]
    
    def _registry_get_server_details(self, server_id: str) -> Dict[str, Any]:
        """
        Retrieve detailed information about a specific registered server.
        
        Args:
            server_id: The ID of the server to retrieve
        
        Returns:
            Server information dictionary
        """
        server = self.db_service.get_server_by_id(server_id)
        if not server:
            return {"error": f"Server with ID {server_id} not found"}

        return {
            "id": server.id,
            "name": server.name,
            "description": server.description,
            "endpoint": server.endpoint,
            "capabilities": server.capabilities.model_dump(),
            "metadata": server.metadata,
            "registered_at": server.registered_at.isoformat(),
            "last_seen": server.last_seen.isoformat() if server.last_seen else None,
            "health_status": server.health_status,
            "tags": server.tags
        }
    
    def _registry_search_servers(self, query: str = "", tags: List[str] = []) -> List[Dict[str, Any]]:
        """
        Search for servers by name, description, or tags.
        
        Args:
            query: Search term to match in server names or descriptions
            tags: List of tags to filter servers by
        
        Returns:
            List of matching server information dictionaries
        """
        servers = self.db_service.search_servers(query=query, tags=tags)
        return [
            {
                "id": server.id,
                "name": server.name,
                "description": server.description,
                "endpoint": server.endpoint,
                "capabilities": server.capabilities.model_dump(),
                "metadata": server.metadata,
                "registered_at": server.registered_at.isoformat(),
                "last_seen": server.last_seen.isoformat() if server.last_seen else None,
                "health_status": server.health_status,
                "tags": server.tags
            }
            for server in servers
        ]
    
    def _registry_register_server(
        self,
        name: str,
        description: str = "",
        endpoint: str = "",
        capabilities: Dict[str, bool] = {},
        metadata: Dict[str, str] = {},
        tags: List[str] = []
    ) -> Dict[str, Any]:
        """
        Register a new MCP server with the registry.
        
        Args:
            name: Name of the server
            description: Description of the server
            endpoint: Endpoint URL or transport method
            capabilities: Dictionary of server capabilities
            metadata: Additional metadata about the server
            tags: Tags for categorizing the server
        
        Returns:
            Result of the registration operation
        """
        from src.models.server import ServerCapabilities
        
        # Create ServerCapabilities object from the dict
        caps = ServerCapabilities(**capabilities)
        
        # Create RegisterServerRequest object
        request = RegisterServerRequest(
            name=name,
            description=description,
            endpoint=endpoint,
            capabilities=caps,
            metadata=metadata,
            tags=tags
        )
        
        try:
            registered_server = self.db_service.register_server(request)
            return {
                "success": True,
                "server_id": registered_server.id,
                "message": f"Server '{name}' registered successfully with ID {registered_server.id}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to register server '{name}': {str(e)}"
            }
    
    def _registry_update_server_status(self, server_id: str, health_status: str) -> Dict[str, Any]:
        """
        Update the health status of a registered server.
        
        Args:
            server_id: The ID of the server to update
            health_status: New health status (healthy, unhealthy, unknown)
        
        Returns:
            Result of the update operation
        """
        # Validate health status
        valid_statuses = ["healthy", "unhealthy", "unknown"]
        if health_status not in valid_statuses:
            return {
                "success": False,
                "error": f"Invalid health status. Must be one of: {valid_statuses}",
                "message": f"Invalid health status: {health_status}"
            }
        
        request = UpdateServerStatusRequest(health_status=health_status)
        success = self.db_service.update_server_status(server_id, request)
        
        if success:
            return {
                "success": True,
                "message": f"Health status for server {server_id} updated to {health_status}"
            }
        else:
            return {
                "success": False,
                "error": "Server not found",
                "message": f"Server with ID {server_id} not found"
            }
    
    def _get_all_servers_resource(self) -> Dict[str, Any]:
        """
        Resource providing all registered servers in structured format.
        """
        servers = self.db_service.get_all_servers()
        return {
            "servers": [
                {
                    "id": server.id,
                    "name": server.name,
                    "description": server.description,
                    "endpoint": server.endpoint,
                    "capabilities": server.capabilities.model_dump(),
                    "metadata": server.metadata,
                    "registered_at": server.registered_at.isoformat(),
                    "last_seen": server.last_seen.isoformat() if server.last_seen else None,
                    "health_status": server.health_status,
                    "tags": server.tags
                }
                for server in servers
            ],
            "total_count": len(servers),
            "fetched_at": datetime.utcnow().isoformat()
        }
    
    def _get_all_capabilities_resource(self) -> Dict[str, Any]:
        """
        Resource providing collective capabilities of all registered servers.
        """
        servers = self.db_service.get_all_servers()
        
        # Aggregate capabilities across all servers
        all_capabilities = {
            "resources": False,
            "tools": False,
            "prompts": False,
            "roots": False,
            "sampling": False
        }
        
        for server in servers:
            caps = server.capabilities
            all_capabilities["resources"] = all_capabilities["resources"] or caps.resources
            all_capabilities["tools"] = all_capabilities["tools"] or caps.tools
            all_capabilities["prompts"] = all_capabilities["prompts"] or caps.prompts
            all_capabilities["roots"] = all_capabilities["roots"] or caps.roots
            all_capabilities["sampling"] = all_capabilities["sampling"] or caps.sampling
        
        return {
            "collective_capabilities": all_capabilities,
            "server_count": len(servers),
            "fetched_at": datetime.utcnow().isoformat()
        }
    
    def _get_health_status_resource(self) -> Dict[str, Any]:
        """
        Resource providing current health status of registered servers.
        """
        servers = self.db_service.get_all_servers()
        
        health_summary = {
            "total_servers": len(servers),
            "healthy": 0,
            "unhealthy": 0,
            "unknown": 0,
            "details": []
        }
        
        for server in servers:
            health_summary[server.health_status] += 1
            health_summary["details"].append({
                "id": server.id,
                "name": server.name,
                "status": server.health_status
            })
        
        health_summary["fetched_at"] = datetime.utcnow().isoformat()
        return health_summary
    
    def run(self, transport: str = "stdio", **kwargs):
        """
        Run the registry server.

        Args:
            transport: Transport method ('stdio', 'streamable-http', etc.)
            **kwargs: Additional arguments for the transport (host, port for HTTP)
        """
        import asyncio
        import uvicorn
        
        # Define an async wrapper to properly manage the event loop
        async def run_with_health_monitor():
            # Start the health monitor in the background
            health_task = asyncio.create_task(self.health_monitor.start_periodic_health_checks())
            
            # Run the MCP server based on transport type
            if transport == "streamable-http":
                # For streamable-http, we need to run the FastAPI app with uvicorn
                # But we need to do this properly within the async context
                # We'll run the app in a separate thread or use an alternative approach
                host = kwargs.get("host", "0.0.0.0")
                port = kwargs.get("port", 8080)
                
                # Get the FastAPI app for streamable HTTP transport
                app = self.mcp.streamable_http_app
                
                # Run the app in a separate thread so we can continue with the event loop
                import threading
                import time
                
                def run_uvicorn():
                    uvicorn.run(app, host=host, port=port, log_level="info")
                
                # Start uvicorn in a separate thread
                server_thread = threading.Thread(target=run_uvicorn, daemon=True)
                server_thread.start()
                
                # Keep the main event loop running
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    print("Shutting down server...")
            else:
                # For stdio transport, run normally
                await self.mcp.run(transport=transport)

        # Run the async wrapper
        asyncio.run(run_with_health_monitor())


# For standalone execution
if __name__ == "__main__":
    import sys
    
    registry_server = RegistryServer()
    
    # Determine transport based on arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--http":
        registry_server.run(transport="streamable-http", host="0.0.0.0", port=8080)
    else:
        # Default to stdio for local connections
        registry_server.run(transport="stdio")