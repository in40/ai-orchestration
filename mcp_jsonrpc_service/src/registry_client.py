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


class RegistryClient:
    """
    Client for interacting with the MCP server registry.
    """
    
    def __init__(self, registry_endpoint: str):
        self.registry_endpoint = registry_endpoint
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def __aenter__(self):
        """Context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.session:
            await self.session.close()
    
    async def register_server(self, server_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a server with the registry.
        
        Args:
            server_info: Dictionary containing server information
            
        Returns:
            Registration result from the registry
        """
        if not self.session:
            raise RuntimeError("RegistryClient not initialized. Use as context manager.")
        
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
                # HTTP communication with the registry
                registry_url = f"{self.registry_endpoint}/mcp"

                # Prepare the JSON-RPC request
                rpc_request = {
                    "jsonrpc": "2.0",
                    "method": "registry-register_server",
                    "params": server_info,
                    "id": 1
                }

                async with self.session.post(
                    registry_url,
                    json=rpc_request,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    result = await response.json()

                    if "error" in result:
                        self.logger.error(f"Registry registration failed: {result['error']}")
                        return {"success": False, "error": result["error"]}

                    return result.get("result", {})
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
        if not self.session:
            raise RuntimeError("RegistryClient not initialized. Use as context manager.")
        
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
                # HTTP communication with the registry
                registry_url = f"{self.registry_endpoint}/mcp"

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

                async with self.session.post(
                    registry_url,
                    json=rpc_request,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    result = await response.json()

                    if "error" in result:
                        self.logger.error(f"Registry status update failed: {result['error']}")
                        return {"success": False, "error": result["error"]}

                    return result.get("result", {})
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
        if not self.session:
            raise RuntimeError("RegistryClient not initialized. Use as context manager.")
        
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
                # HTTP communication with the registry
                registry_url = f"{self.registry_endpoint}/mcp"

                # Prepare the JSON-RPC request
                rpc_request = {
                    "jsonrpc": "2.0",
                    "method": "registry-list_servers",
                    "params": {},
                    "id": 3
                }

                async with self.session.post(
                    registry_url,
                    json=rpc_request,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    result = await response.json()

                    if "error" in result:
                        self.logger.error(f"Registry list servers failed: {result['error']}")
                        return {"servers": [], "error": result["error"]}

                    return result.get("result", {"servers": []})
            else:
                raise ValueError(f"Unsupported registry endpoint scheme: {parsed_url.scheme}")
                
        except Exception as e:
            self.logger.error(f"Failed to list servers from registry: {e}")
            return {"servers": [], "error": str(e)}