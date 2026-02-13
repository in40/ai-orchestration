"""
HTTP/SSE Transport for MCP Server
Legacy HTTP/SSE transport implementation with separate endpoints
"""
import asyncio
import json
from typing import Callable, Dict, Any
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
import threading
from sse_starlette.sse import EventSourceResponse
from ..utils.json_rpc import JsonRpcMessage, MessageType


class HttpSseTransport:
    """Legacy HTTP/SSE transport implementation with separate endpoints"""

    def __init__(self, rpc_handler, host: str = "127.0.0.1", port: int = 3030):
        self.rpc_handler = rpc_handler
        self.host = host
        self.port = port
        self.app = FastAPI()
        self.running = False
        self.server_thread = None
        self.message_callback = None
        
        # Client session management
        self.clients = {}
        self.session_counter = 0
        
        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup FastAPI routes for the transport"""
        @self.app.post("/send")  # Using /send as the main endpoint for client-to-server
        async def handle_send(request: Request):
            """Handle client-to-server communication"""
            try:
                # Get the session ID from header
                session_id = request.headers.get("X-MCP-Session-ID", "default")
                
                # Read the request body
                body = await request.json()
                
                # Create a message object
                message = JsonRpcMessage(body, MessageType.REQUEST)
                
                # Process the message
                response = self.rpc_handler.handle_message_sync(message)
                
                # Return the response
                if response:
                    return JSONResponse(content=json.loads(response.to_json()))
                else:
                    return JSONResponse(content={"jsonrpc": "2.0", "result": {}})
                    
            except Exception as e:
                return JSONResponse(
                    status_code=500,
                    content={
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32603,
                            "message": f"Internal error: {str(e)}"
                        }
                    }
                )

        @self.app.get("/sse")
        async def handle_sse(request: Request):
            """Handle server-sent events for server-to-client communication"""
            session_id = f"sse_session_{self.session_counter}"
            self.session_counter += 1
            self.clients[session_id] = request
            
            async def event_generator():
                # Send initial event with endpoint information
                yield {
                    "event": "endpoint",
                    "data": json.dumps({"endpoint": f"http://{self.host}:{self.port}/send"})
                }
                
                # Keep the connection alive and wait for server-initiated messages
                # In a real implementation, you'd have a queue or pub/sub system
                # to receive messages from the server to send to clients
                try:
                    while True:
                        # In this basic implementation, we just keep the connection alive
                        # In a real implementation, you'd wait for messages to send
                        await asyncio.sleep(30)  # Ping every 30 seconds
                        yield {"event": "ping", "data": json.dumps({"timestamp": asyncio.get_event_loop().time()})}
                except asyncio.CancelledError:
                    # Client disconnected
                    if session_id in self.clients:
                        del self.clients[session_id]
                    raise

            return EventSourceResponse(event_generator())

        @self.app.get("/metrics")
        async def get_metrics(request: Request):
            """Get server metrics"""
            metrics = self.rpc_handler.get_metrics()
            return JSONResponse(content=metrics)

    def start(self, message_callback: Callable[[JsonRpcMessage], None]):
        """Start the HTTP/SSE transport server"""
        self.message_callback = message_callback
        self.running = True
        
        # Run the server in a separate thread
        def run_server():
            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                log_level="warning"  # Suppress most logs but keep errors
            )
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

    def stop(self):
        """Stop the HTTP/SSE transport server"""
        self.running = False
        # Note: uvicorn doesn't have a clean shutdown method from another thread
        # In a real implementation, you'd want to handle this more gracefully

    def send_message(self, message: JsonRpcMessage):
        """Send a message to all connected clients"""
        # In SSE, we don't typically send unsolicited messages through this method
        # Instead, we'd send them through the SSE connection
        pass

    def _send_response(self, response):
        """Send a response message"""
        # This would be called when we have a response to send back
        # In FastAPI, responses are sent as part of the route handler
        pass

    def send_message_to_client(self, message: JsonRpcMessage):
        """Send a message to clients via SSE"""
        # Convert message to SSE format and send to all connected clients
        json_message = json.loads(message.to_json())
        
        # In a real implementation, you'd push this to an event queue
        # that the SSE generator could pick up and send to clients
        # For now, we'll just log that we attempted to send
        print(f"SSE message sent: {json_message}")

    def send_error(self, error_msg: str):
        """Send an error message"""
        print(f"Transport Error: {error_msg}")