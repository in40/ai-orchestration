"""
MCP Client Implementation
Implements an MCP client that can connect to other MCP servers to submit tasks
"""
import signal
import sys
import threading
import time
from typing import Optional, Dict, Any
import argparse
import asyncio

from .utils.json_rpc import JsonRpcHandler, MessageType
from .transports.client_stdio import ClientStdioTransport
from .transports.client_http_sse import ClientHttpSseTransport
from .transports.client_streamable_http import ClientStreamableHttpTransport
from .handlers.client_operations import ClientOperationsHandlers
from .utils.service_registry_db import ServiceRegistryDB


class McpClient:
    """Main MCP Client implementation that connects to other MCP servers"""

    def __init__(self, transport_type: str = "streamable-http", host: str = "127.0.0.1", port: int = 3030,
                 endpoint: Optional[str] = None, max_concurrent_requests: int = 10):
        self.transport_type = transport_type
        self.host = host
        self.port = port
        self.endpoint = endpoint  # Specific endpoint for the remote server
        self.running = False
        self.max_concurrent_requests = max_concurrent_requests

        # Initialize components
        self.rpc_handler = JsonRpcHandler(max_concurrent_requests=max_concurrent_requests)
        
        # Client operations handlers for managing remote operations
        self.operations_handlers = ClientOperationsHandlers(self.rpc_handler)
        
        # Initialize transport based on type
        if transport_type == "stdio":
            self.transport = ClientStdioTransport(self.rpc_handler, endpoint)
        elif transport_type == "http":
            # Legacy HTTP/SSE transport
            self.transport = ClientHttpSseTransport(self.rpc_handler, host, port, endpoint)
        elif transport_type == "streamable-http":
            # Modern Streamable HTTP transport
            self.transport = ClientStreamableHttpTransport(self.rpc_handler, host, port, endpoint)
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")

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
            # The client can still be stopped programmatically
            pass

    def _register_handlers(self):
        """Register all handlers with the RPC handler"""
        self.operations_handlers.register_handlers(self.rpc_handler)

    def _message_callback(self, message):
        """Callback to handle incoming messages"""
        # Check if this is a response to a client-initiated request
        if message.message_type == MessageType.RESPONSE and message.id is not None:
            # This is a response to a client-initiated request to the remote server
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

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"Received signal {signum}, initiating graceful shutdown...")
        self.stop()
        sys.exit(0)

    def connect(self):
        """Connect to the remote MCP server"""
        print(f"Connecting to MCP server with {self.transport_type} transport...")
        self.running = True

        # Start the transport
        self.transport.start(self._message_callback)

        print(f"MCP client connected to {self.transport_type} transport")

    def disconnect(self):
        """Disconnect from the remote MCP server"""
        print("Disconnecting MCP client...")

        self.running = False
        self.transport.stop()
        print("MCP client disconnected")

    def is_connected(self) -> bool:
        """Check if the client is currently connected"""
        return self.running and self.transport.is_connected()

    # Client operation methods
    def call_tool(self, tool_name: str, arguments: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        """Call a tool on the remote server"""
        return self.operations_handlers.call_remote_tool(tool_name, arguments, timeout)

    def list_tools(self, timeout: float = 30.0) -> Dict[str, Any]:
        """List tools available on the remote server"""
        return self.operations_handlers.list_remote_tools(timeout)

    def read_resource(self, uri: str, timeout: float = 30.0) -> Dict[str, Any]:
        """Read a resource from the remote server"""
        return self.operations_handlers.read_remote_resource(uri, timeout)

    def list_resources(self, timeout: float = 30.0) -> Dict[str, Any]:
        """List resources available on the remote server"""
        return self.operations_handlers.list_remote_resources(timeout)

    def get_prompt(self, prompt_name: str, arguments: Optional[Dict[str, Any]] = None, timeout: float = 30.0) -> Dict[str, Any]:
        """Get a prompt from the remote server"""
        return self.operations_handlers.get_remote_prompt(prompt_name, arguments or {}, timeout)

    def list_prompts(self, timeout: float = 30.0) -> Dict[str, Any]:
        """List prompts available on the remote server"""
        return self.operations_handlers.list_remote_prompts(timeout)


def main():
    """Main entry point for the MCP client"""
    parser = argparse.ArgumentParser(description='MCP (Model Context Protocol) Client')
    parser.add_argument('--transport',
                       choices=['stdio', 'http', 'streamable-http'],
                       default='streamable-http',
                       help='Transport mechanism to use (default: streamable-http)')
    parser.add_argument('--host',
                       default='127.0.0.1',
                       help='Host of the remote MCP server (default: 127.0.0.1)')
    parser.add_argument('--port',
                       type=int,
                       default=3030,
                       help='Port of the remote MCP server (default: 3030)')
    parser.add_argument('--endpoint',
                       help='Specific endpoint of the remote MCP server (overrides host:port)')
    parser.add_argument('--max-concurrent-requests',
                       type=int,
                       default=10,
                       help='Maximum number of concurrent requests (default: 10)')

    args = parser.parse_args()

    # Construct endpoint if not provided
    if not args.endpoint:
        if args.transport == 'stdio':
            # For stdio, we don't need host/port, but we'll use a placeholder
            args.endpoint = 'stdio'
        else:
            args.endpoint = f"http://{args.host}:{args.port}"

    client = McpClient(
        transport_type=args.transport,
        host=args.host,
        port=args.port,
        endpoint=args.endpoint,
        max_concurrent_requests=args.max_concurrent_requests
    )
    
    try:
        client.connect()
        print(f"Connected to MCP server at {args.endpoint}")
        
        # Keep the client running
        while client.running:
            time.sleep(0.1)  # Small sleep to prevent busy waiting
            
    except KeyboardInterrupt:
        print("Interrupt received, shutting down...")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()