"""
Advanced Assignment Handlers for IT Lead MCP Server
Implements advanced assignment logic for software development teams
"""
import json
import time
from typing import Dict, Any, List, Optional
from ..utils.json_rpc import JsonRpcHandler


class AdvancedAssignmentHandlers:
    """Handles advanced assignment specific MCP server methods for software development teams"""

    def __init__(self, llm_client=None, agent_registry=None, task_storage=None):
        self.llm_client = llm_client
        self.agent_registry = agent_registry
        self.task_storage = task_storage
        
        # Advanced assignment tools
        self.tools = [
            {
                "name": "balance_agent_load",
                "description": "Balance workload across available agents",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task": {"$ref": "#/definitions/task"},
                        "agent_pool": {"type": "array", "items": {"type": "string"}, "description": "Pool of available agents"},
                        "load_balancing_strategy": {"type": "string", "enum": ["round_robin", "least_loaded", "capability_optimized"]}
                    },
                    "required": ["task", "agent_pool"]
                }
            },
            {
                "name": "match_agent_to_task",
                "description": "Match the most suitable agent to a specific task",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task": {"$ref": "#/definitions/task"},
                        "candidate_agents": {"type": "array", "items": {"type": "string"}, "description": "Candidate agent IDs"},
                        "matching_strategy": {"type": "string", "enum": ["semantic", "llm_evaluated", "hybrid"]}
                    },
                    "required": ["task", "candidate_agents"]
                }
            },
            {
                "name": "check_agent_availability",
                "description": "Check real-time availability of an agent",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string", "description": "ID of the agent to check"},
                        "task_requirements": {"type": "object", "description": "Requirements for the task"}
                    },
                    "required": ["agent_id"]
                }
            }
        ]

    def register_handlers(self, rpc_handler: JsonRpcHandler):
        """Register advanced assignment handlers with the RPC handler"""
        # Note: Do NOT register tools/call here - the main handler in extended_server_handlers.py
        # is responsible for routing tool calls to this module. Registering tools/call here
        # would override the main handler and prevent proper task storage.

    def handle_tools_call(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle tools/call request for advanced assignment tools"""
        if params is None:
            params = {}

        tool_name = params.get("name") or params.get("tool")
        tool_arguments = params.get("arguments", {})

        # Find the tool in advanced assignment tools
        tool = None
        for t in self.tools:
            if t["name"] == tool_name:
                tool = t
                break

        if not tool:
            return None  # Return None to indicate this tool isn't handled here

        # Execute the advanced assignment tool
        return self._execute_tool(tool, tool_arguments)

    def _execute_tool(self, tool: Dict[str, Any], arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific advanced assignment tool with given arguments"""
        tool_name = tool["name"]

        if tool_name == "balance_agent_load":
            return self._balance_agent_load(arguments)
        
        elif tool_name == "match_agent_to_task":
            return self._match_agent_to_task(arguments)
        
        elif tool_name == "check_agent_availability":
            return self._check_agent_availability(arguments)

        # For any other tools, return None to indicate this module doesn't handle them
        return None

    def _balance_agent_load(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Balance workload across available agents"""
        task = arguments.get("task", {})
        agent_pool = arguments.get("agent_pool", [])
        strategy = arguments.get("load_balancing_strategy", "least_loaded")
        
        # Use LLM to optimize assignment
        if self.llm_client:
            result = self._optimize_assignment_with_llm(task, agent_pool)
        else:
            # Fallback implementation - simple round-robin
            if agent_pool:
                recommended_agent = agent_pool[0]  # Simple round-robin
                result = {
                    "recommended_agent": recommended_agent,
                    "reasoning": "Selected first available agent",
                    "confidence_score": 0.8,
                    "alternative_agents": agent_pool[1:],
                    "load_impact": {
                        "current_load": 2,
                        "predicted_load": 3
                    }
                }
            else:
                result = {
                    "recommended_agent": None,
                    "reasoning": "No agents available",
                    "confidence_score": 0.0,
                    "alternative_agents": [],
                    "load_impact": {
                        "current_load": 0,
                        "predicted_load": 0
                    }
                }

        return {"result": result}

    def _optimize_assignment_with_llm(self, task: dict, agent_pool: List[str]):
        """Use LLM to optimize agent assignment"""
        # Get agent details from registry
        agents = []
        if self.agent_registry:
            for agent_id in agent_pool:
                # Check if the registry has the get_agent_info method (enhanced registry)
                if hasattr(self.agent_registry, 'get_agent_info'):
                    agent_info = self.agent_registry.get_agent_info(agent_id)
                else:
                    # Fallback for basic registry
                    agent_info = self.agent_registry.get_agent_info(agent_id) if hasattr(self.agent_registry, 'get_agent_info') else {
                        "id": agent_id,
                        "name": f"Agent {agent_id}",
                        "capabilities": [],
                        "specialties": [],
                        "experience_domains": []
                    }
                if agent_info:
                    agents.append(agent_info)
        
        prompt = f"""
        You are an intelligent task assignment optimizer. Given the following task and available agents, 
        recommend the optimal assignment considering both load balancing and capability matching:

        TASK TO ASSIGN:
        {{
          "id": "{task.get('id', 'unknown')}",
          "description": "{task.get('description', 'No description')}",
          "required_skills": {json.dumps(task.get('required_skills', []))},
          "complexity": "{task.get('complexity', 'medium')}",
          "estimated_duration": "{task.get('estimated_duration', 'medium')}"
        }}

        AVAILABLE AGENTS:
        {json.dumps(agents, indent=2)}

        For each agent, consider:
        1. Current workload (number of active tasks)
        2. Skill match with required skills
        3. Historical performance on similar tasks
        4. Capacity limits

        Return the optimal assignment with reasoning:
        {{
          "recommended_agent": "agent_id",
          "reasoning": "Why this agent is optimal",
          "confidence_score": 0.0-1.0,
          "alternative_agents": ["agent_id1", "agent_id2"],
          "load_impact": {{
            "current_load": "before assignment",
            "predicted_load": "after assignment"
          }}
        }}
        """
        
        # Call the LLM with the prompt
        try:
            import requests
            response = requests.post(
                self.llm_client.llm_provider_url,
                json={
                    "model": self.llm_client.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        return {"recommended_agent": None, "error": "Could not parse LLM response"}
            else:
                return {"recommended_agent": None, "error": f"LLM call failed: {response.status_code}"}
        except Exception as e:
            return {"recommended_agent": None, "error": f"LLM call failed: {str(e)}"}

    def _match_agent_to_task(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Match the most suitable agent to a specific task"""
        task = arguments.get("task", {})
        candidate_agents = arguments.get("candidate_agents", [])
        strategy = arguments.get("matching_strategy", "llm_evaluated")
        
        if strategy == "llm_evaluated" and self.llm_client:
            # Get agent details from registry
            agents = []
            if self.agent_registry:
                for agent_id in candidate_agents:
                    # Check if the registry has the get_agent_info method (enhanced registry)
                    if hasattr(self.agent_registry, 'get_agent_info'):
                        agent_info = self.agent_registry.get_agent_info(agent_id)
                    else:
                        # Fallback for basic registry
                        agent_info = self.agent_registry.get_agent_info(agent_id) if hasattr(self.agent_registry, 'get_agent_info') else {
                            "id": agent_id,
                            "name": f"Agent {agent_id}",
                            "capabilities": [],
                            "specialties": [],
                            "experience_domains": []
                        }
                    if agent_info:
                        agents.append(agent_info)
            
            # Evaluate each agent against the task
            best_match = None
            best_score = 0
            
            for agent in agents:
                score = self._evaluate_agent_match_with_llm(task, agent)
                if score.get("overall_score", 0) > best_score:
                    best_score = score.get("overall_score", 0)
                    best_match = agent
            
            if best_match:
                result = {
                    "recommended_agent": best_match.get("id"),
                    "evaluation": score,
                    "confidence": score.get("confidence", 0.0)
                }
            else:
                result = {
                    "recommended_agent": None,
                    "evaluation": {},
                    "confidence": 0.0
                }
        else:
            # Fallback implementation
            if candidate_agents:
                result = {
                    "recommended_agent": candidate_agents[0],
                    "evaluation": {
                        "skill_match": 0.8,
                        "domain_match": 0.7,
                        "complexity_match": 0.9,
                        "overall_score": 0.8,
                        "challenges": [],
                        "confidence": 0.8,
                        "recommendation": "good_match"
                    },
                    "confidence": 0.8
                }
            else:
                result = {
                    "recommended_agent": None,
                    "evaluation": {},
                    "confidence": 0.0
                }

        return {"result": result}

    def _evaluate_agent_match_with_llm(self, task: dict, agent: dict):
        """Use LLM to evaluate agent-task match"""
        # Check if this is a requirements-related task
        task_domain = task.get('domain', 'general')
        task_description = task.get('description', '').lower()
        is_requirements_task = ('requirement' in task_description or 
                               'analyze' in task_description or 
                               'specification' in task_description or
                               'business' in task_description or
                               'translate' in task_description)
        
        prompt = f"""
        Evaluate the match between the following task and agent:

        TASK:
        {{
          "id": "{task.get('id', 'unknown')}",
          "title": "{task.get('title', 'No title')}",
          "description": "{task.get('description', 'No description')}",
          "required_skills": {json.dumps(task.get('required_skills', []))},
          "complexity_level": "{task.get('complexity', 'medium')}",
          "domain": "{task.get('domain', 'general')}",
          "is_requirements_related": {json.dumps(is_requirements_task)}
        }}

        AGENT:
        {{
          "id": "{agent.get('id', 'unknown')}",
          "name": "{agent.get('name', 'Unknown')}",
          "capabilities": {json.dumps(agent.get('capabilities', {}))},
          "specialties": {json.dumps(agent.get('specialties', []))},
          "experience_domains": {json.dumps(agent.get('experience_domains', []))}
        }}

        Please evaluate:
        1. Skill match score (0.0-1.0)
        2. Domain expertise match (0.0-1.0)
        3. Complexity appropriateness (0.0-1.0)
        4. Overall recommendation score (0.0-1.0)
        5. Potential challenges
        6. Recommendation confidence
        7. If this is a requirements-related task, consider if the agent has requirements engineering specialty

        Return as JSON:
        {{
          "skill_match": 0.0-1.0,
          "domain_match": 0.0-1.0,
          "complexity_match": 0.0-1.0,
          "overall_score": 0.0-1.0,
          "challenges": ["challenge1", "challenge2"],
          "confidence": 0.0-1.0,
          "recommendation": "strong_match|good_match|moderate_match|not_recommended",
          "is_requirements_specialist": {json.dumps("requirements_engineering" in agent.get('specialties', []))}
        }}
        """
        
        # Call the LLM with the prompt
        try:
            import requests
            response = requests.post(
                self.llm_client.llm_provider_url,
                json={
                    "model": self.llm_client.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        return {"overall_score": 0.0, "error": "Could not parse LLM response"}
            else:
                return {"overall_score": 0.0, "error": f"LLM call failed: {response.status_code}"}
        except Exception as e:
            return {"overall_score": 0.0, "error": f"LLM call failed: {str(e)}"}

    def _check_agent_availability(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Check real-time availability of an agent"""
        agent_id = arguments.get("agent_id", "")
        task_requirements = arguments.get("task_requirements", {})
        
        # Check agent availability through registry or direct communication
        if self.agent_registry:
            # Check if the registry has the check_agent_availability method (enhanced registry)
            if hasattr(self.agent_registry, 'check_agent_availability'):
                availability = self.agent_registry.check_agent_availability(agent_id)
            else:
                # Fallback for basic registry
                availability = self.agent_registry.check_agent_availability(agent_id) if hasattr(self.agent_registry, 'check_agent_availability') else {
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
        else:
            # Fallback implementation
            availability = {
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

        result = {
            "agent_id": agent_id,
            "availability_status": availability.get("status", "unknown"),
            "current_load": availability.get("current_load", 0),
            "available_capacity": availability.get("available_capacity", 0),
            "can_accept_task": availability.get("status") == "available" and availability.get("available_capacity", 0) > 0,
            "estimated_start_time": "immediate" if availability.get("status") == "available" else "delayed"
        }

        return {"result": result}