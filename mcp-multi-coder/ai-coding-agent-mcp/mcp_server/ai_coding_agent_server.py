"""
AI Coding Agent MCP Server
Implements an MCP server that provides AI coding assistance using a local LLM (LM Studio).
Handles coding tasks asynchronously via a task queue with configurable concurrent workers.
"""
import asyncio
import os
import signal
import sys
import time
from typing import Optional, Dict, Any
import argparse
import logging

from .utils.json_rpc import JsonRpcHandler
from .transports.stdio import StdioTransport
from .transports.http_sse import HttpSseTransport
from .handlers.server_handlers import McpServerHandlers
from .handlers.client_handlers import ClientMethodsHandlers
from .utils.notifications import NotificationManager
from .utils.heartbeat_manager import HeartbeatManager, RemoteHeartbeatManager

from task_manager.task_manager import TaskManager
from lmstudio_client.lmstudio_client import LMStudioClient
from prompt_manager import PromptManager


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AiCodingAgentMcpServer:
    """AI Coding Agent MCP Server implementation"""

    def __init__(self, transport_type: str = "stdio", host: str = "127.0.0.1", port: int = 3050, 
                 enable_registry: bool = False, register_with_registry: bool = False, 
                 registry_host: str = "127.0.0.1", registry_port: int = 3031,
                 use_postgres: bool = False, postgres_host: str = "localhost", 
                 postgres_port: int = 5432, postgres_db: str = "mcp_registry", 
                 postgres_user: str = "postgres", postgres_password: str = "",
                 max_concurrent_requests: int = 10):
        self.transport_type = transport_type
        self.host = host
        self.port = port
        self.running = False
        self.enable_registry = enable_registry
        self.register_with_registry = register_with_registry
        self.registry_host = registry_host
        self.registry_port = registry_port
        self.use_postgres = use_postgres
        self.postgres_host = postgres_host
        self.postgres_port = postgres_port
        self.postgres_db = postgres_db
        self.postgres_user = postgres_user
        self.postgres_password = postgres_password
        self.max_concurrent_requests = max_concurrent_requests

        # Get number of concurrent workers from environment variable (default: 2)
        self.concurrent_workers = int(os.getenv('CONCURRENT_WORKERS', '2'))

        # Initialize components
        self.rpc_handler = JsonRpcHandler(max_concurrent_requests=max_concurrent_requests)

        # Prepare PostgreSQL configuration if needed
        postgres_config = {}
        if self.use_postgres:
            # Use 127.0.0.1 instead of localhost to avoid IPv6 resolution issues
            host = self.postgres_host
            if host == "localhost":
                host = "127.0.0.1"
            elif host == "::1":
                host = "127.0.0.1"

            postgres_config = {
                "host": host,
                "port": self.postgres_port,
                "database": self.postgres_db,
                "user": self.postgres_user,
                "password": self.postgres_password
            }

        # Initialize custom handlers
        self.server_handlers = McpServerHandlers(
            enable_registry=enable_registry,
            use_postgres=self.use_postgres,
            postgres_config=postgres_config
        )
        self.client_handlers = ClientMethodsHandlers(self.rpc_handler)
        self.notification_manager = NotificationManager(self.rpc_handler)

        # Initialize custom components
        self.lmstudio_client = LMStudioClient()
        self.prompt_manager = PromptManager()
        self.task_manager = TaskManager(
            num_workers=self.concurrent_workers,
            lmstudio_client=self.lmstudio_client,
            prompt_manager=self.prompt_manager
        )

        # Clear default tools, resources, and prompts from skeleton
        self.server_handlers.tools = []
        self.server_handlers.resources = []
        self.server_handlers.prompts = []

        # Add custom tools for AI coding agent
        self._add_custom_tools()
        
        # Add custom resources for prompt templates
        self._add_custom_resources()

        # Optional registry functionality
        if self.enable_registry:
            # Use the same registry as the handlers (either PostgreSQL or SQLite)
            self.service_registry = self.server_handlers.service_registry
            # Register this server with itself if it's acting as a registry
            self.service_info = {
                "id": f"ai-coding-agent-registry-{host}:{port}",
                "name": "AI Coding Agent Service Registry",
                "description": "Registry for AI coding agent services",
                "endpoint": f"http://{host}:{port}",
                "capabilities": {
                    "registry": True,
                    "methods": ["registry/register", "registry/list", "registry/unregister"]
                }
            }
            self.service_registry.register_service(self.service_info)

            # Initialize heartbeat manager for the registry server
            self.heartbeat_manager = HeartbeatManager(
                self.service_registry,
                self.service_info["id"],
                heartbeat_interval=30,  # Every 30 seconds
                max_age_minutes=10      # Remove services not seen in 10 minutes
            )
        else:
            self.heartbeat_manager = None

        # Initialize remote heartbeat manager for auto-registration
        self.remote_heartbeat_manager = None

        # Initialize transport based on type
        if transport_type == "stdio":
            self.transport = StdioTransport(self.rpc_handler)
        elif transport_type == "http":
            self.transport = HttpSseTransport(self.rpc_handler, host, port)
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")

        # Register all handlers
        self._register_handlers()

        # Set up signal handling for graceful shutdown
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except ValueError:
            # If running in a thread, signal handling won't work - that's OK
            pass

    def _add_custom_tools(self):
        """Add custom tools for the AI coding agent"""
        # LM Studio health check tool
        self.server_handlers.tools.append({
            "name": "lmstudio_health",
            "description": "Check connectivity to LM Studio and return model list",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        })

        # Submit coding task tool
        self.server_handlers.tools.append({
            "name": "submit_coding_task",
            "description": "Submit a coding task; enqueues for asynchronous processing. Returns task ID.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The coding task description"
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language for the task (optional)"
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum number of tokens to generate (optional)",
                        "minimum": 1,
                        "maximum": 4096
                    }
                },
                "required": ["task"]
            }
        })

        # Get task status tool
        self.server_handlers.tools.append({
            "name": "get_task_status",
            "description": "Retrieve current status and result (if completed) of a task",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The ID of the task to check"
                    }
                },
                "required": ["task_id"]
            }
        })

        # List tasks tool
        self.server_handlers.tools.append({
            "name": "list_tasks",
            "description": "List all tasks, optionally filtered by status",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter tasks by status (optional)",
                        "enum": ["pending", "processing", "completed", "failed", "cancelled"]
                    }
                }
            }
        })

        # Cancel task tool
        self.server_handlers.tools.append({
            "name": "cancel_task",
            "description": "Cancel a pending task",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The ID of the task to cancel"
                    }
                },
                "required": ["task_id"]
            }
        })

        # Render prompt tool
        self.server_handlers.tools.append({
            "name": "render_prompt",
            "description": "Render a prompt template with given variables",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "template_name": {
                        "type": "string",
                        "description": "Name of the prompt template to render"
                    },
                    "variables": {
                        "type": "object",
                        "description": "Variables to substitute in the template"
                    }
                },
                "required": ["template_name", "variables"]
            }
        })

    def _add_custom_resources(self):
        """Add custom resources for prompt templates"""
        # Add a resource for each prompt template
        for prompt_name in self.prompt_manager.list_prompts():
            self.server_handlers.resources.append({
                "uri": f"file://prompts/{prompt_name}.txt",
                "name": f"Prompt Template: {prompt_name}",
                "description": f"Prompt template for {prompt_name}"
            })

    def _register_with_registry(self):
        """Register this server with a registry server"""
        if not self.register_with_registry:
            return

        try:
            import requests
            import json

            registry_url = f"http://{self.registry_host}:{self.registry_port}"

            # Prepare registration payload
            self.service_info = {
                "id": f"ai-coding-agent-{self.host}-{self.port}",
                "name": "AI Coding Agent MCP Server",
                "description": "MCP server that provides AI coding assistance using a local LLM (LM Studio). Accepts coding tasks, manages their lifecycle asynchronously via a task queue, and returns generated code or explanations. Supports concurrent processing of multiple tasks with a configurable number of worker coroutines.",
                "endpoint": f"http://{self.host}:{self.port}",
                "capabilities": {
                    "tools": [tool["name"] for tool in self.server_handlers.tools],
                    "resources": [resource["uri"] for resource in self.server_handlers.resources],
                    "prompts": []  # No prompts capability since we handle them differently
                }
            }

            payload = {
                "jsonrpc": "2.0",
                "id": f"register-{self.port}",
                "method": "registry/register",
                "params": self.service_info
            }

            response = requests.post(f"{registry_url}/send", json=payload)

            if response.status_code == 200:
                print(f"Successfully registered with registry at {self.registry_host}:{self.registry_port}")

                # Initialize remote heartbeat manager to maintain registration
                self.remote_heartbeat_manager = RemoteHeartbeatManager(
                    registry_url=registry_url,
                    service_info=self.service_info,
                    heartbeat_interval=30,  # Every 30 seconds
                    max_age_minutes=10      # Registry considers service stale after 10 minutes
                )
                self.remote_heartbeat_manager.start()
            else:
                print(f"Failed to register with registry: {response.status_code} - {response.text}")

        except ImportError:
            print("Warning: 'requests' library not available. Install it to enable auto-registration with registry.")
        except Exception as e:
            print(f"Error registering with registry: {e}")
            import traceback
            traceback.print_exc()

    def _register_handlers(self):
        """Register all handlers with the RPC handler"""
        # Register standard handlers
        self.server_handlers.register_handlers(self.rpc_handler)
        self.client_handlers.register_handlers(self.rpc_handler)
        self.notification_manager.register_handlers(self.rpc_handler)

        # Register custom tool handlers (override the default tools/call handler)
        self.rpc_handler.register_request_handler('tools/call', self._handle_custom_tools_call)

        # Register notification callbacks
        self.notification_manager.register_notification_callback(
            "notifications/tools/list_changed",
            self._send_notification
        )
        self.notification_manager.register_notification_callback(
            "notifications/resources/list_changed",
            self._send_notification
        )
        self.notification_manager.register_notification_callback(
            "notifications/prompts/list_changed",
            self._send_notification
        )

    async def _handle_custom_tools_call(self, params: Dict[str, Any], request_id: str):
        """Handle custom tool calls"""
        tool_name = params.get("name")
        tool_arguments = params.get("arguments", {})

        try:
            if tool_name == "lmstudio_health":
                result = await self.lmstudio_client.check_health()
                return {"result": result}
            
            elif tool_name == "submit_coding_task":
                task_description = tool_arguments.get("task")
                language = tool_arguments.get("language", "python")
                max_tokens = tool_arguments.get("max_tokens", 512)
                
                # Create parameters dict
                parameters = {"language": language, "max_tokens": max_tokens}
                
                task_id = await self.task_manager.create_task(task_description, parameters)
                return {"result": {"task_id": task_id}}
            
            elif tool_name == "get_task_status":
                task_id = tool_arguments.get("task_id")
                task = await self.task_manager.get_task(task_id)
                
                if task is None:
                    return {"error": {"code": -32000, "message": f"Task {task_id} not found"}}
                
                return {"result": task.model_dump()}
            
            elif tool_name == "list_tasks":
                status_filter = tool_arguments.get("status")
                if status_filter:
                    from task_manager.task_manager import TaskStatus
                    status_enum = TaskStatus(status_filter)
                    tasks = await self.task_manager.list_tasks(status_enum)
                else:
                    tasks = await self.task_manager.list_tasks()
                
                # Return simplified task info
                task_summaries = []
                for task in tasks:
                    task_summaries.append({
                        "id": task.id,
                        "status": task.status.value,
                        "created_at": task.created_at,
                        "updated_at": task.updated_at
                    })
                
                return {"result": task_summaries}
            
            elif tool_name == "cancel_task":
                task_id = tool_arguments.get("task_id")
                success = await self.task_manager.cancel_task(task_id)
                
                if success:
                    return {"result": {"success": True}}
                else:
                    return {"error": {"code": -32000, "message": f"Could not cancel task {task_id}"}}
            
            elif tool_name == "render_prompt":
                template_name = tool_arguments.get("template_name")
                variables = tool_arguments.get("variables", {})
                
                try:
                    rendered_prompt = self.prompt_manager.render_prompt(template_name, variables)
                    return {"result": {"rendered_prompt": rendered_prompt}}
                except Exception as e:
                    return {"error": {"code": -32000, "message": f"Error rendering prompt: {str(e)}"}}
            
            else:
                # Handle standard tools from parent class
                return await self.server_handlers.handle_tools_call(params, request_id)
        
        except Exception as e:
            logger.error(f"Error in custom tool {tool_name}: {str(e)}")
            return {"error": {"code": -32000, "message": f"Error executing tool {tool_name}: {str(e)}"}}

    def _message_callback(self, message):
        """Callback to handle incoming messages"""
        # Use the synchronous version of handle_message for stdio transport
        try:
            response = self.rpc_handler.handle_message_sync(message)

            if response:
                self._send_response(response)
        except Exception as e:
            # Log error and send error response if it was a request
            if hasattr(message, 'message_type') and message.message_type.value == 'request':
                error_response = self.rpc_handler._create_error_response(
                    message.get_id(),
                    -32603,
                    f"Internal error: {str(e)}"
                )
                self._send_response(error_response)
            else:
                # For notifications, just log the error
                self.transport.send_error(f"Error handling message: {e}")

    def _send_response(self, response):
        """Send a response message through the transport"""
        # Use the transport's specific response method if available
        if hasattr(self.transport, '_send_response'):
            self.transport._send_response(response)
        else:
            self.transport.send_message(response)

    def _send_notification(self, notification):
        """Send a notification message through the transport"""
        if self.transport_type == "stdio":
            self.transport.send_message(notification)
        elif self.transport_type == "http":
            # For HTTP/SSE, send to all connected clients
            self.transport.send_message_to_client(notification)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"Received signal {signum}, initiating graceful shutdown...")
        self.stop()
        sys.exit(0)

    def start(self):
        """Start the AI Coding Agent MCP server"""
        print(f"Starting AI Coding Agent MCP server with {self.transport_type} transport...")
        self.running = True

        # Start the transport
        self.transport.start(self._message_callback)

        # Start task manager workers in the main event loop
        import threading
        import asyncio
        
        def run_worker_loop():
            # Create a new event loop for the worker tasks
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Start the task manager workers
                loop.run_until_complete(self.task_manager.start_workers())
                print(f"Started {self.concurrent_workers} task worker(s)")
                
                # Keep the loop running while the server is running
                while self.running:
                    loop.run_until_complete(asyncio.sleep(1))
            except Exception as e:
                print(f"Error in worker loop: {e}")
            finally:
                loop.run_until_complete(self.task_manager.stop_workers())
                loop.close()

        # Start the worker loop in a separate thread
        worker_thread = threading.Thread(target=run_worker_loop, daemon=True)
        worker_thread.start()

        print(f"AI Coding Agent MCP server running with {self.transport_type} transport on port {self.port}")

        # Register with registry if configured to do so
        if self.register_with_registry:
            print(f"Registering with registry at {self.registry_host}:{self.registry_port}...")
            self._register_with_registry()
        elif self.enable_registry and self.heartbeat_manager:
            # Start heartbeat manager for registry server
            self.heartbeat_manager.start()

        # Keep the server running
        try:
            while self.running:
                time.sleep(0.1)  # Small sleep to prevent busy waiting
                # Check for any pending notifications to send
                changes = self.notification_manager.get_changes_status()

                if changes["tools_changed"]:
                    self.notification_manager.notify_tools_list_changed()
                if changes["resources_changed"]:
                    self.notification_manager.notify_resources_list_changed()
                if changes["prompts_changed"]:
                    self.notification_manager.notify_prompts_list_changed()

        except KeyboardInterrupt:
            print("Interrupt received, shutting down...")
        finally:
            self.stop()

    def stop(self):
        """Stop the AI Coding Agent MCP server"""
        print("Stopping AI Coding Agent MCP server...")

        # Stop heartbeat managers first
        if self.remote_heartbeat_manager:
            print("Stopping remote heartbeat manager...")
            self.remote_heartbeat_manager.stop()

        if self.heartbeat_manager:
            print("Stopping local heartbeat manager...")
            self.heartbeat_manager.stop()

        # Stop task manager workers
        asyncio.run(self.task_manager.stop_workers())

        self.running = False
        self.transport.stop()
        
        # Close LM Studio client
        asyncio.run(self.lmstudio_client.close())
        
        print("AI Coding Agent MCP server stopped")


