"""
Base MCP Server Implementation

This module defines the base class for an MCP server that can be extended with specific functionality.
"""
import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
import os

import mcp.types as types
from mcp.server import Server
from mcp import stdio_server
from fastapi import FastAPI
import uvicorn

from .errors import (
    RPCException,
    ParseError,
    InvalidRequestError,
    MethodNotFoundError,
    InvalidParamsError,
    InternalError,
    handle_rpc_error
)


class BaseMCPServer:
    """
    Base class for an MCP server that handles registration with the registry and basic functionality.
    """
    
    def __init__(self, transport: str = "stdio", host: str = "0.0.0.0", port: int = 8080):
        self.transport = transport
        self.host = host
        self.port = port
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Server identification
        self.id: Optional[str] = None
        self.name: str = "base-mcp-server"
        self.description: str = "Base MCP server skeleton"
        
        # Server capabilities as defined in the registry requirements
        self.capabilities = {
            "resources": False,
            "tools": False,
            "prompts": False,
            "roots": False,
            "sampling": False
        }
        
        # Metadata and tags
        self.metadata: Dict[str, Any] = {}
        self.tags: List[str] = []
        
        # Health status
        self.health_status = "unknown"
        self.last_seen: Optional[datetime] = None
        
        # Internal server instance
        self._server: Optional[Server] = None
        self._shutdown_event = asyncio.Event()
        self._http_server_task: Optional[asyncio.Task] = None
        self._health_monitor_task: Optional[asyncio.Task] = None
        
        # Initialize the MCP server based on transport
        self._initialize_server()
        
        # Define the OpenRPC schema for this server
        self._openrpc_schema = self._generate_openrpc_schema()
    
    def _initialize_server(self):
        """Initialize the underlying MCP server based on the selected transport."""
        self._server = Server(self.name)
        
        # Add default handlers
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """Setup default handlers for basic MCP functionality."""
        # Add handlers for basic functionality
        pass

    def _generate_openrpc_schema(self) -> Dict[str, Any]:
        """Generate the OpenRPC schema for this server."""
        # This is a simplified version - in a real implementation, 
        # this would be a complete OpenRPC schema
        return {
            "openrpc": "1.3.2",
            "info": {
                "title": self.name,
                "description": self.description,
                "version": "1.0.0"
            },
            "servers": [
                {
                    "url": self._get_endpoint(),
                    "name": self.name,
                    "description": self.description
                }
            ],
            "methods": [
                {
                    "name": "rpc.discover",
                    "summary": "Return the OpenRPC schema for this service",
                    "description": "Returns the complete OpenRPC schema describing this service.",
                    "params": [],
                    "result": {
                        "name": "discoverResult",
                        "schema": {
                            "$ref": "#"
                        }
                    }
                }
            ]
        }

    async def handle_discover_method(self) -> Dict[str, Any]:
        """Handle the rpc.discover method call."""
        return self._openrpc_schema
    
    def set_capability(self, capability: str, enabled: bool):
        """Enable or disable a specific capability."""
        if capability in self.capabilities:
            self.capabilities[capability] = enabled
            self.logger.info(f"Capability '{capability}' set to {enabled}")
        else:
            self.logger.warning(f"Unknown capability: {capability}")
    
    def add_tag(self, tag: str):
        """Add a tag to the server."""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def set_metadata(self, key: str, value: str):
        """Set metadata for the server."""
        self.metadata[key] = value
    
    async def start(self):
        """Start the MCP server."""
        self.logger.info(f"Starting server with transport: {self.transport}")
        
        if self.transport == "stdio":
            await self._start_stdio()
        elif self.transport == "http":
            await self._start_http()
        else:
            raise ValueError(f"Unsupported transport: {self.transport}")
        
        self.logger.info("Server started successfully")
        self.health_status = "healthy"
        self.last_seen = datetime.now()
    
    async def _start_stdio(self):
        """Start the server using stdio transport."""
        async with stdio_server(self._server) as make_socket:
            await make_socket()
    
    async def _start_http(self):
        """Start the server using HTTP transport."""
        self.logger.info(f"Starting HTTP server on {self.host}:{self.port}")
        
        # Create FastAPI app
        app = FastAPI(title=self.name, description=self.description)
        
        # Add security headers middleware
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.responses import Response
        
        class SecurityHeadersMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                response = await call_next(request)
                # Add security headers
                response.headers["X-Content-Type-Options"] = "nosniff"
                response.headers["X-Frame-Options"] = "DENY"
                response.headers["X-XSS-Protection"] = "1; mode=block"
                return response
        
        app.add_middleware(SecurityHeadersMiddleware)
        
        # Add health check endpoint as required by the registry
        @app.get("/health")
        async def health_check():
            return {
                "status": self.health_status,
                "timestamp": self.last_seen.isoformat() if self.last_seen else None,
                "server": self.name
            }
        
        # Add security configuration for production
        if os.getenv("ENVIRONMENT") == "production":
            # Add HTTPS redirect middleware if needed
            from starlette.responses import RedirectResponse
            @app.middleware("http")
            async def force_https(request, call_next):
                if request.url.scheme != "https" and os.getenv("FORCE_HTTPS", "").lower() == "true":
                    https_url = request.url.replace(scheme="https")
                    return RedirectResponse(url=str(https_url))
                response = await call_next(request)
                return response
        
        # Add the MCP server routes to the FastAPI app
        # Implement both GET and POST for /rpc endpoint as per OpenRPC spec
        
        # Import required classes
        from fastapi import Request
        
        # GET /rpc: Provides information about the MCP server capabilities
        @app.get("/rpc")
        async def get_rpc_info():
            return {
                "server_info": {
                    "name": self.name,
                    "description": self.description,
                    "capabilities": self.capabilities,
                    "endpoint": self._get_endpoint()
                }
            }
        
        # POST /rpc: Accepts JSON-RPC 2.0 requests via POST method for MCP protocol communication
        @app.post("/rpc")
        async def handle_rpc_post(request: Request):
            from starlette.requests import Request as StarletteRequest
            
            # Get raw body to process JSON-RPC request
            body_bytes = await request.body()
            try:
                rpc_request = json.loads(body_bytes.decode())
                
                # Process the JSON-RPC request
                if rpc_request.get("method") == "rpc.discover":
                    result = await self.handle_discover_method()
                    
                    # Create JSON-RPC response
                    response = {
                        "jsonrpc": "2.0",
                        "result": result,
                        "id": rpc_request.get("id")
                    }
                    return response
                else:
                    # For other methods, return method not found error
                    response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32601,  # Method not found
                            "message": "Method not implemented"
                        },
                        "id": rpc_request.get("id")
                    }
                    return response
            except json.JSONDecodeError:
                # Invalid JSON
                response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,  # Parse error
                        "message": "Parse error"
                    },
                    "id": None
                }
                return response
            except Exception as e:
                # Internal error
                response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,  # Internal error
                        "message": f"Internal error: {str(e)}"
                    },
                    "id": rpc_request.get("id") if 'rpc_request' in locals() else None
                }
                return response

        # Run the server in a background task
        config = uvicorn.Config(
            app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)

        # Run the server in a background task
        self._http_server_task = asyncio.create_task(server.serve())

        # Wait for the server to actually start
        await asyncio.sleep(0.1)
    
    async def shutdown(self):
        """Shutdown the MCP server."""
        self.logger.info("Shutting down server")
        
        # Cancel the HTTP server task if it exists
        if self._http_server_task:
            self._http_server_task.cancel()
            try:
                await self._http_server_task
            except asyncio.CancelledError:
                pass  # Expected when cancelling the task
        
        # Cancel the health monitor task if it exists
        if self._health_monitor_task:
            self._health_monitor_task.cancel()
            try:
                await self._health_monitor_task
            except asyncio.CancelledError:
                pass  # Expected when cancelling the task
        
        self.health_status = "unhealthy"
        self._shutdown_event.set()
    
    async def wait_for_shutdown(self):
        """Wait for the server to be shut down."""
        await self._shutdown_event.wait()
    
    def get_registration_info(self) -> Dict[str, Any]:
        """Get the server information needed for registration with the registry."""
        return {
            "name": self.name,
            "description": self.description,
            "endpoint": self._get_endpoint(),
            "capabilities": self.capabilities,
            "metadata": self.metadata,
            "tags": self.tags
        }
    
    def _get_endpoint(self) -> str:
        """Get the endpoint URL based on transport method."""
        if self.transport == "stdio":
            return "stdio://"
        elif self.transport == "http":
            return f"http://{self.host}:{self.port}"
        else:
            # For other transports, return a generic identifier
            return f"{self.transport}://"
    
    async def register_with_registry(self, registry_endpoint: str = "stdio://"):
        """
        Register this server with the MCP registry.
        
        Args:
            registry_endpoint: The endpoint of the registry server to register with
        """
        self.logger.info(f"Registering with registry at {registry_endpoint}")
        
        # Import here to avoid circular dependencies
        from .registry_client import RegistryClient
        
        # Prepare registration data
        registration_data = self.get_registration_info()
        
        # Use the registry client to register
        async with RegistryClient(registry_endpoint) as client:
            result = await client.register_server(registration_data)
            
            if result.get("success"):
                # Store the server ID returned by the registry
                self.id = result.get("server_id")
                self.logger.info(f"Server {self.name} registered successfully with ID: {self.id}")
            else:
                self.logger.error(f"Failed to register server: {result.get('error', 'Unknown error')}")
            
            return result
    
    def update_health_status(self, status: str):
        """Update the health status of the server."""
        if status in ["healthy", "unhealthy", "unknown"]:
            self.health_status = status
            self.last_seen = datetime.now()
            self.logger.info(f"Health status updated to: {status}")
        else:
            self.logger.warning(f"Invalid health status: {status}")
    
    async def _health_monitor(self, interval: int = 60):
        """
        Background task to periodically check and report server health status.
        
        Args:
            interval: Time in seconds between health checks
        """
        self.logger.info(f"Starting health monitor with {interval}s interval")
        
        while not self._shutdown_event.is_set():
            try:
                # Perform health checks
                await self._perform_health_check()
                
                # If we have a registry connection, update our status
                if hasattr(self, '_registry_endpoint') and self.id:
                    await self._report_health_to_registry()
                
                # Wait for the specified interval or until shutdown
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=interval)
                except asyncio.TimeoutError:
                    # Normal case - continue the loop
                    continue
                
                # If we reach here, shutdown event was set
                break
                
            except Exception as e:
                self.logger.error(f"Error in health monitor: {e}")
                # Even if there's an error, continue checking
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=interval)
                except asyncio.TimeoutError:
                    continue
    
    async def _perform_health_check(self):
        """
        Perform internal health checks on the server.
        Override this method in subclasses to implement custom health checks.
        """
        # Basic health check - just confirm we're still running
        self.update_health_status("healthy")
        self.logger.debug("Health check completed")
    
    async def _report_health_to_registry(self):
        """
        Report the current health status to the registry.
        """
        if not hasattr(self, '_registry_endpoint'):
            return
        
        try:
            from .registry_client import RegistryClient
            
            async with RegistryClient(self._registry_endpoint) as client:
                result = await client.update_server_status(self.id, self.health_status)
                
                if not result.get("success"):
                    self.logger.warning(f"Failed to update health status in registry: {result.get('error')}")
                else:
                    self.logger.debug(f"Health status reported to registry: {self.health_status}")
        except Exception as e:
            self.logger.error(f"Error reporting health to registry: {e}")
    
    def enable_health_monitoring(self, interval: int = 60, registry_endpoint: str = None):
        """
        Enable automatic health monitoring and reporting.
        
        Args:
            interval: Time in seconds between health checks
            registry_endpoint: Registry endpoint to report health status to
        """
        if registry_endpoint:
            self._registry_endpoint = registry_endpoint
        
        # Cancel any existing health monitor task
        if self._health_monitor_task:
            self._health_monitor_task.cancel()
        
        # Start a new health monitor task
        self._health_monitor_task = asyncio.create_task(self._health_monitor(interval))
        self.logger.info(f"Health monitoring enabled with {interval}s interval")


class MCPServerExtension(ABC):
    """
    Abstract base class for extending the base MCP server with specific functionality.
    Subclasses should implement the required methods to add specific capabilities.
    """
    
    @abstractmethod
    async def initialize(self, server: BaseMCPServer):
        """Initialize the extension with the server instance."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the name of this extension."""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get the description of this extension."""
        pass