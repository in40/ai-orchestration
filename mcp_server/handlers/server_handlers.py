"""
Standard MCP Server Handlers
Implements all standard server methods as per MCP specification
"""
from typing import Dict, Any, List, Optional
from datetime import datetime


class McpServerHandlers:
    """Handler class containing all standard MCP server methods"""
    
    def __init__(self, enable_registry=False, use_postgres=False, postgres_config=None):
        # Initialize server capabilities
        self.capabilities = {
            "prompts": {
                "listChanged": False
            },
            "resources": {
                "listChanged": False
            },
            "tools": {
                "listChanged": False
            }
        }
        
        # Sample data for demonstration
        self.tools = [
            {
                "name": "example_tool",
                "description": "An example tool for demonstration",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "param1": {
                            "type": "string",
                            "description": "An example parameter"
                        }
                    },
                    "required": ["param1"]
                }
            }
        ]
        
        self.resources = [
            {
                "uri": "example://resource1",
                "name": "Example Resource 1",
                "description": "An example resource for demonstration"
            }
        ]
        
        self.prompts = [
            {
                "name": "example_prompt",
                "description": "An example prompt template",
                "arguments": [
                    {
                        "name": "param1",
                        "type": "string",
                        "description": "An example parameter"
                    }
                ]
            }
        ]
        
        # Optional registry functionality
        self.enable_registry = enable_registry
        self.use_postgres = use_postgres
        self.postgres_config = postgres_config or {}
        
        if self.enable_registry:
            if self.use_postgres:
                from ..utils.postgres_registry_db import PostgresServiceRegistry
                try:
                    # Use PostgreSQL registry with provided configuration
                    self.service_registry = PostgresServiceRegistry(
                        host=self.postgres_config.get("host", "localhost"),
                        port=self.postgres_config.get("port", 5432),
                        database=self.postgres_config.get("database", "mcp_registry"),
                        user=self.postgres_config.get("user", "postgres"),
                        password=self.postgres_config.get("password", "")
                    )
                except Exception as e:
                    print(f"Failed to connect to PostgreSQL registry: {e}")
                    print("Falling back to SQLite registry")
                    from ..utils.service_registry_db import ServiceRegistryDB
                    self.service_registry = ServiceRegistryDB()
            else:
                from ..utils.service_registry_db import ServiceRegistryDB
                self.service_registry = ServiceRegistryDB()
            
            # Add registry-specific tools
            self.tools.extend([
                {
                    "name": "register_service",
                    "description": "Register a service with the MCP registry",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Unique service identifier"},
                            "name": {"type": "string", "description": "Service name"},
                            "description": {"type": "string", "description": "Service description"},
                            "endpoint": {"type": "string", "description": "Service endpoint URL"},
                            "capabilities": {
                                "type": "object",
                                "description": "Service capabilities"
                            }
                        },
                        "required": ["id", "name", "endpoint"]
                    }
                },
                {
                    "name": "list_services",
                    "description": "List all registered services in the MCP registry",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "filter": {
                                "type": "string",
                                "description": "Optional filter for services"
                            }
                        }
                    }
                }
            ])
    
    def handle_initialize(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Handle initialize request as per MCP specification
        """
        # Extract client info
        client_info = params.get('clientInfo', {})
        
        # Prepare server capabilities response
        server_capabilities = {
            "serverInfo": {
                "name": "mcp-standard-server",
                "version": "1.0.0"
            },
            "capabilities": self.capabilities
        }
        
        return server_capabilities
    
    def handle_tools_list(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Handle tools/list request as per MCP specification
        """
        # Pagination support
        pagination_token = params.get('pagination', {}).get('token')
        limit = params.get('pagination', {}).get('limit', len(self.tools))
        
        # Apply pagination if token is provided
        start_idx = 0
        if pagination_token:
            # In a real implementation, this would decode the token to get start index
            start_idx = int(pagination_token)
        
        end_idx = min(start_idx + limit, len(self.tools))
        paginated_tools = self.tools[start_idx:end_idx]
        
        response = {
            "tools": paginated_tools
        }
        
        # Add next token if there are more items
        if end_idx < len(self.tools):
            response["next"] = {
                "token": str(end_idx)
            }
        
        return response
    
    def handle_tools_call(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Handle tools/call request as per MCP specification
        """
        tool_name = params.get('name')
        tool_arguments = params.get('arguments', {})
        
        # Find the requested tool
        tool = None
        for t in self.tools:
            if t['name'] == tool_name:
                tool = t
                break
        
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        # Execute the tool (in a real implementation, this would call the actual tool)
        # For demonstration, we'll just return the arguments
        result = {
            "output": f"Executed tool '{tool_name}' with arguments: {tool_arguments}",
            "isError": False
        }
        
        return result
    
    def handle_resources_list(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Handle resources/list request as per MCP specification
        """
        # Pagination support
        pagination_token = params.get('pagination', {}).get('token')
        limit = params.get('pagination', {}).get('limit', len(self.resources))
        
        # Apply pagination if token is provided
        start_idx = 0
        if pagination_token:
            start_idx = int(pagination_token)
        
        end_idx = min(start_idx + limit, len(self.resources))
        paginated_resources = self.resources[start_idx:end_idx]
        
        response = {
            "resources": paginated_resources
        }
        
        # Add next token if there are more items
        if end_idx < len(self.resources):
            response["next"] = {
                "token": str(end_idx)
            }
        
        return response
    
    def handle_resources_read(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Handle resources/read request as per MCP specification
        """
        uri = params.get('uri')
        
        # Find the requested resource
        resource = None
        for r in self.resources:
            if r['uri'] == uri:
                resource = r
                break
        
        if not resource:
            raise ValueError(f"Resource with URI '{uri}' not found")
        
        # In a real implementation, this would read the actual resource content
        # For demonstration, we'll return sample content
        content = {
            "uri": uri,
            "contents": [
                {
                    "type": "text",
                    "text": f"Content of resource {uri} at {datetime.now().isoformat()}"
                }
            ],
            "version": "1.0"
        }
        
        return content
    
    def handle_prompts_list(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Handle prompts/list request as per MCP specification
        """
        # Pagination support
        pagination_token = params.get('pagination', {}).get('token')
        limit = params.get('pagination', {}).get('limit', len(self.prompts))
        
        # Apply pagination if token is provided
        start_idx = 0
        if pagination_token:
            start_idx = int(pagination_token)
        
        end_idx = min(start_idx + limit, len(self.prompts))
        paginated_prompts = self.prompts[start_idx:end_idx]
        
        response = {
            "prompts": paginated_prompts
        }
        
        # Add next token if there are more items
        if end_idx < len(self.prompts):
            response["next"] = {
                "token": str(end_idx)
            }
        
        return response
    
    def handle_prompts_get(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Handle prompts/get request as per MCP specification
        """
        prompt_name = params.get('name')
        arguments = params.get('arguments', {})
        
        # Find the requested prompt
        prompt = None
        for p in self.prompts:
            if p['name'] == prompt_name:
                prompt = p
                break
        
        if not prompt:
            raise ValueError(f"Prompt '{prompt_name}' not found")
        
        # In a real implementation, this would substitute the arguments into the prompt template
        # For demonstration, we'll return sample content
        resolved_prompt = {
            "description": f"Resolved prompt '{prompt_name}' with arguments: {arguments}",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"This is the resolved content for prompt '{prompt_name}' with arguments: {arguments}"
                        }
                    ]
                }
            ]
        }
        
        return resolved_prompt
    
    def handle_shutdown(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Handle shutdown request as per MCP specification
        """
        # In a real implementation, this would initiate graceful shutdown
        return {}
    
    def handle_register_service(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Handle registry/register request.

        This method allows other MCP servers to register themselves with this server
        when implementing a registry architecture.

        Expected parameters:
        - id: Unique identifier for the service
        - name: Human-readable name for the service
        - description: Brief description of the service
        - endpoint: Connection endpoint (URL, etc.)
        - capabilities: Dictionary of service capabilities

        Registration Protocol:
        1. Service sends a JSON-RPC request to registry's /send endpoint:
           {
             "jsonrpc": "2.0",
             "id": "req-123",
             "method": "registry/register",
             "params": {
               "id": "service-unique-id",
               "name": "Service Name",
               "description": "Description of the service",
               "endpoint": "http://service-host:port",
               "capabilities": {
                 "tools": ["tool1", "tool2"],
                 "resources": ["resource1", "resource2"],
                 "prompts": ["prompt1", "prompt2"]
               }
             }
           }

        2. Registry responds with success/failure:
           {
             "jsonrpc": "2.0",
             "id": "req-123",
             "result": {
               "success": true,
               "service_id": "service-unique-id",
               "message": "Service registered successfully"
             }
           }
        """
        print(f"DEBUG: handle_register_service called with params: {params.get('id', 'unknown')}")
        print(f"DEBUG: enable_registry: {getattr(self, 'enable_registry', False)}")
        print(f"DEBUG: service_registry exists: {hasattr(self, 'service_registry')}")
        
        if not hasattr(self, 'enable_registry') or not self.enable_registry:
            print("DEBUG: Registry functionality is not enabled")
            raise ValueError("Registry functionality is not enabled")

        if not hasattr(self, 'service_registry'):
            print("DEBUG: Service registry is not initialized")
            raise ValueError("Service registry is not initialized")

        print(f"DEBUG: Service registry type: {type(self.service_registry).__name__}")
        
        service_info = {
            "id": params.get("id"),
            "name": params.get("name"),
            "description": params.get("description"),
            "endpoint": params.get("endpoint"),
            "capabilities": params.get("capabilities", {})
        }
        
        print(f"DEBUG: Processing service registration: {service_info['id']}")

        # Validate required fields
        if not service_info["id"] or not service_info["name"] or not service_info["endpoint"]:
            print(f"DEBUG: Missing required fields in service_info: id={bool(service_info['id'])}, name={bool(service_info['name'])}, endpoint={bool(service_info['endpoint'])}")
            raise ValueError("Service registration requires 'id', 'name', and 'endpoint' parameters")

        print(f"DEBUG: Calling service_registry.register_service with id: {service_info['id']}")
        success = self.service_registry.register_service(service_info)
        print(f"DEBUG: register_service returned: {success}")

        result = {
            "success": success,
            "service_id": service_info["id"],
            "message": "Service registered successfully" if success else "Failed to register service"
        }
        print(f"DEBUG: Returning registration result: {result}")
        
        return result

    def handle_list_services(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Handle registry/list request.
        
        This method returns all registered services in the registry.
        
        Expected parameters:
        - filter: Optional filter string to search in service names/descriptions
        
        Discovery Protocol:
        1. AI agent sends a JSON-RPC request to registry's /send endpoint:
           {
             "jsonrpc": "2.0",
             "id": "req-456",
             "method": "registry/list",
             "params": {
               "filter": "database"  // optional
             }
           }
        
        2. Registry responds with list of services:
           {
             "jsonrpc": "2.0",
             "id": "req-456",
             "result": {
               "services": [
                 {
                   "id": "db-service-1",
                   "name": "Database Access Service",
                   "description": "Provides database query capabilities",
                   "endpoint": "http://localhost:8081",
                   "capabilities": {
                     "tools": ["query_db", "insert_record"],
                     "resources": ["db://users", "db://products"]
                   },
                   "registered_at": "2023-10-01T10:00:00Z",
                   "last_seen": "2023-10-01T12:00:00Z"
                 }
               ],
               "total_count": 1
             }
           }
        """
        print(f"DEBUG: handle_list_services called with params: {params}")
        print(f"DEBUG: enable_registry: {getattr(self, 'enable_registry', False)}")
        print(f"DEBUG: service_registry exists: {hasattr(self, 'service_registry')}")
        
        if not hasattr(self, 'enable_registry') or not self.enable_registry:
            print("DEBUG: Registry functionality is not enabled")
            raise ValueError("Registry functionality is not enabled")
        
        if not hasattr(self, 'service_registry'):
            print("DEBUG: Service registry is not initialized")
            raise ValueError("Service registry is not initialized")

        print(f"DEBUG: Service registry type: {type(self.service_registry).__name__}")
        
        filter_param = params.get("filter")
        print(f"DEBUG: Getting services from registry, filter: {filter_param}")
        services = self.service_registry.list_services()
        print(f"DEBUG: Retrieved {len(services)} services from registry")

        # Apply filter if provided
        if filter_param:
            print(f"DEBUG: Applying filter: {filter_param}")
            services = [s for s in services if filter_param.lower() in s["name"].lower() or 
                        filter_param.lower() in s["description"].lower()]
            print(f"DEBUG: After filtering: {len(services)} services")

        result = {
            "services": services,
            "total_count": len(services)
        }
        print(f"DEBUG: Returning list result with {len(services)} services")
        return result
        
    def handle_unregister_service(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Handle registry/unregister request.
        
        This method allows services to deregister themselves from the registry.
        
        Expected parameters:
        - id: Unique identifier of the service to unregister
        
        Deregistration Protocol:
        1. Service sends a JSON-RPC request to registry's /send endpoint:
           {
             "jsonrpc": "2.0",
             "id": "req-789",
             "method": "registry/unregister",
             "params": {
               "id": "service-unique-id"
             }
           }
        
        2. Registry responds with success/failure:
           {
             "jsonrpc": "2.0",
             "id": "req-789",
             "result": {
               "success": true,
               "message": "Service unregistered successfully"
             }
           }
        """
        if not hasattr(self, 'enable_registry') or not self.enable_registry:
            raise ValueError("Registry functionality is not enabled")
        
        if not hasattr(self, 'service_registry'):
            raise ValueError("Service registry is not initialized")

        service_id = params.get("id")
        if not service_id:
            raise ValueError("Service unregistration requires 'id' parameter")

        success = self.service_registry.unregister_service(service_id)

        return {
            "success": success,
            "message": "Service unregistered successfully" if success else "Failed to unregister service"
        }
    
    def register_handlers(self, rpc_handler):
        """Register all standard handlers with the RPC handler"""
        # Server initialization
        rpc_handler.register_request_handler('initialize', self.handle_initialize)
        rpc_handler.register_request_handler('shutdown', self.handle_shutdown)
        
        # Tools
        rpc_handler.register_request_handler('tools/list', self.handle_tools_list)
        rpc_handler.register_request_handler('tools/call', self.handle_tools_call)
        
        # Resources
        rpc_handler.register_request_handler('resources/list', self.handle_resources_list)
        rpc_handler.register_request_handler('resources/read', self.handle_resources_read)
        
        # Prompts
        rpc_handler.register_request_handler('prompts/list', self.handle_prompts_list)
        rpc_handler.register_request_handler('prompts/get', self.handle_prompts_get)
        
        # Registry handlers - available when registry is enabled
        rpc_handler.register_request_handler('registry/register', self.handle_register_service)
        rpc_handler.register_request_handler('registry/list', self.handle_list_services)
        rpc_handler.register_request_handler('registry/unregister', self.handle_unregister_service)