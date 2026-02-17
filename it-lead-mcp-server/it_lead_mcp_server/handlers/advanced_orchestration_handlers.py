"""
Advanced Orchestration Handlers for IT Lead MCP Server
Implements advanced orchestration capabilities for software development teams
"""
import json
import time
import asyncio
from typing import Dict, Any, List, Optional
from ..utils.json_rpc import JsonRpcHandler


class AdvancedOrchestrationHandlers:
    """Handles advanced orchestration specific MCP server methods for software development teams"""

    def __init__(self, llm_client=None, agent_registry=None, task_storage=None):
        self.llm_client = llm_client
        self.agent_registry = agent_registry
        self.task_storage = task_storage
        
        # Advanced orchestration tools
        self.tools = [
            {
                "name": "execute_workflow",
                "description": "Execute a defined workflow pattern",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_type": {"type": "string", "enum": ["sequential", "parallel", "iterative", "event_driven", "requirements_gathering", "requirements_validation"]},
                        "tasks": {"type": "array", "items": {"$ref": "#/definitions/task"}},
                        "context": {"type": "object", "description": "Workflow execution context"}
                    },
                    "required": ["workflow_type", "tasks"]
                }
            },
            {
                "name": "process_event",
                "description": "Process an event and trigger appropriate responses",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "event_type": {"type": "string", "description": "Type of event"},
                        "event_data": {"type": "object", "description": "Event-specific data"},
                        "handlers": {"type": "array", "items": {"type": "string"}, "description": "Event handlers to trigger"}
                    },
                    "required": ["event_type", "event_data"]
                }
            },
            {
                "name": "resolve_conflict",
                "description": "Resolve conflicts between agent outputs",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "outputs": {"type": "array", "items": {"type": "object"}, "description": "Conflicting outputs"},
                        "context": {"type": "object", "description": "Context of the conflict"},
                        "resolution_strategy": {"type": "string", "enum": ["majority", "expert", "compromise", "llm_mediated"]}
                    },
                    "required": ["outputs", "context"]
                }
            }
        ]

    def register_handlers(self, rpc_handler: JsonRpcHandler):
        """Register advanced orchestration handlers with the RPC handler"""
        # Note: Do NOT register tools/call here - the main handler in extended_server_handlers.py
        # is responsible for routing tool calls to this module. Registering tools/call here
        # would override the main handler and prevent proper task storage.

    def handle_tools_call(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle tools/call request for advanced orchestration tools"""
        if params is None:
            params = {}

        tool_name = params.get("name") or params.get("tool")
        tool_arguments = params.get("arguments", {})

        # Find the tool in advanced orchestration tools
        tool = None
        for t in self.tools:
            if t["name"] == tool_name:
                tool = t
                break

        if not tool:
            return None  # Return None to indicate this tool isn't handled here

        # Execute the advanced orchestration tool
        return self._execute_tool(tool, tool_arguments)

    def _execute_tool(self, tool: Dict[str, Any], arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific advanced orchestration tool with given arguments"""
        tool_name = tool["name"]

        if tool_name == "execute_workflow":
            return self._execute_workflow(arguments)
        
        elif tool_name == "process_event":
            return self._process_event(arguments)
        
        elif tool_name == "resolve_conflict":
            return self._resolve_conflict(arguments)

        # For any other tools, return None to indicate this module doesn't handle them
        return None

    def _execute_workflow(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a defined workflow pattern"""
        workflow_type = arguments.get("workflow_type", "sequential")
        tasks = arguments.get("tasks", [])
        context = arguments.get("context", {})

        if workflow_type == "sequential":
            result = self._execute_sequential_workflow(tasks, context)
        elif workflow_type == "parallel":
            result = self._execute_parallel_workflow(tasks, context)
        elif workflow_type == "iterative":
            result = self._execute_iterative_workflow(tasks, context)
        elif workflow_type == "event_driven":
            result = self._execute_event_driven_workflow(tasks, context)
        elif workflow_type == "requirements_gathering":
            result = self._execute_requirements_gathering_workflow(tasks, context)
        elif workflow_type == "requirements_validation":
            result = self._execute_requirements_validation_workflow(tasks, context)
        else:
            result = {
                "status": "error",
                "message": f"Unknown workflow type: {workflow_type}",
                "executed_tasks": [],
                "failed_tasks": tasks
            }

        return {"result": result}

    def _execute_sequential_workflow(self, tasks: List[dict], context: dict) -> dict:
        """Execute tasks in sequential order"""
        executed_tasks = []
        failed_tasks = []
        
        for task in tasks:
            try:
                # In a real implementation, this would call the appropriate agent
                # For now, we'll simulate execution
                task_result = {
                    "task_id": task.get("id", f"task-{int(time.time())}"),
                    "status": "completed",
                    "execution_time": 1.5,  # seconds
                    "output": f"Simulated output for {task.get('title', 'unnamed task')}"
                }
                executed_tasks.append(task_result)
            except Exception as e:
                failed_tasks.append({
                    "task_id": task.get("id", f"task-{int(time.time())}"),
                    "error": str(e)
                })
        
        return {
            "workflow_type": "sequential",
            "executed_tasks": executed_tasks,
            "failed_tasks": failed_tasks,
            "total_execution_time": sum([t.get("execution_time", 0) for t in executed_tasks]),
            "status": "completed" if not failed_tasks else "partial"
        }

    def _execute_parallel_workflow(self, tasks: List[dict], context: dict) -> dict:
        """Execute tasks in parallel when possible"""
        # Identify independent tasks that can run in parallel
        independent_tasks = self._identify_independent_tasks(tasks)
        
        executed_tasks = []
        failed_tasks = []
        
        # For simulation, we'll just process all tasks
        for task in tasks:
            try:
                task_result = {
                    "task_id": task.get("id", f"task-{int(time.time())}"),
                    "status": "completed",
                    "execution_time": 1.0,  # seconds
                    "output": f"Simulated output for {task.get('title', 'unnamed task')}"
                }
                executed_tasks.append(task_result)
            except Exception as e:
                failed_tasks.append({
                    "task_id": task.get("id", f"task-{int(time.time())}"),
                    "error": str(e)
                })
        
        return {
            "workflow_type": "parallel",
            "executed_tasks": executed_tasks,
            "failed_tasks": failed_tasks,
            "total_execution_time": max([t.get("execution_time", 0) for t in executed_tasks]),  # Max time since running in parallel
            "status": "completed" if not failed_tasks else "partial"
        }

    def _identify_independent_tasks(self, tasks: List[dict]) -> List[dict]:
        """Identify tasks that can run independently"""
        # Simple implementation - in reality this would check dependencies
        return tasks

    def _execute_iterative_workflow(self, tasks: List[dict], context: dict) -> dict:
        """Execute tasks iteratively with feedback loops"""
        executed_tasks = []
        failed_tasks = []
        
        for iteration in range(3):  # Example: 3 iterations
            for task in tasks:
                try:
                    task_result = {
                        "task_id": task.get("id", f"task-{int(time.time())}"),
                        "iteration": iteration + 1,
                        "status": "completed",
                        "execution_time": 1.2,  # seconds
                        "output": f"Iteration {iteration + 1} output for {task.get('title', 'unnamed task')}"
                    }
                    executed_tasks.append(task_result)
                except Exception as e:
                    failed_tasks.append({
                        "task_id": task.get("id", f"task-{int(time.time())}"),
                        "iteration": iteration + 1,
                        "error": str(e)
                    })
        
        return {
            "workflow_type": "iterative",
            "executed_tasks": executed_tasks,
            "failed_tasks": failed_tasks,
            "iterations_completed": 3,
            "status": "completed" if not failed_tasks else "partial"
        }

    def _execute_requirements_gathering_workflow(self, tasks: List[dict], context: dict) -> dict:
        """Execute requirements gathering workflow involving requirements engineer"""
        executed_tasks = []
        failed_tasks = []

        # Check if requirements engineer is available
        req_eng_available = self._check_agent_availability("requirements-engineer")
        
        if not req_eng_available:
            print("Requirements engineer unavailable, proceeding with local requirements gathering")
        
        # Simulate requirements gathering workflow
        for task in tasks:
            try:
                # This would involve calling the requirements engineer agent if available
                task_result = {
                    "task_id": task.get("id", f"req-gather-{int(time.time())}"),
                    "status": "completed",
                    "execution_time": 2.5,  # seconds
                    "output": f"Requirements gathered: {task.get('title', 'unnamed task')}",
                    "workflow_phase": "requirements_gathering",
                    "involved_agents": ["requirements-engineer"] if req_eng_available else ["it-lead-local"],
                    "requirements_engineer_available": req_eng_available
                }
                executed_tasks.append(task_result)
            except Exception as e:
                failed_tasks.append({
                    "task_id": task.get("id", f"req-gather-{int(time.time())}"),
                    "error": str(e),
                    "workflow_phase": "requirements_gathering"
                })

        return {
            "workflow_type": "requirements_gathering",
            "executed_tasks": executed_tasks,
            "failed_tasks": failed_tasks,
            "total_execution_time": sum([t.get("execution_time", 0) for t in executed_tasks]),
            "status": "completed" if not failed_tasks else "partial",
            "requirements_engineer_involved": req_eng_available,
            "requirements_engineer_available": req_eng_available
        }
    
    def _check_agent_availability(self, agent_id: str) -> bool:
        """Check if an agent is available"""
        if self.agent_registry:
            try:
                availability = self.agent_registry.check_agent_availability(agent_id)
                return availability.get("status") == "available"
            except Exception:
                # If we can't check availability, assume the agent is not available
                return False
        return False

    def _execute_requirements_validation_workflow(self, tasks: List[dict], context: dict) -> dict:
        """Execute requirements validation workflow involving requirements engineer"""
        executed_tasks = []
        failed_tasks = []

        # Check if requirements engineer is available
        req_eng_available = self._check_agent_availability("requirements-engineer")
        
        if not req_eng_available:
            print("Requirements engineer unavailable, proceeding with local requirements validation")
        
        # Simulate requirements validation workflow
        for task in tasks:
            try:
                # This would involve calling the requirements engineer agent for validation if available
                task_result = {
                    "task_id": task.get("id", f"req-validate-{int(time.time())}"),
                    "status": "completed",
                    "execution_time": 2.0,  # seconds
                    "output": f"Requirements validated: {task.get('title', 'unnamed task')}",
                    "workflow_phase": "requirements_validation",
                    "involved_agents": ["requirements-engineer"] if req_eng_available else ["it-lead-local"],
                    "requirements_engineer_available": req_eng_available
                }
                executed_tasks.append(task_result)
            except Exception as e:
                failed_tasks.append({
                    "task_id": task.get("id", f"req-validate-{int(time.time())}"),
                    "error": str(e),
                    "workflow_phase": "requirements_validation"
                })

        return {
            "workflow_type": "requirements_validation",
            "executed_tasks": executed_tasks,
            "failed_tasks": failed_tasks,
            "total_execution_time": sum([t.get("execution_time", 0) for t in executed_tasks]),
            "status": "completed" if not failed_tasks else "partial",
            "requirements_engineer_involved": req_eng_available,
            "requirements_engineer_available": req_eng_available
        }

    def _execute_event_driven_workflow(self, tasks: List[dict], context: dict) -> dict:
        """Execute tasks based on events"""
        executed_tasks = []
        failed_tasks = []

        # Simulate event-driven execution
        for task in tasks:
            try:
                task_result = {
                    "task_id": task.get("id", f"task-{int(time.time())}"),
                    "triggered_by_event": "simulated_event",
                    "status": "completed",
                    "execution_time": 0.8,  # seconds
                    "output": f"Event-driven output for {task.get('title', 'unnamed task')}"
                }
                executed_tasks.append(task_result)
            except Exception as e:
                failed_tasks.append({
                    "task_id": task.get("id", f"task-{int(time.time())}"),
                    "triggered_by_event": "simulated_event",
                    "error": str(e)
                })

        return {
            "workflow_type": "event_driven",
            "executed_tasks": executed_tasks,
            "failed_tasks": failed_tasks,
            "events_processed": len(tasks),
            "status": "completed" if not failed_tasks else "partial"
        }

    def _process_event(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Process an event and trigger appropriate responses"""
        event_type = arguments.get("event_type", "")
        event_data = arguments.get("event_data", {})
        handlers = arguments.get("handlers", [])
        
        # Process the event and trigger handlers
        triggered_actions = []
        
        for handler in handlers:
            try:
                action_result = {
                    "handler": handler,
                    "status": "executed",
                    "result": f"Action taken for {event_type} event"
                }
                triggered_actions.append(action_result)
            except Exception as e:
                triggered_actions.append({
                    "handler": handler,
                    "status": "failed",
                    "error": str(e)
                })
        
        result = {
            "event_type": event_type,
            "event_data": event_data,
            "triggered_actions": triggered_actions,
            "processed_by": "it-lead-agent",
            "timestamp": time.time()
        }

        return {"result": result}

    def _resolve_conflict(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve conflicts between agent outputs"""
        outputs = arguments.get("outputs", [])
        context = arguments.get("context", {})
        strategy = arguments.get("resolution_strategy", "llm_mediated")
        
        if strategy == "llm_mediated" and self.llm_client and len(outputs) >= 2:
            # Use LLM to mediate between conflicting outputs
            result = self._resolve_conflict_with_llm(outputs[0], outputs[1], context)
        else:
            # Fallback implementation
            if outputs:
                result = {
                    "root_cause": "Conflict between different approaches",
                    "comparison": {
                        "output1_strengths": ["Has good structure"],
                        "output1_weaknesses": ["Lacks detail"],
                        "output2_strengths": ["Detailed implementation"],
                        "output2_weaknesses": ["Complex approach"]
                    },
                    "recommended_resolution": outputs[0],  # Choose first output as default
                    "implementation_plan": ["Integrate best elements from both outputs"],
                    "risks": ["Potential integration issues"],
                    "compromise_solution": "Hybrid approach combining both outputs"
                }
            else:
                result = {
                    "root_cause": "No outputs provided",
                    "comparison": {},
                    "recommended_resolution": None,
                    "implementation_plan": [],
                    "risks": ["Cannot resolve without outputs"],
                    "compromise_solution": "Need at least one output to work with"
                }

        return {"result": result}

    def _resolve_conflict_with_llm(self, output1: dict, output2: dict, context: dict):
        """Use LLM to resolve conflicts between outputs"""
        prompt = f"""
        You are a senior architect mediating a technical conflict between two solutions. 
        Please analyze the following conflicting outputs and provide a resolution:

        CONTEXT:
        {json.dumps(context, indent=2)}

        OUTPUT 1:
        {json.dumps(output1, indent=2)}

        OUTPUT 2:
        {json.dumps(output2, indent=2)}

        Please provide:
        1. Root cause analysis of the conflict
        2. Objective comparison of both approaches
        3. Recommended resolution approach
        4. Implementation plan for the resolution
        5. Potential risks of the recommended approach
        6. Alternative compromise solution if needed

        Format as JSON:
        {{
          "root_cause": "Analysis of why conflict occurred",
          "comparison": {{
            "output1_strengths": ["strength1", "strength2"],
            "output1_weaknesses": ["weakness1", "weakness2"],
            "output2_strengths": ["strength1", "strength2"],
            "output2_weaknesses": ["weakness1", "weakness2"]
          }},
          "recommended_resolution": "Chosen approach",
          "implementation_plan": ["step1", "step2", "step3"],
          "risks": ["risk1", "risk2"],
          "compromise_solution": "Alternative if pure approach not feasible"
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
                        return {
                            "root_cause": "Could not parse LLM response",
                            "comparison": {},
                            "recommended_resolution": None,
                            "implementation_plan": [],
                            "risks": ["Could not parse LLM response"],
                            "compromise_solution": "Manual resolution required"
                        }
            else:
                return {
                    "root_cause": f"LLM call failed: {response.status_code}",
                    "comparison": {},
                    "recommended_resolution": None,
                    "implementation_plan": [],
                    "risks": [f"LLM call failed: {response.status_code}"],
                    "compromise_solution": "Manual resolution required"
                }
        except Exception as e:
            return {
                "root_cause": f"LLM call failed: {str(e)}",
                "comparison": {},
                "recommended_resolution": None,
                "implementation_plan": [],
                "risks": [f"LLM call failed: {str(e)}"],
                "compromise_solution": "Manual resolution required"
            }