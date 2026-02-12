"""
Main MCP Server Implementation
Ties together all components to create a fully compliant MCP server
"""
import signal
import sys
import threading
import time
from typing import Optional, Dict, Any
import argparse

from .utils.json_rpc import JsonRpcHandler
from .transports.stdio import StdioTransport
from .transports.http_sse import HttpSseTransport
from .transports.streamable_http import StreamableHttpTransport
from .handlers.server_handlers import McpServerHandlers
from .handlers.client_handlers import ClientMethodsHandlers
from .utils.notifications import NotificationManager
from .utils.heartbeat_manager import HeartbeatManager, RemoteHeartbeatManager
from dependencies.vibe_coder import register_vibe_coding_tool


class McpServer:
    """Main MCP Server implementation that combines all components"""

    def __init__(self, transport_type: str = "streamable-http", host: str = "127.0.0.1", port: int = 3030, enable_registry: bool = False,
                 register_with_registry: bool = False, registry_host: str = "127.0.0.1", registry_port: int = 3031,
                 use_postgres: bool = False, postgres_host: str = "localhost", postgres_port: int = 5432,
                 postgres_db: str = "mcp_registry", postgres_user: str = "postgres", postgres_password: str = "",
                 max_concurrent_requests: int = 10):
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

        self.notification_manager = NotificationManager(self.rpc_handler)
        self.server_handlers = McpServerHandlers(
            enable_registry=enable_registry,
            use_postgres=self.use_postgres,
            postgres_config=postgres_config,
            notification_manager=self.notification_manager
        )
        self.client_handlers = ClientMethodsHandlers(self.rpc_handler)

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

        # Register all handlers
        self._register_handlers()
        
        # Register vibe coding tool after handlers are set up
        self._register_vibe_coding_tool()

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
                "id": f"server-{self.host}-{self.port}",
                "name": f"MCP Server on {self.host}:{self.port}",
                "description": f"MCP server providing services on {self.host}:{self.port}",
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
                print(f"Successfully registered with registry at {self.registry_host}:{self.registry_port}")

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

    def _register_vibe_coding_tool(self):
        """Register the vibe coding tool with the server handlers"""
        register_vibe_coding_tool(self.server_handlers)

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
        print(f"Starting MCP server with {self.transport_type} transport...")
        self.running = True

        # Start the transport
        self.transport.start(self._message_callback)

        print(f"MCP server running with {self.transport_type} transport")

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
        print("Stopping MCP server...")

        # Stop heartbeat managers first
        if self.remote_heartbeat_manager:
            print("Stopping remote heartbeat manager...")
            self.remote_heartbeat_manager.stop()

        if self.heartbeat_manager:
            print("Stopping local heartbeat manager...")
            self.heartbeat_manager.stop()

        self.running = False
        self.transport.stop()
        print("MCP server stopped")


def main():
    """Main entry point for the MCP server"""
    parser = argparse.ArgumentParser(description='MCP (Model Context Protocol) Server')
    parser.add_argument('--transport',
                       choices=['stdio', 'http', 'streamable-http'],
                       default='streamable-http',
                       help='Transport mechanism to use (default: streamable-http)')
    parser.add_argument('--host',
                       default='127.0.0.1',
                       help='Host for HTTP transport (default: 127.0.0.1)')
    parser.add_argument('--port',
                       type=int,
                       default=3030,
                       help='Port for HTTP transport (default: 3030)')
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

    server = McpServer(
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