"""
HTTP/SSE Transport for MCP Server
Implements HTTP with Server-Sent Events transport as per MCP specification
"""
import json
import asyncio
import threading
from typing import Callable, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from ..utils.json_rpc import JsonRpcHandler, JsonRpcMessage


class HttpSseTransport:
    """Transport mechanism using HTTP with Server-Sent Events as per MCP specification"""
    
    def __init__(self, rpc_handler: JsonRpcHandler, host: str = "127.0.0.1", port: int = 3030):
        self.rpc_handler = rpc_handler
        self.host = host
        self.port = port
        self.app = FastAPI()
        self.running = False
        self.server_thread: Optional[threading.Thread] = None
        self.message_callback: Optional[Callable[[JsonRpcMessage], None]] = None
        
        # Connection state
        self.active_connections: Dict[str, Any] = {}
        self.client_message_queues: Dict[str, asyncio.Queue] = {}
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup FastAPI routes for HTTP/SSE transport"""
        # SSE endpoint for server messages
        @self.app.get("/sse")
        async def sse_endpoint(request: Request):
            return EventSourceResponse(
                self._event_generator(request),
                ping=10,  # Send ping every 10 seconds
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                }
            )
        
        # HTTP POST endpoint for client messages
        @self.app.post("/send")
        async def send_message(request: Request):
            try:
                body = await request.json()
                message = self.rpc_handler.parse_message(json.dumps(body))
                
                if self.message_callback:
                    self.message_callback(message)
                
                return {"status": "received"}
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid message: {str(e)}")
    
    async def _event_generator(self, request: Request):
        """Generate Server-Sent Events for connected clients"""
        client_id = str(id(request))  # Unique identifier for this connection
        
        # Add to active connections
        self.active_connections[client_id] = request
        self.client_message_queues[client_id] = asyncio.Queue()
        
        # Send endpoint event as per MCP spec
        yield {
            "event": "endpoint",
            "data": json.dumps({
                "uri": f"http://{self.host}:{self.port}/send"
            })
        }
        
        try:
            # Keep connection alive and send messages as they arrive
            while self.running and client_id in self.active_connections:
                try:
                    # Wait for a message with timeout
                    message = await asyncio.wait_for(
                        self.client_message_queues[client_id].get(), 
                        timeout=1.0
                    )
                    
                    if isinstance(message, JsonRpcMessage):
                        yield {
                            "event": "message",
                            "data": message.to_json()
                        }
                except asyncio.TimeoutError:
                    # Send a ping to keep connection alive
                    yield ": ping\n"
                    continue
        except Exception:
            pass
        finally:
            # Clean up connection
            if client_id in self.active_connections:
                del self.active_connections[client_id]
            if client_id in self.client_message_queues:
                del self.client_message_queues[client_id]
    
    def start(self, message_callback: Callable[[JsonRpcMessage], None]):
        """Start the HTTP/SSE transport server"""
        self.message_callback = message_callback
        self.running = True
        
        def run_server():
            import uvicorn
            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                log_level="info"
            )
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
    
    def stop(self):
        """Stop the HTTP/SSE transport server"""
        self.running = False
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=1.0)
    
    def send_message_to_client(self, message: JsonRpcMessage, client_id: Optional[str] = None):
        """Send a message to a specific client or all clients"""
        if not self.running:
            return
        
        if client_id and client_id in self.client_message_queues:
            # Send to specific client
            asyncio.create_task(self.client_message_queues[client_id].put(message))
        else:
            # Send to all connected clients
            for queue in self.client_message_queues.values():
                asyncio.create_task(queue.put(message))
    
    def send_message(self, message: JsonRpcMessage):
        """Send a message to all clients (for compatibility with base transport interface)"""
        self.send_message_to_client(message)
    
    def send_error(self, error_msg: str):
        """Log error message"""
        print(f"[HTTP/SSE Transport Error] {error_msg}")