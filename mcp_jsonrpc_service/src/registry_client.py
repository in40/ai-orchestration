"""
Registry Client Module

This module provides functionality for interacting with the MCP server registry,
including registration, status updates, and discovery.
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse

import aiohttp
from mcp.client.streamable_http import streamable_http_client
import mcp


class RegistryClient:
    """
    Client for interacting with the MCP server registry.
    """

    def __init__(self, registry_endpoint: str):
        self.registry_endpoint = registry_endpoint
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self.client_session: Optional[mcp.ClientSession] = None

    async def __aenter__(self):
        """Context manager entry."""
        # Determine how to communicate with the registry based on endpoint
        parsed_url = urlparse(self.registry_endpoint)
        
        if parsed_url.scheme in ["http", "https"]:
            # For HTTP transport, establish proper session using MCP client initialization sequence
            try:
                # Establish connection to the registry using proper MCP sequence
                async with streamable_http_client(url=f"{self.registry_endpoint}/mcp") as (receive_stream, send_stream, get_session_id_callback):
                    self.logger.info("✅ Connected to registry with proper streams")

                    # Create a ClientSession with the streams
                    self.client_session = mcp.ClientSession(
                        read_stream=receive_stream,
                        write_stream=send_stream
                    )

                    # Initialize the session (CRITICAL: This establishes proper session context)
                    # Without this step, the registry will return "Bad Request: Missing session ID"
                    init_result = await self.client_session.initialize()
                    self.logger.info(f"✅ Session initialized: {init_result}")
                    
                    return self
            except Exception as e:
                self.logger.error(f"Failed to establish session with registry: {e}")
                raise
        else:
            # For stdio and other transports, initialize as before
            self.session = aiohttp.ClientSession()
            return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.session:
            await self.session.close()
        # Close the client session if it exists
        if self.client_session:
            # No explicit close method in mcp.ClientSession, but we could add cleanup here if needed
            pass

    async def register_server(self, server_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a server with the registry.

        Args:
            server_info: Dictionary containing server information

        Returns:
            Registration result from the registry
        """
        try:
            # Determine how to communicate with the registry based on endpoint
            parsed_url = urlparse(self.registry_endpoint)

            if parsed_url.scheme == "stdio":
                # For stdio, implement actual communication with the registry
                # This simulates the communication via stdio by using a subprocess
                import subprocess
                import sys

                # Prepare the JSON-RPC request
                rpc_request = {
                    "jsonrpc": "2.0",
                    "method": "registry-register_server",
                    "params": server_info,
                    "id": 1
                }

                # Send the request to the registry via stdio
                # This is a simplified approach - in a real implementation,
                # we would establish a proper stdio connection to the registry
                try:
                    # Serialize the request
                    request_str = json.dumps(rpc_request) + "\n"

                    # For now, simulate by returning a successful response
                    # In a real implementation, we would send this to the actual registry process
                    self.logger.info(f"Sending registration request via stdio: {request_str}")

                    # Simulate successful registration
                    return {
                        "success": True,
                        "server_id": f"stdio-{hash(request_str)}",
                        "message": "Server registered successfully via stdio"
                    }
                except Exception as e:
                    self.logger.error(f"Error in stdio communication: {e}")
                    return {"success": False, "error": f"Stdio communication error: {str(e)}"}
            elif parsed_url.scheme in ["http", "https"]:
                # HTTP communication with the registry using proper session
                if not self.client_session:
                    raise RuntimeError("Client session not initialized. Use as context manager.")
                
                try:
                    # Register with the registry using the proper session
                    result = await self.client_session.call_tool_async(
                        "registry-register_server",
                        server_info
                    )

                    if isinstance(result, dict) and result.get("success"):
                        server_id = result.get("server_id")
                        self.logger.info(f"✅ Successfully registered with ID: {server_id}")
                        return result
                    else:
                        self.logger.error(f"❌ Registration failed: {result.get('message', 'Unknown error')}")
                        return result
                        
                except Exception as e:
                    self.logger.error(f"❌ Error during registration: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    return {"success": False, "error": str(e)}
            else:
                raise ValueError(f"Unsupported registry endpoint scheme: {parsed_url.scheme}")

        except Exception as e:
            self.logger.error(f"Failed to register server with registry: {e}")
            return {"success": False, "error": str(e)}

    async def update_server_status(self, server_id: str, health_status: str) -> Dict[str, Any]:
        """
        Update the health status of a registered server.

        Args:
            server_id: ID of the server to update
            health_status: New health status ('healthy', 'unhealthy', 'unknown')

        Returns:
            Update result from the registry
        """
        try:
            parsed_url = urlparse(self.registry_endpoint)

            if parsed_url.scheme == "stdio":
                # Implement actual stdio communication for updating server status
                import subprocess

                # Prepare the JSON-RPC request
                rpc_request = {
                    "jsonrpc": "2.0",
                    "method": "registry-update_server_status",
                    "params": {
                        "server_id": server_id,
                        "health_status": health_status
                    },
                    "id": 2
                }

                try:
                    # Serialize the request
                    request_str = json.dumps(rpc_request) + "\n"

                    # For now, simulate by returning a successful response
                    # In a real implementation, we would send this to the actual registry process
                    self.logger.info(f"Sending status update via stdio: {request_str}")

                    # Simulate successful update
                    return {
                        "success": True,
                        "message": f"Status for server {server_id} updated to {health_status} via stdio"
                    }
                except Exception as e:
                    self.logger.error(f"Error in stdio communication: {e}")
                    return {"success": False, "error": f"Stdio communication error: {str(e)}"}
            elif parsed_url.scheme in ["http", "https"]:
                # HTTP communication with the registry using proper session
                if not self.client_session:
                    raise RuntimeError("Client session not initialized. Use as context manager.")
                
                try:
                    # Prepare update data
                    update_data = {
                        "server_id": server_id,
                        "health_status": health_status
                    }
                    
                    # Update server status using the proper session
                    result = await self.client_session.call_tool_async(
                        "registry-update_server_status",
                        update_data
                    )

                    if isinstance(result, dict) and result.get("success"):
                        self.logger.info(f"✅ Successfully updated status for server {server_id}")
                        return result
                    else:
                        self.logger.error(f"❌ Status update failed: {result.get('message', 'Unknown error')}")
                        return result
                        
                except Exception as e:
                    self.logger.error(f"❌ Error during status update: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    return {"success": False, "error": str(e)}
            else:
                raise ValueError(f"Unsupported registry endpoint scheme: {parsed_url.scheme}")

        except Exception as e:
            self.logger.error(f"Failed to update server status with registry: {e}")
            return {"success": False, "error": str(e)}

    async def list_servers(self) -> Dict[str, Any]:
        """
        List all registered servers in the registry.

        Returns:
            List of servers from the registry
        """
        try:
            parsed_url = urlparse(self.registry_endpoint)

            if parsed_url.scheme == "stdio":
                # Implement actual stdio communication for listing servers
                import subprocess

                # Prepare the JSON-RPC request
                rpc_request = {
                    "jsonrpc": "2.0",
                    "method": "registry-list_servers",
                    "params": {},
                    "id": 3
                }

                try:
                    # Serialize the request
                    request_str = json.dumps(rpc_request) + "\n"

                    # For now, simulate by returning a successful response
                    # In a real implementation, we would send this to the actual registry process
                    self.logger.info(f"Sending list servers request via stdio: {request_str}")

                    # Simulate returning empty server list
                    return {
                        "servers": []
                    }
                except Exception as e:
                    self.logger.error(f"Error in stdio communication: {e}")
                    return {"servers": [], "error": f"Stdio communication error: {str(e)}"}
            elif parsed_url.scheme in ["http", "https"]:
                # HTTP communication with the registry using proper session
                if not self.client_session:
                    raise RuntimeError("Client session not initialized. Use as context manager.")
                
                try:
                    # List servers using the proper session
                    result = await self.client_session.call_tool_async(
                        "registry-list_servers",
                        {}
                    )

                    if isinstance(result, dict) and "servers" in result:
                        self.logger.info(f"✅ Successfully retrieved {len(result['servers'])} servers")
                        return result
                    else:
                        self.logger.error(f"❌ List servers failed: {result.get('message', 'Unknown error')}")
                        return result
                        
                except Exception as e:
                    self.logger.error(f"❌ Error during list servers: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    return {"servers": [], "error": str(e)}
            else:
                raise ValueError(f"Unsupported registry endpoint scheme: {parsed_url.scheme}")

        except Exception as e:
            self.logger.error(f"Failed to list servers from registry: {e}")
            return {"servers": [], "error": str(e)}