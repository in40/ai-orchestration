"""
Client Handlers for MCP Server
Handles methods that the server can initiate on the client
"""
import asyncio
import time
from typing import Dict, Any
from ..utils.json_rpc import JsonRpcHandler, JsonRpcMessage


class ClientMethodsHandlers:
    """Handles client-initiated methods that the server can call"""

    def __init__(self, rpc_handler: JsonRpcHandler):
        self.rpc_handler = rpc_handler

    def register_handlers(self, rpc_handler: JsonRpcHandler):
        """Register client method handlers with the RPC handler"""
        # These are methods that the server can call on the client
        # They are registered so the server knows they exist
        pass

    async def request_sampling_complete(self, params: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        """Request sampling completion from the client"""
        # Create a request to send to the client
        request = JsonRpcMessage.create_request(
            method="sampling/complete",
            params=params,
            message_type=self.rpc_handler.MessageType.REQUEST
        )

        # Send the request and wait for response
        try:
            response = await self.rpc_handler.send_request_and_wait(request, timeout)
            return response.result if hasattr(response, 'result') else response
        except asyncio.TimeoutError:
            return {
                "error": {
                    "type": "timeout",
                    "message": f"Request timed out after {timeout} seconds"
                }
            }
        except Exception as e:
            return {
                "error": {
                    "type": "request_failed",
                    "message": f"Request failed: {str(e)}"
                }
            }

    async def request_elicitation(self, params: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        """Request user input from the client"""
        # Create a request to send to the client
        request = JsonRpcMessage.create_request(
            method="elicitation/request",
            params=params,
            message_type=self.rpc_handler.MessageType.REQUEST
        )

        # Send the request and wait for response
        try:
            response = await self.rpc_handler.send_request_and_wait(request, timeout)
            return response.result if hasattr(response, 'result') else response
        except asyncio.TimeoutError:
            return {
                "error": {
                    "type": "timeout",
                    "message": f"Request timed out after {timeout} seconds"
                }
            }
        except Exception as e:
            return {
                "error": {
                    "type": "request_failed",
                    "message": f"Request failed: {str(e)}"
                }
            }

    async def send_logging_message(self, params: Dict[str, Any], timeout: float = 10.0) -> Dict[str, Any]:
        """Send a log message to the client"""
        # Create a request to send to the client
        request = JsonRpcMessage.create_request(
            method="logging/message",
            params=params,
            message_type=self.rpc_handler.MessageType.REQUEST
        )

        # Send the request and wait for response
        try:
            response = await self.rpc_handler.send_request_and_wait(request, timeout)
            return response.result if hasattr(response, 'result') else response
        except asyncio.TimeoutError:
            # For logging, timeout might be acceptable
            print(f"Log message delivery timed out after {timeout} seconds: {params.get('message', '')}")
            return {"status": "timeout_but_logged"}
        except Exception as e:
            print(f"Failed to send log message: {e}")
            return {
                "error": {
                    "type": "delivery_failed",
                    "message": f"Log delivery failed: {str(e)}"
                }
            }