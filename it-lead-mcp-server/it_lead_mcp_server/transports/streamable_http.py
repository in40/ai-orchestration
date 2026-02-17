"""
Streamable HTTP Transport for MCP Server
Modern Streamable HTTP transport implementation using a single /mcp endpoint
"""
import asyncio
import json
from typing import Callable, Dict, Any
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import uvicorn
import threading
from ..utils.json_rpc import JsonRpcMessage, MessageType


class StreamableHttpTransport:
    """Modern Streamable HTTP transport implementation using a single /mcp endpoint"""

    def __init__(self, rpc_handler, host: str = "127.0.0.1", port: int = 3030):
        self.rpc_handler = rpc_handler
        self.host = host
        self.port = port
        self.app = FastAPI()
        self.running = False
        self.server_thread = None
        self.message_callback = None
        
        # Session management
        self.sessions = {}
        self.session_counter = 0
        
        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup FastAPI routes for the transport"""
        @self.app.post("/mcp")
        async def handle_post(request: Request):
            """Handle POST requests - client-to-server communication"""
            try:
                # Get the session ID from header
                session_id = request.headers.get("MCP-Session-Id", "default")
                
                # Read the request body
                body = await request.json()
                
                # Create a message object
                message = JsonRpcMessage(body, MessageType.REQUEST)
                
                # Process the message
                response = self.rpc_handler.handle_message_sync(message)
                
                # Return the response
                if response:
                    with open("/tmp/mcp_debug.log", "a") as f:
                        f.write(f"DEBUG: response is not None\n")
                        f.write(f"DEBUG: response.to_json() = {response.to_json()}\n")
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

        @self.app.get("/mcp")
        async def handle_get(websocket: WebSocket):
            """Handle GET requests - server-to-client communication via WebSocket"""
            await websocket.accept()
            
            # Generate a unique session ID
            session_id = f"session_{self.session_counter}"
            self.session_counter += 1
            self.sessions[session_id] = websocket
            
            try:
                # Listen for messages from the client (though in Streamable HTTP, 
                # this is primarily for connection metadata)
                while True:
                    # Wait for a message (but we don't really expect any in this model)
                    data = await websocket.receive_text()
                    # In the Streamable HTTP model, the GET endpoint is primarily for
                    # establishing the connection, not for receiving messages
                    # So we'll just acknowledge receipt
                    await websocket.send_text('{"type": "ack", "message": "connection established"}')
            except WebSocketDisconnect:
                # Clean up session
                if session_id in self.sessions:
                    del self.sessions[session_id]

        @self.app.get("/metrics")
        async def get_metrics(request: Request):
            """Get server metrics"""
            metrics = self.rpc_handler.get_metrics()
            return JSONResponse(content=metrics)

    def start(self, message_callback: Callable[[JsonRpcMessage], None]):
        """Start the HTTP transport server"""
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
        """Stop the HTTP transport server"""
        self.running = False
        # Note: uvicorn doesn't have a clean shutdown method from another thread
        # In a real implementation, you'd want to handle this more gracefully

    def send_message(self, message: JsonRpcMessage):
        """Send a message to all connected clients"""
        # In Streamable HTTP, we don't typically send unsolicited messages
        # Instead, responses are sent as part of the request-response cycle
        # This method is mainly for notifications in a mixed-mode scenario
        pass

    def _send_response(self, response):
        """Send a response message"""
        # This would be called when we have a response to send back
        # In FastAPI, responses are sent as part of the route handler
        pass

    def send_message_to_client(self, message: JsonRpcMessage):
        """Send a message to a specific client (for server-initiated requests)"""
        # In Streamable HTTP, server-initiated requests are sent as part of the 
        # request-response cycle when the client polls the endpoint
        # For true server pushes, we'd need to use the WebSocket connection
        json_message = json.loads(message.to_json())
        
        # Send to all active WebSocket sessions
        disconnected_sessions = []
        for session_id, websocket in self.sessions.items():
            try:
                asyncio.create_task(websocket.send_text(json.dumps(json_message)))
            except WebSocketDisconnect:
                disconnected_sessions.append(session_id)
        
        # Clean up disconnected sessions
        for session_id in disconnected_sessions:
            if session_id in self.sessions:
                del self.sessions[session_id]

    def send_error(self, error_msg: str):
        """Send an error message"""
        print(f"Transport Error: {error_msg}")