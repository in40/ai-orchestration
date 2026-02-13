"""
Strategic Planning Handlers for IT Lead MCP Server
Implements advanced strategic planning capabilities for software development teams
"""
import json
import time
from typing import Dict, Any, List, Optional
from ..utils.json_rpc import JsonRpcHandler, JsonRpcMessage


class StrategicPlanningHandlers:
    """Handles strategic planning specific MCP server methods for software development teams"""

    def __init__(self, llm_client=None, agent_registry=None, task_storage=None):
        self.llm_client = llm_client
        self.agent_registry = agent_registry
        self.task_storage = task_storage
        
        # Strategic planning tools
        self.tools = [
            {
                "name": "decompose_requirements",
                "description": "Decompose high-level requirements into actionable tasks",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "requirement_document": {"type": "string", "description": "High-level requirement document"},
                        "project_context": {"type": "string", "description": "Project context and constraints"},
                        "existing_artifacts": {"type": "array", "items": {"type": "string"}, "description": "Existing project artifacts"}
                    },
                    "required": ["requirement_document", "project_context"]
                }
            },
            {
                "name": "sequence_sdlc_tasks",
                "description": "Organize tasks into SDLC phases with proper dependencies",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tasks": {
                            "type": "array", 
                            "items": {"$ref": "#/definitions/task"},
                            "description": "List of tasks to sequence"
                        },
                        "project_constraints": {"type": "object", "description": "Project timeline and resource constraints"},
                        "phase_requirements": {"type": "object", "description": "Phase-specific requirements"}
                    },
                    "required": ["tasks"]
                }
            },
            {
                "name": "manage_dependencies",
                "description": "Manage and track dependencies between tasks",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tasks": {"type": "array", "items": {"$ref": "#/definitions/task"}},
                        "dependency_rules": {"type": "object", "description": "Rules for dependency management"}
                    },
                    "required": ["tasks"]
                }
            }
        ]

        self.resources = [
            {
                "uri": "it-lead://resource/strategic-plan",
                "name": "Strategic Plan",
                "description": "Decomposed strategic plan with tasks and dependencies"
            }
        ]

    def register_handlers(self, rpc_handler: JsonRpcHandler):
        """Register strategic planning handlers with the RPC handler"""
        rpc_handler.register_request_handler('tools/call', self.handle_tools_call)

    def handle_tools_call(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle tools/call request for strategic planning tools"""
        if params is None:
            params = {}

        tool_name = params.get("name") or params.get("tool")
        tool_arguments = params.get("arguments", {})

        # Find the tool in strategic planning tools
        tool = None
        for t in self.tools:
            if t["name"] == tool_name:
                tool = t
                break

        if not tool:
            return None  # Return None to indicate this tool isn't handled here

        # Execute the strategic planning tool
        return self._execute_tool(tool, tool_arguments)

    def _execute_tool(self, tool: Dict[str, Any], arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific strategic planning tool with given arguments"""
        tool_name = tool["name"]

        if tool_name == "decompose_requirements":
            return self._decompose_requirements(arguments)
        
        elif tool_name == "sequence_sdlc_tasks":
            return self._sequence_sdlc_tasks(arguments)
        
        elif tool_name == "manage_dependencies":
            return self._manage_dependencies(arguments)

        # For any other tools, return a generic response
        return {"result": f"Executed strategic planning tool '{tool_name}' with arguments: {arguments}"}

    def _decompose_requirements(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Decompose high-level requirements into actionable tasks"""
        requirement_document = arguments.get("requirement_document", "")
        project_context = arguments.get("project_context", "")
        
        # Use LLM to decompose requirements
        if self.llm_client:
            result = self._decompose_requirements_with_llm(requirement_document, project_context)
        else:
            # Fallback implementation
            result = {
                "tasks": [
                    {
                        "id": f"task-{int(time.time())}-1",
                        "title": "Example Task",
                        "description": "Example task from requirement decomposition",
                        "effort_estimate": "4h",
                        "priority": "medium",
                        "required_expertise": ["developer"],
                        "dependencies": [],
                        "success_criteria": ["Deliverable completed"],
                        "risks": ["Scope creep"]
                    }
                ]
            }

        # Store the strategic plan in the database
        if self.task_storage:
            self.task_storage.store_received_task(
                task_id=f"strategic-plan-{int(time.time())}",
                title="Strategic Plan",
                description=f"Decomposed requirements from: {requirement_document[:100]}...",
                assigned_to="system",
                priority="high",
                source_server="internal",
                metadata={"tool_call": "decompose_requirements", "original_arguments": arguments}
            )

        return {"result": result}

    def _decompose_requirements_with_llm(self, requirement_document: str, project_context: str):
        """Use LLM to decompose requirements into tasks"""
        prompt = f"""
        You are an experienced software architect and project planner. Decompose the following high-level requirements into specific, actionable tasks:

        REQUIREMENTS:
        {requirement_document}

        PROJECT CONTEXT:
        {project_context}

        Please return a structured response with:
        1. Individual tasks with clear objectives
        2. Estimated effort (in hours or story points)
        3. Priority level (critical/high/medium/low)
        4. Required expertise (architect/developer/tester/security/etc.)
        5. Dependencies between tasks
        6. Success criteria for each task
        7. Potential risks for each task

        Format the response as JSON with the following structure:
        {{
          "tasks": [
            {{
              "id": "unique_task_id",
              "title": "Task title",
              "description": "Detailed task description",
              "effort_estimate": "hours or story points",
              "priority": "critical|high|medium|low",
              "required_expertise": ["architect", "developer", "tester"],
              "dependencies": ["other_task_id"],
              "success_criteria": ["specific measurable outcomes"],
              "risks": ["potential risks"]
            }}
          ]
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
                    # Parse the JSON response
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        # If parsing fails, return a basic structure
                        return {"tasks": [], "error": "Could not parse LLM response"}
            else:
                return {"tasks": [], "error": f"LLM call failed: {response.status_code}"}
        except Exception as e:
            return {"tasks": [], "error": f"LLM call failed: {str(e)}"}

    def _sequence_sdlc_tasks(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Organize tasks into SDLC phases with proper dependencies"""
        tasks = arguments.get("tasks", [])
        constraints = arguments.get("project_constraints", {})
        
        # Use LLM to sequence tasks
        if self.llm_client:
            result = self._sequence_tasks_with_llm(tasks, constraints)
        else:
            # Fallback implementation
            result = {
                "phases": {
                    "requirements": tasks[:1] if tasks else [],
                    "design": tasks[1:2] if len(tasks) > 1 else [],
                    "implementation": tasks[2:3] if len(tasks) > 2 else [],
                    "testing": tasks[3:4] if len(tasks) > 3 else [],
                    "deployment": tasks[4:] if len(tasks) > 4 else []
                },
                "critical_path": [task.get("id", f"task-{i}") for i, task in enumerate(tasks)],
                "parallel_tasks": [],
                "estimated_timeline": {
                    "requirements_duration": "2 days",
                    "design_duration": "3 days",
                    "implementation_duration": "10 days",
                    "testing_duration": "5 days",
                    "deployment_duration": "2 days"
                }
            }

        return {"result": result}

    def _sequence_tasks_with_llm(self, tasks: List[dict], constraints: dict):
        """Use LLM to sequence tasks into SDLC phases"""
        prompt = f"""
        You are an experienced software project manager. Organize the following tasks into SDLC phases considering dependencies and constraints:

        TASKS:
        {json.dumps(tasks, indent=2)}

        CONSTRAINTS:
        {json.dumps(constraints, indent=2)}

        Please return a phased execution plan with:
        1. Requirements phase tasks
        2. Design phase tasks  
        3. Implementation phase tasks
        4. Testing phase tasks
        5. Deployment phase tasks
        6. Dependencies between phases
        7. Parallelizable tasks within phases
        8. Critical path identification
        9. Estimated timeline for each phase

        Format as JSON:
        {{
          "phases": {{
            "requirements": [{{"task_id": "...", "dependencies": []}}], 
            "design": [...],
            "implementation": [...],
            "testing": [...],
            "deployment": [...]
          }},
          "critical_path": ["task_id1", "task_id2", "..."],
          "parallel_tasks": [["task_a", "task_b"], ["task_c", "task_d"]],
          "estimated_timeline": {{
            "requirements_duration": "days",
            "design_duration": "days", 
            "implementation_duration": "days",
            "testing_duration": "days",
            "deployment_duration": "days"
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
                        return {"phases": {}, "error": "Could not parse LLM response"}
            else:
                return {"phases": {}, "error": f"LLM call failed: {response.status_code}"}
        except Exception as e:
            return {"phases": {}, "error": f"LLM call failed: {str(e)}"}

    def _manage_dependencies(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Manage and track dependencies between tasks"""
        tasks = arguments.get("tasks", [])
        
        # Create a simple dependency graph
        dependency_graph = {}
        for task in tasks:
            task_id = task.get("id", f"task-{int(time.time())}")
            dependencies = task.get("dependencies", [])
            dependency_graph[task_id] = dependencies

        result = {
            "dependency_graph": dependency_graph,
            "ready_tasks": self._get_ready_tasks(dependency_graph),
            "critical_path": self._find_critical_path(dependency_graph),
            "potential_bottlenecks": self._find_bottlenecks(dependency_graph)
        }

        return {"result": result}

    def _get_ready_tasks(self, dependency_graph: Dict[str, List[str]]) -> List[str]:
        """Get tasks whose dependencies are satisfied"""
        ready_tasks = []
        for task_id, deps in dependency_graph.items():
            # For simplicity, we'll say a task is ready if it has no dependencies
            # In a real implementation, we'd check completion status
            if not deps:
                ready_tasks.append(task_id)
        return ready_tasks

    def _find_critical_path(self, dependency_graph: Dict[str, List[str]]) -> List[str]:
        """Find the critical path in the dependency graph"""
        # Simplified implementation - in reality this would be more complex
        # For now, return a simple path through the graph
        if dependency_graph:
            return list(dependency_graph.keys())[:3]  # First 3 tasks as example
        return []

    def _find_bottlenecks(self, dependency_graph: Dict[str, List[str]]) -> List[str]:
        """Find potential bottlenecks in the dependency graph"""
        # Find tasks that many others depend on
        dependency_counts = {}
        for task_id, deps in dependency_graph.items():
            for dep in deps:
                if dep in dependency_counts:
                    dependency_counts[dep] += 1
                else:
                    dependency_counts[dep] = 1
        
        # Return tasks that are dependencies for multiple other tasks
        bottlenecks = [task_id for task_id, count in dependency_counts.items() if count > 1]
        return bottlenecks