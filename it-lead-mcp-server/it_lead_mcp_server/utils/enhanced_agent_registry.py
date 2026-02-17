"""
Enhanced Agent Registry Interface for IT Lead MCP Server
Provides registry functionality for agent discovery and management
"""


class EnhancedAgentRegistry:
    """Enhanced agent registry interface for agent discovery and management"""
    
    def __init__(self, service_registry=None):
        self.service_registry = service_registry
    
    def get_agent_info(self, agent_id: str) -> dict:
        """Get detailed information about an agent"""
        if self.service_registry:
            services = self.service_registry.list_services()
            for service in services:
                if service.get("id") == agent_id:
                    return {
                        "id": service.get("id"),
                        "name": service.get("name"),
                        "description": service.get("description"),
                        "endpoint": service.get("endpoint"),
                        "capabilities": service.get("capabilities", {}),
                        "status": "available",  # Would be determined by health check in real implementation
                        "current_load": 0,  # Would be tracked in real implementation
                        "max_concurrent": 5,  # Default assumption
                        "capabilities": service.get("capabilities", {}).get("tools", []),
                        "specialties": self._extract_specialties(service.get("capabilities", {})),
                        "experience_domains": self._extract_experience_domains(service.get("capabilities", {}))
                    }
        # Return default values if registry not available
        return {
            "id": agent_id,
            "name": f"Agent {agent_id}",
            "description": "Unknown agent",
            "endpoint": "unknown",
            "capabilities": [],
            "status": "unknown",
            "current_load": 0,
            "max_concurrent": 5,
            "specialties": [],
            "experience_domains": []
        }
    
    def check_agent_availability(self, agent_id: str) -> dict:
        """Check real-time availability of an agent"""
        if self.service_registry:
            # In a real implementation, this would make a health check call to the agent
            # For now, return simulated data
            agent_info = self.get_agent_info(agent_id)
            return {
                "status": "available",
                "current_load": agent_info.get("current_load", 0),
                "max_concurrent": agent_info.get("max_concurrent", 5),
                "available_capacity": agent_info.get("max_concurrent", 5) - agent_info.get("current_load", 0),
                "response_time_ms": 45,
                "system_resources": {
                    "cpu_usage": 45,
                    "memory_usage": 60,
                    "disk_space": 85
                }
            }
        else:
            # Return default availability info
            return {
                "status": "available",
                "current_load": 2,
                "max_concurrent": 5,
                "available_capacity": 3,
                "response_time_ms": 45,
                "system_resources": {
                    "cpu_usage": 45,
                    "memory_usage": 60,
                    "disk_space": 85
                }
            }
    
    def _extract_specialties(self, capabilities: dict) -> list:
        """Extract specialties from agent capabilities"""
        # In a real implementation, this would parse the agent's capabilities
        # to determine specialties
        specialties = []
        if "tools" in capabilities:
            tools = capabilities["tools"]
            if any("architect" in tool.lower() for tool in tools):
                specialties.append("architecture")
            if any("code" in tool.lower() or "develop" in tool.lower() for tool in tools):
                specialties.append("development")
            if any("test" in tool.lower() or "qa" in tool.lower() for tool in tools):
                specialties.append("testing")
            if any("security" in tool.lower() for tool in tools):
                specialties.append("security")
            if any("requirement" in tool.lower() or "analyze_requirements" in tool.lower() or "translate_business_to_technical" in tool.lower() for tool in tools):
                specialties.append("requirements_engineering")
        return specialties
    
    def _extract_experience_domains(self, capabilities: dict) -> list:
        """Extract experience domains from agent capabilities"""
        # In a real implementation, this would parse the agent's capabilities
        # to determine experience domains
        domains = []
        if "tools" in capabilities:
            tools = capabilities["tools"]
            if any("web" in tool.lower() or "frontend" in tool.lower() for tool in tools):
                domains.append("web_development")
            if any("api" in tool.lower() or "backend" in tool.lower() for tool in tools):
                domains.append("backend_development")
            if any("data" in tool.lower() or "db" in tool.lower() for tool in tools):
                domains.append("data_engineering")
        return domains