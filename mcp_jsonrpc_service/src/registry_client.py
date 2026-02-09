"""
Registry Client Module

This module provides functionality for interacting with the MCP server registry,
including registration, status updates, and discovery.
"""
import asyncio
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
                # For stdio, we would need to implement a different communication mechanism
                # This is a simplified placeholder
                self.logger.info("Using stdio transport for registry communication (simulated)")
                return {
                    "success": True,
                    "server_id": "simulated-stdio-id",
                    "message": "Server registered successfully via stdio"
                }
            elif parsed_url.scheme in ["http", "https"]:
                # HTTP communication with the registry
                registry_url = f"{self.registry_endpoint}/rpc"
                
                # Prepare the JSON-RPC request
                rpc_request = {
                    "jsonrpc": "2.0",
                    "method": "registry/register_server",
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
                # Simulated stdio communication
                self.logger.info(f"Updating status for server {server_id} via stdio (simulated)")
                return {
                    "success": True,
                    "message": f"Status for server {server_id} updated to {health_status}"
                }
            elif parsed_url.scheme in ["http", "https"]:
                # HTTP communication with the registry
                registry_url = f"{self.registry_endpoint}/rpc"
                
                # Prepare the JSON-RPC request
                rpc_request = {
                    "jsonrpc": "2.0",
                    "method": "registry/update_server_status",
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
                # Simulated stdio communication
                self.logger.info("Listing servers via stdio (simulated)")
                return {
                    "servers": []
                }
            elif parsed_url.scheme in ["http", "https"]:
                # HTTP communication with the registry
                registry_url = f"{self.registry_endpoint}/rpc"
                
                # Prepare the JSON-RPC request
                rpc_request = {
                    "jsonrpc": "2.0",
                    "method": "registry/list_servers",
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