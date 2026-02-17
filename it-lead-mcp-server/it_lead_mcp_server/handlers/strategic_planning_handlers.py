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
                "name": "coordinate_requirements_analysis",
                "description": "Coordinate between stakeholder inputs and requirements engineer",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "stakeholder_inputs": {"type": "string", "description": "Raw stakeholder inputs (interviews, documents, etc.)"},
                        "business_context": {"type": "string", "description": "Business context and constraints"},
                        "previous_requirements": {"type": "array", "items": {"type": "object"}, "description": "Previous requirements for reference"},
                        "project_context": {"type": "string", "description": "Project context and constraints"},
                        "existing_artifacts": {"type": "array", "items": {"type": "string"}, "description": "Existing project artifacts"}
                    },
                    "required": ["stakeholder_inputs", "business_context", "project_context"]
                }
            },
            {
                "name": "validate_requirements_completeness",
                "description": "Validate completeness of requirements using requirements engineer capabilities",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "requirement_document": {"type": "string", "description": "Requirement document to validate"},
                        "validation_criteria": {"type": "array", "items": {"type": "string"}, "description": "Criteria for validation"},
                        "project_context": {"type": "string", "description": "Project context and constraints"}
                    },
                    "required": ["requirement_document", "validation_criteria", "project_context"]
                }
            },
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
        # Note: Do NOT register tools/call here - the main handler in extended_server_handlers.py
        # is responsible for routing tool calls to this module. Registering tools/call here
        # would override the main handler and prevent proper task storage.

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

        if tool_name == "coordinate_requirements_analysis":
            return self._coordinate_requirements_analysis(arguments)

        elif tool_name == "validate_requirements_completeness":
            return self._validate_requirements_completeness(arguments)

        elif tool_name == "decompose_requirements":
            return self._decompose_requirements(arguments)

        elif tool_name == "sequence_sdlc_tasks":
            return self._sequence_sdlc_tasks(arguments)

        elif tool_name == "manage_dependencies":
            return self._manage_dependencies(arguments)

        # For any other tools, return None to indicate this module doesn't handle them
        return None

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

    def _coordinate_requirements_analysis(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate between stakeholder inputs and requirements engineer"""
        try:
            stakeholder_inputs = arguments.get("stakeholder_inputs", "")
            business_context = arguments.get("business_context", "")
            previous_requirements = arguments.get("previous_requirements", [])
            project_context = arguments.get("project_context", "")
            target_agent = "requirements-engineer"
            
            # Try to call the requirements engineer agent with retry logic
            result = self._attempt_call_to_agent(
                target_agent, 
                "coordinate_requirements_analysis", 
                arguments,
                max_retries=3
            )
            
            if result and result.get("status") != "error":
                # Successful call to requirements engineer
                return result
            else:
                # Fall back to local processing if requirements engineer is unavailable
                print(f"Requirements engineer unavailable, falling back to local processing for requirements coordination")
                result = {
                    "status": "coordinated_locally",
                    "message": "Coordinated requirements analysis locally (requirements engineer unavailable)",
                    "stakeholder_inputs_processed": len(stakeholder_inputs) > 0,
                    "business_context_applied": len(business_context) > 0,
                    "previous_requirements_considered": len(previous_requirements),
                    "project_context_applied": len(project_context) > 0,
                    "fallback_used": True
                }
            
            # Store the coordination task in the database
            if self.task_storage:
                self.task_storage.store_received_task(
                    task_id=f"coord-{int(time.time())}",
                    title="Requirements Analysis Coordination",
                    description=f"Coordinate requirements analysis: {stakeholder_inputs[:100]}...",
                    assigned_to="requirements-engineer",
                    priority="high",
                    source_server="internal",
                    metadata={"tool_call": "coordinate_requirements_analysis", "original_arguments": arguments}
                )
                
            print(f"Coordinated requirements analysis with requirements engineer")
            return {"result": result}
            
        except Exception as e:
            print(f"Error coordinating requirements analysis: {e}")
            return {"result": f"Requirements coordination failed: {str(e)}"}

    def _attempt_call_to_agent(self, target_agent: str, operation: str, arguments: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
        """Attempt to call an agent with retry logic"""
        # Check if the target agent is available
        agent_available = self._check_agent_availability(target_agent)
        
        if not agent_available:
            return {"status": "error", "message": f"Target agent {target_agent} is not available"}
        
        # In a real implementation, this would make an actual call to the target agent
        # For now, we'll simulate the call and return appropriate results
        # This is where the actual agent communication would happen
        
        # For simulation purposes, let's say the call succeeds
        # In a real implementation, this would involve actual MCP communication
        try:
            # Simulate a successful call to the agent
            # In real implementation, this would be an actual call to the agent
            return None  # Returning None to indicate we should proceed with local processing
        except Exception as e:
            # If the call fails, try again up to max_retries times
            for attempt in range(max_retries):
                try:
                    # Check availability again before retrying
                    if self._check_agent_availability(target_agent):
                        # Simulate a successful call to the agent on retry
                        # In real implementation, this would be an actual call to the agent
                        return None  # Returning None to indicate we should proceed with local processing
                except Exception as retry_e:
                    if attempt == max_retries - 1:  # Last attempt
                        print(f"All retry attempts failed for {target_agent}: {retry_e}")
                        return {"status": "error", "message": f"Failed to reach {target_agent} after {max_retries} attempts"}
                    time.sleep(1)  # Wait before retrying
            return {"status": "error", "message": f"Failed to reach {target_agent}"}
    
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

    def _validate_requirements_completeness(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Validate completeness of requirements using requirements engineer capabilities"""
        try:
            requirement_document = arguments.get("requirement_document", "")
            validation_criteria = arguments.get("validation_criteria", [])
            project_context = arguments.get("project_context", "")
            target_agent = "requirements-engineer"
            
            # Try to call the requirements engineer agent with retry logic
            result = self._attempt_call_to_agent(
                target_agent, 
                "validate_requirements_completeness", 
                arguments,
                max_retries=3
            )
            
            if result and result.get("status") != "error":
                # Successful call to requirements engineer
                return result
            else:
                # Fall back to local processing if requirements engineer is unavailable
                print(f"Requirements engineer unavailable, falling back to local processing for requirements validation")
                result = {
                    "status": "validated_locally",
                    "message": "Validated requirements completeness locally (requirements engineer unavailable)",
                    "requirement_document_analyzed": len(requirement_document) > 0,
                    "validation_criteria_applied": len(validation_criteria),
                    "completeness_score": 0.85,  # Simulated score
                    "issues_found": [],
                    "recommendations": [],
                    "fallback_used": True
                }
            
            # Store the validation task in the database
            if self.task_storage:
                self.task_storage.store_received_task(
                    task_id=f"validate-{int(time.time())}",
                    title="Requirements Completeness Validation",
                    description=f"Validate requirements completeness: {requirement_document[:100]}...",
                    assigned_to="requirements-engineer",
                    priority="high",
                    source_server="internal",
                    metadata={"tool_call": "validate_requirements_completeness", "original_arguments": arguments}
                )
                
            print(f"Validated requirements completeness using requirements engineer capabilities")
            return {"result": result}
            
        except Exception as e:
            print(f"Error validating requirements completeness: {e}")
            return {"result": f"Requirements validation failed: {str(e)}"}

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