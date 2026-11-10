"""
Human Interface Handlers for IT Lead MCP Server
Implements human interface capabilities for software development teams
"""
import json
import time
import datetime
from typing import Dict, Any, List, Optional
from ..utils.json_rpc import JsonRpcHandler


class HumanInterfaceHandlers:
    """Handles human interface specific MCP server methods for software development teams"""

    def __init__(self, llm_client=None, agent_registry=None, task_storage=None, task_assignment_manager=None):
        self.llm_client = llm_client
        self.agent_registry = agent_registry
        self.task_storage = task_storage
        self.task_assignment_manager = task_assignment_manager
        
        # Human interface tools
        self.tools = [
            {
                "name": "escalate_to_human",
                "description": "Escalate decision to human operator",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "ID of the task requiring escalation"},
                        "reason": {"type": "string", "description": "Reason for escalation"},
                        "context": {"type": "object", "description": "Context for the decision"},
                        "options": {"type": "array", "items": {"type": "string"}, "description": "Available options for decision"}
                    },
                    "required": ["task_id", "reason", "context"]
                }
            },
            {
                "name": "request_task_rework",
                "description": "Request rework on a completed task that is not acceptable",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "ID of the completed task requiring rework"},
                        "issue_description": {"type": "string", "description": "Description of the issue or why rework is needed"},
                        "additional_comments": {"type": "string", "description": "Optional additional comments for the developer"},
                        "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"], "description": "Priority for the rework", "default": "medium"}
                    },
                    "required": ["task_id", "issue_description"]
                }
            }
        ]

        self.resources = [
            {
                "uri": "it-lead://resource/progress-report",
                "name": "Progress Report",
                "description": "Comprehensive project progress report"
            }
        ]

    def register_handlers(self, rpc_handler: JsonRpcHandler):
        """Register human interface handlers with the RPC handler"""
        # Note: Do NOT register tools/call here - the main handler in extended_server_handlers.py
        # is responsible for routing tool calls to this module. Registering tools/call here
        # would override the main handler and prevent proper task storage.

    def handle_tools_call(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle tools/call request for human interface tools"""
        if params is None:
            params = {}

        tool_name = params.get("name") or params.get("tool")
        tool_arguments = params.get("arguments", {})

        # Find the tool in human interface tools
        tool = None
        for t in self.tools:
            if t["name"] == tool_name:
                tool = t
                break

        if not tool:
            return None  # Return None to indicate this tool isn't handled here

        # Execute the human interface tool
        return self._execute_tool(tool, tool_arguments)

    def _execute_tool(self, tool: Dict[str, Any], arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific human interface tool with given arguments"""
        tool_name = tool["name"]

        if tool_name == "escalate_to_human":
            return self._escalate_to_human(arguments)
        elif tool_name == "request_task_rework":
            return self._request_task_rework(arguments)

        # For any other tools, return None to indicate this module doesn't handle them
        return None

    def _escalate_to_human(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Escalate decision to human operator"""
        task_id = arguments.get("task_id", "")
        reason = arguments.get("reason", "")
        context = arguments.get("context", {})
        options = arguments.get("options", [])
        
        # Use LLM to prepare escalation
        if self.llm_client:
            result = self._prepare_escalation_with_llm(
                {"id": task_id}, 
                context, 
                options
            )
        else:
            # Fallback implementation
            result = {
                "situation_summary": f"Task {task_id} requires human decision",
                "intervention_reason": reason,
                "decision_options": [
                    {
                        "option": opt,
                        "pros": ["Pros for this option"],
                        "cons": ["Cons for this option"],
                        "impact": "Impact of choosing this option"
                    } for opt in options
                ],
                "context": context,
                "urgency": "medium",
                "recommended_action": options[0] if options else "No options provided"
            }

        # Store escalation in task storage
        if self.task_storage:
            self.task_storage.update_task_status(
                task_id=task_id,
                status="awaiting_human_input",
                result=json.dumps(result)
            )

        return {"result": result}

    def _prepare_escalation_with_llm(self, task: dict, context: dict, options: List[str]):
        """Use LLM to prepare escalation request"""
        prompt = f"""
        You are preparing an escalation request for a human decision-maker. The AI system has encountered a situation requiring human judgment.

        TASK:
        {json.dumps(task, indent=2)}

        CONTEXT:
        {json.dumps(context, indent=2)}

        AVAILABLE OPTIONS:
        {json.dumps(options, indent=2)}

        Please prepare a clear, concise escalation request that includes:
        1. Summary of the situation
        2. Why human intervention is needed
        3. Clear presentation of available options
        4. Potential impacts of each option
        5. Relevant context and background information
        6. Urgency level

        Format as JSON:
        {{
          "situation_summary": "Brief summary of what's happening",
          "intervention_reason": "Why human decision is needed",
          "decision_options": [
            {{
              "option": "Option text",
              "pros": ["advantage1", "advantage2"],
              "cons": ["disadvantage1", "disadvantage2"],
              "impact": "What happens if chosen"
            }}
          ],
          "context": "Relevant background information",
          "urgency": "high|medium|low",
          "recommended_action": "Which option seems best based on AI analysis"
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
                            "situation_summary": "Could not parse LLM response",
                            "intervention_reason": "Error in escalation preparation",
                            "decision_options": [],
                            "context": context,
                            "urgency": "medium",
                            "recommended_action": "No recommendation due to error"
                        }
            else:
                return {
                    "situation_summary": "LLM call failed",
                    "intervention_reason": f"LLM call failed: {response.status_code}",
                    "decision_options": [],
                    "context": context,
                    "urgency": "medium",
                    "recommended_action": "No recommendation due to error"
                }
        except Exception as e:
            return {
                "situation_summary": "LLM call failed",
                "intervention_reason": f"LLM call failed: {str(e)}",
                "decision_options": [],
                "context": context,
                "urgency": "medium",
                "recommended_action": "No recommendation due to error"
            }

    def _request_task_rework(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Request rework on a completed task that is not acceptable"""
        task_id = arguments.get("task_id", "")
        issue_description = arguments.get("issue_description", "")
        additional_comments = arguments.get("additional_comments", "")
        priority = arguments.get("priority", "medium")

        # Validate task exists and is in done status
        if self.task_storage:
            task = self.task_storage.get_task(task_id)
            if not task:
                return {
                    "success": False,
                    "error": f"Task not found: {task_id}",
                    "message": "Cannot request rework for non-existent task"
                }

            current_status = task.get("status", "")
            # Allow rework for tasks that have completed (done/failed) or are in revision workflow (needs_revision/rework_in_progress)
            if current_status not in ("done", "failed", "needs_revision", "rework_in_progress"):
                return {
                    "success": False,
                    "error": f"Task is not in a state for rework: {current_status}",
                    "message": f"Can only request rework for tasks with status 'done', 'failed', 'needs_revision', or 'rework_in_progress', current status is '{current_status}'"
                }

        # Prepare rework request
        rework_request = {
            "task_id": task_id,
            "issue_description": issue_description,
            "additional_comments": additional_comments,
            "requested_by": "human_operator",
            "requested_at": datetime.now().isoformat() if hasattr(datetime, 'isoformat') else str(time.time()),
            "priority": priority,
            "status": "pending_review"
        }

        # Store rework request in task metadata
        if self.task_storage:
            try:
                import json
                task = self.task_storage.get_task(task_id)
                if task:
                    existing_meta = {}
                    metadata = task.get("metadata", {}) or {}
                    try:
                        existing_meta = json.loads(metadata) if isinstance(metadata, str) else metadata
                    except:
                        pass

                    # Add rework_request to history
                    rework_history = existing_meta.get("rework_requests", [])
                    if isinstance(rework_history, str):
                        rework_history = json.loads(rework_history)
                    rework_history.append(rework_request)

                    # Update metadata with rework request
                    existing_meta["rework_requests"] = rework_history
                    existing_meta["last_rework_requested_at"] = rework_request["requested_at"]

                    # Update task status to needs_revision
                    self.task_storage.update_task_status_only(
                        task_id=task_id,
                        status="needs_revision",
                        status_reason=f"Rework requested: {issue_description[:100]}...",
                        metadata=existing_meta
                    )
            except Exception as e:
                print(f"Error storing rework request: {e}")
                import traceback
                traceback.print_exc()

        # Trigger rework workflow if task_assignment_manager is available
        if self.task_assignment_manager and task:
            issue_desc_for_workflow = issue_description if issue_description else "Issues found in deployed code"
            self.task_assignment_manager._trigger_rework_workflow(
                task_id=task_id,
                issue_description=issue_desc_for_workflow,
                additional_comments=additional_comments if additional_comments else "",
                priority=priority if priority else "medium"
            )

        return {
            "success": True,
            "message": f"Rework requested for task {task_id}",
            "rework_request": rework_request
        }