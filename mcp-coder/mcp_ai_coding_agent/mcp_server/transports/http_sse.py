"""
HTTP/SSE Transport for MCP Server
Implements HTTP with Server-Sent Events transport as per MCP specification
"""
import json
import asyncio
import threading
import uuid
from typing import Callable, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from ..utils.json_rpc import JsonRpcHandler, JsonRpcMessage
from ..utils.concurrency_monitor import get_monitor


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
        # Track which SSE connection should receive responses for which request
        self.request_to_client_map: Dict[str, str] = {}
        # Track SSE connection sessions
        self.sse_sessions: Dict[str, Dict] = {}

        # Dictionary to hold direct client queues for responses
        self.direct_response_queues = {}
        
        # Store reference to the main event loop
        try:
            self.main_loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop yet, will be set when the server starts
            self.main_loop = None

        self._setup_routes()
        
        # Setup the response distribution mechanism
        self._setup_response_distribution()
    
    def _setup_response_distribution(self):
        """Setup response distribution mechanism"""
        # Response distribution is handled directly in _send_response method
        pass

    def _setup_routes(self):
        """Setup FastAPI routes for HTTP/SSE transport"""
        # SSE endpoint for server messages
        @self.app.get("/sse")
        async def sse_endpoint(request: Request):
            # Generate a unique session ID for this SSE connection
            session_id = str(uuid.uuid4())
            return EventSourceResponse(
                self._event_generator(request, session_id),
                ping=10,  # Send ping every 10 seconds
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                }
            )

        # HTTP GET endpoint for monitoring and diagnostics
        @self.app.get("/metrics")
        async def get_metrics(request: Request):
            try:
                monitor = get_monitor()
                metrics = monitor.get_detailed_metrics()
                return metrics
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error retrieving metrics: {str(e)}")

        # HTTP POST endpoint for client messages
        @self.app.post("/send")
        async def send_message(request: Request):
            try:
                body = await request.json()
                message = self.rpc_handler.parse_message(json.dumps(body))
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid message format: {str(e)}")

            try:
                # Process the message using the message callback
                # The response will be handled by the callback and sent via SSE
                if self.message_callback:
                    # If this is a request (has an ID), track which client should receive the response
                    if hasattr(message, 'get_id') and message.get_id():
                        # Check if the client provided a session ID in the request headers
                        client_session_id = request.headers.get('X-MCP-Session-ID')

                        # If no session ID provided, try to determine the most likely client
                        if not client_session_id and len(self.active_connections) == 1:
                            # If only one client is connected, assume it's that client
                            client_session_id = next(iter(self.active_connections.keys()))
                        elif not client_session_id and len(self.active_connections) > 1:
                            # If multiple clients are connected and no session ID provided,
                            # we can't reliably determine which client made the request
                            # In this case, we'll send to all clients (current behavior)
                            # But let's try to use the most recently connected client as a heuristic
                            # Sort connections by connection time and pick the most recent
                            if self.sse_sessions:
                                # Get the most recently connected client
                                most_recent = max(self.sse_sessions.items(),
                                                key=lambda x: x[1].get('connected_at', 0))
                                client_session_id = most_recent[0]

                        # Map the request ID to the client session ID if we have one
                        if client_session_id and client_session_id in self.active_connections:
                            self.request_to_client_map[message.get_id()] = client_session_id

                    # Check if the callback is a coroutine function
                    if asyncio.iscoroutinefunction(self.message_callback):
                        await self.message_callback(message)
                    else:
                        # Run the synchronous callback in a thread pool to avoid blocking the event loop
                        await asyncio.get_event_loop().run_in_executor(None, self.message_callback, message)

                return {"status": "received"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

    async def _event_generator(self, request: Request, session_id: str):
        """Generate Server-Sent Events for connected clients"""
        client_id = session_id  # Use the session ID as the client identifier

        # Add to active connections
        self.active_connections[client_id] = request
        self.client_message_queues[client_id] = asyncio.Queue()

        # Add session info to track this connection
        self.sse_sessions[client_id] = {
            "connected_at": asyncio.get_event_loop().time(),
            "request": request
        }

        # Send endpoint event as per MCP spec
        yield {
            "event": "endpoint",
            "data": json.dumps({
                "uri": f"http://{self.host}:{self.port}/send",
                "sessionId": client_id  # Include the session ID for client correlation
            })
        }

        try:
            # Keep connection alive and send messages as they arrive
            while self.running and client_id in self.active_connections:
                try:
                    # Wait for a message with timeout from the client-specific queue
                    # This will get both direct messages to this client and responses distributed to it
                    message = await asyncio.wait_for(
                        self.client_message_queues[client_id].get(),
                        timeout=0.1  # Reduced timeout to allow frequent checks of the response queue
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
        except Exception as e:
            print(f"Error in event generator: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Clean up connection
            if client_id in self.active_connections:
                del self.active_connections[client_id]
            if client_id in self.client_message_queues:
                del self.client_message_queues[client_id]
            if client_id in self.sse_sessions:
                del self.sse_sessions[client_id]
            # Remove any request mappings for this client
            requests_to_remove = []
            for req_id, mapped_client_id in self.request_to_client_map.items():
                if mapped_client_id == client_id:
                    requests_to_remove.append(req_id)
            for req_id in requests_to_remove:
                del self.request_to_client_map[req_id]

    def start(self, message_callback: Callable[[JsonRpcMessage], None]):
        """Start the HTTP/SSE transport server"""
        self.message_callback = message_callback
        self.running = True

        # Capture the current event loop if available
        try:
            self.main_loop = asyncio.get_running_loop()
        except RuntimeError:
            # No event loop running in this thread, will be set when server starts
            pass

        def run_server():
            import uvicorn
            # Set the main loop reference when the server starts
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                # Update the main loop reference in case it's different
                self.main_loop = loop
                # Start the response distribution worker in this loop
                asyncio.create_task(self._response_distribution_worker())
            except RuntimeError:
                # If there's no running loop, we're in a thread context
                # In this case, we'll try to handle it differently
                pass
            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                log_level="info"
            )

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        # Also store the main loop at the time of start() call
        if not hasattr(self, 'main_loop') or self.main_loop is None:
            try:
                self.main_loop = asyncio.get_running_loop()
            except RuntimeError:
                # If no loop is available, we'll need to handle this differently
                pass

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

    def get_client_headers(self, client_id: str) -> Dict[str, str]:
        """Get headers that a client should include to identify itself"""
        return {
            "X-MCP-Session-ID": client_id,
            "Content-Type": "application/json"
        }

    def send_error(self, error_msg: str):
        """Log error message"""
        print(f"[HTTP/SSE Transport Error] {error_msg}")

    def _send_response(self, response):
        """Send response back to the appropriate client (for server compatibility)"""
        import asyncio
        import concurrent.futures
        import threading
        
        try:
            # Get the response ID to find the corresponding client
            response_id = None
            if hasattr(response, 'get_id'):
                response_id = response.get_id()
            elif hasattr(response, 'data') and 'id' in response.data:
                response_id = response.data['id']
            
            # Check if this response should go to a specific client
            target_client_id = None
            if response_id and response_id in self.request_to_client_map:
                target_client_id = self.request_to_client_map[response_id]
                # Remove the mapping after identifying the target
                # Use pop to safely remove and avoid KeyError if already removed
                self.request_to_client_map.pop(response_id, None)
            
            # Put the response directly in the appropriate client's queue
            if target_client_id and target_client_id in self.client_message_queues:
                # Use a thread-safe approach to schedule the coroutine
                loop = self.main_loop
                if loop and not loop.is_closed():
                    future = asyncio.run_coroutine_threadsafe(
                        self.client_message_queues[target_client_id].put(response),
                        loop
                    )
                else:
                    # If no main loop is available, try to get the current running loop
                    try:
                        current_loop = asyncio.get_running_loop()
                        asyncio.run_coroutine_threadsafe(
                            self.client_message_queues[target_client_id].put(response),
                            current_loop
                        )
                    except RuntimeError:
                        # No loop running, we're in a sync context
                        # Create a temporary thread with its own loop to handle this
                        def run_in_thread():
                            temp_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(temp_loop)
                            try:
                                temp_loop.run_until_complete(
                                    self.client_message_queues[target_client_id].put(response)
                                )
                            finally:
                                temp_loop.close()
                        
                        thread = threading.Thread(target=run_in_thread, daemon=True)
                        thread.start()
            else:
                # If no specific target, send to all clients (fallback behavior)
                for client_queue in self.client_message_queues.values():
                    loop = self.main_loop
                    if loop and not loop.is_closed():
                        future = asyncio.run_coroutine_threadsafe(
                            client_queue.put(response),
                            loop
                        )
                    else:
                        # If no main loop is available, try to get the current running loop
                        try:
                            current_loop = asyncio.get_running_loop()
                            asyncio.run_coroutine_threadsafe(
                                client_queue.put(response),
                                current_loop
                            )
                        except RuntimeError:
                            # No loop running, we're in a sync context
                            # Create a temporary thread with its own loop to handle this
                            def run_in_thread():
                                temp_loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(temp_loop)
                                try:
                                    temp_loop.run_until_complete(client_queue.put(response))
                                finally:
                                    temp_loop.close()
                            
                            thread = threading.Thread(target=run_in_thread, daemon=True)
                            thread.start()
        except Exception as e:
            print(f"Error sending response: {e}")
            import traceback
            traceback.print_exc()