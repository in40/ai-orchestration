"""Registry adapters for discovering MCP servers."""
import httpx
import urllib.parse
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod


class RegistryAdapter(ABC):
    """Abstract base class for registry adapters."""
    
    @abstractmethod
    async def search_servers(self) -> List[Dict[str, Any]]:
        """Search for available servers."""
        pass


class LocalhostRegistryAdapter(RegistryAdapter):
    """Adapter for localhost:3031 default registry."""

    def __init__(self, base_url: str = "http://localhost:3031/mcp"):
        self.base_url = base_url

    async def search_servers(self) -> List[Dict[str, Any]]:
        """Attempt to connect to localhost:3031 and get registered servers."""
        try:
            # First, check if the server is available
            async with httpx.AsyncClient() as client:
                # Check if the endpoint is accessible
                health_check = await client.get(f"{self.base_url}", timeout=5.0)
                if health_check.status_code != 200:
                    return []

                # For a registry, we need to initialize an MCP session to query for servers
                # First, initialize the connection
                init_req = {
                    "jsonrpc": "2.0",
                    "id": "init-registry-query",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {
                            "streams": False,
                            "experimental": {}
                        }
                    }
                }
                
                init_response = await client.post(
                    f"{self.base_url}",
                    json=init_req,
                    timeout=5.0
                )
                
                if init_response.status_code != 200:
                    return []
                
                init_data = init_response.json()
                server_info = init_data.get("result", {}).get("serverInfo", {})
                
                # Complete initialization handshake
                initialized_req = {
                    "jsonrpc": "2.0",
                    "id": "complete-init",
                    "method": "initialized",
                    "params": {
                        "serverInfo": server_info,
                        "capabilities": {"experimental": {}}
                    }
                }
                
                await client.post(f"{self.base_url}", json=initialized_req, timeout=5.0)
                
                # Now try to list tools to see if registry tools are available
                tools_req = {
                    "jsonrpc": "2.0",
                    "id": "list-tools",
                    "method": "tools/list"
                }
                
                tools_response = await client.post(
                    f"{self.base_url}",
                    json=tools_req,
                    timeout=5.0
                )
                
                if tools_response.status_code != 200:
                    return []
                
                tools_data = tools_response.json()
                tools_list = tools_data.get("result", {}).get("tools", [])
                
                # Check if registry tools are available
                registry_list_tool = next((tool for tool in tools_list if tool.get("name") == "registry/list"), None)
                
                if registry_list_tool:
                    # This is a registry server, call the registry/list tool to get registered servers
                    list_req = {
                        "jsonrpc": "2.0",
                        "id": "get-registered-servers",
                        "method": "tools/call",
                        "params": {
                            "tool": "registry/list",
                            "arguments": {}
                        }
                    }
                    
                    list_response = await client.post(
                        f"{self.base_url}",
                        json=list_req,
                        timeout=5.0
                    )
                    
                    if list_response.status_code == 200:
                        list_data = list_response.json()
                        result = list_data.get("result", {})
                        
                        # The result contains services in a 'services' array
                        servers_from_registry = result.get("services", []) or result.get("output", [])
                        
                        if isinstance(servers_from_registry, list):
                            # Format the servers to match our expected structure
                            formatted_servers = []
                            for server in servers_from_registry:
                                if isinstance(server, dict):
                                    # Get the URL for the server
                                    server_url = server.get("endpoint", server.get("url", self.base_url))
                                    
                                    # Normalize the URL - if it's the same host/port as registry but missing path, add /mcp
                                    # Parse the base URL to compare host and port
                                    registry_parsed = urllib.parse.urlparse(self.base_url)
                                    server_parsed = urllib.parse.urlparse(server_url)
                                    
                                    # If host and port match but path is missing or root, append the registry path
                                    # Handle equivalent hostnames like localhost and 127.0.0.1
                                    normalized_server_host = server_parsed.hostname
                                    if normalized_server_host == 'localhost':
                                        normalized_server_host = '127.0.0.1'
                                    normalized_registry_host = registry_parsed.hostname
                                    if normalized_registry_host == 'localhost':
                                        normalized_registry_host = '127.0.0.1'
                                        
                                    if (normalized_server_host == normalized_registry_host and 
                                        server_parsed.port == registry_parsed.port and
                                        (not server_parsed.path or server_parsed.path == '/')):
                                        server_url = self.base_url
                                    
                                    # Include all servers including the registry itself if it offers MCP services
                                    formatted_servers.append({
                                        "name": server.get("name", server.get("id", "unknown")),
                                        "url": server_url,
                                        "description": server.get("description", "Registered MCP server"),
                                        "adapter_type": "registry"
                                    })
                            
                            # If we got servers from the registry, return them
                            if formatted_servers:
                                return formatted_servers
                
                # If no registry functionality found, treat the server itself as an MCP server
                return [{
                    "name": server_info.get("name", "localhost-registry"),
                    "url": self.base_url,
                    "description": server_info.get("description", "Default local MCP registry"),
                    "adapter_type": "localhost"
                }]
                
        except httpx.RequestError:
            # Server is not available
            return []
        except Exception:
            # Any other error
            return []


