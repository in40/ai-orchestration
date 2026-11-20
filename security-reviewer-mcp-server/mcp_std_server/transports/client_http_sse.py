"""
Client HTTP/SSE Transport for MCP Client
Implements HTTP with Server-Sent Events transport as a client connecting to another MCP server
This is the legacy transport method, maintained for backward compatibility.
"""
import json
import asyncio
import threading
import uuid
from typing import Callable, Optional, Dict, Any
from ..utils.json_rpc import JsonRpcHandler, JsonRpcMessage


class ClientHttpSseTransport:
    """Client transport mechanism using HTTP with Server-Sent Events to connect to another MCP server"""

    def __init__(self, rpc_handler: JsonRpcHandler, host: str = "127.0.0.0.1", port: int = 3030,
                 endpoint: Optional[str] = None):
        self.rpc_handler = rpc_handler
        self.host = host
        self.port = port
        self.running = False
        self.endpoint = endpoint or f"http://{host}:{port}"
        self.message_callback: Optional[Callable[[JsonRpcMessage], None]] = None
        
        # Connection state
        self.session_id = str(uuid.uuid4())
        self.connection_thread: Optional[threading.Thread] = None
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None

        # For HTTP/SSE, we'll use requests and aiohttp for client-side communication
        self.remote_endpoint = endpoint or f"http://{host}:{port}"
        self.sse_url = f"{self.remote_endpoint.rstrip('/')}/sse"
        self.message_url = f"{self.remote_endpoint.rstrip('/')}/message"
        self.send_url = f"{self.remote_endpoint.rstrip('/')}/send"

    def start(self, message_callback: Callable[[JsonRpcMessage], None]):
        """Start the HTTP/SSE transport client"""
        self.message_callback = message_callback
        self.running = True

        # Start a thread to handle SSE connection
        self.connection_thread = threading.Thread(target=self._connect_to_sse, daemon=True)
        self.connection_thread.start()

    def stop(self):
        """Stop the HTTP/SSE transport client"""
        self.running = False
        if self.connection_thread and self.connection_thread.is_alive():
            self.connection_thread.join(timeout=1.0)

    def _connect_to_sse(self):
        """Connect to the remote server's SSE endpoint"""
        try:
            import requests
            from sseclient import SSEClient
            
            # Connect to the SSE endpoint of the remote server
            headers = {'Accept': 'text/event-stream'}
            response = requests.get(self.sse_url, headers=headers, stream=True)
            
            # Use SSEClient to parse the event stream
            client = SSEClient(response)
            
            for event in client.events():
                if not self.running:
                    break
                    
                if event.event == 'message':
                    try:
                        # Parse the message from the remote server
                        message_data = json.loads(event.data)
                        message = self.rpc_handler.parse_message(json.dumps(message_data))
                        
                        # Process the message using the callback
                        if self.message_callback:
                            self.message_callback(message)
                    except Exception as e:
                        self.send_error(f"Error processing SSE message: {str(e)}")
                elif event.event == 'endpoint':
                    try:
                        # Handle endpoint information from the server
                        endpoint_info = json.loads(event.data)
                        if 'uri' in endpoint_info:
                            self.message_url = endpoint_info['uri']
                    except Exception as e:
                        self.send_error(f"Error processing endpoint event: {str(e)}")
                        
        except ImportError:
            self.send_error("Required library 'sseclient' not found. Install with 'pip install sseclient-py'")
        except Exception as e:
            self.send_error(f"Error connecting to SSE endpoint: {str(e)}")

    def send_message(self, message: JsonRpcMessage):
        """Send a message to the remote server via HTTP POST"""
        if not self.running:
            return

        try:
            import requests
            
            # Determine which URL to use based on server's advertised endpoint
            url = self.send_url  # Default to send URL for legacy compatibility
            
            msg_str = message.to_json()
            headers = {
                'Content-Type': 'application/json',
                'X-MCP-Session-ID': self.session_id
            }
            
            response = requests.post(url, data=msg_str, headers=headers)
            
            if response.status_code != 200:
                self.send_error(f"Error sending message: {response.status_code} - {response.text}")
                
        except ImportError:
            self.send_error("Required library 'requests' not found. Install with 'pip install requests'")
        except Exception as e:
            self.send_error(f"Error sending message to remote server: {str(e)}")

    def send_error(self, error_msg: str):
        """Send an error message"""
        print(f"[Client HTTP/SSE Transport Error] {error_msg}")

    def is_connected(self) -> bool:
        """Check if the client is connected"""
        # For HTTP/SSE, we consider connected if the SSE connection thread is running
        return self.running and self.connection_thread is not None and self.connection_thread.is_alive()