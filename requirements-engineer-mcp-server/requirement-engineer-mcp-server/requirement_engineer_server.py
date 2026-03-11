"""
Requirement Engineer MCP Server Implementation
Specialized server for requirements engineering tasks
"""
import signal
import sys
import threading
import time
from typing import Optional, Dict, Any
import argparse

from mcp_std_server.utils.json_rpc import JsonRpcHandler, MessageType
from mcp_std_server.transports.stdio import StdioTransport
from mcp_std_server.transports.http_sse import HttpSseTransport
from mcp_std_server.transports.streamable_http import StreamableHttpTransport
from mcp_std_server.handlers.client_handlers import ClientMethodsHandlers
from mcp_std_server.utils.notifications import NotificationManager
from mcp_std_server.utils.heartbeat_manager import HeartbeatManager, RemoteHeartbeatManager
from requirement_engineer_handlers import RequirementEngineerHandlers


class RequirementEngineerMcpServer:
    """Requirement Engineer MCP Server implementation that combines all components"""

    def __init__(self, transport_type: str = "streamable-http", host: str = "127.0.0.1", port: int = 3062, enable_registry: bool = False,
                 register_with_registry: bool = True, registry_host: str = "127.0.0.1", registry_port: int = 3031,
                 use_postgres: bool = True, postgres_host: str = "localhost", postgres_port: int = 5432,
                 postgres_db: str = "mcp_registry", postgres_user: str = "postgres", postgres_password: str = "",
                 max_concurrent_requests: int = 10,
                 enable_client_mode: bool = False, client_transport_type: str = "streamable-http",
                 client_host: str = "127.0.0.1", client_port: int = 3030, client_endpoint: Optional[str] = None,
                 llm_model: Optional[str] = None, llm_provider_url: Optional[str] = None):
        self.transport_type = transport_type
        self.host = host
        self.port = port
        self.running = False
        self.enable_registry = enable_registry  # Optional registry functionality
        self.register_with_registry = register_with_registry  # Auto-register with registry
        self.registry_host = registry_host
        self.registry_port = registry_port
        self.use_postgres = use_postgres  # Use PostgreSQL for registry
        self.postgres_host = postgres_host
        self.postgres_port = postgres_port
        self.postgres_db = postgres_db
        self.postgres_user = postgres_user
        self.postgres_password = postgres_password
        self.max_concurrent_requests = max_concurrent_requests
        self.llm_model = llm_model
        self.llm_provider_url = llm_provider_url

        # Client mode configuration
        self.enable_client_mode = enable_client_mode
        self.client_transport_type = client_transport_type
        self.client_host = client_host
        self.client_port = client_port
        self.client_endpoint = client_endpoint

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

        self.client_handlers = ClientMethodsHandlers(self.rpc_handler)
        # Use RequirementEngineerHandlers instead of default McpServerHandlers
        self.server_handlers = RequirementEngineerHandlers(
            enable_registry=enable_registry,
            use_postgres=self.use_postgres,
            postgres_config=postgres_config,
            client_handlers=self.client_handlers,
            llm_model=self.llm_model,
            llm_provider_url=self.llm_provider_url
        )
        self.notification_manager = NotificationManager(self.rpc_handler)

        # Optional registry functionality
        if self.enable_registry:
            # Use the same registry as the handlers (either PostgreSQL or SQLite)
            self.service_registry = self.server_handlers.service_registry
            # Register this server with itself if it's acting as a registry
            self.service_info = {
                "id": f"registry-{host}:{port}",
                "name": "MCP Service Registry",
                "description": "Central registry for MCP services",
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
            # Legacy HTTP/SSE transport
            self.transport = HttpSseTransport(self.rpc_handler, host, port)
        elif transport_type == "streamable-http":
            # Modern Streamable HTTP transport
            self.transport = StreamableHttpTransport(self.rpc_handler, host, port)
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")

        # Initialize client if client mode is enabled
        self.client = None
        if self.enable_client_mode:
            from mcp_std_server.client import McpClient
            self.client = McpClient(
                transport_type=self.client_transport_type,
                host=self.client_host,
                port=self.client_port,
                endpoint=self.client_endpoint,
                max_concurrent_requests=max_concurrent_requests
            )

        # Connect the transport layer to the RPC handler for bidirectional communication
        self.rpc_handler.set_transport_layer(self.transport)

        # Register all handlers
        self._register_handlers()

        # Set up signal handling for graceful shutdown (only in main thread/process)
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except ValueError:
            # If running in a thread, signal handling won't work - that's OK
            # The server can still be stopped programmatically
            pass

    def _register_with_registry(self):
        """Register this server with a registry server"""
        print(f"DEBUG: _register_with_registry called, register_with_registry={self.register_with_registry}")
        if not self.register_with_registry:
            print("DEBUG: register_with_registry is False, skipping registration")
            return

        print(f"DEBUG: Attempting to register with registry at {self.registry_host}:{self.registry_port}")
        try:
            import requests
            import json

            # Determine the correct endpoint based on the transport type
            if self.transport_type == "streamable-http":
                registry_url = f"http://{self.registry_host}:{self.registry_port}/mcp"
                endpoint_url = f"http://{self.host}:{self.port}/mcp"
            else:
                # For legacy transport, use the send endpoint
                registry_url = f"http://{self.registry_host}:{self.registry_port}/send"
                endpoint_url = f"http://{self.host}:{self.port}/send"

            print(f"DEBUG: Preparing registration payload to {registry_url}")

            # Prepare registration payload
            self.service_info = {
                "id": f"requirement-engineer-server-{self.host}-{self.port}",
                "name": f"Requirement Engineer MCP Server on {self.host}:{self.port}",
                "description": f"Specialized MCP server for requirements engineering tasks on {self.host}:{self.port}",
                "endpoint": endpoint_url,
                "capabilities": {
                    "tools": [tool["name"] for tool in self.server_handlers.tools],
                    "resources": [resource["uri"] for resource in self.server_handlers.resources],
                    "prompts": [prompt["name"] for prompt in self.server_handlers.prompts]
                }
            }

            payload = {
                "jsonrpc": "2.0",
                "id": f"register-{self.port}",
                "method": "registry/register",
                "params": self.service_info
            }
            print(f"DEBUG: Registration payload prepared: {payload['params']['id']}")

            print(f"DEBUG: Sending registration request to {registry_url}")
            response = requests.post(registry_url, json=payload)
            print(f"DEBUG: Registration response status: {response.status_code}")
            print(f"DEBUG: Registration response text: {response.text}")

            if response.status_code == 200:
                print(f"Successfully registered requirement engineer server with registry at {self.registry_host}:{self.registry_port}")

                # Initialize remote heartbeat manager to maintain registration
                registry_base_url = f"http://{self.registry_host}:{self.registry_port}"
                self.remote_heartbeat_manager = RemoteHeartbeatManager(
                    registry_url=registry_base_url,
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
        self.server_handlers.register_handlers(self.rpc_handler)
        self.client_handlers.register_handlers(self.rpc_handler)
        self.notification_manager.register_handlers(self.rpc_handler)

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

    def _message_callback(self, message):
        """Callback to handle incoming messages"""
        # Check if this is a response to a server-initiated request
        if message.message_type == MessageType.RESPONSE and message.id is not None:
            # This is a response to a server-initiated request to the client
            self.rpc_handler.handle_client_response(message)
            return  # Don't process further as this is handled by the pending request mechanism

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
        elif self.transport_type in ["http", "streamable-http"]:
            # For HTTP transports, send to all connected clients
            if hasattr(self.transport, 'send_message_to_client'):
                self.transport.send_message_to_client(notification)
            elif hasattr(self.transport, 'send_message_to_session'):
                # For streamable HTTP transport
                # This would require tracking all active sessions
                # For now, use the generic send_message
                self.transport.send_message(notification)
            else:
                # Fallback to generic send_message
                self.transport.send_message(notification)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"Received signal {signum}, initiating graceful shutdown...")
        self.stop()
        sys.exit(0)

    def start(self):
        """Start the MCP server"""
        print(f"Starting Requirement Engineer MCP server with {self.transport_type} transport...")
        self.running = True

        # Start the transport
        self.transport.start(self._message_callback)

        print(f"Requirement Engineer MCP server running with {self.transport_type} transport on {self.host}:{self.port}")

        # Start client if client mode is enabled
        if self.enable_client_mode and self.client:
            print(f"Starting MCP client with {self.client_transport_type} transport to connect to remote server...")
            self.client.connect()

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
        """Stop the MCP server"""
        print("Stopping Requirement Engineer MCP server...")

        # Stop client if client mode is enabled
        if self.enable_client_mode and self.client:
            print("Stopping MCP client...")
            self.client.disconnect()

        # Stop heartbeat managers first
        if self.remote_heartbeat_manager:
            print("Stopping remote heartbeat manager...")
            self.remote_heartbeat_manager.stop()

        if self.heartbeat_manager:
            print("Stopping local heartbeat manager...")
            self.heartbeat_manager.stop()

        self.running = False
        self.transport.stop()
        print("Requirement Engineer MCP server stopped")


def main():
    """Main entry point for the Requirement Engineer MCP server"""
    parser = argparse.ArgumentParser(description='Requirement Engineer MCP (Model Context Protocol) Server')
    parser.add_argument('--transport',
                       choices=['stdio', 'http', 'streamable-http'],
                       default='streamable-http',
                       help='Transport mechanism to use (default: streamable-http)')
    parser.add_argument('--host',
                       default='127.0.0.1',
                       help='Host for HTTP transport (default: 127.0.0.1)')
    parser.add_argument('--port',
                       type=int,
                       default=3062,  # Changed to 3062 as required
                       help='Port for HTTP transport (default: 3062)')
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
                       default=3031,  # Registry port as required
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
    # Client mode arguments
    parser.add_argument('--enable-client-mode',
                       action='store_true',
                       help='Enable client mode to connect to another MCP server (default: False)')
    parser.add_argument('--client-transport',
                       choices=['stdio', 'http', 'streamable-http'],
                       default='streamable-http',
                       help='Transport mechanism for client connection (default: streamable-http)')
    parser.add_argument('--client-host',
                       default='127.0.0.1',
                       help='Host of the remote MCP server to connect to (default: 127.0.0.1)')
    parser.add_argument('--client-port',
                       type=int,
                       default=3030,
                       help='Port of the remote MCP server to connect to (default: 3030)')
    parser.add_argument('--client-endpoint',
                       help='Specific endpoint of the remote MCP server (overrides host:port)')
    parser.add_argument('--max-concurrent-requests',
                       type=int,
                       default=10,
                       help='Maximum number of concurrent requests (default: 10)')
    # LLM configuration
    parser.add_argument('--llm-provider-url',
                       default='http://192.168.51.237:1234/v1/chat/completions',
                       help='LLM provider URL (default: http://192.168.51.237:1234/v1/chat/completions)')
    parser.add_argument('--llm-model',
                       default='qwen3-coder-next@q5_k_xl',
                       help='LLM model name (default: qwen3-coder-next@q5_k_xl)')

    args = parser.parse_args()

    # Convert localhost to 127.0.0.1 to avoid IPv6 resolution issues
    postgres_host = args.postgres_host
    if postgres_host == "localhost":
        postgres_host = "127.0.0.1"
    elif postgres_host == "::1":
        postgres_host = "127.0.0.1"

    # Set default values for registry connection as required
    # ENABLE_REGISTRY should be false (not become a new registry)
    # REGISTER_WITH_REGISTRY should be true (connect to existing registry)
    enable_registry = False  # As per requirement: should not become a new registry
    register_with_registry = True  # As per requirement: should connect to existing registry

    server = RequirementEngineerMcpServer(
        transport_type=args.transport,
        host=args.host,
        port=args.port,
        enable_registry=enable_registry,
        register_with_registry=register_with_registry,
        registry_host=args.registry_host,
        registry_port=args.registry_port,
        use_postgres=args.use_postgres,
        postgres_host=postgres_host,
        postgres_port=args.postgres_port,
        postgres_db=args.postgres_db,
        postgres_user=args.postgres_user,
        postgres_password=args.postgres_password,
        max_concurrent_requests=args.max_concurrent_requests,
        enable_client_mode=args.enable_client_mode,
        client_transport_type=args.client_transport,
        client_host=args.client_host,
        client_port=args.client_port,
        client_endpoint=args.client_endpoint,
        llm_model=args.llm_model,
        llm_provider_url=args.llm_provider_url
    )
    server.start()


if __name__ == "__main__":
    main()