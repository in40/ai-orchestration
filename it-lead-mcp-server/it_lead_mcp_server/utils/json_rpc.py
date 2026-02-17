"""
JSON-RPC 2.0 Handler for MCP Server
Implements the core JSON-RPC 2.0 message handling with concurrency control
"""
import asyncio
import json
import time
from enum import Enum
from typing import Dict, Any, Callable, Optional, Union
from concurrent.futures import ThreadPoolExecutor
import threading


class MessageType(Enum):
    """Type of JSON-RPC message"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"


class JsonRpcMessage:
    """Represents a JSON-RPC 2.0 message"""
    
    def __init__(self, json_data: Union[str, Dict[str, Any]], message_type: MessageType):
        if isinstance(json_data, str):
            self.data = json.loads(json_data)
        else:
            self.data = json_data
        
        self.message_type = message_type
        self.id = self.data.get('id')
        self.method = self.data.get('method')
        self.params = self.data.get('params')
        self.jsonrpc = self.data.get('jsonrpc')
        
        # Determine if this is a notification (no id) or request/response (has id)
        if self.id is None:
            self.is_notification = True
        else:
            self.is_notification = False
    
    @classmethod
    def create_request(cls, method: str, params: Dict[str, Any], message_type: MessageType):
        """Create a new request message"""
        message_data = {
            "jsonrpc": "2.0",
            "id": f"req_{int(time.time() * 1000000)}",  # Unique ID based on timestamp
            "method": method,
            "params": params
        }
        return cls(message_data, message_type)
    
    def get_id(self) -> Optional[str]:
        """Get the message ID"""
        return self.id
    
    def get_method(self) -> Optional[str]:
        """Get the method name"""
        return self.method
    
    def get_params(self) -> Optional[Dict[str, Any]]:
        """Get the parameters"""
        return self.params
    
    def to_json(self) -> str:
        """Convert the message to JSON string"""
        return json.dumps(self.data)


class JsonRpcHandler:
    """Handles JSON-RPC 2.0 messages with concurrency control"""
    
    def __init__(self, max_concurrent_requests: int = 10):
        self.request_handlers: Dict[str, Callable] = {}
        self.notification_handlers: Dict[str, Callable] = {}
        self.response_callbacks: Dict[str, Callable] = {}
        self.pending_requests: Dict[str, asyncio.Future] = {}
        
        # Concurrency control
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.current_concurrent_requests = 0
        self.max_concurrent_requests = max_concurrent_requests
        self.total_requests = 0
        self.failed_requests = 0
        
        # Transport layer reference for sending responses
        self.transport_layer = None
        
        # Thread pool for CPU-bound operations
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Lock for thread-safe operations
        self.lock = threading.Lock()
    
    def set_transport_layer(self, transport_layer):
        """Set the transport layer for sending responses"""
        self.transport_layer = transport_layer
    
    def register_request_handler(self, method: str, handler: Callable):
        """Register a handler for a specific request method"""
        self.request_handlers[method] = handler
    
    def register_notification_handler(self, method: str, handler: Callable):
        """Register a handler for a specific notification method"""
        self.notification_handlers[method] = handler
    
    def register_response_callback(self, request_id: str, callback: Callable):
        """Register a callback for a specific request ID"""
        self.response_callbacks[request_id] = callback
    
    async def handle_message(self, message: JsonRpcMessage):
        """Asynchronously handle an incoming message"""
        async with self.semaphore:
            with self.lock:
                self.current_concurrent_requests += 1
                self.total_requests += 1
            
            try:
                if message.is_notification:
                    # Handle notification
                    return await self._handle_notification(message)
                else:
                    # Handle request or response
                    if message.message_type == MessageType.RESPONSE:
                        # This is a response to a previous request we made
                        return await self._handle_response(message)
                    else:
                        # This is a request from the client
                        return await self._handle_request(message)
            except Exception as e:
                print(f"Error handling message: {e}")
                self.failed_requests += 1
                raise
            finally:
                with self.lock:
                    self.current_concurrent_requests -= 1
    
    def handle_message_sync(self, message: JsonRpcMessage):
        """Synchronously handle an incoming message (for stdio transport)"""
        # Acquire semaphore synchronously
        # Since this is sync, we'll just check the count
        with self.lock:
            if self.current_concurrent_requests >= self.max_concurrent_requests:
                raise Exception(f"Max concurrent requests ({self.max_concurrent_requests}) exceeded")
            
            self.current_concurrent_requests += 1
            self.total_requests += 1
        
        try:
            if message.is_notification:
                # Handle notification
                return self._handle_notification_sync(message)
            else:
                # Handle request or response
                if message.message_type == MessageType.RESPONSE:
                    # This is a response to a previous request we made
                    return self._handle_response_sync(message)
                else:
                    # This is a request from the client
                    return self._handle_request_sync(message)
        except Exception as e:
            print(f"Error handling message: {e}")
            self.failed_requests += 1
            raise
        finally:
            with self.lock:
                self.current_concurrent_requests -= 1
    
    async def _handle_request(self, message: JsonRpcMessage):
        """Handle an incoming request"""
        method = message.get_method()
        params = message.get_params()
        request_id = message.get_id()
        
        if method in self.request_handlers:
            try:
                # Call the handler and get result
                result = await self._call_handler_async(self.request_handlers[method], params, request_id)
                
                # Create response
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
                
                return JsonRpcMessage(response, MessageType.RESPONSE)
            except Exception as e:
                # Create error response
                error_response = self._create_error_response(request_id, -32603, str(e))
                return error_response
        else:
            # Method not found
            error_response = self._create_error_response(request_id, -32601, f"Method '{method}' not found")
            return error_response
    
    def _handle_request_sync(self, message: JsonRpcMessage):
        """Handle an incoming request synchronously"""
        method = message.get_method()
        params = message.get_params()
        request_id = message.get_id()
        
        if method in self.request_handlers:
            try:
                # Call the handler and get result
                result = self._call_handler_sync(self.request_handlers[method], params, request_id)
                
                # Create response
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
                
                return JsonRpcMessage(response, MessageType.RESPONSE)
            except Exception as e:
                # Create error response
                error_response = self._create_error_response(request_id, -32603, str(e))
                return error_response
        else:
            # Method not found
            error_response = self._create_error_response(request_id, -32601, f"Method '{method}' not found")
            return error_response
    
    async def _handle_notification(self, message: JsonRpcMessage):
        """Handle an incoming notification"""
        method = message.get_method()
        params = message.get_params()
        
        if method in self.notification_handlers:
            # Call the handler (notifications don't have responses)
            await self._call_handler_async(self.notification_handlers[method], params, None)
        else:
            # Unknown notification, just log it
            print(f"Unknown notification method: {method}")
    
    def _handle_notification_sync(self, message: JsonRpcMessage):
        """Handle an incoming notification synchronously"""
        method = message.get_method()
        params = message.get_params()
        
        if method in self.notification_handlers:
            # Call the handler (notifications don't have responses)
            self._call_handler_sync(self.notification_handlers[method], params, None)
        else:
            # Unknown notification, just log it
            print(f"Unknown notification method: {method}")
    
    async def _handle_response(self, message: JsonRpcMessage):
        """Handle an incoming response to a request we made"""
        request_id = message.get_id()
        
        # Check if we have a pending request for this ID
        if request_id in self.pending_requests:
            future = self.pending_requests[request_id]
            # Complete the future with the response
            future.set_result(message)
            # Remove from pending requests
            del self.pending_requests[request_id]
        else:
            # No pending request for this ID, log warning
            print(f"Received response for unknown request ID: {request_id}")
    
    def _handle_response_sync(self, message: JsonRpcMessage):
        """Handle an incoming response to a request we made (sync)"""
        request_id = message.get_id()
        
        # Check if we have a pending request for this ID
        if request_id in self.pending_requests:
            future = self.pending_requests[request_id]
            # Complete the future with the response
            future.set_result(message)
            # Remove from pending requests
            del self.pending_requests[request_id]
        else:
            # No pending request for this ID, log warning
            print(f"Received response for unknown request ID: {request_id}")
    
    def handle_client_response(self, message: JsonRpcMessage):
        """Handle a response from the client to a request we initiated"""
        request_id = message.get_id()
        
        if request_id in self.pending_requests:
            future = self.pending_requests[request_id]
            if not future.done():
                future.set_result(message)
        elif request_id in self.response_callbacks:
            # Call the registered callback
            callback = self.response_callbacks[request_id]
            callback(message)
        else:
            print(f"Received response for untracked request ID: {request_id}")
    
    async def _call_handler_async(self, handler: Callable, params: Dict[str, Any], request_id: Optional[str]):
        """Call a handler function asynchronously"""
        # Check if handler is already async
        if asyncio.iscoroutinefunction(handler):
            return await handler(params, request_id)
        else:
            # Run sync function in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self.executor, handler, params, request_id)
    
    def _call_handler_sync(self, handler: Callable, params: Dict[str, Any], request_id: Optional[str]):
        """Call a handler function synchronously"""
        # Just call the handler directly
        return handler(params, request_id)
    
    def _create_error_response(self, request_id: str, code: int, message: str):
        """Create an error response message"""
        error_response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }
        return JsonRpcMessage(error_response, MessageType.RESPONSE)
    
    async def send_request_and_wait(self, request: JsonRpcMessage, timeout: float = 1200.0):
        """Send a request and wait for the response"""
        request_id = request.get_id()
        
        # Create a future to hold the response
        future = asyncio.Future()
        self.pending_requests[request_id] = future
        
        # Send the request through the transport
        if self.transport_layer:
            self.transport_layer.send_message(request)
        else:
            raise Exception("Transport layer not set")
        
        try:
            # Wait for the response with timeout
            response = await asyncio.wait_for(future, timeout)
            return response
        except asyncio.TimeoutError:
            # Remove the pending request
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]
            raise TimeoutError(f"Request {request_id} timed out after {timeout} seconds")
    
    def get_metrics(self):
        """Get current metrics about the RPC handler"""
        return {
            "current_concurrent_requests": self.current_concurrent_requests,
            "max_concurrent_requests": self.max_concurrent_requests,
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "uptime": getattr(self, '_start_time', time.time()) - time.time()
        }