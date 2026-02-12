"""
JSON-RPC 2.0 Message Handler for MCP Server
Handles parsing, validation, and routing of JSON-RPC messages
"""
import asyncio
import json
import uuid
from typing import Dict, Any, Callable, Optional
from enum import Enum

from .concurrency_monitor import get_monitor


class RpcMessageType(Enum):
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"


class JsonRpcMessage:
    """Represents a JSON-RPC 2.0 message"""

    def __init__(self, message_type: RpcMessageType, data: Dict[str, Any]):
        self.message_type = message_type
        self.data = data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JsonRpcMessage':
        """Create a JsonRpcMessage from a dictionary"""
        # Determine message type based on presence of 'id' and 'result/error'
        if 'id' not in data:
            message_type = RpcMessageType.NOTIFICATION
        elif 'result' in data or 'error' in data:
            message_type = RpcMessageType.RESPONSE
        else:
            message_type = RpcMessageType.REQUEST

        return cls(message_type, data)

    def to_json(self) -> str:
        """Convert the message to JSON string"""
        return json.dumps(self.data)

    def get_method(self) -> Optional[str]:
        """Get the method name for requests/notifications"""
        return self.data.get('method')

    def get_id(self) -> Optional[str]:
        """Get the message ID for requests/responses"""
        return self.data.get('id')


class JsonRpcHandler:
    """Handles JSON-RPC 2.0 message processing"""

    def __init__(self, max_concurrent_requests: int = 10):
        self.request_handlers: Dict[str, Callable] = {}
        self.notification_handlers: Dict[str, Callable] = {}
        self.pending_requests: Dict[str, Dict] = {}
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)  # Limit concurrent requests

    def register_request_handler(self, method: str, handler: Callable):
        """Register a handler for a specific request method"""
        self.request_handlers[method] = handler

    def register_notification_handler(self, method: str, handler: Callable):
        """Register a handler for a specific notification method"""
        self.notification_handlers[method] = handler
    
    def parse_message(self, raw_message: str) -> Optional[JsonRpcMessage]:
        """Parse a raw JSON string into a JsonRpcMessage object"""
        try:
            data = json.loads(raw_message.strip())

            # Validate JSON-RPC 2.0 format
            if 'jsonrpc' not in data or data['jsonrpc'] != '2.0':
                raise ValueError("Invalid JSON-RPC version")

            return JsonRpcMessage.from_dict(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
        except Exception as e:
            raise ValueError(f"Error parsing message: {e}")

    async def handle_message(self, message: JsonRpcMessage) -> Optional[JsonRpcMessage]:
        """Handle an incoming message and return a response if needed"""
        if message.message_type == RpcMessageType.REQUEST:
            return await self._handle_request(message)
        elif message.message_type == RpcMessageType.NOTIFICATION:
            await self._handle_notification(message)
            return None
        elif message.message_type == RpcMessageType.RESPONSE:
            await self._handle_response(message)
            return None
        else:
            raise ValueError(f"Unknown message type: {message.message_type}")

    def handle_message_sync(self, message: JsonRpcMessage) -> Optional[JsonRpcMessage]:
        """Synchronous version of handle_message for sync transports like stdio"""
        import asyncio

        # Check if we're already in an event loop
        try:
            loop = asyncio.get_running_loop()
            # We're in an event loop, so we can't use asyncio.run()
            # Instead, we need to run the coroutine in a separate thread
            import concurrent.futures
            import threading

            def run_in_new_loop():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(self.handle_message(message))
                finally:
                    new_loop.close()

            # Run the async function in a separate thread with its own event loop
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_in_new_loop)
                return future.result(timeout=30)
        except RuntimeError:
            # No event loop is running, we can safely use asyncio.run()
            # This can happen when called from a thread pool
            try:
                return asyncio.run(self.handle_message(message))
            except RuntimeError:
                # If asyncio.run() fails (which can happen in some contexts),
                # create and run in a new event loop manually
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(self.handle_message(message))
                finally:
                    new_loop.close()

    async def _handle_request(self, message: JsonRpcMessage) -> JsonRpcMessage:
        """Handle a request message"""
        method = message.get_method()
        msg_id = message.get_id()

        if not method:
            return self._create_error_response(msg_id, -32601, "Method not found")

        if method not in self.request_handlers:
            return self._create_error_response(msg_id, -32601, f"Method '{method}' not found")

        # Record request start in monitor
        monitor = get_monitor()
        request_metric = monitor.request_started(msg_id, method)

        # Acquire semaphore to limit concurrent requests
        async with self.semaphore:
            try:
                handler = self.request_handlers[method]
                params = message.data.get('params', {})
                
                # Call async handler if it's async, otherwise run in thread pool
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(params, msg_id)
                else:
                    result = await asyncio.to_thread(handler, params, msg_id)

                # Record successful completion
                monitor.request_finished(msg_id, "completed")
                
                return JsonRpcMessage(
                    RpcMessageType.RESPONSE,
                    {
                        'jsonrpc': '2.0',
                        'id': msg_id,
                        'result': result
                    }
                )
            except Exception as e:
                # Record error completion
                monitor.request_finished(msg_id, "error", str(e))
                return self._create_error_response(msg_id, -32603, f"Internal error: {str(e)}")

    async def _handle_notification(self, message: JsonRpcMessage):
        """Handle a notification message"""
        method = message.get_method()

        if not method:
            return  # Ignore notifications without method

        if method in self.notification_handlers:
            try:
                handler = self.notification_handlers[method]
                params = message.data.get('params', {})
                
                # Call async handler if it's async, otherwise run in thread pool
                if asyncio.iscoroutinefunction(handler):
                    await handler(params)
                else:
                    await asyncio.to_thread(handler, params)
            except Exception:
                # Notifications should not return errors, so just log
                pass

    async def _handle_response(self, message: JsonRpcMessage):
        """Handle a response message"""
        msg_id = message.get_id()

        if msg_id in self.pending_requests:
            # Process the response for the pending request
            # This would typically involve resolving a future/promise
            del self.pending_requests[msg_id]
    
    def _create_error_response(self, msg_id: Optional[str], code: int, message: str) -> JsonRpcMessage:
        """Create an error response message"""
        error_data = {
            'code': code,
            'message': message
        }

        response_data = {
            'jsonrpc': '2.0',
            'id': msg_id,
            'error': error_data
        }

        return JsonRpcMessage(RpcMessageType.RESPONSE, response_data)

    def create_request(self, method: str, params: Dict[str, Any] = None) -> JsonRpcMessage:
        """Create a request message"""
        msg_id = str(uuid.uuid4())
        data = {
            'jsonrpc': '2.0',
            'id': msg_id,
            'method': method
        }

        if params:
            data['params'] = params

        return JsonRpcMessage(RpcMessageType.REQUEST, data)

    def create_notification(self, method: str, params: Dict[str, Any] = None) -> JsonRpcMessage:
        """Create a notification message"""
        data = {
            'jsonrpc': '2.0',
            'method': method
        }

        if params:
            data['params'] = params

        return JsonRpcMessage(RpcMessageType.NOTIFICATION, data)

    def create_success_response(self, msg_id: str, result: Any) -> JsonRpcMessage:
        """Create a success response message"""
        data = {
            'jsonrpc': '2.0',
            'id': msg_id,
            'result': result
        }

        return JsonRpcMessage(RpcMessageType.RESPONSE, data)