"""
Client Handlers for MCP Server
Implements all standard MCP client methods that the server can initiate
"""
import asyncio
from typing import Dict, Any, Callable
from ..utils.json_rpc import JsonRpcHandler


class ClientMethodsHandlers:
    """Handles all standard MCP client methods that the server can initiate"""

    def __init__(self, rpc_handler: JsonRpcHandler):
        self.rpc_handler = rpc_handler
        self.client_callbacks: Dict[str, Callable] = {}

    def register_handlers(self, rpc_handler: JsonRpcHandler):
        """Register all client method handlers with the RPC handler"""
        # These are methods that the server can call on the client
        # In a real implementation, these would send requests to the client
        # and wait for responses
        pass

    async def request_sampling_complete(self, params: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        """Request sampling/complete from client - request completion from client"""
        # This would typically be called by the server to request a language model completion
        # from the client (e.g., an LLM)
        try:
            result = await self.rpc_handler.send_request_to_client(
                method="sampling/complete",
                params=params,
                timeout=timeout
            )
            return result
        except TimeoutError:
            # Return a specific timeout error
            return {
                "error": {
                    "type": "timeout_error",
                    "message": f"Timeout waiting for sampling/complete response from client ({timeout}s)"
                }
            }
        except Exception as e:
            # Return an error response if the client doesn't support the method or times out
            return {
                "error": {
                    "type": "client_error",
                    "message": f"Failed to get completion from client: {str(e)}"
                }
            }

    async def request_elicitation(self, params: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        """Request elicitation/request from client - request user input from client"""
        # This would typically be called by the server to request user input
        # from the client (e.g., asking the user a question)
        try:
            result = await self.rpc_handler.send_request_to_client(
                method="elicitation/request",
                params=params,
                timeout=timeout
            )
            return result
        except TimeoutError:
            # Return a specific timeout error
            return {
                "error": {
                    "type": "timeout_error",
                    "message": f"Timeout waiting for elicitation/request response from client ({timeout}s)"
                }
            }
        except Exception as e:
            # Return an error response if the client doesn't support the method or times out
            return {
                "error": {
                    "type": "client_error",
                    "message": f"Failed to get user input from client: {str(e)}"
                }
            }

    async def send_logging_message(self, params: Dict[str, Any], timeout: float = 10.0) -> Dict[str, Any]:
        """Send logging/message to client - send log message to client"""
        # Add timestamp if not present
        if "timestamp" not in params:
            import datetime
            params["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"

        # Send the log message to the client
        try:
            result = await self.rpc_handler.send_request_to_client(
                method="logging/message",
                params=params,
                timeout=timeout
            )
            return result
        except TimeoutError:
            # Just log the error if sending to client fails, but don't raise an exception
            # since logging shouldn't break the main functionality
            level = params.get("level", "info")
            message = params.get("message", "")
            logger_name = params.get("logger", "mcp-server")
            print(f"[{logger_name}] {level.upper()}: {message} (Timeout sending to client: {timeout}s)")
            return {}
        except Exception as e:
            # Just log the error if sending to client fails, but don't raise an exception
            # since logging shouldn't break the main functionality
            level = params.get("level", "info")
            message = params.get("message", "")
            logger_name = params.get("logger", "mcp-server")
            print(f"[{logger_name}] {level.upper()}: {message} (Failed to send to client: {str(e)})")
            return {}