class GitHubRegistryAdapter(RegistryAdapter):
    """Adapter for GitHub MCP registry."""
    
    def __init__(self, base_url: str = "https://registry.modelcontextprotocol.io/v0.1/servers"):
        self.base_url = base_url
        
    async def search_servers(self) -> List[Dict[str, Any]]:
        """Fetch servers from GitHub registry."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, timeout=10.0)
                response.raise_for_status()
                
                servers_data = response.json()
                
                # Format the server data to match our expected structure
                servers = []
                for server in servers_data.get('servers', []):
                    servers.append({
                        "name": server.get('name', 'unknown'),
                        "url": server.get('url', ''),
                        "description": server.get('description', ''),
                        "adapter_type": "github"
                    })
                    
                return servers
        except (httpx.RequestError, KeyError):
            return []


class NacosRegistryAdapter(RegistryAdapter):
    """Adapter for Nacos registry."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        
    async def search_servers(self) -> List[Dict[str, Any]]:
        """Fetch servers from Nacos registry."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/nacos/v1/ns/catalog/services", timeout=10.0)
                response.raise_for_status()
                
                services_data = response.json()
                
                # Format the service data to match our expected structure
                servers = []
                for service in services_data.get('serviceList', []):
                    servers.append({
                        "name": service.get('name', 'unknown'),
                        "url": f"{self.base_url}/{service.get('name', '')}",
                        "description": service.get('groupName', ''),
                        "adapter_type": "nacos"
                    })
                    
                return servers
        except (httpx.RequestError, KeyError):
            return []


class CustomRegistryAdapter(RegistryAdapter):
    """Adapter for custom registry URLs."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        
    async def search_servers(self) -> List[Dict[str, Any]]:
        """Fetch servers from a custom registry URL."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, timeout=10.0)
                response.raise_for_status()
                
                # Try to parse as registry format
                data = response.json()
                
                # Format the data to match our expected structure
                servers = []
                
                # Check if it follows the standard registry format
                if 'servers' in data:
                    for server in data['servers']:
                        servers.append({
                            "name": server.get('name', 'unknown'),
                            "url": server.get('url', ''),
                            "description": server.get('description', ''),
                            "adapter_type": "custom"
                        })
                else:
                    # Assume it's a single server entry
                    servers.append({
                        "name": data.get('name', 'custom-server'),
                        "url": self.base_url,
                        "description": data.get('description', 'Custom MCP server'),
                        "adapter_type": "custom"
                    })
                    
                return servers
        except (httpx.RequestError, KeyError, ValueError):
            return []


class RegistryManager:
    """Manages multiple registry adapters."""
    
    def __init__(self):
        self.adapters: List[RegistryAdapter] = []
        # Add the default localhost adapter
        self.add_adapter(LocalhostRegistryAdapter())
        
    def add_adapter(self, adapter: RegistryAdapter):
        """Add a registry adapter."""
        self.adapters.append(adapter)
        
    def remove_adapter(self, adapter: RegistryAdapter):
        """Remove a registry adapter."""
        if adapter in self.adapters:
            self.adapters.remove(adapter)
            
    async def search_all_servers(self) -> List[Dict[str, Any]]:
        """Search all registered adapters for available servers."""
        all_servers = []
        
        for adapter in self.adapters:
            try:
                servers = await adapter.search_servers()
                all_servers.extend(servers)
            except Exception:
                # Skip adapters that fail
                continue
                
        return all_servers