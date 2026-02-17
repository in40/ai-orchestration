"""
Team Coordination Module for IT Lead Server
Handles discovery and coordination with other agents in the MCP ecosystem
"""
import time
import json
from typing import Dict, Any, List, Optional
import requests
from ..utils.json_rpc import JsonRpcHandler


class TeamCoordinationManager:
    """Manages team coordination and agent discovery for the IT Lead server"""
    
    def __init__(self, service_registry, llm_client, task_storage):
        self.service_registry = service_registry
        self.llm_client = llm_client
        self.task_storage = task_storage
        
        # Cache of discovered agents
        self.discovered_agents = {}
        self.last_discovery_time = 0
        self.discovery_cache_ttl = 30  # Cache TTL in seconds
        
        # Define team roles and their required capabilities
        self.team_role_mappings = {
            "IT Lead": ["assign_task", "review_code", "generate_project_plan", "analyze_architecture"],
            "Requirements Engineer": ["analyze_requirements", "validate_requirements", "generate_requirement_document", "trace_requirements"],
            "Implementation Engineer": ["implement_feature", "generate_code", "refactor_code", "write_tests", "debug_issue"],
            "Code Reviewer": ["review_pull_request", "check_code_quality", "identify_security_issues"],
            "Security Engineer": ["perform_security_audit", "scan_vulnerabilities", "review_security_practices"],
            "DevOps Engineer": ["deploy_application", "configure_infrastructure", "monitor_system_performance"]
        }
    
    def discover_agents(self) -> Dict[str, Any]:
        """Discover available agents by making live calls to the registry"""
        current_time = time.time()

        # Check if cache is still valid
        if (current_time - self.last_discovery_time) < self.discovery_cache_ttl and self.discovered_agents:
            return self.discovered_agents

        # Default agents setup
        discovered_agents = {}
        
        # Add IT Lead (this server) as online
        discovered_agents["IT Lead"] = {
            "id": "it-lead-server-127.0.0.1-3061",
            "name": "IT Lead Agent Server",
            "endpoint": "http://127.0.0.1:3061/mcp",
            "capabilities": ["assign_task", "review_code", "generate_project_plan", "analyze_architecture"],
            "status": "online",
            "last_seen": current_time,
            "description": "IT Lead Agent Server on 127.0.0.1:3061"
        }

        # Add default offline agents
        for role in self.team_role_mappings:
            if role != "IT Lead":  # Skip IT Lead as we added it above
                discovered_agents[role] = {
                    "id": "",
                    "name": role,
                    "endpoint": "",
                    "capabilities": self.team_role_mappings[role],
                    "status": "offline",
                    "last_seen": None,
                    "description": f"{role} agent not currently available"
                }

        # Query the central registry server to discover agents
        # The central registry is the authoritative source for agent discovery
        try:
            import requests
            
            print("DEBUG: Attempting to connect to central registry at http://127.0.0.1:3031/mcp")
            
            # The central registry server is at port 3031
            registry_endpoint = "http://127.0.0.1:3031/mcp"
            
            # Make a call to the registry to list services
            response = requests.post(
                registry_endpoint,
                json={
                    "jsonrpc": "2.0",
                    "id": "list_services",
                    "method": "registry/list",  # Standard method to list registered services
                    "params": {}
                },
                timeout=5
            )
            
            print(f"DEBUG: Registry response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"DEBUG: Registry response: {result}")
                
                if "result" in result and "services" in result["result"]:
                    services = result["result"]["services"]
                    print(f"DEBUG: Found {len(services)} services in registry")
                    
                    # Map discovered services to team roles
                    for service in services:
                        print(f"DEBUG: Processing service: {service.get('name', 'unknown')}")
                        
                        # Extract capabilities from the service
                        capabilities = service.get("capabilities", {})
                        tools = capabilities.get("tools", [])
                        
                        role = self._map_agent_to_team_role(service.get("name", ""), tools)
                        
                        if role and role in discovered_agents:
                            print(f"DEBUG: Mapping service {service.get('name')} to role {role}")
                            # Update the agent with actual service info
                            discovered_agents[role] = {
                                "id": service.get("id"),
                                "name": service.get("name"),
                                "endpoint": service.get("endpoint"),
                                "capabilities": tools,
                                "status": "online",  # Confirmed online since it's in the registry
                                "last_seen": service.get("last_seen"),
                                "description": service.get("description", f"{role} agent")
                            }
                        else:
                            print(f"DEBUG: Could not map service {service.get('name')} to any role")
                else:
                    print("DEBUG: No services found in registry response")
            else:
                print(f"DEBUG: Registry responded with status {response.status_code}")
        except ImportError:
            print("requests library not available for registry discovery")
            # Continue with default agents
        except Exception as e:
            print(f"Error discovering agents from central registry: {e}")
            import traceback
            traceback.print_exc()
            # Continue with default agents if registry lookup fails

        self.discovered_agents = discovered_agents
        self.last_discovery_time = current_time

        return self.discovered_agents
    
    def _map_agent_to_team_role(self, service_name: str, capabilities: List[str]) -> Optional[str]:
        """Map a service to a team role based on its capabilities"""
        # First, check for exact matches based on known agent types
        service_lower = service_name.lower()

        # Check for specific agent types based on name
        if "requirement" in service_lower or "requirements" in service_lower:
            return "Requirements Engineer"
        elif "implementation" in service_lower or "impl" in service_lower:
            return "Implementation Engineer"
        elif "team management" in service_lower or "team_management" in service_lower or "team-management" in service_lower:
            # Special case: Team Management server often handles implementation tasks
            return "Implementation Engineer"
        elif "code" in service_lower and "review" in service_lower:
            return "Code Reviewer"
        elif "security" in service_lower:
            return "Security Engineer"
        elif "devops" in service_lower:
            return "DevOps Engineer"

        # Normalize capabilities by extracting just the action part (after last slash if present)
        normalized_capabilities = set()
        for cap in capabilities:
            # Extract the actual capability name (e.g., "team_management/implement_feature" -> "implement_feature")
            if '/' in cap:
                normalized_capabilities.add(cap.split('/')[-1])
            else:
                normalized_capabilities.add(cap)
        
        # Check for agents based on their capabilities (using normalized capabilities)
        # Requirements Engineer typically has these capabilities
        requirements_caps = {"analyze_requirements", "resolve_ambiguity", "translate_business_to_technical",
                           "generate_traceability_matrix", "identify_edge_cases"}
        req_matches = sum(1 for cap in requirements_caps if cap in normalized_capabilities)
        if req_matches >= 2:  # At least 2 requirements-related capabilities
            return "Requirements Engineer"

        # Implementation Engineer typically has these capabilities
        implementation_caps = {"implement_feature", "generate_code", "refactor_code", "write_tests",
                             "debug_issue", "apply_coding_standards", "generate_unit_tests"}
        impl_matches = sum(1 for cap in implementation_caps if cap in normalized_capabilities)
        if impl_matches >= 2:  # At least 2 implementation-related capabilities
            return "Implementation Engineer"

        # Code Reviewer capabilities
        review_caps = {"review_pull_request", "check_code_quality", "identify_security_issues"}
        review_matches = sum(1 for cap in review_caps if cap in normalized_capabilities)
        if review_matches >= 1:
            return "Code Reviewer"

        # Security Engineer capabilities
        security_caps = {"perform_security_audit", "scan_vulnerabilities", "review_security_practices"}
        sec_matches = sum(1 for cap in security_caps if cap in normalized_capabilities)
        if sec_matches >= 1:
            return "Security Engineer"

        # DevOps Engineer capabilities
        devops_caps = {"deploy_application", "configure_infrastructure", "monitor_system_performance"}
        devops_matches = sum(1 for cap in devops_caps if cap in normalized_capabilities)
        if devops_matches >= 1:
            return "DevOps Engineer"

        # Check each team role to see if the service's capabilities match
        for role, required_capabilities in self.team_role_mappings.items():
            # Count how many required capabilities the service has (using normalized capabilities)
            matched_capabilities = [cap for cap in required_capabilities if cap in normalized_capabilities]

            # If the service has at least half of the required capabilities, consider it a match
            if len(matched_capabilities) >= len(required_capabilities) * 0.5:
                return role

        # If no strong match, check if the service name contains keywords related to roles
        for role in self.team_role_mappings:
            if role.lower() in service_lower:
                return role

        # If no match found, return None
        return None
    
    def _get_default_agents(self) -> Dict[str, Any]:
        """Get default agent mappings when discovery fails"""
        default_agents = {}
        for role in self.team_role_mappings:
            default_agents[role] = {
                "id": "",
                "name": role,
                "endpoint": "",
                "capabilities": self.team_role_mappings[role],
                "status": "offline",
                "last_seen": None,
                "description": f"{role} agent not currently available"
            }
        return default_agents
    
    def get_agent_by_role(self, role: str) -> Optional[Dict[str, Any]]:
        """Get agent information by team role"""
        agents = self.discover_agents()
        return agents.get(role)
    
    def get_available_agents(self) -> List[Dict[str, Any]]:
        """Get list of all available (online) agents"""
        agents = self.discover_agents()
        return [agent for agent in agents.values() if agent["status"] == "online"]
    
    def get_team_status(self) -> Dict[str, Any]:
        """Get overall team status"""
        agents = self.discover_agents()
        online_count = sum(1 for agent in agents.values() if agent["status"] == "online")
        total_count = len(agents)
        
        return {
            "team_size": total_count,
            "online_agents": online_count,
            "offline_agents": total_count - online_count,
            "agent_statuses": {role: agent["status"] for role, agent in agents.items()},
            "last_discovery": self.last_discovery_time
        }
    
    def delegate_task_to_agent(self, role: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate a task to a specific agent by role"""
        agent = self.get_agent_by_role(role)
        
        if not agent or agent["status"] != "online":
            return {
                "success": False,
                "error": f"No available agent for role: {role}",
                "result": None
            }
        
        try:
            # Construct the endpoint URL for the agent
            agent_endpoint = agent["endpoint"]
            
            # For now, we'll simulate calling the agent
            # In a real implementation, this would make an HTTP request to the agent's endpoint
            print(f"Delegating task to {role} at {agent_endpoint}")
            print(f"Tool: {tool_name}, Arguments: {arguments}")
            
            # Simulate the delegation result
            result = {
                "delegated_to": role,
                "tool_called": tool_name,
                "arguments_used": arguments,
                "status": "simulated_success",
                "message": f"Task delegated to {role} successfully (simulated)"
            }
            
            return {
                "success": True,
                "error": None,
                "result": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "result": None
            }
    
    def coordinate_multi_agent_task(self, task_description: str, required_roles: List[str]) -> Dict[str, Any]:
        """Coordinate a task that requires multiple agents"""
        agents = self.discover_agents()
        
        # Check if all required roles are available
        available_roles = [role for role, agent in agents.items() if agent["status"] == "online"]
        missing_roles = [role for role in required_roles if role not in available_roles]
        
        if missing_roles:
            return {
                "success": False,
                "error": f"Missing required agents for roles: {missing_roles}",
                "completed_by": available_roles,
                "result": None
            }
        
        try:
            # In a real implementation, this would coordinate the multi-agent task
            # For now, we'll simulate the coordination
            result = {
                "task_description": task_description,
                "required_roles": required_roles,
                "available_roles": available_roles,
                "status": "simulated_coordinated",
                "message": f"Multi-agent task coordinated among: {available_roles} (simulated)"
            }
            
            return {
                "success": True,
                "error": None,
                "result": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "result": None
            }