"""
MCP Registry Client for IT Lead Server
Connects to central MCP Registry Server via MCP protocol to discover agents
and introspect their tools via standard MCP tools/list method.
"""
import requests
import json
import time
from typing import Dict, List, Any, Optional


class McpRegistryClient:
    """
    MCP Registry Client that communicates with the central MCP Registry Server
    via MCP protocol (HTTP POST to /mcp endpoint) to discover registered agents
    and introspect their available tools.

    This is the CORRECT way to discover agents and tools - via MCP protocol,
    not direct DB access or hardcoded lists.
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
        self._cache_ttl = 300  # Cache for 5 minutes (was 60 seconds)
        self._tools_cache = {}  # Cache for individual agent tools
        self._tools_cache_timestamp = {}
        self._tools_cache_ttl = 300  # Cache tool schemas for 5 minutes

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
        cache_check = use_cache and self._cache and (time.time() - self._cache_timestamp) < self._cache_ttl
        print(f"🔍 list_services called: use_cache={use_cache}, has_cache={self._cache is not None}, cache_check={cache_check}")
        
        if cache_check:
            print(f"📦 Returning cached services: {len(self._cache)}")
            return self._cache

        print(f"🌐 Fetching fresh services from {self.registry_endpoint}")
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
        
        # Normalize agent name for matching (remove common suffixes/prefixes)
        agent_name_normalized = agent_name_lower.replace("-engineer", "").replace("_", "-").strip("-")

        for service in services:
            service_name = service.get("name", "").lower()
            service_id = service.get("id", "").lower()

            # Match agent name to service name using multiple strategies
            # Strategy 1: Direct substring match
            if agent_name_lower in service_name or service_name in agent_name_lower:
                endpoint = service.get("endpoint")
                if endpoint:
                    print(f"✅ Found endpoint for {agent_name} (strategy 1): {endpoint}")
                    return endpoint
            
            # Strategy 2: Match normalized name (e.g., "devops" matches "devops-release-engineer")
            if agent_name_normalized and agent_name_normalized in service_name:
                endpoint = service.get("endpoint")
                if endpoint:
                    print(f"✅ Found endpoint for {agent_name} (strategy 2): {endpoint}")
                    return endpoint
            
            # Strategy 3: Match against service ID
            if agent_name_lower in service_id or agent_name_normalized in service_id:
                endpoint = service.get("endpoint")
                if endpoint:
                    print(f"✅ Found endpoint for {agent_name} (strategy 3): {endpoint}")
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

    def discover_all_agents_with_tools(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Discover all registered agents and introspect their tools via MCP protocol.

        For each registered agent:
        1. Get agent info from registry (name, endpoint, description)
        2. Call tools/list on agent's MCP endpoint
        3. Return complete agent info with full tool schemas and agent_id

        Args:
            use_cache: Whether to use cached results (default True)

        Returns:
            List of agent info with full tool schemas:
            [
                {
                    "agent_id": "requirements-engineer",  # Normalized ID for matching
                    "name": "Requirement Engineer MCP Server on 0.0.0.0:3062",
                    "endpoint": "http://0.0.0.0:3062/mcp",
                    "description": "...",
                    "status": "online",
                    "tools": [...]
                },
                ...
            ]
        """
        agents = []
        services = self.list_services(use_cache=use_cache)

        print(f"🔍 Discovering tools for {len(services)} registered services...")

        for service in services:
            service_name = service.get("name", "")
            endpoint = service.get("endpoint")

            # Skip the registry server itself
            if "registry" in service_name.lower():
                continue

            # Generate a normalized agent_id from the service name
            agent_id = self._generate_agent_id(service_name)

            agent_info = {
                "agent_id": agent_id,  # Normalized ID for LLM matching
                "name": service_name,
                "endpoint": endpoint,
                "description": service.get("description", "No description"),
                "status": "unknown",
                "tools": [],
                "capabilities": service.get("capabilities", {})
            }

            # Call tools/list on agent's MCP endpoint
            if endpoint:
                try:
                    tools = self._introspect_agent_tools(endpoint, use_cache=use_cache)
                    agent_info["tools"] = tools
                    agent_info["status"] = "online"
                    print(f"  ✅ {agent_id}: {len(tools)} tools discovered")
                except Exception as e:
                    agent_info["status"] = "offline"
                    agent_info["error"] = str(e)
                    print(f"  ❌ {agent_id}: {str(e)}")
            else:
                agent_info["status"] = "no_endpoint"
                print(f"  ⚠️  {agent_id}: No endpoint configured")

            agents.append(agent_info)

        online_count = sum(1 for a in agents if a["status"] == "online")
        print(f"✅ Discovery complete: {online_count}/{len(agents)} agents online")

        return agents

    def _generate_agent_id(self, service_name: str) -> str:
        """
        Generate a normalized agent_id from service name.
        
        Examples:
            "Requirement Engineer MCP Server on 0.0.0.0:3062" → "requirements-engineer"
            "Implementation Engineer: on 0.0.0.0:3060" → "implementation-engineer"
            "DevOps Release Engineer Server on 0.0.0.0:3071" → "devops-engineer"
        
        Args:
            service_name: Full service name from registry
        
        Returns:
            Normalized agent_id
        """
        import re
        
        # Convert to lowercase
        name = service_name.lower()
        
        # Remove common suffixes
        name = re.sub(r" mcp server", "", name)
        name = re.sub(r" server", "", name)
        name = re.sub(r" on .*", "", name)
        
        # Extract key agent type
        agent_types = {
            "requirement": "requirements-engineer",
            "implementation": "implementation-engineer",
            "code-review": "code-reviewer",
            "code reviewer": "code-reviewer",
            "qa-test": "qa-test-engineer",
            "qa test": "qa-test-engineer",
            "security": "security-engineer",
            "devops": "devops-engineer",
            "it-lead": "it-lead",
            "it lead": "it-lead",
            "team-management": "team-management",
            "team management": "team-management",
        }
        
        for key, agent_id in agent_types.items():
            if key in name:
                return agent_id
        
        # Fallback: use the first two words as agent_id
        words = name.split()[:2]
        return "-".join(words) if words else "unknown-agent"

    def _introspect_agent_tools(self, agent_endpoint: str, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Call tools/list on an agent's MCP endpoint to get full tool schemas.
        
        Uses MCP protocol standard method: tools/list
        
        Args:
            agent_endpoint: Agent's MCP endpoint (e.g., "http://0.0.0.0:3060/mcp")
            use_cache: Whether to use cached results (default True)
        
        Returns:
            List of tool schemas from tools/list response:
            [
                {
                    "name": "vibe_code_async",
                    "description": "...",
                    "inputSchema": {...}
                },
                ...
            ]
        """
        # Check cache first
        if use_cache and agent_endpoint in self._tools_cache:
            cache_age = time.time() - self._tools_cache_timestamp.get(agent_endpoint, 0)
            if cache_age < self._tools_cache_ttl:
                print(f"  📦 Using cached tools for {agent_endpoint} (age: {cache_age:.0f}s)")
                return self._tools_cache[agent_endpoint]
        
        try:
            # Call tools/list via MCP protocol
            response = requests.post(
                agent_endpoint,
                json={
                    "jsonrpc": "2.0",
                    "id": f"tools-list-{int(time.time() * 1000)}",
                    "method": "tools/list",
                    "params": {}
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                tools = result.get("result", {}).get("tools", [])
                
                # Update cache
                self._tools_cache[agent_endpoint] = tools
                self._tools_cache_timestamp[agent_endpoint] = time.time()
                
                return tools
            else:
                raise Exception(f"Agent returned status {response.status_code}: {response.text[:200]}")
        
        except requests.RequestException as e:
            raise Exception(f"Failed to connect to agent: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON from agent: {e}")
        except Exception as e:
            raise Exception(f"Tool introspection failed: {e}")

    def get_agent_tools_with_schemas(self, agent_name: str, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Get tools with full schemas for a specific agent.
        
        Args:
            agent_name: Name of the agent (e.g., "implementation-engineer")
            use_cache: Whether to use cached results (default True)
        
        Returns:
            List of tool schemas for the agent
        """
        agents = self.discover_all_agents_with_tools(use_cache=use_cache)
        agent_name_lower = agent_name.lower()
        
        for agent in agents:
            if agent_name_lower in agent["name"].lower() or agent["name"].lower() in agent_name_lower:
                return agent.get("tools", [])
        
        return []

    def clear_tools_cache(self, agent_endpoint: Optional[str] = None):
        """
        Clear tool introspection cache.
        
        Args:
            agent_endpoint: Specific endpoint to clear, or None to clear all
        """
        if agent_endpoint:
            self._tools_cache.pop(agent_endpoint, None)
            self._tools_cache_timestamp.pop(agent_endpoint, None)
        else:
            self._tools_cache = {}
            self._tools_cache_timestamp = {}
