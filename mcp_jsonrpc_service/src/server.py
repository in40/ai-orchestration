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
from mcp.server import FastMCP
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

        # Internal server instance using FastMCP as recommended
        self._server: Optional[FastMCP] = None
        self._shutdown_event = asyncio.Event()
        self._http_server_task: Optional[asyncio.Task] = None
        self._health_monitor_task: Optional[asyncio.Task] = None

        # Initialize the MCP server based on transport
        self._initialize_server()

        # Define the OpenRPC schema for this server
        self._openrpc_schema = self._generate_openrpc_schema()
    
    def _initialize_server(self):
        """Initialize the underlying MCP server based on the selected transport.

        For HTTP transport, sets up endpoints at /mcp for both GET and POST methods
        as per the new MCP standards, replacing the deprecated /rpc endpoint.
        """
        # Initialize using FastMCP as recommended in the technology rules
        self._server = FastMCP(self.name, streamable_http_path="/mcp")

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
        schema = {
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
        
        # If using HTTP transport, add information about the /mcp endpoint
        if self.transport == "http":
            schema["paths"] = {
                "/mcp": {
                    "post": {
                        "summary": "Handle MCP JSON-RPC requests over HTTP",
                        "description": "Accepts JSON-RPC 2.0 requests via POST method for MCP protocol communication",
                        "operationId": "handleMcpPost"
                    },
                    "get": {
                        "summary": "MCP Protocol Info Endpoint",
                        "description": "Provides information about the MCP server capabilities",
                        "operationId": "handleMcpGet"
                    }
                }
            }
        
        return schema

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
                "status": "healthy",  # According to requirements, should return 200 when operational
                "timestamp": datetime.utcnow().isoformat(),
                "details": {
                    "server": self.name,
                    "health_status": self.health_status
                }
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
        # Implement both GET and POST for /mcp endpoint as per new MCP standards

        # Import required classes
        from fastapi import Request
        from fastapi.responses import JSONResponse

        # GET /mcp: Provides information about the MCP server capabilities
        @app.get("/mcp")
        async def get_mcp_info(request: Request):
            # Check Accept header as required by MCP protocol
            accept_header = request.headers.get("accept", "")
            accepts_json = "application/json" in accept_header
            accepts_stream = "text/event-stream" in accept_header

            if not (accepts_json and accepts_stream):
                # Return 406 Not Acceptable if client doesn't accept both required content types
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": 406,  # Not Acceptable
                        "message": "Not Acceptable - Client must accept both application/json and text/event-stream"
                    },
                    "id": None
                }
                return JSONResponse(content=error_response, status_code=406)

            return {
                "server_info": {
                    "name": self.name,
                    "description": self.description,
                    "capabilities": self.capabilities,
                    "endpoint": self._get_endpoint()
                }
            }

        # POST /mcp: Accepts JSON-RPC 2.0 requests via POST method for MCP protocol communication
        @app.post("/mcp")
        async def handle_mcp_post(request: Request):
            from starlette.requests import Request as StarletteRequest

            # Check Accept header as required by MCP protocol
            accept_header = request.headers.get("accept", "")
            accepts_json = "application/json" in accept_header
            accepts_stream = "text/event-stream" in accept_header

            if not (accepts_json and accepts_stream):
                # Return 406 Not Acceptable if client doesn't accept both required content types
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": 406,  # Not Acceptable
                        "message": "Not Acceptable - Client must accept both application/json and text/event-stream"
                    },
                    "id": None
                }
                return JSONResponse(content=error_response, status_code=406)

            # Get raw body to process JSON-RPC request
            body_bytes = await request.body()
            try:
                rpc_request = json.loads(body_bytes.decode())

                # Check for session context for security-critical operations
                method_requires_session = rpc_request.get("method") in [
                    "registry-register_server", 
                    "registry-update_server_status"
                ]
                
                if method_requires_session:
                    # In a real implementation, we would validate the session here
                    # For now, we'll just check if there's a session header
                    session_id = request.headers.get("x-session-id")
                    if not session_id:
                        # Return -32600 error for missing session ID
                        error_response = {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32600,  # Invalid Request (Bad Request)
                                "message": "Bad Request: Missing session ID"
                            },
                            "id": rpc_request.get("id")
                        }
                        return JSONResponse(content=error_response, status_code=400)

                # Process the JSON-RPC request
                if rpc_request.get("method") == "rpc.discover":
                    result = await self.handle_discover_method()

                    # Create JSON-RPC response
                    response = {
                        "jsonrpc": "2.0",
                        "result": result,
                        "id": rpc_request.get("id")
                    }
                    return JSONResponse(content=response)
                elif rpc_request.get("method") == "registry-register_server":
                    # Handle registry registration request
                    result = await self.handle_register_server(rpc_request.get("params", {}))
                    
                    # Create JSON-RPC response
                    response = {
                        "jsonrpc": "2.0",
                        "result": result,
                        "id": rpc_request.get("id")
                    }
                    return JSONResponse(content=response)
                elif rpc_request.get("method") == "registry-update_server_status":
                    # Handle registry update server status request
                    params = rpc_request.get("params", {})
                    server_id = params.get("server_id")
                    health_status = params.get("health_status")
                    result = await self.handle_update_server_status(server_id, health_status)
                    
                    # Create JSON-RPC response
                    response = {
                        "jsonrpc": "2.0",
                        "result": result,
                        "id": rpc_request.get("id")
                    }
                    return JSONResponse(content=response)
                elif rpc_request.get("method") == "registry-list_servers":
                    # Handle registry list servers request
                    result = await self.handle_list_servers()
                    
                    # Create JSON-RPC response
                    response = {
                        "jsonrpc": "2.0",
                        "result": result,
                        "id": rpc_request.get("id")
                    }
                    return JSONResponse(content=response)
                elif rpc_request.get("method") == "registry-get_server_details":
                    # Handle registry get server details request
                    params = rpc_request.get("params", {})
                    server_id = params.get("server_id")
                    result = await self.handle_get_server_details(server_id)
                    
                    # Create JSON-RPC response
                    response = {
                        "jsonrpc": "2.0",
                        "result": result,
                        "id": rpc_request.get("id")
                    }
                    return JSONResponse(content=response)
                elif rpc_request.get("method") == "registry-search_servers":
                    # Handle registry search servers request
                    params = rpc_request.get("params", {})
                    query = params.get("query", "")
                    tags = params.get("tags", [])
                    result = await self.handle_search_servers(query, tags)
                    
                    # Create JSON-RPC response
                    response = {
                        "jsonrpc": "2.0",
                        "result": result,
                        "id": rpc_request.get("id")
                    }
                    return JSONResponse(content=response)
                elif rpc_request.get("method") == "registry://servers":
                    # Handle registry servers resource request
                    result = await self.handle_all_servers_resource()
                    
                    # Create JSON-RPC response
                    response = {
                        "jsonrpc": "2.0",
                        "result": result,
                        "id": rpc_request.get("id")
                    }
                    return JSONResponse(content=response)
                elif rpc_request.get("method") == "registry://capabilities":
                    # Handle registry capabilities resource request
                    result = await self.handle_all_capabilities_resource()
                    
                    # Create JSON-RPC response
                    response = {
                        "jsonrpc": "2.0",
                        "result": result,
                        "id": rpc_request.get("id")
                    }
                    return JSONResponse(content=response)
                elif rpc_request.get("method") == "registry://health-status":
                    # Handle registry health status resource request
                    result = await self.handle_health_status_resource()
                    
                    # Create JSON-RPC response
                    response = {
                        "jsonrpc": "2.0",
                        "result": result,
                        "id": rpc_request.get("id")
                    }
                    return JSONResponse(content=response)
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
                    return JSONResponse(content=response, status_code=404)
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
                return JSONResponse(content=response, status_code=400)
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
                return JSONResponse(content=response, status_code=500)

        # Update the OpenRPC schema to reflect the new endpoint
        self._openrpc_schema = self._generate_openrpc_schema()

        # Update the docstring to reflect the new endpoint
        """Initialize the underlying MCP server based on the selected transport.

        For HTTP transport, sets up endpoints at /mcp for both GET and POST methods
        as per the new MCP standards, replacing the deprecated /rpc endpoint.
        """

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

    async def handle_register_server(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the registry-register_server method call."""
        # This is a simplified implementation - in a real registry, 
        # you would store server info in a database
        name = params.get("name", "")
        description = params.get("description", "")
        endpoint = params.get("endpoint", "")
        capabilities = params.get("capabilities", {})
        metadata = params.get("metadata", {})
        tags = params.get("tags", [])

        # Generate a server ID (in a real implementation, this would be stored in a database)
        import hashlib
        server_id = hashlib.sha256(f"{name}{endpoint}{str(capabilities)}".encode()).hexdigest()[:16]

        # Store server info (in memory for this example)
        if not hasattr(self, '_registered_servers'):
            self._registered_servers = {}
        
        self._registered_servers[server_id] = {
            "id": server_id,
            "name": name,
            "description": description,
            "endpoint": endpoint,
            "capabilities": capabilities,
            "metadata": metadata,
            "tags": tags,
            "registered_at": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "health_status": "unknown"
        }

        return {
            "success": True,
            "server_id": server_id,
            "message": f"Server {name} registered successfully"
        }

    async def handle_update_server_status(self, server_id: str, health_status: str) -> Dict[str, Any]:
        """Handle the registry-update_server_status method call."""
        if not hasattr(self, '_registered_servers') or server_id not in self._registered_servers:
            return {
                "success": False,
                "error": f"Server with ID {server_id} not found"
            }

        # Update the server's health status
        self._registered_servers[server_id]["health_status"] = health_status
        self._registered_servers[server_id]["last_seen"] = datetime.now().isoformat()

        return {
            "success": True,
            "message": f"Status for server {server_id} updated to {health_status}"
        }

    async def handle_list_servers(self) -> Dict[str, Any]:
        """Handle the registry-list_servers method call."""
        if not hasattr(self, '_registered_servers'):
            servers = []
        else:
            servers = list(self._registered_servers.values())

        return {
            "servers": servers
        }

    async def handle_get_server_details(self, server_id: str) -> Dict[str, Any]:
        """Handle the registry-get_server_details method call."""
        if not hasattr(self, '_registered_servers') or server_id not in self._registered_servers:
            return {
                "error": f"Server with ID {server_id} not found"
            }

        return self._registered_servers[server_id]

    async def handle_search_servers(self, query: str = "", tags: List[str] = []) -> Dict[str, Any]:
        """Handle the registry-search_servers method call."""
        if not hasattr(self, '_registered_servers'):
            servers = []
        else:
            servers = list(self._registered_servers.values())

        # Filter servers based on query and tags
        filtered_servers = []
        for server in servers:
            # Check if query matches name or description
            matches_query = not query or query.lower() in server["name"].lower() or query.lower() in server.get("description", "").lower()
            
            # Check if all tags are present
            matches_tags = not tags or all(tag in server.get("tags", []) for tag in tags)
            
            if matches_query and matches_tags:
                filtered_servers.append(server)

        return {
            "servers": filtered_servers
        }

    async def handle_all_servers_resource(self) -> Dict[str, Any]:
        """Handle the registry://servers resource call."""
        if not hasattr(self, '_registered_servers'):
            servers = []
        else:
            servers = list(self._registered_servers.values())

        return {
            "servers": servers,
            "total_count": len(servers),
            "fetched_at": datetime.now().isoformat()
        }

    async def handle_all_capabilities_resource(self) -> Dict[str, Any]:
        """Handle the registry://capabilities resource call."""
        if not hasattr(self, '_registered_servers'):
            collective_capabilities = {
                "resources": False,
                "tools": False,
                "prompts": False,
                "roots": False,
                "sampling": False
            }
            server_count = 0
        else:
            servers = list(self._registered_servers.values())
            server_count = len(servers)
            
            # Aggregate capabilities across all servers
            collective_capabilities = {
                "resources": any(server["capabilities"].get("resources", False) for server in servers),
                "tools": any(server["capabilities"].get("tools", False) for server in servers),
                "prompts": any(server["capabilities"].get("prompts", False) for server in servers),
                "roots": any(server["capabilities"].get("roots", False) for server in servers),
                "sampling": any(server["capabilities"].get("sampling", False) for server in servers)
            }

        return {
            "collective_capabilities": collective_capabilities,
            "server_count": server_count,
            "fetched_at": datetime.now().isoformat()
        }

    async def handle_health_status_resource(self) -> Dict[str, Any]:
        """Handle the registry://health-status resource call."""
        if not hasattr(self, '_registered_servers'):
            servers = []
        else:
            servers = list(self._registered_servers.values())

        # Count health statuses
        total_servers = len(servers)
        healthy = sum(1 for server in servers if server.get("health_status") == "healthy")
        unhealthy = sum(1 for server in servers if server.get("health_status") == "unhealthy")
        unknown = sum(1 for server in servers if server.get("health_status") == "unknown")

        # Create details list
        details = []
        for server in servers:
            details.append({
                "id": server["id"],
                "name": server["name"],
                "status": server.get("health_status", "unknown")
            })

        return {
            "total_servers": total_servers,
            "healthy": healthy,
            "unhealthy": unhealthy,
            "unknown": unknown,
            "details": details,
            "fetched_at": datetime.now().isoformat()
        }
    
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

        # Pre-registration validation
        if not self._validate_server_readiness():
            self.logger.error("Server is not ready for registration")
            return {"success": False, "error": "Server is not ready for registration"}

        # Import here to avoid circular dependencies
        from .registry_client import RegistryClient

        # Prepare registration data
        registration_data = self.get_registration_info()

        # Validate registration data accuracy
        if not self._validate_registration_data(registration_data):
            self.logger.error("Registration data validation failed")
            return {"success": False, "error": "Registration data validation failed"}

        # Attempt registration with retry logic
        max_attempts = getattr(self, 'max_registration_attempts', 3)
        attempt = 0
        
        while attempt < max_attempts:
            try:
                self.logger.info(f"Attempt {attempt + 1}/{max_attempts} for registration")
                
                # Use the registry client to register
                async with RegistryClient(registry_endpoint) as client:
                    result = await client.register_server(registration_data)

                    if result.get("success"):
                        # Store the server ID returned by the registry
                        self.id = result.get("server_id")
                        self.logger.info(f"Server {self.name} registered successfully with ID: {self.id}")
                        
                        # Post-registration validation
                        await self._post_registration_validation(result)
                        
                        return result
                    else:
                        self.logger.error(f"Registration attempt {attempt + 1} failed: {result.get('error', 'Unknown error')}")
                        attempt += 1
                        
                        if attempt < max_attempts:
                            # Exponential backoff: wait 2^attempt seconds
                            wait_time = min(2 ** attempt, 60)  # Cap at 60 seconds
                            self.logger.info(f"Waiting {wait_time}s before retry...")
                            await asyncio.sleep(wait_time)
                        else:
                            self.logger.error(f"All {max_attempts} registration attempts failed")
                            return result
                            
            except Exception as e:
                attempt += 1
                self.logger.error(f"Registration attempt {attempt} failed with exception: {str(e)}")
                
                if attempt >= max_attempts:
                    self.logger.error(f"All {max_attempts} registration attempts failed due to exceptions")
                    return {"success": False, "error": f"Registration failed after {max_attempts} attempts: {str(e)}"}
                
                # Exponential backoff: wait 2^attempt seconds
                wait_time = min(2 ** attempt, 60)  # Cap at 60 seconds
                self.logger.info(f"Waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)

    def _validate_server_readiness(self) -> bool:
        """
        Validate that the server is fully operational before registration.
        
        Returns:
            bool: True if server is ready, False otherwise
        """
        # Check if required capabilities are properly implemented
        # This is a simplified check - in a real implementation, you'd check
        # that each advertised capability actually works
        for capability, enabled in self.capabilities.items():
            if enabled:
                # Add specific validation for each capability type
                if capability == "tools" and not hasattr(self, '_tools_registered'):
                    self.logger.warning(f"Tools capability enabled but no tools registered")
                elif capability == "resources" and not hasattr(self, '_resources_registered'):
                    self.logger.warning(f"Resources capability enabled but no resources registered")
                elif capability == "prompts" and not hasattr(self, '_prompts_registered'):
                    self.logger.warning(f"Prompts capability enabled but no prompts registered")
        
        # Check if health check endpoint is accessible (if using HTTP transport)
        if self.transport == "http":
            # In a real implementation, we might check if the health endpoint responds
            pass
        
        # Server is considered ready if it has been initialized properly
        return self._server is not None

    def _validate_registration_data(self, registration_data: Dict[str, Any]) -> bool:
        """
        Validate the registration data before sending to registry.
        
        Args:
            registration_data: The registration data to validate
            
        Returns:
            bool: True if data is valid, False otherwise
        """
        required_fields = ["name", "endpoint", "capabilities"]
        
        for field in required_fields:
            if field not in registration_data or not registration_data[field]:
                self.logger.error(f"Missing required field in registration data: {field}")
                return False
        
        # Validate capabilities structure
        capabilities = registration_data.get("capabilities", {})
        required_caps = ["resources", "tools", "prompts", "roots", "sampling"]
        
        for cap in required_caps:
            if cap not in capabilities:
                self.logger.error(f"Missing capability in registration data: {cap}")
                return False
            if not isinstance(capabilities[cap], bool):
                self.logger.error(f"Capability {cap} must be boolean, got {type(capabilities[cap])}")
                return False
        
        return True

    async def _post_registration_validation(self, registration_result: Dict[str, Any]):
        """
        Perform validation after successful registration.
        
        Args:
            registration_result: The result from the registration call
        """
        self.logger.info("Performing post-registration validation...")
        
        # Update internal state to reflect registration
        server_id = registration_result.get("server_id")
        if server_id:
            self.id = server_id
            self.logger.info(f"Updated server ID to: {server_id}")
        
        # Optionally, verify registration by querying the registry
        # This is an optional step that could be implemented based on requirements
    
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