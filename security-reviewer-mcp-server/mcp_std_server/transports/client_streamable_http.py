"""
Client Streamable HTTP Transport for MCP Client
Implements the modern Streamable HTTP transport as a client connecting to another MCP server
"""
import json
import asyncio
import threading
import uuid
from typing import Callable, Optional, Dict, Any
from ..utils.json_rpc import JsonRpcHandler, JsonRpcMessage


class ClientStreamableHttpTransport:
    """Client transport mechanism using Streamable HTTP to connect to another MCP server"""

    def __init__(self, rpc_handler: JsonRpcHandler, host: str = "127.0.0.1", port: int = 3030,
                 endpoint: Optional[str] = None):
        self.rpc_handler = rpc_handler
        self.host = host
        self.port = port
        self.running = False
        self.endpoint = endpoint or f"http://{host}:{port}/mcp"
        self.message_callback: Optional[Callable[[JsonRpcMessage], None]] = None
        
        # Connection state
        self.session_id = str(uuid.uuid4())
        self.connection_thread: Optional[threading.Thread] = None

        # For Streamable HTTP, we'll use requests for client-side communication
        self.remote_endpoint = endpoint or f"http://{host}:{port}/mcp"

    def start(self, message_callback: Callable[[JsonRpcMessage], None]):
        """Start the Streamable HTTP transport client"""
        self.message_callback = message_callback
        self.running = True

        # Note: For Streamable HTTP, the client doesn't maintain a persistent connection
        # Instead, it sends requests to the server and receives responses
        # So we don't need a dedicated connection thread like with SSE

    def stop(self):
        """Stop the Streamable HTTP transport client"""
        self.running = False

    def send_message(self, message: JsonRpcMessage):
        """Send a message to the remote server via HTTP POST"""
        if not self.running:
            return

        try:
            import requests
            
            msg_str = message.to_json()
            headers = {
                'Content-Type': 'application/json',
                'MCP-Session-Id': self.session_id
            }
            
            response = requests.post(self.remote_endpoint, data=msg_str, headers=headers)
            
            if response.status_code == 200:
                # Process the response from the server
                try:
                    response_data = response.json()
                    response_message = self.rpc_handler.parse_message(json.dumps(response_data))
                    
                    # Process the response message using the callback
                    if self.message_callback:
                        self.message_callback(response_message)
                except Exception as e:
                    self.send_error(f"Error processing response: {str(e)}")
            else:
                self.send_error(f"Error sending message: {response.status_code} - {response.text}")
                
        except ImportError:
            self.send_error("Required library 'requests' not found. Install with 'pip install requests'")
        except Exception as e:
            self.send_error(f"Error sending message to remote server: {str(e)}")

    def send_error(self, error_msg: str):
        """Send an error message"""
        print(f"[Client Streamable HTTP Transport Error] {error_msg}")

    def is_connected(self) -> bool:
        """Check if the client is connected"""
        # For Streamable HTTP, we consider connected if the transport is running
        # Since it's request-response based, there's no persistent connection
        return self.running