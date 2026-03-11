"""
DevOps Release Engineer MCP Server Implementation
An AI agent serving as a DevOps Release Engineer for software delivery pipelines,
handling CI/CD configuration, infrastructure provisioning, deployment orchestration,
and build optimization.
"""
import signal
import sys
import threading
import time
from typing import Optional, Dict, Any
import argparse
import asyncio
import json
import requests

from devops_release_engineer_mcp_server.utils.json_rpc import JsonRpcHandler, MessageType
from devops_release_engineer_mcp_server.transports.stdio import StdioTransport
from devops_release_engineer_mcp_server.transports.http_sse import HttpSseTransport
from devops_release_engineer_mcp_server.transports.streamable_http import StreamableHttpTransport
from devops_release_engineer_mcp_server.handlers.server_handlers import DevOpsReleaseEngineerHandlers
from devops_release_engineer_mcp_server.handlers.client_handlers import ClientMethodsHandlers
from devops_release_engineer_mcp_server.utils.notifications import NotificationManager
from devops_release_engineer_mcp_server.utils.heartbeat_manager import HeartbeatManager, RemoteHeartbeatManager


class DevOpsReleaseEngineerMcpServer:
    """DevOps Release Engineer MCP Server implementation for CI/CD, IaC, and deployment orchestration"""

    def __init__(self, transport_type: str = "streamable-http", host: str = "127.0.0.1", port: int = 3071,
                 enable_registry: bool = False,  # Registry is not enabled for this server
                 register_with_registry: bool = True, registry_host: str = "127.0.0.1", registry_port: int = 3031,
                 use_postgres: bool = False, postgres_host: str = "localhost", postgres_port: int = 5432,
                 postgres_db: str = "mcp_registry", postgres_user: str = "postgres", postgres_password: str = "",
                 max_concurrent_requests: int = 10,
                 enable_client_mode: bool = True, client_transport_type: str = "streamable-http",
                 client_host: str = "127.0.0.1", client_port: int = 3030, client_endpoint: Optional[str] = None,
                 llm_provider_url: str = None,  # REQUIRED from config
                 llm_model: str = None,  # REQUIRED from config
                 prompts_dir: str = "."):
        self.transport_type = transport_type
        self.host = host
        self.port = port
        self.running = False
        self.enable_registry = enable_registry  # Registry is not enabled for this server
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

        # Client mode configuration
        self.enable_client_mode = enable_client_mode
        self.client_transport_type = client_transport_type
        if client_host == "127.0.0.1" and client_port == 3030 and register_with_registry:
            self.client_host = registry_host
            self.client_port = registry_port
        else:
            self.client_host = client_host
            self.client_port = client_port
        self.client_endpoint = client_endpoint

        # LLM Configuration - MUST come from environment or command line, NO defaults
        import os
        if not llm_provider_url:
            llm_provider_url = os.environ.get("LLM_PROVIDER_URL")
            if not llm_provider_url:
                raise ValueError("LLM_PROVIDER_URL environment variable not set - must be defined in .env file")
        if not llm_model:
            llm_model = os.environ.get("LLM_MODEL")
            if not llm_model:
                raise ValueError("LLM_MODEL environment variable not set - must be defined in .env file")
        
        self.llm_provider_url = llm_provider_url
        self.llm_model = llm_model
        self.prompts_dir = prompts_dir

        # Initialize components
        self.rpc_handler = JsonRpcHandler(max_concurrent_requests=max_concurrent_requests)

        # Prepare PostgreSQL configuration if needed
        postgres_config = {}
        if self.use_postgres:
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
        self.server_handlers = DevOpsReleaseEngineerHandlers(
            enable_registry=enable_registry,
            use_postgres=self.use_postgres,
            postgres_config=postgres_config,
            client_handlers=self.client_handlers,
            llm_provider_url=llm_provider_url,
            llm_model=llm_model,
            prompts_dir=prompts_dir
        )
        self.notification_manager = NotificationManager(self.rpc_handler)

        # Initialize heartbeat manager
        self.heartbeat_manager = None
        self.remote_heartbeat_manager = None

        # Initialize transport based on type
        if transport_type == "stdio":
            self.transport = StdioTransport(self.rpc_handler)
        elif transport_type == "http":
            self.transport = HttpSseTransport(self.rpc_handler, host, port)
        elif transport_type == "streamable-http":
            self.transport = StreamableHttpTransport(self.rpc_handler, host, port)
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")

        # Initialize client if client mode is enabled
        self.client = None
        if self.enable_client_mode:
            from devops_release_engineer_mcp_server.client import McpClient
            self.client = McpClient(
                transport_type=self.client_transport_type,
                host=self.client_host,
                port=self.client_port,
                endpoint=self.client_endpoint,
                max_concurrent_requests=max_concurrent_requests
            )

        # Connect the transport layer to the RPC handler
        self.rpc_handler.set_transport_layer(self.transport)

        # Register all handlers
        self._register_handlers()

        # Set up signal handling for graceful shutdown
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except ValueError:
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
                registry_url = f"http://{self.registry_host}:{self.registry_port}/send"
                endpoint_url = f"http://{self.host}:{self.port}/send"

            print(f"DEBUG: Preparing registration payload to {registry_url}")

            # Prepare registration payload
            self.service_info = {
                "id": f"devops-release-engineer-{self.host}-{self.port}",
                "name": f"DevOps Release Engineer Server on {self.host}:{self.port}",
                "description": "AI agent serving as DevOps Release Engineer for CI/CD, IaC, and deployment orchestration",
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
                print(f"Successfully registered DevOps Release Engineer server with registry at {self.registry_host}:{self.registry_port}")

                # Initialize remote heartbeat manager to maintain registration
                registry_base_url = f"http://{self.registry_host}:{self.registry_port}"
                self.remote_heartbeat_manager = RemoteHeartbeatManager(
                    registry_url=registry_base_url,
                    service_info=self.service_info,
                    heartbeat_interval=30,
                    max_age_minutes=10
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
        print("DEBUG: Starting handler registration...")
        print(f"DEBUG: RPC handler has {len(self.rpc_handler.request_handlers)} request handlers before registration")

        print("DEBUG: Registering server handlers...")
        self.server_handlers.register_handlers(self.rpc_handler)
        print(f"DEBUG: After server handlers registration, RPC handler has {len(self.rpc_handler.request_handlers)} request handlers")

        print("DEBUG: Registering client handlers...")
        self.client_handlers.register_handlers(self.rpc_handler)
        print(f"DEBUG: After client handlers registration, RPC handler has {len(self.rpc_handler.request_handlers)} request handlers")

        print("DEBUG: Registering notification handlers...")
        self.notification_manager.register_handlers(self.rpc_handler)
        print(f"DEBUG: After all handlers registration, RPC handler has {len(self.rpc_handler.request_handlers)} request handlers")

        print(f"DEBUG: Registered methods: {list(self.rpc_handler.request_handlers.keys())}")

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
        if message.message_type == MessageType.RESPONSE and message.id is not None:
            self.rpc_handler.handle_client_response(message)
            return

        try:
            response = self.rpc_handler.handle_message_sync(message)

            if response:
                self._send_response(response)
        except Exception as e:
            if hasattr(message, 'message_type') and message.message_type.value == 'request':
                error_response = self.rpc_handler._create_error_response(
                    message.get_id(),
                    -32603,
                    f"Internal error: {str(e)}"
                )
                self._send_response(error_response)
            else:
                self.transport.send_error(f"Error handling message: {e}")

    def _send_response(self, response):
        """Send a response message through the transport"""
        if hasattr(self.transport, '_send_response'):
            self.transport._send_response(response)
        else:
            self.transport.send_message(response)

    def _send_notification(self, notification):
        """Send a notification message through the transport"""
        if self.transport_type == "stdio":
            self.transport.send_message(notification)
        elif self.transport_type in ["http", "streamable-http"]:
            if hasattr(self.transport, 'send_message_to_client'):
                self.transport.send_message_to_client(notification)
            elif hasattr(self.transport, 'send_message_to_session'):
                self.transport.send_message(notification)
            else:
                self.transport.send_message(notification)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"Received signal {signum}, initiating graceful shutdown...")
        self.stop()
        sys.exit(0)

    def start(self):
        """Start the DevOps Release Engineer MCP server"""
        print(f"Starting DevOps Release Engineer MCP server with {self.transport_type} transport on port {self.port}...")
        self.running = True

        self.transport.start(self._message_callback)

        print(f"DevOps Release Engineer MCP server running with {self.transport_type} transport on port {self.port}")

        if self.enable_client_mode and self.client:
            print(f"Starting MCP client with {self.client_transport_type} transport to connect to remote server...")
            self.client.connect()

        if self.register_with_registry:
            print(f"Registering with registry at {self.registry_host}:{self.registry_port}...")
            self._register_with_registry()

        try:
            while self.running:
                time.sleep(0.1)
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
        """Stop the DevOps Release Engineer MCP server"""
        print("Stopping DevOps Release Engineer MCP server...")

        if self.enable_client_mode and self.client:
            print("Stopping MCP client...")
            self.client.disconnect()

        if self.remote_heartbeat_manager:
            print("Stopping remote heartbeat manager...")
            self.remote_heartbeat_manager.stop()

        if self.heartbeat_manager:
            print("Stopping local heartbeat manager...")
            self.heartbeat_manager.stop()

        self.running = False
        self.transport.stop()
        print("DevOps Release Engineer MCP server stopped")


def main():
    """Main entry point for the DevOps Release Engineer MCP server"""
    parser = argparse.ArgumentParser(description='DevOps Release Engineer MCP Server - AI agent for CI/CD, IaC, and deployment orchestration')
    parser.add_argument('--transport',
                       choices=['stdio', 'http', 'streamable-http'],
                       default='streamable-http',
                       help='Transport mechanism to use (default: streamable-http)')
    parser.add_argument('--host',
                       default='127.0.0.1',
                       help='Host for HTTP transport (default: 127.0.0.1)')
    parser.add_argument('--port',
                       type=int,
                       default=3071,
                       help='Port for HTTP transport (default: 3071)')
    parser.add_argument('--enable-registry',
                       action='store_true',
                       default=False,
                       help='Enable registry functionality (for running as registry server)')
    parser.add_argument('--register-with-registry',
                       action='store_true',
                       default=True,
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
                       default=False,
                       help='Use PostgreSQL for registry storage instead of SQLite (default: False)')
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
    parser.add_argument('--enable-client-mode',
                       action='store_true',
                       default=True,
                       help='Enable client mode to connect to other MCP servers (default: True)')
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
    parser.add_argument('--llm-provider-url',
                       default='http://192.168.51.237:1234/v1/chat/completions',
                       help='URL for the LLM provider (default: http://192.168.51.237:1234/v1/chat/completions)')
    parser.add_argument('--llm-model',
                       default='qwen3.5-35b-a3b@q5_k_xl',
                       help='LLM model name (default: qwen3.5-35b-a3b@q5_k_xl)')
    parser.add_argument('--prompts-dir',
                       default='.',
                       help='Directory to keep prompts (default: current directory)')

    args = parser.parse_args()

    postgres_host = args.postgres_host
    if postgres_host == "localhost":
        postgres_host = "127.0.0.1"
    elif postgres_host == "::1":
        postgres_host = "127.0.0.1"

    server = DevOpsReleaseEngineerMcpServer(
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
        max_concurrent_requests=args.max_concurrent_requests,
        enable_client_mode=args.enable_client_mode,
        client_transport_type=args.client_transport,
        client_host=args.client_host,
        client_port=args.client_port,
        client_endpoint=args.client_endpoint,
        llm_provider_url=args.llm_provider_url,
        llm_model=args.llm_model,
        prompts_dir=args.prompts_dir
    )
    server.start()
