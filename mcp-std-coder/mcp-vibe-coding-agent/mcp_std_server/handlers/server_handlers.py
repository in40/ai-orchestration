"""
Server Handlers for MCP Server
Implements all standard MCP server methods and functionality
"""
import time
import os
import json
from typing import Dict, Any, List, Optional
from ..utils.json_rpc import JsonRpcHandler, JsonRpcMessage


class McpServerHandlers:
    """Handles all standard MCP server methods"""

    def __init__(self, enable_registry: bool = False, use_postgres: bool = False,
                 postgres_config: Optional[Dict[str, Any]] = None, notification_manager=None):
        # Standard MCP tools, resources, and prompts
        self.tools: List[Dict[str, Any]] = [
            {
                "name": "example_tool",
                "description": "An example tool that echoes back the input",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "input": {"type": "string", "description": "Input to echo back"}
                    },
                    "required": ["input"]
                }
            }
        ]

        self.resources: List[Dict[str, Any]] = [
            {
                "uri": "example://resource/data",
                "name": "Example Resource",
                "description": "An example resource that returns sample data"
            }
        ]

        # Initialize prompts directory
        self.prompts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "prompts")
        os.makedirs(self.prompts_dir, exist_ok=True)

        # Load existing prompts from files
        self.prompts: List[Dict[str, Any]] = self._load_prompts_from_files()
        
        # Add example prompt if no prompts exist
        if not self.prompts:
            self.prompts = [
                {
                    "name": "example_prompt",
                    "description": "An example prompt template",
                    "arguments": [
                        {
                            "name": "subject",
                            "type": "string",
                            "description": "Subject for the prompt"
                        }
                    ]
                }
            ]

        # Optional registry functionality
        self.enable_registry = enable_registry
        self.service_registry = None
        self.postgres_config = postgres_config or {}
        
        # Store notification manager reference
        self.notification_manager = notification_manager
        
        if self.enable_registry:
            self._initialize_registry(use_postgres)

        # Add registry-specific tools if enabled
        if self.enable_registry:
            self._add_registry_methods()

    def _initialize_registry(self, use_postgres: bool):
        """Initialize the service registry with either SQLite or PostgreSQL"""
        try:
            if use_postgres and self.postgres_config:
                from ..utils.postgres_registry_db import PostgresServiceRegistry
                self.service_registry = PostgresServiceRegistry(
                    host=self.postgres_config.get("host", "localhost"),
                    port=self.postgres_config.get("port", 5432),
                    database=self.postgres_config.get("database", "mcp_registry"),
                    user=self.postgres_config.get("user", "postgres"),
                    password=self.postgres_config.get("password", "")
                )
            else:
                from ..utils.service_registry_db import ServiceRegistryDB
                self.service_registry = ServiceRegistryDB()
        except Exception as e:
            print(f"Failed to initialize registry: {e}")
            print("Registry functionality will be disabled")
            self.enable_registry = False

    def _add_registry_methods(self):
        """Add registry-specific methods to the server"""
        # Add registry tools to the tools list
        registry_tools = [
            {
                "name": "registry/register",
                "description": "Register a service with the MCP registry",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Unique identifier for the service"},
                        "name": {"type": "string", "description": "Name of the service"},
                        "description": {"type": "string", "description": "Description of the service"},
                        "endpoint": {"type": "string", "description": "Endpoint URL for the service"},
                        "capabilities": {
                            "type": "object",
                            "description": "Capabilities of the service",
                            "properties": {
                                "tools": {"type": "array", "items": {"type": "string"}},
                                "resources": {"type": "array", "items": {"type": "string"}},
                                "prompts": {"type": "array", "items": {"type": "string"}}
                            }
                        }
                    },
                    "required": ["id", "name", "description", "endpoint", "capabilities"]
                }
            },
            {
                "name": "registry/list",
                "description": "List all registered services in the MCP registry",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filter": {"type": "string", "description": "Optional filter for services"}
                    }
                }
            },
            {
                "name": "registry/unregister",
                "description": "Unregister a service from the MCP registry",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "ID of the service to unregister"}
                    },
                    "required": ["id"]
                }
            }
        ]
        
        # Add registry tools to the tools list
        self.tools.extend(registry_tools)

    def register_handlers(self, rpc_handler: JsonRpcHandler):
        """Register all server handlers with the RPC handler"""
        # Standard MCP methods
        rpc_handler.register_request_handler('initialize', self.handle_initialize)
        rpc_handler.register_request_handler('tools/list', self.handle_tools_list)
        rpc_handler.register_request_handler('tools/call', self.handle_tools_call)
        rpc_handler.register_request_handler('resources/list', self.handle_resources_list)
        rpc_handler.register_request_handler('resources/read', self.handle_resources_read)
        rpc_handler.register_request_handler('prompts/list', self.handle_prompts_list)
        rpc_handler.register_request_handler('prompts/get', self.handle_prompts_get)
        # Additional prompt handlers
        rpc_handler.register_request_handler('prompts/submit', self.handle_prompts_submit)
        rpc_handler.register_request_handler('prompts/update', self.handle_prompts_update)
        rpc_handler.register_request_handler('prompts/delete', self.handle_prompts_delete)
        rpc_handler.register_request_handler('prompts/search', self.handle_prompts_search)
        rpc_handler.register_request_handler('prompts/export', self.handle_prompts_export)
        rpc_handler.register_request_handler('shutdown', self.handle_shutdown)
        rpc_handler.register_request_handler('ping', self.handle_ping)
        
        # Registry handlers - available when registry is enabled
        if self.enable_registry:
            rpc_handler.register_request_handler('registry/register', self.handle_register_service)
            rpc_handler.register_request_handler('registry/list', self.handle_list_services)
            rpc_handler.register_request_handler('registry/unregister', self.handle_unregister_service)
        
        # Register the initialized request handler (acknowledges receipt of initialization)
        rpc_handler.register_request_handler('initialized', self.handle_initialized_request)

    def handle_initialize(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle initialize request"""
        client_info = params.get("clientInfo", {})
        print(f"Initializing connection with client: {client_info.get('name', 'Unknown')} v{client_info.get('version', 'Unknown')}")
        
        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": {
                "name": "mcp-standard-server",
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": {
                    "listChanged": True
                },
                "resources": {
                    "listChanged": True
                },
                "prompts": {
                    "listChanged": True
                }
            }
        }

    def handle_initialized_request(self, params: Dict[str, Any], request_id: str):
        """Handle initialized request - acknowledges receipt of server's initialization response"""
        print("Client acknowledged server initialization response")
        # This is part of the handshake protocol, return an empty result
        return {}

    def handle_tools_list(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle tools/list request"""
        # Handle case where params is None (when no params are provided in the request)
        if params is None:
            params = {}
        
        # Extract pagination parameters if provided
        pagination = params.get("pagination", {})
        cursor = pagination.get("cursor")
        limit = min(pagination.get("limit", len(self.tools)), 100)  # Cap at 100

        # Apply pagination
        if cursor:
            # In a real implementation, cursor would be used to resume listing
            # For simplicity, we'll return all tools
            pass

        # Return tools with pagination info
        return {
            "tools": self.tools[:limit],
            "pagination": {
                "hasMore": len(self.tools) > limit,
                "nextCursor": f"cursor_{limit}" if len(self.tools) > limit else None
            } if limit < len(self.tools) else {}
        }

    def handle_tools_call(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle tools/call request"""
        # Handle case where params is None (when no params are provided in the request)
        if params is None:
            params = {}
            
        # Support both "name" and "tool" as the parameter name for compatibility
        tool_name = params.get("name") or params.get("tool")
        tool_arguments = params.get("arguments", {})

        # Find the tool
        tool = None
        for t in self.tools:
            if t["name"] == tool_name:
                tool = t
                break

        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")

        # Execute the tool
        return self._execute_tool(tool, tool_arguments)

    def _execute_tool(self, tool: Dict[str, Any], arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific tool with given arguments"""
        tool_name = tool["name"]

        # Example implementation for the built-in example tool
        if tool_name == "example_tool":
            input_text = arguments.get("input", "No input provided")
            return {"output": f"Echo: {input_text}"}
        
        # Handle registry tools by calling their respective handlers
        # Pass arguments as params since that's what the handlers expect
        elif tool_name == "registry/register":
            return self.handle_register_service(arguments, "temp_id_for_tool_call")
        elif tool_name == "registry/list":
            return self.handle_list_services(arguments, "temp_id_for_tool_call")
        elif tool_name == "registry/unregister":
            return self.handle_unregister_service(arguments, "temp_id_for_tool_call")

        # Add more tool implementations here as needed
        # This is where you'd add custom tool logic

        # For now, return a generic response
        return {"result": f"Executed tool '{tool_name}' with arguments: {arguments}"}

    def handle_resources_list(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle resources/list request"""
        # Handle case where params is None (when no params are provided in the request)
        if params is None:
            params = {}
        
        # Extract pagination parameters if provided
        pagination = params.get("pagination", {})
        cursor = pagination.get("cursor")
        limit = min(pagination.get("limit", len(self.resources)), 100)  # Cap at 100

        # Apply pagination
        if cursor:
            # In a real implementation, cursor would be used to resume listing
            # For simplicity, we'll return all resources
            pass

        # Return resources with pagination info
        return {
            "resources": self.resources[:limit],
            "pagination": {
                "hasMore": len(self.resources) > limit,
                "nextCursor": f"cursor_{limit}" if len(self.resources) > limit else None
            } if limit < len(self.resources) else {}
        }

    def handle_resources_read(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle resources/read request"""
        # Handle case where params is None (when no params are provided in the request)
        if params is None:
            params = {}
            
        uri = params.get("uri")

        # Find the resource
        resource = None
        for r in self.resources:
            if r["uri"] == uri:
                resource = r
                break

        if not resource:
            raise ValueError(f"Resource '{uri}' not found")

        # Return resource content
        return self._read_resource(resource)

    def _read_resource(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Read content from a specific resource"""
        uri = resource["uri"]
        
        # Example implementation for the built-in example resource
        if uri == "example://resource/data":
            return {
                "contents": [{
                    "uri": uri,
                    "text": "This is example resource data."
                }]
            }
        
        # Add more resource implementations here as needed
        # This is where you'd add custom resource logic
        
        # For now, return a generic response
        return {
            "contents": [{
                "uri": uri,
                "text": f"Content for resource: {uri}"
            }]
        }

    def handle_prompts_list(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle prompts/list request"""
        # Handle case where params is None (when no params are provided in the request)
        if params is None:
            params = {}
        
        # Extract pagination parameters if provided
        pagination = params.get("pagination", {})
        cursor = pagination.get("cursor")
        limit = min(pagination.get("limit", len(self.prompts)), 100)  # Cap at 100

        # Apply pagination
        if cursor:
            # In a real implementation, cursor would be used to resume listing
            # For simplicity, we'll return all prompts
            pass

        # Return prompts with pagination info
        return {
            "prompts": self.prompts[:limit],
            "pagination": {
                "hasMore": len(self.prompts) > limit,
                "nextCursor": f"cursor_{limit}" if len(self.prompts) > limit else None
            } if limit < len(self.prompts) else {}
        }

    def handle_prompts_get(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle prompts/get request"""
        # Handle case where params is None (when no params are provided in the request)
        if params is None:
            params = {}
            
        prompt_name = params.get("name")
        prompt_arguments = params.get("arguments", {})

        # Find the prompt
        prompt = None
        for p in self.prompts:
            if p["name"] == prompt_name:
                prompt = p
                break

        if not prompt:
            raise ValueError(f"Prompt '{prompt_name}' not found")

        # Return resolved prompt
        return self._resolve_prompt(prompt, prompt_arguments)

    def _resolve_prompt(self, prompt: Dict[str, Any], arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve a prompt with given arguments"""
        prompt_name = prompt["name"]
        prompt_content = prompt.get("content", "")

        # Example implementation for the built-in example prompt
        if prompt_name == "example_prompt":
            subject = arguments.get("subject", "default subject")
            resolved_text = f"This is an example prompt about {subject}."
            return {
                "contents": [{
                    "type": "text",
                    "text": resolved_text
                }]
            }

        # For prompts with content field, substitute arguments in the content
        if prompt_content:
            # Simple argument substitution - replace {{arg_name}} with actual values
            resolved_content = prompt_content
            for arg_name, arg_value in arguments.items():
                placeholder = f"{{{{{arg_name}}}}}"  # Creates {{arg_name}}
                resolved_content = resolved_content.replace(placeholder, str(arg_value))
            
            return {
                "contents": [{
                    "type": "text",
                    "text": resolved_content
                }]
            }

        # Add more prompt implementations here as needed
        # This is where you'd add custom prompt logic

        # For now, return a generic response
        return {
            "contents": [{
                "type": "text",
                "text": f"Resolved prompt '{prompt_name}' with arguments: {arguments}"
            }]
        }

    def _load_prompts_from_files(self) -> List[Dict[str, Any]]:
        """Load prompts from JSON files in the prompts directory"""
        prompts = []
        for filename in os.listdir(self.prompts_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.prompts_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        prompt_data = json.load(f)
                        # Validate that it has required fields
                        if isinstance(prompt_data, dict) and 'name' in prompt_data:
                            prompts.append(prompt_data)
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Error loading prompt from {filepath}: {e}")
        return prompts

    def _save_prompt_to_file(self, prompt: Dict[str, Any]) -> bool:
        """Save a prompt to a JSON file in the prompts directory"""
        try:
            filename = f"{prompt['name']}.json"
            filepath = os.path.join(self.prompts_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(prompt, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"Error saving prompt to {filepath}: {e}")
            return False

    def _delete_prompt_file(self, prompt_name: str) -> bool:
        """Delete a prompt file from the prompts directory"""
        try:
            filename = f"{prompt_name}.json"
            filepath = os.path.join(self.prompts_dir, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False
        except IOError as e:
            print(f"Error deleting prompt file {filepath}: {e}")
            return False

    def handle_prompts_submit(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle prompts/submit request - submit a new prompt from text content"""
        if params is None:
            params = {}

        # Extract prompt data from parameters
        prompt_name = params.get("name")
        prompt_content = params.get("content", "")  # Raw text content of the prompt
        prompt_description = params.get("description", "Submitted prompt")
        prompt_arguments = params.get("arguments", [])
        prompt_tags = params.get("tags", [])

        if not prompt_name:
            raise ValueError("Prompt name is required for submission")

        # Check if prompt already exists
        existing_prompt_idx = None
        for i, p in enumerate(self.prompts):
            if p["name"] == prompt_name:
                existing_prompt_idx = i
                break

        # Create new prompt object
        new_prompt = {
            "name": prompt_name,
            "description": prompt_description,
            "content": prompt_content,  # Store the raw content
            "arguments": prompt_arguments,
            "tags": prompt_tags,
            "created_at": time.time(),
            "updated_at": time.time()
        }

        # Save to file
        if self._save_prompt_to_file(new_prompt):
            if existing_prompt_idx is not None:
                # Update existing prompt
                self.prompts[existing_prompt_idx] = new_prompt
            else:
                # Add new prompt
                self.prompts.append(new_prompt)
            
            # Notify that prompts list has changed
            if hasattr(self, 'notification_manager'):
                self.notification_manager.mark_prompts_changed()
                
            return {
                "result": "success",
                "message": f"Prompt '{prompt_name}' {'updated' if existing_prompt_idx is not None else 'submitted'} successfully",
                "prompt": new_prompt
            }
        else:
            raise ValueError(f"Failed to save prompt '{prompt_name}' to file")

    def handle_prompts_update(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle prompts/update request - update an existing prompt"""
        if params is None:
            params = {}

        prompt_name = params.get("name")
        if not prompt_name:
            raise ValueError("Prompt name is required for update")

        # Find the existing prompt
        prompt_idx = None
        for i, p in enumerate(self.prompts):
            if p["name"] == prompt_name:
                prompt_idx = i
                break

        if prompt_idx is None:
            raise ValueError(f"Prompt '{prompt_name}' not found for update")

        # Get update data
        update_data = {k: v for k, v in params.items() if k != "name"}  # Exclude name from update
        
        # Update the prompt
        updated_prompt = self.prompts[prompt_idx].copy()
        for key, value in update_data.items():
            if key in ["content", "description", "arguments", "tags"]:
                updated_prompt[key] = value
        updated_prompt["updated_at"] = time.time()

        # Save to file
        if self._save_prompt_to_file(updated_prompt):
            self.prompts[prompt_idx] = updated_prompt
            
            # Notify that prompts list has changed
            if hasattr(self, 'notification_manager'):
                self.notification_manager.mark_prompts_changed()
                
            return {
                "result": "success",
                "message": f"Prompt '{prompt_name}' updated successfully",
                "prompt": updated_prompt
            }
        else:
            raise ValueError(f"Failed to update prompt '{prompt_name}'")

    def handle_prompts_delete(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle prompts/delete request - delete an existing prompt"""
        if params is None:
            params = {}

        prompt_name = params.get("name")
        if not prompt_name:
            raise ValueError("Prompt name is required for deletion")

        # Find the prompt
        prompt_idx = None
        for i, p in enumerate(self.prompts):
            if p["name"] == prompt_name:
                prompt_idx = i
                break

        if prompt_idx is None:
            raise ValueError(f"Prompt '{prompt_name}' not found for deletion")

        # Remove from in-memory list
        deleted_prompt = self.prompts.pop(prompt_idx)

        # Delete from file system
        if self._delete_prompt_file(prompt_name):
            # Notify that prompts list has changed
            if hasattr(self, 'notification_manager'):
                self.notification_manager.mark_prompts_changed()
                
            return {
                "result": "success",
                "message": f"Prompt '{prompt_name}' deleted successfully",
                "deleted_prompt": deleted_prompt
            }
        else:
            # If file deletion failed, restore the prompt in memory
            self.prompts.insert(prompt_idx, deleted_prompt)
            raise ValueError(f"Failed to delete prompt file for '{prompt_name}'")

    def handle_prompts_search(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle prompts/search request - search for prompts by name or content"""
        if params is None:
            params = {}

        query = params.get("query", "").lower()
        tags = params.get("tags", [])  # Search by tags
        limit = min(params.get("limit", 100), 100)  # Cap at 100

        if not query and not tags:
            raise ValueError("Either query or tags must be provided for search")

        # Filter prompts based on query and tags
        matching_prompts = []
        for prompt in self.prompts:
            # Check if query matches in name, description, content, or tags
            matches_query = (
                query and (
                    query in prompt.get("name", "").lower() or
                    query in prompt.get("description", "").lower() or
                    query in prompt.get("content", "").lower() or
                    query in " ".join(prompt.get("tags", [])).lower()
                )
            ) if query else True
            
            # Check if all specified tags are present
            matches_tags = all(tag in prompt.get("tags", []) for tag in tags) if tags else True
            
            if matches_query and matches_tags:
                matching_prompts.append(prompt)
                
            # Limit results
            if len(matching_prompts) >= limit:
                break

        return {
            "prompts": matching_prompts[:limit],
            "total_matches": len(matching_prompts),
            "query": query,
            "tags": tags
        }

    def handle_prompts_export(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle prompts/export request - export prompts to a file or return content"""
        if params is None:
            params = {}

        prompt_names = params.get("names", [])  # List of prompt names to export
        all_prompts = params.get("all", False)  # Export all prompts if True

        if all_prompts:
            prompts_to_export = self.prompts
        elif prompt_names:
            prompts_to_export = [p for p in self.prompts if p["name"] in prompt_names]
        else:
            raise ValueError("Either 'names' or 'all' parameter must be provided for export")

        # Return the prompts data
        return {
            "prompts": prompts_to_export,
            "exported_count": len(prompts_to_export),
            "format": "json"
        }

    def handle_shutdown(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle shutdown request"""
        print("Shutdown request received, preparing to shut down...")
        return {}

    def handle_ping(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle ping request for health check"""
        # Handle case where params is None (when no params are provided in the request)
        if params is None:
            params = {}
            
        return {
            "timestamp": time.time(),
            "status": "healthy"
        }

    # Registry-specific handlers
    def handle_register_service(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle registry/register request.

        This method allows MCP servers to register themselves with a central registry,
        enabling service discovery for AI agents and other services.

        How to use registry functionality:
        1. Service sends a JSON-RPC request to registry's /mcp endpoint (POST):

        {
          "jsonrpc": "2.0",
          "id": "1",
          "method": "registry/register",
          "params": {
            "id": "db-service-1",
            "name": "Database Access Service",
            "description": "Provides database query capabilities",
            "endpoint": "http://localhost:3031",  # Different port for the service
            "capabilities": {
              "tools": ["query_db", "insert_record"],
              "resources": ["db://users", "db://products"],
              "prompts": ["sql_generation_prompt"]
            }
          }
        }

        2. Registry responds with success/failure:
        {
          "jsonrpc": "2.0",
          "id": "1",
          "result": {
            "success": true,
            "service_id": "db-service-1",
            "message": "Service registered successfully"
          }
        }
        """
        # Handle case where params is None (when no params are provided in the request)
        if params is None:
            params = {}
            
        if not hasattr(self, 'enable_registry') or not self.enable_registry:
            print("❌ Registry functionality is not enabled")
            raise ValueError("Registry functionality is not enabled")

        if not hasattr(self, 'service_registry'):
            print("❌ Service registry is not initialized")
            raise ValueError("Service registry is not initialized")

        # Extract service information from params
        service_info = {
            "id": params.get("id"),
            "name": params.get("name"),
            "description": params.get("description"),
            "endpoint": params.get("endpoint"),
            "capabilities": params.get("capabilities", {}),
            "registered_at": time.time()
        }

        # Validate required fields
        if not all(k in service_info and service_info[k] for k in ["id", "name", "description", "endpoint"]):
            raise ValueError("Missing required fields for service registration")

        # Check if service already exists
        existing_services = self.service_registry.list_services()

        for existing_service in existing_services:
            if existing_service.get("id") == service_info["id"]:
                print(f"⚠️ Service with ID {service_info['id']} already exists, updating...")
                break

        # Register the service
        success = self.service_registry.register_service(service_info)

        if success:
            print(f"✅ Service '{service_info['name']}' registered with ID '{service_info['id']}'")
            return {
                "success": True,
                "service_id": service_info["id"],
                "message": "Service registered successfully"
            }
        else:
            print(f"❌ Failed to register service '{service_info['name']}'")
            return {
                "success": False,
                "message": "Failed to register service"
            }

    def handle_list_services(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle registry/list request.

        This method returns all registered services in the registry.

        How to use registry functionality:
        1. AI agent sends a JSON-RPC request to registry's /mcp endpoint (POST):

        {
          "jsonrpc": "2.0",
          "id": "2",
          "method": "registry/list",
          "params": {
            "filter": "database"  // optional
          }
        }

        2. Registry responds with list of services:
        {
          "jsonrpc": "2.0",
          "id": "2",
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
        print(f"📋 Registry list request received")

        # Handle case where params is None (when no params are provided in the request)
        if params is None:
            params = {}
            
        if not hasattr(self, 'enable_registry') or not self.enable_registry:
            print("❌ Registry functionality is not enabled")
            raise ValueError("Registry functionality is not enabled")

        if not hasattr(self, 'service_registry'):
            print("❌ Service registry is not initialized")
            raise ValueError("Service registry is not initialized")

        # Get filter from params if provided
        filter_param = params.get("filter")

        services = self.service_registry.list_services()

        # Apply filter if provided
        if filter_param:
            filtered_services = []
            for service in services:
                # Check if filter matches any service property
                service_values = [str(v).lower() for v in service.values() if isinstance(v, (str, int))]
                if any(filter_param.lower() in val for val in service_values):
                    filtered_services.append(service)
            services = filtered_services

        print(f"📊 Returning {len(services)} services from registry")

        return {
            "services": services,
            "total_count": len(services)
        }

    def handle_unregister_service(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle registry/unregister request.

        This method allows services to deregister themselves from the registry.

        How to use registry functionality:
        1. Service sends a JSON-RPC request to registry's /mcp endpoint (POST):

        {
          "jsonrpc": "2.0",
          "id": "3",
          "method": "registry/unregister",
          "params": {
            "id": "db-service-1"
          }
        }

        2. Registry responds with success/failure:
        {
          "jsonrpc": "2.0",
          "id": "3",
          "result": {
            "success": true,
            "message": "Service unregistered successfully"
          }
        }
        """
        # Handle case where params is None (when no params are provided in the request)
        if params is None:
            params = {}
            
        if not hasattr(self, 'enable_registry') or not self.enable_registry:
            raise ValueError("Registry functionality is not enabled")

        if not hasattr(self, 'service_registry'):
            raise ValueError("Service registry is not initialized")

        service_id = params.get("id")
        if not service_id:
            raise ValueError("Service ID is required for unregistration")

        success = self.service_registry.unregister_service(service_id)

        if success:
            print(f"✅ Service with ID '{service_id}' unregistered successfully")
            return {
                "success": True,
                "message": "Service unregistered successfully"
            }
        else:
            print(f"❌ Failed to unregister service with ID '{service_id}'")
            return {
                "success": False,
                "message": "Failed to unregister service or service not found"
            }