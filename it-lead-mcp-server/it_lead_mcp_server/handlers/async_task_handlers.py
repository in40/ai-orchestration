"""
Async Task Handlers for IT Lead MCP Server
Implements asynchronous task management via MCP notifications
"""
import json
import time
from typing import Dict, Any, List, Optional
from ..utils.json_rpc import JsonRpcHandler


class AsyncTaskHandlers:
    """Handles asynchronous task-specific MCP server methods"""

    def __init__(self, llm_client=None, agent_registry=None, task_storage=None, 
                 mcp_client_factory=None, notification_manager=None):
        self.llm_client = llm_client
        self.agent_registry = agent_registry
        self.task_storage = task_storage
        self.mcp_client_factory = mcp_client_factory
        self.notification_manager = notification_manager

        # Async task tools
        self.tools = [
            {
                "name": "assign_task_async",
                "description": "Assign a development task asynchronously to a team member or sub-agent (non-blocking)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "Unique identifier for the task"},
                        "task_description": {"type": "string", "description": "Detailed description of the task"},
                        "assignee": {"type": "string", "description": "Team member or agent to assign the task to"},
                        "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"], "default": "medium"},
                        "deadline": {"type": "string", "description": "Deadline for the task in ISO format"},
                        "tool_to_invoke": {"type": "string", "description": "Specific tool to invoke on the agent (optional, auto-determined if not provided)"},
                        "tool_arguments": {"type": "object", "description": "Arguments for the tool (optional, auto-generated if not provided)"},
                        "callback_requested": {"type": "boolean", "default": True, "description": "Whether to request status callbacks from the agent"}
                    },
                    "required": ["task_id", "task_description", "assignee"]
                }
            },
            {
                "name": "get_async_task_status",
                "description": "Get the current status of an asynchronously executing task",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "ID of the task to check status for"},
                        "include_history": {"type": "boolean", "default": False, "description": "Include status history"}
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "list_async_tasks",
                "description": "List all asynchronous tasks with optional filtering",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "status_filter": {"type": "array", "items": {"type": "string", "enum": ["queued", "assigned", "in_progress", "completed", "failed"]}, "description": "Filter by status values"},
                        "assignee_filter": {"type": "string", "description": "Filter by assignee"},
                        "limit": {"type": "integer", "default": 100, "description": "Maximum number of tasks to return"}
                    }
                }
            },
            {
                "name": "cancel_async_task",
                "description": "Cancel an asynchronously executing task",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "ID of the task to cancel"},
                        "reason": {"type": "string", "description": "Reason for cancellation"}
                    },
                    "required": ["task_id"]
                }
            }
        ]

    def register_handlers(self, rpc_handler: JsonRpcHandler):
        """Register async task handlers with the RPC handler"""
        # Note: tools/call routing is handled by extended_server_handlers.py
        pass

    def handle_tools_call(self, params: Dict[str, Any], request_id: str) -> Optional[Dict[str, Any]]:
        """Handle tools/call request for async task tools"""
        if params is None:
            params = {}

        tool_name = params.get("name") or params.get("tool")
        tool_arguments = params.get("arguments", {})

        # Find the tool in async task tools
        tool = None
        for t in self.tools:
            if t["name"] == tool_name:
                tool = t
                break

        if not tool:
            return None  # Return None to indicate this tool isn't handled here

        # Execute the async task tool
        return self._execute_tool(tool, tool_arguments)

    def _execute_tool(self, tool: Dict[str, Any], arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific async task tool with given arguments"""
        tool_name = tool["name"]

        if tool_name == "assign_task_async":
            return self._assign_task_async(arguments)
        elif tool_name == "get_async_task_status":
            return self._get_async_task_status(arguments)
        elif tool_name == "list_async_tasks":
            return self._list_async_tasks(arguments)
        elif tool_name == "cancel_async_task":
            return self._cancel_async_task(arguments)

        return None

    def _assign_task_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Assign a task asynchronously to an agent"""
        task_id = arguments.get("task_id", f"task_{int(time.time() * 1000)}")
        task_description = arguments.get("task_description", "")
        assignee = arguments.get("assignee", "")
        priority = arguments.get("priority", "medium")
        deadline = arguments.get("deadline")
        tool_to_invoke = arguments.get("tool_to_invoke")
        tool_arguments = arguments.get("tool_arguments")
        callback_requested = arguments.get("callback_requested", True)

        # Determine the tool to invoke on the agent
        if not tool_to_invoke:
            tool_to_invoke = self._determine_agent_tool(assignee, task_description)

        # Build tool arguments if not provided
        if not tool_arguments:
            tool_arguments = self._build_tool_arguments(assignee, tool_to_invoke, task_description, arguments)

        # Store task in local database with initial status
        if self.task_storage:
            self.task_storage.store_received_task(
                task_id=task_id,
                title=f"Async Task: {task_id}",
                description=task_description,
                assigned_to=assignee,
                priority=priority,
                deadline=deadline,
                source_server="internal",
                metadata={
                    "tool_call": "assign_task_async",
                    "tool_to_invoke": tool_to_invoke,
                    "tool_arguments": tool_arguments,
                    "callback_requested": callback_requested,
                    "async_mode": True
                },
                status="assigned"
            )

        # Get agent endpoint from registry
        agent_endpoint = None
        if self.agent_registry:
            services = self.agent_registry.list_services()
            for service in services:
                service_name = service.get("name", "").lower()
                if assignee.lower() in service_name:
                    agent_endpoint = service.get("endpoint")
                    break

        if not agent_endpoint:
            # Agent not found in registry - task is assigned but not forwarded
            return {
                "task_id": task_id,
                "status": "assigned",
                "assigned_to": assignee,
                "message": f"Task assigned to {assignee} but agent not currently available (not in registry)",
                "tracking_resource": f"it-lead://resource/task-status/{task_id}",
                "agent_available": False
            }

        # Send task notification to agent via MCP
        if self.mcp_client_factory:
            agent_client = self.mcp_client_factory(endpoint=agent_endpoint)
            if agent_client.connected:
                notification_result = agent_client.send_task_notification(
                    task_id=task_id,
                    tool=tool_to_invoke,
                    arguments=tool_arguments
                )

                if notification_result.get("success"):
                    # Update task status to 'forwarded'
                    if self.task_storage:
                        self.task_storage.store_received_task(
                            task_id=task_id,
                            title=f"Async Task: {task_id}",
                            description=task_description,
                            assigned_to=assignee,
                            priority=priority,
                            deadline=deadline,
                            source_server="internal",
                            metadata={
                                "tool_call": "assign_task_async",
                                "tool_to_invoke": tool_to_invoke,
                                "agent_endpoint": agent_endpoint,
                                "notification_sent": True,
                                "async_mode": True
                            },
                            status="forwarded"
                        )

                    return {
                        "task_id": task_id,
                        "status": "forwarded",
                        "assigned_to": assignee,
                        "tool_invoked": tool_to_invoke,
                        "agent_endpoint": agent_endpoint,
                        "message": f"Task assigned and forwarded to {assignee} asynchronously",
                        "tracking_resource": f"it-lead://resource/task-status/{task_id}",
                        "agent_available": True,
                        "notification_sent": True
                    }
                else:
                    return {
                        "task_id": task_id,
                        "status": "assigned",
                        "assigned_to": assignee,
                        "message": f"Task assigned to {assignee} but notification failed: {notification_result.get('error')}",
                        "tracking_resource": f"it-lead://resource/task-status/{task_id}",
                        "agent_available": True,
                        "notification_sent": False
                    }
            else:
                return {
                    "task_id": task_id,
                    "status": "assigned",
                    "assigned_to": assignee,
                    "message": f"Task assigned to {assignee} but could not connect to agent",
                    "tracking_resource": f"it-lead://resource/task-status/{task_id}",
                    "agent_available": True,
                    "connected": False
                }

        # Fallback: task stored but no notification sent
        return {
            "task_id": task_id,
            "status": "assigned",
            "assigned_to": assignee,
            "message": f"Task assigned to {assignee} (notification system not available)",
            "tracking_resource": f"it-lead://resource/task-status/{task_id}",
            "agent_available": agent_endpoint is not None
        }

    def _determine_agent_tool(self, agent_id: str, task_description: str) -> str:
        """Determine which tool to invoke on the agent based on agent type and task"""
        agent_lower = agent_id.lower().replace("-", "_").replace(" ", "_")
        task_lower = task_description.lower()

        # Implementation Engineer
        if "implementation" in agent_lower or "impl" in agent_lower:
            if "test" in task_lower:
                return "generate_unit_tests"
            elif "refactor" in task_lower:
                return "refactor_code"
            elif "feature" in task_lower or "implement" in task_lower:
                return "implement_feature"
            else:
                return "generate_code_from_spec"

        # Requirements Engineer
        elif "requirement" in agent_lower or "req" in agent_lower:
            if "translate" in task_lower or "business" in task_lower:
                return "translate_business_to_technical"
            elif "ambigu" in task_lower:
                return "resolve_ambiguity"
            else:
                return "analyze_requirements"

        # Code Reviewer
        elif "review" in agent_lower or "reviewer" in agent_lower:
            return "review_code"

        # QA/Test Engineer
        elif "qa" in agent_lower or "test" in agent_lower:
            return "generate_test_suite"

        # Security Engineer
        elif "security" in agent_lower:
            return "perform_security_analysis"

        # DevOps Engineer
        elif "devops" in agent_lower:
            return "orchestrate_deployments"

        # Architect
        elif "architect" in agent_lower:
            return "analyze_architecture"

        # Technical Writer
        elif "writer" in agent_lower or "documentation" in agent_lower:
            return "generate_documentation"

        # Default
        return "implement_feature"

    def _build_tool_arguments(self, agent_id: str, tool: str, task_description: str, 
                               original_args: Dict[str, Any]) -> Dict[str, Any]:
        """Build appropriate tool arguments for an agent"""
        # Common patterns for different agents
        agent_lower = agent_id.lower()

        if "implementation" in agent_lower:
            if tool == "implement_feature":
                return {
                    "feature_requirements": task_description,
                    "architectural_guidelines": "Follow project coding standards and best practices",
                    "dependencies": original_args.get("dependencies", []),
                    "performance_requirements": original_args.get("performance_requirements", [])
                }
            elif tool == "generate_code_from_spec":
                return {
                    "specifications": task_description,
                    "programming_language": original_args.get("programming_language", "python"),
                    "framework": original_args.get("framework", "")
                }
            elif tool == "generate_unit_tests":
                return {
                    "code": original_args.get("code", ""),
                    "requirements": task_description,
                    "test_framework": original_args.get("test_framework", "pytest")
                }

        elif "requirement" in agent_lower:
            if tool == "analyze_requirements":
                return {
                    "stakeholder_inputs": task_description,
                    "business_context": original_args.get("business_context", "Feature request")
                }

        elif "review" in agent_lower:
            if tool == "review_code":
                return {
                    "pull_request_id": original_args.get("pull_request_id", f"pr_{int(time.time())}"),
                    "code_diff": original_args.get("code_diff", "")
                }

        # Default fallback
        return {"description": task_description}

    def _get_async_task_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get the status of an async task"""
        task_id = arguments.get("task_id", "")
        include_history = arguments.get("include_history", False)

        if not self.task_storage:
            return {
                "error": "Task storage not available",
                "task_id": task_id
            }

        # Get task from storage
        task = None
        try:
            tasks = self.task_storage.get_all_tasks()
            for t in tasks:
                if t.get("task_id") == task_id:
                    task = t
                    break
        except Exception as e:
            return {
                "error": f"Failed to retrieve task: {str(e)}",
                "task_id": task_id
            }

        if not task:
            return {
                "error": f"Task {task_id} not found",
                "task_id": task_id
            }

        # Build status response
        status_response = {
            "task_id": task_id,
            "status": task.get("status", "unknown"),
            "assigned_to": task.get("assigned_to", "unknown"),
            "priority": task.get("priority", "medium"),
            "created_at": task.get("created_at"),
            "updated_at": task.get("updated_at"),
            "metadata": task.get("metadata", {})
        }

        if include_history:
            status_response["status_history"] = task.get("status_history", [])

        return status_response

    def _list_async_tasks(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all async tasks with optional filtering"""
        status_filter = arguments.get("status_filter", [])
        assignee_filter = arguments.get("assignee_filter")
        limit = min(arguments.get("limit", 100), 1000)

        if not self.task_storage:
            return {
                "error": "Task storage not available",
                "tasks": []
            }

        try:
            all_tasks = self.task_storage.get_all_tasks()
        except Exception as e:
            return {
                "error": f"Failed to retrieve tasks: {str(e)}",
                "tasks": []
            }

        # Apply filters
        filtered_tasks = []
        for task in all_tasks:
            # Check if it's an async task
            metadata = task.get("metadata", {})
            if not metadata.get("async_mode", False):
                continue

            # Apply status filter
            if status_filter and task.get("status") not in status_filter:
                continue

            # Apply assignee filter
            if assignee_filter and task.get("assigned_to") != assignee_filter:
                continue

            # Add to results
            filtered_tasks.append({
                "task_id": task.get("task_id"),
                "status": task.get("status"),
                "assigned_to": task.get("assigned_to"),
                "priority": task.get("priority"),
                "created_at": task.get("created_at"),
                "updated_at": task.get("updated_at")
            })

            if len(filtered_tasks) >= limit:
                break

        return {
            "tasks": filtered_tasks,
            "total_count": len(filtered_tasks),
            "limit": limit
        }

    def _cancel_async_task(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Cancel an async task"""
        task_id = arguments.get("task_id", "")
        reason = arguments.get("reason", "User requested cancellation")

        if not self.task_storage:
            return {
                "error": "Task storage not available",
                "task_id": task_id
            }

        # Find and update task
        try:
            tasks = self.task_storage.get_all_tasks()
            for task in tasks:
                if task.get("task_id") == task_id:
                    # Update task status to cancelled
                    self.task_storage.store_received_task(
                        task_id=task_id,
                        title=task.get("title", ""),
                        description=task.get("description", ""),
                        assigned_to=task.get("assigned_to", ""),
                        priority=task.get("priority", "medium"),
                        deadline=task.get("deadline"),
                        source_server="internal",
                        metadata={
                            **task.get("metadata", {}),
                            "cancellation_reason": reason
                        },
                        status="cancelled"
                    )

                    # Notify agent if task was forwarded
                    if task.get("metadata", {}).get("notification_sent"):
                        # Send cancellation notification
                        agent_endpoint = task.get("metadata", {}).get("agent_endpoint")
                        if agent_endpoint and self.mcp_client_factory:
                            agent_client = self.mcp_client_factory(endpoint=agent_endpoint)
                            if agent_client.connected:
                                agent_client.send_notification(
                                    "notifications/tasks/cancelled",
                                    {
                                        "task_id": task_id,
                                        "reason": reason
                                    }
                                )

                    return {
                        "task_id": task_id,
                        "status": "cancelled",
                        "reason": reason,
                        "message": f"Task {task_id} has been cancelled"
                    }

            return {
                "error": f"Task {task_id} not found",
                "task_id": task_id
            }

        except Exception as e:
            return {
                "error": f"Failed to cancel task: {str(e)}",
                "task_id": task_id
            }
