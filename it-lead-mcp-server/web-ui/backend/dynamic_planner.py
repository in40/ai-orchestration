"""
Dynamic Planning System for IT Lead MCP Server

This module implements a flexible task routing system that:
1. Fetches all available agents from MCP registry
2. Gets comprehensive capabilities for each agent
3. Uses LLM to generate dynamic task execution plans
4. Selects optimal agents based on task requirements

Key Features:
- Dynamic agent discovery from registry
- LLM-based intelligent task routing
- Capability-based agent matching
- Multi-agent task delegation
- Planning rationale and explainability
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """Task complexity levels for planning"""
    SIMPLE = "simple"      # Single agent, straightforward
    MODERATE = "moderate"  # 2-3 agents, some coordination
    COMPLEX = "complex"    # Multiple agents, complex workflow
    CROSS_CUTTING = "cross_cutting"  # Requires multiple domains


@dataclass
class AgentCapability:
    """Represents an agent's capability"""
    name: str
    type: str  # 'tool', 'resource', or 'prompt'
    description: str
    input_schema: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "input_schema": self.input_schema
        }


@dataclass
class AgentInfo:
    """Comprehensive agent information"""
    id: str
    name: str
    endpoint: str
    description: str = ""
    status: str = "unknown"
    capabilities: List[AgentCapability] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)
    prompts: List[str] = field(default_factory=list)
    last_seen: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "endpoint": self.endpoint,
            "description": self.description,
            "status": self.status,
            "capabilities": [c.to_dict() if isinstance(c, AgentCapability) else c for c in self.capabilities],
            "tools": self.tools,
            "resources": self.resources,
            "prompts": self.prompts,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None
        }


class RegistryClient:
    """Client for fetching agent information from MCP registry"""
    
    def __init__(self, registry_host: str = "127.0.0.1", registry_port: int = 3031):
        self.registry_host = registry_host
        self.registry_port = registry_port
        self._cache: Dict[str, Any] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = 300  # 5 minutes
    
    async def fetch_all_agents(self) -> List[AgentInfo]:
        """
        Fetch all registered agents from MCP registry
        Returns comprehensive agent information with capabilities
        """
        # Check cache first
        if self._cache and self._cache_timestamp:
            age = (datetime.now() - self._cache_timestamp).total_seconds()
            if age < self._cache_ttl:
                logger.debug(f"Using cached agent list (age: {age:.1f}s)")
                return self._cache.get("agents", [])
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"http://{self.registry_host}:{self.registry_port}/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "id": "fetch_agents",
                        "method": "registry/list",
                        "params": {}
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Registry API returned status {response.status_code}")
                    return self._cache.get("agents", [])
                
                data = response.json()
                
                if "result" not in data or "services" not in data.get("result", {}):
                    logger.error("Registry response missing expected structure")
                    return self._cache.get("agents", [])
                
                services = data["result"]["services"]
                agents = []
                
                for service in services:
                    agent = self._service_to_agent(service)
                    agents.append(agent)
                
                # Cache the result
                self._cache = {"agents": agents}
                self._cache_timestamp = datetime.now()
                
                logger.info(f"Discovered {len(agents)} agents from registry")
                return agents
                
        except httpx.RequestError as e:
            logger.error(f"Failed to fetch agents from registry: {e}")
            return self._cache.get("agents", [])
        except Exception as e:
            logger.error(f"Unexpected error fetching agents: {e}")
            return self._cache.get("agents", [])
    
    def _service_to_agent(self, service: Dict[str, Any]) -> AgentInfo:
        """Convert registry service entry to AgentInfo"""
        capabilities = []
        
        # Extract tools
        tools = service.get("capabilities", {}).get("tools", [])
        for tool_name in tools:
            capabilities.append(AgentCapability(
                name=tool_name,
                type="tool",
                description=""
            ))
        
        # Extract resources
        resources = service.get("capabilities", {}).get("resources", [])
        for resource_uri in resources:
            capabilities.append(AgentCapability(
                name=resource_uri,
                type="resource",
                description=""
            ))
        
        # Extract prompts
        prompts = service.get("capabilities", {}).get("prompts", [])
        for prompt_name in prompts:
            capabilities.append(AgentCapability(
                name=prompt_name,
                type="prompt",
                description=""
            ))
        
        return AgentInfo(
            id=service.get("id", ""),
            name=service.get("name", ""),
            endpoint=service.get("endpoint", ""),
            description=service.get("description", ""),
            status="online",  # If registered, it's online
            capabilities=capabilities,
            tools=tools,
            resources=resources,
            prompts=prompts,
            last_seen=datetime.fromtimestamp(service.get("last_seen", 0)) if service.get("last_seen") else None
        )