def main():
    """Main entry point for the AI Coding Agent MCP server"""
    parser = argparse.ArgumentParser(description='AI Coding Agent MCP Server')
    parser.add_argument('--transport',
                       choices=['stdio', 'http'],
                       default='stdio',
                       help='Transport mechanism to use (default: stdio)')
    parser.add_argument('--host',
                       default='127.0.0.1',
                       help='Host for HTTP transport (default: 127.0.0.1)')
    parser.add_argument('--port',
                       type=int,
                       default=3060,  # Changed default to 3060 as requested
                       help='Port for HTTP transport (default: 3060)')
    parser.add_argument('--enable-registry',
                       action='store_true',
                       help='Enable registry functionality to track multiple MCP services (optional)')
    parser.add_argument('--register-with-registry',
                       action='store_true',
                       help='Register this server with a registry server (requires --registry-host and --registry-port)')
    parser.add_argument('--registry-host',
                       default='127.0.0.1',
                       help='Registry server host to register with (default: 127.0.0.1)')
    parser.add_argument('--registry-port',
                       type=int,
                       default=3031,
                       help='Registry server port to register with (default: 3031)')
    parser.add_argument('--use-postgres',
                       action='store_true',
                       help='Use PostgreSQL for registry storage instead of SQLite (optional)')
    parser.add_argument('--postgres-host',
                       default='127.0.0.1',
                       help='PostgreSQL host (default: 127.0.0.1)')
    parser.add_argument('--postgres-port',
                       type=int,
                       default=5432,
                       help='PostgreSQL port (default: 5432)')
    parser.add_argument('--postgres-db',
                       default='mcp_registry',
                       help='PostgreSQL database name (default: mcp_registry)')
    parser.add_argument('--postgres-user',
                       default='postgres',
                       help='PostgreSQL username (default: postgres)')
    parser.add_argument('--postgres-password',
                       default='',
                       help='PostgreSQL password (default: empty)')
    parser.add_argument('--max-concurrent-requests',
                       type=int,
                       default=10,
                       help='Maximum number of concurrent requests (default: 10)')

    args = parser.parse_args()

    # Convert localhost to 127.0.0.1 to avoid IPv6 resolution issues
    postgres_host = args.postgres_host
    if postgres_host == "localhost":
        postgres_host = "127.0.0.1"
    elif postgres_host == "::1":
        postgres_host = "127.0.0.1"

    server = AiCodingAgentMcpServer(
        transport_type=args.transport,
        host=args.host,
        port=args.port,
        enable_registry=args.enable_registry,
        register_with_registry=args.register_with_registry,
        registry_host=args.registry_host,
        registry_port=args.registry_port,
        use_postgres=args.use_postgres,
        postgres_host=postgres_host,
        postgres_port=args.postgres_port,
        postgres_db=args.postgres_db,
        postgres_user=args.postgres_user,
        postgres_password=args.postgres_password,
        max_concurrent_requests=args.max_concurrent_requests
    )
    server.start()


if __name__ == "__main__":
    main()