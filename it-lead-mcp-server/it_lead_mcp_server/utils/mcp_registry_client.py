"""
MCP Registry Client for IT Lead Server
Connects to central MCP Registry Server via MCP protocol to discover agents
"""
import requests
import json
from typing import Dict, List, Any, Optional


class McpRegistryClient:
    """
    MCP Registry Client that communicates with the central MCP Registry Server
    via MCP protocol (HTTP POST to /mcp endpoint) to discover registered agents.
    
    This is the CORRECT way to discover agents - via MCP protocol, not direct DB access.
    """

    def __init__(self, registry_endpoint: str = "http://127.0.0.1:3031/mcp"):
        """
        Initialize MCP Registry Client
        
        Args:
            registry_endpoint: MCP endpoint of the central Registry Server
        """
        self.registry_endpoint = registry_endpoint
        self._cache = None
        self._cache_timestamp = 0
        self._cache_ttl = 60  # Cache for 60 seconds

    def list_services(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        List all registered services via MCP protocol
        
        Args:
            use_cache: Whether to use cached results (default True)
            
        Returns:
            List of registered services
        """
        import time
        
        # Check cache first
        if use_cache and self._cache and (time.time() - self._cache_timestamp) < self._cache_ttl:
            return self._cache
        
        try:
            # Call registry/list via MCP protocol
            response = requests.post(
                self.registry_endpoint,
                json={
                    "jsonrpc": "2.0",
                    "id": f"registry-list-{int(time.time() * 1000)}",
                    "method": "tools/call",
                    "params": {
                        "name": "registry/list",
                        "arguments": {}
                    }
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                services = result.get("result", {}).get("services", [])
                
                # Update cache
                self._cache = services
                self._cache_timestamp = time.time()
                
                print(f"✅ Retrieved {len(services)} services from MCP Registry Server")
                return services
            else:
                print(f"❌ Registry Server returned status {response.status_code}: {response.text}")
                return self._cache or []
                
        except requests.RequestException as e:
            print(f"❌ Failed to connect to MCP Registry Server at {self.registry_endpoint}: {e}")
            return self._cache or []
        except Exception as e:
            print(f"❌ Unexpected error calling MCP Registry Server: {e}")
            return self._cache or []

    def get_agent_endpoint(self, agent_name: str) -> Optional[str]:
        """
        Get the endpoint for a specific agent by name
        
        Args:
            agent_name: Name of the agent (e.g., "implementation-engineer")
            
        Returns:
            Agent endpoint URL or None if not found
        """
        services = self.list_services()
        
        agent_name_lower = agent_name.lower()
        
        for service in services:
            service_name = service.get("name", "").lower()
            
            # Match agent name to service name
            if agent_name_lower in service_name or service_name in agent_name_lower:
                endpoint = service.get("endpoint")
                if endpoint:
                    print(f"✅ Found endpoint for {agent_name}: {endpoint}")
                    return endpoint
        
        print(f"⚠️  No endpoint found for {agent_name}")
        return None

    def get_service_by_id(self, service_id: str) -> Optional[Dict[str, Any]]:
        """
        Get service details by ID
        
        Args:
            service_id: Service ID
            
        Returns:
            Service details or None if not found
        """
        services = self.list_services()
        
        for service in services:
            if service.get("id") == service_id:
                return service
        
        return None

    def is_agent_available(self, agent_name: str) -> bool:
        """
        Check if an agent is available (registered and has endpoint)
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            True if agent is available, False otherwise
        """
        endpoint = self.get_agent_endpoint(agent_name)
        return endpoint is not None

    def clear_cache(self):
        """Clear the service cache to force fresh lookup"""
        self._cache = None
        self._cache_timestamp = 0

    def get_available_tools(self, agent_name: str) -> List[str]:
        """
        Get list of available tools for an agent
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            List of tool names
        """
        services = self.list_services()
        agent_name_lower = agent_name.lower()
        
        for service in services:
            service_name = service.get("name", "").lower()
            
            if agent_name_lower in service_name or service_name in agent_name_lower:
                capabilities = service.get("capabilities", {})
                tools = capabilities.get("tools", [])
                return tools
        
        return []
