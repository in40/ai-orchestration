"""
IT Lead Server Handlers for MCP Server
Implements IT lead specific functionality for software development teams
"""
import time
import json
import os
from typing import Dict, Any, List, Optional
from ..utils.json_rpc import JsonRpcHandler, JsonRpcMessage
import requests


class ItLeadServerHandlers:
    """Handles IT lead specific MCP server methods for software development teams"""

    def __init__(self, enable_registry: bool = True, use_postgres: bool = True,
                 postgres_config: Optional[Dict[str, Any]] = None, client_handlers=None,
                 llm_provider_url: str = "http://asus-tus:1234/v1/chat/completions",
                 llm_model: str = "qwen3-4b",
                 prompts_dir: str = "."):
        # IT Lead specific tools for software development
        self.tools: List[Dict[str, Any]] = [
            {
                "name": "assign_task",
                "description": "Assign a development task to a team member or sub-agent",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "Unique identifier for the task"},
                        "task_description": {"type": "string", "description": "Detailed description of the task"},
                        "assignee": {"type": "string", "description": "Team member or agent to assign the task to"},
                        "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"], "default": "medium"},
                        "deadline": {"type": "string", "description": "Deadline for the task in ISO format"}
                    },
                    "required": ["task_id", "task_description", "assignee"]
                }
            },
            {
                "name": "review_code",
                "description": "Review code submitted by team members",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "pull_request_id": {"type": "string", "description": "ID of the pull request to review"},
                        "code_diff": {"type": "string", "description": "Code changes to review"},
                        "reviewer": {"type": "string", "description": "Team member assigned to review"}
                    },
                    "required": ["pull_request_id", "code_diff"]
                }
            },
            {
                "name": "generate_project_plan",
                "description": "Generate a project plan based on requirements",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "requirements": {"type": "string", "description": "Project requirements"},
                        "team_size": {"type": "integer", "description": "Number of team members", "default": 3},
                        "timeline_weeks": {"type": "integer", "description": "Timeline in weeks", "default": 8}
                    },
                    "required": ["requirements"]
                }
            },
            {
                "name": "analyze_architecture",
                "description": "Analyze software architecture and suggest improvements",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "current_architecture": {"type": "string", "description": "Current architecture description"},
                        "requirements": {"type": "string", "description": "System requirements"},
                        "constraints": {"type": "string", "description": "Technical or business constraints"}
                    },
                    "required": ["current_architecture", "requirements"]
                }
            },
            {
                "name": "schedule_team_meeting",
                "description": "Schedule a team meeting to discuss project matters",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "meeting_type": {"type": "string", "enum": ["standup", "planning", "retrospective", "ad_hoc"], "default": "standup"},
                        "attendees": {"type": "array", "items": {"type": "string"}, "description": "List of attendees"},
                        "agenda": {"type": "string", "description": "Meeting agenda"},
                        "datetime": {"type": "string", "description": "Meeting date and time in ISO format"}
                    },
                    "required": ["meeting_type", "attendees", "datetime"]
                }
            },
            {
                "name": "track_task_progress",
                "description": "Track progress of assigned tasks",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_ids": {"type": "array", "items": {"type": "string"}, "description": "List of task IDs to track"},
                        "include_details": {"type": "boolean", "default": False, "description": "Include detailed progress information"}
                    },
                    "required": ["task_ids"]
                }
            }
        ]

        self.resources: List[Dict[str, Any]] = [
            {
                "uri": "it-lead://resource/team-status",
                "name": "Team Status Report",
                "description": "Current status of the development team"
            },
            {
                "uri": "it-lead://resource/project-plan",
                "name": "Project Plan",
                "description": "Current project plan and milestones"
            },
            {
                "uri": "it-lead://resource/architecture-document",
                "name": "Architecture Document",
                "description": "Software architecture documentation"
            }
        ]

        self.prompts: List[Dict[str, Any]] = [
            {
                "name": "task_assignment_prompt",
                "description": "Prompt for assigning tasks to team members",
                "arguments": [
                    {
                        "name": "task_description",
                        "type": "string",
                        "description": "Description of the task to assign"
                    },
                    {
                        "name": "assignee",
                        "type": "string",
                        "description": "Team member or agent to assign the task to"
                    },
                    {
                        "name": "deadline",
                        "type": "string",
                        "description": "Deadline for the task"
                    }
                ]
            },
            {
                "name": "code_review_prompt",
                "description": "Prompt for conducting code reviews",
                "arguments": [
                    {
                        "name": "code_diff",
                        "type": "string",
                        "description": "Code changes to review"
                    },
                    {
                        "name": "review_guidelines",
                        "type": "string",
                        "description": "Guidelines for the code review"
                    }
                ]
            },
            {
                "name": "architecture_advice_prompt",
                "description": "Prompt for providing architecture advice",
                "arguments": [
                    {
                        "name": "current_architecture",
                        "type": "string",
                        "description": "Current architecture description"
                    },
                    {
                        "name": "requirements",
                        "type": "string",
                        "description": "System requirements"
                    }
                ]
            }
        ]

        # Optional registry functionality
        self.enable_registry = enable_registry
        self.service_registry = None
        self.postgres_config = postgres_config or {}

        # Client handlers for server-initiated requests
        self.client_handlers = client_handlers

        # LLM Configuration
        self.llm_provider_url = llm_provider_url
        self.llm_model = llm_model
        self.prompts_dir = prompts_dir

        # Initialize task storage
        try:
            from ..utils.task_storage import TaskStorage
            self.task_storage = TaskStorage(
                host=self.postgres_config.get("host", "localhost"),
                port=self.postgres_config.get("port", 5432),
                database=self.postgres_config.get("database", "mcp_registry"),
                user=self.postgres_config.get("user", "postgres"),
                password=self.postgres_config.get("password", "")
            )
        except Exception as e:
            print(f"❌ Failed to initialize task storage: {e}")
            self.task_storage = None

        if self.enable_registry:
            self._initialize_registry(use_postgres)

        # Add registry-specific tools if enabled
        if self.enable_registry:
            self._add_registry_methods()

    def _initialize_registry(self, use_postgres: bool):
        """Initialize the service registry with either SQLite or PostgreSQL"""
        try:
            if use_postgres and self.postgres_config:
                from ..utils.postgres_registry_db import PostgresServiceRegistry
                self.service_registry = PostgresServiceRegistry(
                    host=self.postgres_config.get("host", "localhost"),
                    port=self.postgres_config.get("port", 5432),
                    database=self.postgres_config.get("database", "mcp_registry"),
                    user=self.postgres_config.get("user", "postgres"),
                    password=self.postgres_config.get("password", "")
                )
            else:
                from ..utils.service_registry_db import ServiceRegistryDB
                self.service_registry = ServiceRegistryDB()
        except Exception as e:
            print(f"Failed to initialize registry: {e}")
            print("Registry functionality will be disabled")
            self.enable_registry = False

    def _add_registry_methods(self):
        """Add registry-specific methods to the server"""
        # Add registry tools to the tools list
        registry_tools = [
            {
                "name": "registry/register",
                "description": "Register a service with the MCP registry",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Unique identifier for the service"},
                        "name": {"type": "string", "description": "Name of the service"},
                        "description": {"type": "string", "description": "Description of the service"},
                        "endpoint": {"type": "string", "description": "Endpoint URL for the service"},
                        "capabilities": {
                            "type": "object",
                            "description": "Capabilities of the service",
                            "properties": {
                                "tools": {"type": "array", "items": {"type": "string"}},
                                "resources": {"type": "array", "items": {"type": "string"}},
                                "prompts": {"type": "array", "items": {"type": "string"}}
                            }
                        }
                    },
                    "required": ["id", "name", "description", "endpoint", "capabilities"]
                }
            },
            {
                "name": "registry/list",
                "description": "List all registered services in the MCP registry",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filter": {"type": "string", "description": "Optional filter for services"}
                    }
                }
            },
            {
                "name": "registry/unregister",
                "description": "Unregister a service from the MCP registry",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "ID of the service to unregister"}
                    },
                    "required": ["id"]
                }
            }
        ]

        # Add registry tools to the tools list
        self.tools.extend(registry_tools)

    def register_handlers(self, rpc_handler: JsonRpcHandler):
        """Register all server handlers with the RPC handler"""
        # Standard MCP methods
        rpc_handler.register_request_handler('initialize', self.handle_initialize)
        rpc_handler.register_request_handler('tools/list', self.handle_tools_list)
        rpc_handler.register_request_handler('tools/call', self.handle_tools_call)
        rpc_handler.register_request_handler('resources/list', self.handle_resources_list)
        rpc_handler.register_request_handler('resources/read', self.handle_resources_read)
        rpc_handler.register_request_handler('prompts/list', self.handle_prompts_list)
        rpc_handler.register_request_handler('prompts/get', self.handle_prompts_get)
        rpc_handler.register_request_handler('shutdown', self.handle_shutdown)
        rpc_handler.register_request_handler('ping', self.handle_ping)

        # Registry handlers - available when registry is enabled
        if self.enable_registry:
            rpc_handler.register_request_handler('registry/register', self.handle_register_service)
            rpc_handler.register_request_handler('registry/list', self.handle_list_services)
            rpc_handler.register_request_handler('registry/unregister', self.handle_unregister_service)

        # Register the initialized request handler (acknowledges receipt of initialization)
        rpc_handler.register_request_handler('initialized', self.handle_initialized_request)

    def handle_initialize(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle initialize request"""
        client_info = params.get("clientInfo", {})
        print(f"Initializing IT Lead connection with client: {client_info.get('name', 'Unknown')} v{client_info.get('version', 'Unknown')}")

        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": {
                "name": "it-lead-mcp-server",
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": {
                    "listChanged": True
                },
                "resources": {
                    "listChanged": True
                },
                "prompts": {
                    "listChanged": True
                }
            }
        }

    def handle_initialized_request(self, params: Dict[str, Any], request_id: str):
        """Handle initialized request - acknowledges receipt of server's initialization response"""
        print("Client acknowledged IT Lead server initialization response")
        # This is part of the handshake protocol, return an empty result
        return {}

    def handle_tools_list(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle tools/list request"""
        # Handle case where params is None (when no params are provided in the request)
        if params is None:
            params = {}

        # Extract pagination parameters if provided
        pagination = params.get("pagination", {})
        cursor = pagination.get("cursor")
        limit = min(pagination.get("limit", len(self.tools)), 100)  # Cap at 100

        # Apply pagination
        if cursor:
            # In a real implementation, cursor would be used to resume listing
            # For simplicity, we'll return all tools
            pass

        # Return tools with pagination info
        return {
            "tools": self.tools[:limit],
            "pagination": {
                "hasMore": len(self.tools) > limit,
                "nextCursor": f"cursor_{limit}" if len(self.tools) > limit else None
            } if limit < len(self.tools) else {}
        }

    def handle_tools_call(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle tools/call request"""
        # Handle case where params is None (when no params are provided in the request)
        if params is None:
            params = {}

        # Support both "name" and "tool" as the parameter name for compatibility
        tool_name = params.get("name") or params.get("tool")
        tool_arguments = params.get("arguments", {})

        # Find the tool
        tool = None
        for t in self.tools:
            if t["name"] == tool_name:
                tool = t
                break

        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")

        # Execute the tool
        return self._execute_tool(tool, tool_arguments)

    def _execute_tool(self, tool: Dict[str, Any], arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific tool with given arguments"""
        tool_name = tool["name"]

        # IT Lead specific tools
        if tool_name == "assign_task":
            task_id = arguments.get("task_id", "unknown")
            task_description = arguments.get("task_description", "")
            assignee = arguments.get("assignee", "")
            priority = arguments.get("priority", "medium")
            deadline = arguments.get("deadline", "")

            # In a real implementation, this would assign the task to the appropriate agent
            # For now, we'll simulate the assignment and return a result
            result = {
                "task_id": task_id,
                "assigned_to": assignee,
                "priority": priority,
                "deadline": deadline,
                "status": "assigned",
                "message": f"Task '{task_id}' assigned to {assignee} with priority {priority}"
            }

            # Store the task in the database
            if self.task_storage:
                self.task_storage.store_received_task(
                    task_id=task_id,
                    title=f"Task: {task_id}",
                    description=task_description,
                    assigned_to=assignee,
                    priority=priority,
                    deadline=deadline,
                    source_server="internal",
                    metadata={"tool_call": "assign_task", "original_arguments": arguments}
                )

            # Log the task assignment
            print(f"Assigned task: {task_id} to {assignee}, priority: {priority}, deadline: {deadline}")
            
            return result

        elif tool_name == "review_code":
            pull_request_id = arguments.get("pull_request_id", "unknown")
            code_diff = arguments.get("code_diff", "")
            reviewer = arguments.get("reviewer", "auto")

            # Simulate code review process
            # In a real implementation, this would call an LLM to review the code
            review_result = self._perform_code_review(code_diff)
            
            result = {
                "pull_request_id": pull_request_id,
                "reviewer": reviewer,
                "status": "completed",
                "review_summary": review_result
            }

            # Store the review task in the database
            if self.task_storage:
                self.task_storage.store_received_task(
                    task_id=f"review-{pull_request_id}",
                    title=f"Code Review: PR #{pull_request_id}",
                    description=f"Review code changes for PR #{pull_request_id}",
                    assigned_to=reviewer,
                    priority="medium",
                    source_server="internal",
                    metadata={"tool_call": "review_code", "original_arguments": arguments}
                )

            print(f"Completed code review for PR #{pull_request_id}")
            return result

        elif tool_name == "generate_project_plan":
            requirements = arguments.get("requirements", "")
            team_size = arguments.get("team_size", 3)
            timeline_weeks = arguments.get("timeline_weeks", 8)

            # Generate a project plan using the LLM
            plan = self._generate_project_plan(requirements, team_size, timeline_weeks)
            
            result = {
                "requirements": requirements,
                "team_size": team_size,
                "timeline_weeks": timeline_weeks,
                "project_plan": plan
            }

            # Store the project plan task in the database
            if self.task_storage:
                self.task_storage.store_received_task(
                    task_id=f"plan-{int(time.time())}",
                    title="Project Plan Generation",
                    description=f"Generate project plan for: {requirements[:100]}...",
                    assigned_to="system",
                    priority="high",
                    source_server="internal",
                    metadata={"tool_call": "generate_project_plan", "original_arguments": arguments}
                )

            print(f"Generated project plan for requirements: {requirements[:50]}...")
            return result

        elif tool_name == "analyze_architecture":
            current_architecture = arguments.get("current_architecture", "")
            requirements = arguments.get("requirements", "")
            constraints = arguments.get("constraints", "")

            # Analyze architecture using the LLM
            analysis = self._analyze_architecture(current_architecture, requirements, constraints)
            
            result = {
                "current_architecture": current_architecture,
                "requirements": requirements,
                "constraints": constraints,
                "analysis": analysis
            }

            # Store the architecture analysis task in the database
            if self.task_storage:
                self.task_storage.store_received_task(
                    task_id=f"arch-analysis-{int(time.time())}",
                    title="Architecture Analysis",
                    description=f"Analyze architecture: {current_architecture[:100]}...",
                    assigned_to="system",
                    priority="high",
                    source_server="internal",
                    metadata={"tool_call": "analyze_architecture", "original_arguments": arguments}
                )

            print(f"Completed architecture analysis for: {current_architecture[:50]}...")
            return result

        elif tool_name == "schedule_team_meeting":
            meeting_type = arguments.get("meeting_type", "standup")
            attendees = arguments.get("attendees", [])
            agenda = arguments.get("agenda", "")
            datetime = arguments.get("datetime", "")

            result = {
                "meeting_type": meeting_type,
                "attendees": attendees,
                "agenda": agenda,
                "datetime": datetime,
                "status": "scheduled",
                "message": f"{meeting_type.title()} meeting scheduled for {datetime}"
            }

            # Store the meeting scheduling task in the database
            if self.task_storage:
                self.task_storage.store_received_task(
                    task_id=f"meeting-{int(time.time())}",
                    title=f"Team Meeting: {meeting_type}",
                    description=f"Schedule {meeting_type} meeting for {datetime}",
                    assigned_to="organizer",
                    priority="medium",
                    source_server="internal",
                    metadata={"tool_call": "schedule_team_meeting", "original_arguments": arguments}
                )

            print(f"Scheduled {meeting_type} meeting for {datetime} with {len(attendees)} attendees")
            return result

        elif tool_name == "track_task_progress":
            task_ids = arguments.get("task_ids", [])
            include_details = arguments.get("include_details", False)

            # Simulate tracking task progress
            progress_data = []
            for task_id in task_ids:
                progress_data.append({
                    "task_id": task_id,
                    "progress_percentage": 75,  # Simulated progress
                    "status": "in_progress",
                    "estimated_completion": "2023-12-31T10:00:00Z"
                })

            result = {
                "tracked_tasks": progress_data,
                "summary": {
                    "total_tasks": len(task_ids),
                    "completed": 0,
                    "in_progress": len(task_ids),
                    "on_schedule": len(task_ids)
                }
            }

            # Store the task tracking task in the database
            if self.task_storage:
                self.task_storage.store_received_task(
                    task_id=f"tracking-{int(time.time())}",
                    title="Task Progress Tracking",
                    description=f"Track progress for {len(task_ids)} tasks: {', '.join(task_ids[:5])}{'...' if len(task_ids) > 5 else ''}",
                    assigned_to="system",
                    priority="low",
                    source_server="internal",
                    metadata={"tool_call": "track_task_progress", "original_arguments": arguments}
                )

            print(f"Tracked progress for {len(task_ids)} tasks")
            return result

        # Handle registry tools by calling their respective handlers
        elif tool_name == "registry/register":
            return self.handle_register_service(arguments, "temp_id_for_tool_call")
        elif tool_name == "registry/list":
            return self.handle_list_services(arguments, "temp_id_for_tool_call")
        elif tool_name == "registry/unregister":
            return self.handle_unregister_service(arguments, "temp_id_for_tool_call")

        # For any other tools, return a generic response
        return {"result": f"Executed tool '{tool_name}' with arguments: {arguments}"}

    def _perform_code_review(self, code_diff: str) -> str:
        """Perform code review using the LLM"""
        try:
            # Create a prompt for the LLM to review the code
            prompt = f"""
            Please review the following code changes and provide feedback:
            
            Code Diff:
            {code_diff}
            
            Provide feedback on:
            1. Code quality and best practices
            2. Potential bugs or issues
            3. Suggestions for improvement
            4. Security concerns if any
            """
            
            # Call the LLM to perform the review
            response = self._call_llm(prompt)
            return response
            
        except Exception as e:
            print(f"Error performing code review: {e}")
            return f"Code review failed: {str(e)}"

    def _generate_project_plan(self, requirements: str, team_size: int, timeline_weeks: int) -> str:
        """Generate a project plan using the LLM"""
        try:
            prompt = f"""
            Generate a detailed project plan based on the following requirements:
            
            Requirements:
            {requirements}
            
            Team Size: {team_size} members
            Timeline: {timeline_weeks} weeks
            
            Include:
            1. Phases and milestones
            2. Task breakdown
            3. Resource allocation
            4. Risk assessment
            5. Dependencies
            """
            
            response = self._call_llm(prompt)
            return response
            
        except Exception as e:
            print(f"Error generating project plan: {e}")
            return f"Project plan generation failed: {str(e)}"

    def _analyze_architecture(self, current_architecture: str, requirements: str, constraints: str) -> str:
        """Analyze software architecture using the LLM"""
        try:
            prompt = f"""
            Analyze the following software architecture and provide suggestions for improvements:
            
            Current Architecture:
            {current_architecture}
            
            Requirements:
            {requirements}
            
            Constraints:
            {constraints}
            
            Provide analysis on:
            1. Scalability
            2. Performance
            3. Security
            4. Maintainability
            5. Technology choices
            6. Suggested improvements
            """
            
            response = self._call_llm(prompt)
            return response
            
        except Exception as e:
            print(f"Error analyzing architecture: {e}")
            return f"Architecture analysis failed: {str(e)}"

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM with the given prompt"""
        try:
            headers = {
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.llm_model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            }
            
            response = requests.post(self.llm_provider_url, headers=headers, json=data, timeout=1200)
            
            if response.status_code == 200:
                result = response.json()
                # Extract the content from the response
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
                else:
                    return "LLM response format not recognized"
            else:
                print(f"LLM API call failed with status {response.status_code}: {response.text}")
                return f"LLM call failed: {response.status_code}"
                
        except Exception as e:
            print(f"Error calling LLM: {e}")
            return f"LLM call failed: {str(e)}"

    def handle_resources_list(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle resources/list request"""
        # Handle case where params is None (when no params are provided in the request)
        if params is None:
            params = {}

        # Extract pagination parameters if provided
        pagination = params.get("pagination", {})
        cursor = pagination.get("cursor")
        limit = min(pagination.get("limit", len(self.resources)), 100)  # Cap at 100

        # Apply pagination
        if cursor:
            # In a real implementation, cursor would be used to resume listing
            # For simplicity, we'll return all resources
            pass

        # Return resources with pagination info
        return {
            "resources": self.resources[:limit],
            "pagination": {
                "hasMore": len(self.resources) > limit,
                "nextCursor": f"cursor_{limit}" if len(self.resources) > limit else None
            } if limit < len(self.resources) else {}
        }

    def handle_resources_read(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle resources/read request"""
        # Handle case where params is None (when no params are provided in the request)
        if params is None:
            params = {}

        uri = params.get("uri")

        # Find the resource
        resource = None
        for r in self.resources:
            if r["uri"] == uri:
                resource = r
                break

        if not resource:
            raise ValueError(f"Resource '{uri}' not found")

        # Return resource content
        return self._read_resource(resource)

    def _read_resource(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Read content from a specific resource"""
        uri = resource["uri"]

        # IT Lead specific resources
        if uri == "it-lead://resource/team-status":
            # In a real implementation, this would fetch actual team status
            # For now, return simulated data
            return {
                "contents": [{
                    "uri": uri,
                    "text": json.dumps({
                        "team_size": 5,
                        "active_projects": 3,
                        "overall_velocity": 25,
                        "current_bottlenecks": ["dependency_resolution", "code_review_backlog"],
                        "upcoming_milestones": ["release_v1.2", "security_audit"],
                        "team_health": "good"
                    }, indent=2)
                }]
            }

        elif uri == "it-lead://resource/project-plan":
            # In a real implementation, this would fetch actual project plan
            # For now, return simulated data
            return {
                "contents": [{
                    "uri": uri,
                    "text": json.dumps({
                        "project_name": "New Feature Development",
                        "start_date": "2023-10-01",
                        "end_date": "2024-01-15",
                        "milestones": [
                            {"name": "Requirements Gathering", "date": "2023-10-15", "status": "completed"},
                            {"name": "Design Phase", "date": "2023-11-01", "status": "in_progress"},
                            {"name": "Development Phase", "date": "2023-12-15", "status": "pending"},
                            {"name": "Testing Phase", "date": "2024-01-01", "status": "pending"},
                            {"name": "Deployment", "date": "2024-01-15", "status": "pending"}
                        ],
                        "team_allocation": {
                            "backend_developers": 2,
                            "frontend_developers": 2,
                            "qa_engineers": 1
                        }
                    }, indent=2)
                }]
            }

        elif uri == "it-lead://resource/architecture-document":
            # In a real implementation, this would fetch actual architecture doc
            # For now, return simulated data
            return {
                "contents": [{
                    "uri": uri,
                    "text": json.dumps({
                        "architecture_style": "Microservices",
                        "components": [
                            {"name": "API Gateway", "technology": "Express.js", "responsibilities": ["routing", "authentication"]},
                            {"name": "User Service", "technology": "Node.js", "responsibilities": ["user management", "authentication"]},
                            {"name": "Order Service", "technology": "Python", "responsibilities": ["order processing", "inventory"]},
                            {"name": "Payment Service", "technology": "Java", "responsibilities": ["payment processing", "billing"]}
                        ],
                        "data_store": {
                            "primary_database": "PostgreSQL",
                            "cache": "Redis",
                            "message_queue": "RabbitMQ"
                        },
                        "deployment": {
                            "infrastructure": "Docker + Kubernetes",
                            "cloud_provider": "AWS",
                            "monitoring": "Prometheus + Grafana"
                        }
                    }, indent=2)
                }]
            }

        # For any other resources, return a generic response
        return {
            "contents": [{
                "uri": uri,
                "text": f"Content for resource: {uri}"
            }]
        }

    def handle_prompts_list(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle prompts/list request"""
        # Handle case where params is None (when no params are provided in the request)
        if params is None:
            params = {}

        # Extract pagination parameters if provided
        pagination = params.get("pagination", {})
        cursor = pagination.get("cursor")
        limit = min(pagination.get("limit", len(self.prompts)), 100)  # Cap at 100

        # Apply pagination
        if cursor:
            # In a real implementation, cursor would be used to resume listing
            # For simplicity, we'll return all prompts
            pass

        # Return prompts with pagination info
        return {
            "prompts": self.prompts[:limit],
            "pagination": {
                "hasMore": len(self.prompts) > limit,
                "nextCursor": f"cursor_{limit}" if len(self.prompts) > limit else None
            } if limit < len(self.prompts) else {}
        }

    def handle_prompts_get(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle prompts/get request"""
        # Handle case where params is None (when no params are provided in the request)
        if params is None:
            params = {}

        prompt_name = params.get("name")
        prompt_arguments = params.get("arguments", {})

        # Find the prompt
        prompt = None
        for p in self.prompts:
            if p["name"] == prompt_name:
                prompt = p
                break

        if not prompt:
            raise ValueError(f"Prompt '{prompt_name}' not found")

        # Return resolved prompt
        return self._resolve_prompt(prompt, prompt_arguments)

    def _resolve_prompt(self, prompt: Dict[str, Any], arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve a prompt with given arguments"""
        prompt_name = prompt["name"]

        # IT Lead specific prompts
        if prompt_name == "task_assignment_prompt":
            task_description = arguments.get("task_description", "No description provided")
            assignee = arguments.get("assignee", "Not specified")
            deadline = arguments.get("deadline", "No deadline specified")
            
            resolved_text = f"""
            TASK ASSIGNMENT

            Task: {task_description}
            Assigned to: {assignee}
            Deadline: {deadline}

            Instructions:
            1. Review the task requirements carefully
            2. Break down the task into smaller subtasks if needed
            3. Estimate the time required for each subtask
            4. Start working on the task and provide regular updates
            5. Reach out if you encounter any blockers
            """
            return {
                "contents": [{
                    "type": "text",
                    "text": resolved_text
                }]
            }

        elif prompt_name == "code_review_prompt":
            code_diff = arguments.get("code_diff", "No code provided")
            review_guidelines = arguments.get("review_guidelines", "Follow standard code review practices")
            
            resolved_text = f"""
            CODE REVIEW REQUEST

            Code to review:
            {code_diff}

            Review Guidelines:
            {review_guidelines}

            Please check for:
            1. Code correctness and logic
            2. Adherence to coding standards
            3. Performance implications
            4. Security vulnerabilities
            5. Test coverage
            6. Documentation completeness
            """
            return {
                "contents": [{
                    "type": "text",
                    "text": resolved_text
                }]
            }

        elif prompt_name == "architecture_advice_prompt":
            current_architecture = arguments.get("current_architecture", "No architecture provided")
            requirements = arguments.get("requirements", "No requirements provided")
            
            resolved_text = f"""
            ARCHITECTURE ADVICE REQUEST

            Current Architecture:
            {current_architecture}

            Requirements:
            {requirements}

            Please provide advice on:
            1. Scalability improvements
            2. Performance optimizations
            3. Security enhancements
            4. Technology recommendations
            5. Potential risks and mitigation strategies
            """
            return {
                "contents": [{
                    "type": "text",
                    "text": resolved_text
                }]
            }

        # For any other prompts, return a generic response
        return {
            "contents": [{
                "type": "text",
                "text": f"Resolved prompt '{prompt_name}' with arguments: {arguments}"
            }]
        }

    def handle_shutdown(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle shutdown request"""
        print("IT Lead server shutdown request received, preparing to shut down...")
        return {}

    def handle_ping(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle ping request for health check"""
        # Handle case where params is None (when no params are provided in the request)
        if params is None:
            params = {}

        # Perform custom health checks
        health_status = self._perform_health_checks()

        return {
            "timestamp": time.time(),
            "status": "healthy" if health_status["overall_status"] else "unhealthy",
            "server_type": "IT Lead Agent",
            "health_details": health_status
        }

    def _perform_health_checks(self) -> Dict[str, Any]:
        """Perform custom health checks for the IT Lead server"""
        health_status = {
            "overall_status": True,
            "checks": {},
            "llm_connection": False,
            "registry_connection": False,
            "database_connection": False
        }

        # Check LLM connection
        try:
            import requests
            # Test the LLM provider connection by sending a simple request
            test_prompt = {
                "model": self.llm_model,
                "messages": [{"role": "user", "content": "health check"}],
                "max_tokens": 5
            }
            response = requests.post(self.llm_provider_url, json=test_prompt, timeout=1200)
            health_status["llm_connection"] = response.status_code in [200, 401, 400]  # 401/400 means connection worked but auth/token issue
            health_status["checks"]["llm"] = {
                "status": "healthy" if health_status["llm_connection"] else "unhealthy",
                "message": f"LLM provider connection: {'OK' if health_status['llm_connection'] else 'FAILED'}"
            }
        except Exception as e:
            health_status["checks"]["llm"] = {
                "status": "unhealthy",
                "message": f"LLM provider connection failed: {str(e)}"
            }

        # Check registry connection if enabled
        if self.enable_registry:
            try:
                # Check if we can access the registry
                if hasattr(self, 'service_registry') and self.service_registry:
                    # Try to list services as a basic registry connectivity test
                    services = self.service_registry.list_services()
                    health_status["registry_connection"] = True
                    health_status["checks"]["registry"] = {
                        "status": "healthy",
                        "message": f"Registry connection: OK, found {len(services)} services"
                    }
                else:
                    health_status["registry_connection"] = False
                    health_status["checks"]["registry"] = {
                        "status": "unhealthy",
                        "message": "Registry not properly initialized"
                    }
            except Exception as e:
                health_status["checks"]["registry"] = {
                    "status": "unhealthy",
                    "message": f"Registry connection failed: {str(e)}"
                }

        # Check database connection if registry is enabled
        if self.enable_registry and hasattr(self, 'service_registry') and self.service_registry:
            try:
                # Try to list services as a basic DB connectivity test
                services = self.service_registry.list_services()
                health_status["database_connection"] = True
                health_status["checks"]["database"] = {
                    "status": "healthy",
                    "message": f"Database connection: OK, found {len(services)} services"
                }
            except Exception as e:
                health_status["database_connection"] = False
                health_status["checks"]["database"] = {
                    "status": "unhealthy",
                    "message": f"Database connection failed: {str(e)}"
                }

        # Overall status is healthy only if all critical checks pass
        health_status["overall_status"] = (
            health_status["llm_connection"] and
            (not self.enable_registry or health_status["registry_connection"]) and
            (not self.enable_registry or health_status["database_connection"])
        )

        return health_status

    # Registry-specific handlers
    def handle_register_service(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle registry/register request."""
        # Handle case where params is None (when no params are provided in the request)
        if params is None:
            params = {}

        if not hasattr(self, 'enable_registry') or not self.enable_registry:
            print("❌ Registry functionality is not enabled")
            raise ValueError("Registry functionality is not enabled")

        if not hasattr(self, 'service_registry'):
            print("❌ Service registry is not initialized")
            raise ValueError("Service registry is not initialized")

        # Extract service information from params
        service_info = {
            "id": params.get("id"),
            "name": params.get("name"),
            "description": params.get("description"),
            "endpoint": params.get("endpoint"),
            "capabilities": params.get("capabilities", {}),
            "registered_at": time.time()
        }

        # Validate required fields
        if not all(k in service_info and service_info[k] for k in ["id", "name", "description", "endpoint"]):
            raise ValueError("Missing required fields for service registration")

        # Check if service already exists
        existing_services = self.service_registry.list_services()

        for existing_service in existing_services:
            if existing_service.get("id") == service_info["id"]:
                print(f"⚠️ Service with ID {service_info['id']} already exists, updating...")
                break

        # Register the service
        success = self.service_registry.register_service(service_info)

        if success:
            print(f"✅ Service '{service_info['name']}' registered with ID '{service_info['id']}'")
            return {
                "success": True,
                "service_id": service_info["id"],
                "message": "Service registered successfully"
            }
        else:
            print(f"❌ Failed to register service '{service_info['name']}'")
            return {
                "success": False,
                "message": "Failed to register service"
            }

    def handle_list_services(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle registry/list request."""
        print(f"📋 IT Lead registry list request received")

        # Handle case where params is None (when no params are provided in the request)
        if params is None:
            params = {}

        if not hasattr(self, 'enable_registry') or not self.enable_registry:
            print("❌ Registry functionality is not enabled")
            raise ValueError("Registry functionality is not enabled")

        if not hasattr(self, 'service_registry'):
            print("❌ Service registry is not initialized")
            raise ValueError("Service registry is not initialized")

        # Get filter from params if provided
        filter_param = params.get("filter")

        services = self.service_registry.list_services()

        # Apply filter if provided
        if filter_param:
            filtered_services = []
            for service in services:
                # Check if filter matches any service property
                service_values = [str(v).lower() for v in service.values() if isinstance(v, (str, int))]
                if any(filter_param.lower() in val for val in service_values):
                    filtered_services.append(service)
            services = filtered_services

        print(f"📊 Returning {len(services)} services from IT Lead registry")

        return {
            "services": services,
            "total_count": len(services)
        }

    def handle_unregister_service(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle registry/unregister request."""
        # Handle case where params is None (when no params are provided in the request)
        if params is None:
            params = {}

        if not hasattr(self, 'enable_registry') or not self.enable_registry:
            raise ValueError("Registry functionality is not enabled")

        if not hasattr(self, 'service_registry'):
            raise ValueError("Service registry is not initialized")

        service_id = params.get("id")
        if not service_id:
            raise ValueError("Service ID is required for unregistration")

        success = self.service_registry.unregister_service(service_id)

        if success:
            print(f"✅ Service with ID '{service_id}' unregistered successfully")
            return {
                "success": True,
                "message": "Service unregistered successfully"
            }
        else:
            print(f"❌ Failed to unregister service with ID '{service_id}'")
            return {
                "success": False,
                "message": "Failed to unregister service or service not found"
            }