class TaskPlanGenerator:
    """
    Generates dynamic task execution plans using LLM
    """
    
    def __init__(self, llm_provider_url: str, llm_model: str):
        self.llm_provider_url = llm_provider_url
        self.llm_model = llm_model
    
    async def generate_task_plan(
        self,
        task: Dict[str, Any],
        agents: List[AgentInfo]
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive execution plan for the given task
        
        Args:
            task: Task information (title, description, context, etc.)
            agents: List of available agents with their capabilities
        
        Returns:
            Dictionary containing:
            - primary_agent: Main agent for task execution
            - secondary_agents: Additional agents needed
            - execution_plan: Step-by-step plan
            - rationale: Explanation for routing decision
            - confidence: Confidence score (0-1)
            - complexity: Task complexity level
            - estimated_duration: Estimated time
        """
        
        # Format agent capabilities for LLM
        agents_context = self._format_agents_for_prompt(agents)
        
        # Extract task details
        task_title = task.get("title", task.get("name", "Unknown"))
        task_description = task.get("description", "")
        task_context = task.get("context", {})
        
        prompt = f"""You are an intelligent task router for an AI agent team.

Available Agents and Their Capabilities:
{agents_context}

Task to Route:
Title: {task_title}
Description: {task_description}
Context: {json.dumps(task_context, indent=2)}

Your Task:
1. Analyze the task requirements
2. Identify which agent(s) can execute this task based on their capabilities
3. Create a detailed execution plan with steps
4. Determine if multiple agents are needed and the sequence
5. Assess complexity and estimate duration

Return a JSON object with:
- "primary_agent": Name of main agent to execute this task
- "secondary_agents": Array of additional agent names needed
- "execution_plan": Array of steps to complete the task
- "rationale": Detailed explanation of why this agent was selected
- "confidence": Float between 0 and 1 indicating routing confidence
- "complexity": One of: "simple", "moderate", "complex", "cross_cutting"
- "estimated_duration": Estimated execution time (e.g., "5-10 minutes")
- "required_capabilities": List of capabilities needed from agents

Rules:
- Select the agent with the most relevant capabilities
- If task requires multiple domains, use multiple agents
- For coordination tasks, use "IT Lead" as primary
- If no agent has suitable capabilities, return "IT Lead" for review
- Always provide a rationale explaining your decision

JSON Output:"""
        
        try:
            response = await self._call_llm(prompt)
            plan = json.loads(response)
            
            # Validate plan structure
            if not isinstance(plan, dict):
                logger.warning("LLM response not valid JSON object")
                return self._create_fallback_plan(task, agents)
            
            # Add timestamp
            plan["generated_at"] = datetime.now().isoformat()
            plan["task_id"] = task.get("id", task.get("task_id", "unknown"))
            
            logger.info(f"Generated plan: primary={plan.get('primary_agent')}, complexity={plan.get('complexity')}")
            return plan
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return self._create_fallback_plan(task, agents)
        except Exception as e:
            logger.error(f"Error generating task plan: {e}")
            return self._create_fallback_plan(task, agents)
    
    def _format_agents_for_prompt(self, agents: List[AgentInfo]) -> str:
        """Format agent information for LLM prompt"""
        output = []
        
        for agent in agents:
            output.append(f"## {agent.name}")
            output.append(f"ID: {agent.id}")
            output.append(f"Endpoint: {agent.endpoint}")
            if agent.description:
                output.append(f"Description: {agent.description}")
            
            output.append("Tools:")
            for tool in agent.tools[:10]:  # Limit to 10 tools
                output.append(f"  - {tool}")
            if len(agent.tools) > 10:
                output.append(f"  ... and {len(agent.tools) - 10} more tools")
            
            output.append("")
        
        return "\n".join(output)
    
    def _create_fallback_plan(self, task: Dict[str, Any], agents: List[AgentInfo]) -> Dict[str, Any]:
        """Create a fallback plan when LLM fails"""
        # Find IT Lead if available
        it_lead = next((a for a in agents if "it" in a.name.lower() and "lead" in a.name.lower()), None)
        primary = it_lead.name if it_lead else "IT Lead"
        
        return {
            "primary_agent": primary,
            "secondary_agents": [],
            "execution_plan": [
                "IT Lead will analyze the task manually",
                "IT Lead will determine the appropriate agent",
                "Task will be delegated with full context"
            ],
            "rationale": "LLM routing failed, using fallback to IT Lead",
            "confidence": 0.5,
            "complexity": "moderate",
            "estimated_duration": "10-15 minutes",
            "required_capabilities": ["assign_task"],
            "generated_at": datetime.now().isoformat(),
            "task_id": task.get("id", "unknown"),
            "fallback": True
        }
    
    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt"""
        payload = {
            "model": self.llm_model,
            "messages": [
                {"role": "system", "content": "You are an intelligent task router. Always respond with valid JSON." },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,  # Low temperature for more deterministic output
            "max_tokens": 2000
        }
        
        response = await asyncio.to_thread(
            lambda: __import__('requests').post(self.llm_provider_url, json=payload, timeout=60)
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get("choices", [{}])[0].get("message", {}).get("content", "")


class DynamicPlanner:
    """
    Main dynamic planning orchestrator
    Combines registry fetching and LLM planning
    """
    
    def __init__(
        self,
        registry_host: str = "127.0.0.1",
        registry_port: int = 3031,
        llm_provider_url: str = "http://192.168.51.237:1234/v1/chat/completions",
        llm_model: str = "qwen3.5-35b-a3b@q5_k_xl"
    ):
        self.registry_client = RegistryClient(registry_host, registry_port)
        self.plan_generator = TaskPlanGenerator(llm_provider_url, llm_model)
    
    async def route_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route a task to the appropriate agent using dynamic planning
        
        Args:
            task: Task information to route
        
        Returns:
            Routing decision with agent selection and execution plan
        """
        # Step 1: Fetch all available agents
        agents = await self.registry_client.fetch_all_agents()
        
        if not agents:
            logger.warning("No agents found in registry")
            return {
                "success": False,
                "error": "No agents available in registry",
                "primary_agent": "IT Lead",
                "rationale": "Fallback: No agents discovered"
            }
        
        logger.info(f"Discovered {len(agents)} agents: {[a.name for a in agents]}")
        
        # Step 2: Generate execution plan using LLM
        plan = await self.plan_generator.generate_task_plan(task, agents)
        
        # Step 3: Build routing decision
        routing_decision = {
            "success": True,
            "task": task,
            "plan": plan,
            "agents": [a.to_dict() for a in agents]
        }
        
        return routing_decision
    
    async def get_available_agents(self) -> List[Dict[str, Any]]:
        """Get list of all available agents"""
        agents = await self.registry_client.fetch_all_agents()
        return [a.to_dict() for a in agents]


# Global planner instance
_planner: Optional[DynamicPlanner] = None

def get_planner() -> DynamicPlanner:
    """Get or create global planner instance"""
    global _planner
    
    if _planner is None:
        _planner = DynamicPlanner()
    
    return _planner
