"""
Client Operations Handlers for MCP Client
Implements methods for interacting with remote MCP servers
"""
import asyncio
import uuid
from typing import Dict, Any, Optional
from ..utils.json_rpc import JsonRpcHandler


class ClientOperationsHandlers:
    """Handles operations for communicating with remote MCP servers"""

    def __init__(self, rpc_handler: JsonRpcHandler):
        self.rpc_handler = rpc_handler

    def register_handlers(self, rpc_handler: JsonRpcHandler):
        """Register any client-specific handlers with the RPC handler"""
        # Currently, client operations are initiated by the client, not handled as incoming requests
        pass

    def call_remote_tool(self, tool_name: str, arguments: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        """Call a tool on the remote server"""
        try:
            params = {
                "name": tool_name,
                "arguments": arguments
            }
            
            result = asyncio.run(self._send_request_to_server(
                method="tools/call",
                params=params,
                timeout=timeout
            ))
            return result
        except Exception as e:
            return {
                "error": {
                    "type": "remote_call_error",
                    "message": f"Failed to call tool '{tool_name}' on remote server: {str(e)}"
                }
            }

    def list_remote_tools(self, timeout: float = 30.0) -> Dict[str, Any]:
        """List tools available on the remote server"""
        try:
            result = asyncio.run(self._send_request_to_server(
                method="tools/list",
                params={},
                timeout=timeout
            ))
            return result
        except Exception as e:
            return {
                "error": {
                    "type": "remote_call_error",
                    "message": f"Failed to list tools on remote server: {str(e)}"
                }
            }

    def read_remote_resource(self, uri: str, timeout: float = 30.0) -> Dict[str, Any]:
        """Read a resource from the remote server"""
        try:
            params = {"uri": uri}
            
            result = asyncio.run(self._send_request_to_server(
                method="resources/read",
                params=params,
                timeout=timeout
            ))
            return result
        except Exception as e:
            return {
                "error": {
                    "type": "remote_call_error",
                    "message": f"Failed to read resource '{uri}' from remote server: {str(e)}"
                }
            }

    def list_remote_resources(self, timeout: float = 30.0) -> Dict[str, Any]:
        """List resources available on the remote server"""
        try:
            result = asyncio.run(self._send_request_to_server(
                method="resources/list",
                params={},
                timeout=timeout
            ))
            return result
        except Exception as e:
            return {
                "error": {
                    "type": "remote_call_error",
                    "message": f"Failed to list resources on remote server: {str(e)}"
                }
            }

    def get_remote_prompt(self, prompt_name: str, arguments: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        """Get a prompt from the remote server"""
        try:
            params = {
                "name": prompt_name,
                "arguments": arguments
            }
            
            result = asyncio.run(self._send_request_to_server(
                method="prompts/get",
                params=params,
                timeout=timeout
            ))
            return result
        except Exception as e:
            return {
                "error": {
                    "type": "remote_call_error",
                    "message": f"Failed to get prompt '{prompt_name}' from remote server: {str(e)}"
                }
            }

    def list_remote_prompts(self, timeout: float = 30.0) -> Dict[str, Any]:
        """List prompts available on the remote server"""
        try:
            result = asyncio.run(self._send_request_to_server(
                method="prompts/list",
                params={},
                timeout=timeout
            ))
            return result
        except Exception as e:
            return {
                "error": {
                    "type": "remote_call_error",
                    "message": f"Failed to list prompts on remote server: {str(e)}"
                }
            }

    async def _send_request_to_server(self, method: str, params: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        """
        Send a request to the remote server and wait for a response.
        """
        if not self.rpc_handler.transport_layer:
            raise RuntimeError("Transport layer not set. Cannot send request to server.")

        # Generate a unique ID for this request
        request_id = str(uuid.uuid4())

        # Import JsonRpcMessage and MessageType from the json_rpc module
        from ..utils.json_rpc import JsonRpcMessage, MessageType
        
        # Create the request message
        request_message = JsonRpcMessage(
            message_type=MessageType.REQUEST,
            id=request_id,
            method=method,
            params=params
        )

        # Create a Future to wait for the response
        future = asyncio.Future()
        self.rpc_handler.pending_client_requests[request_id] = future

        try:
            # Send the request to the server via the transport layer
            self.rpc_handler.transport_layer.send_message(request_message)

            # Wait for the response with timeout
            response_data = await asyncio.wait_for(future, timeout=timeout)
            return response_data
        except asyncio.TimeoutError:
            # Clean up the pending request
            if request_id in self.rpc_handler.pending_client_requests:
                del self.rpc_handler.pending_client_requests[request_id]
            raise TimeoutError(f"Timeout waiting for response to {method} request")
        except Exception as e:
            # Clean up the pending request
            if request_id in self.rpc_handler.pending_client_requests:
                del self.rpc_handler.pending_client_requests[request_id]
            raise e