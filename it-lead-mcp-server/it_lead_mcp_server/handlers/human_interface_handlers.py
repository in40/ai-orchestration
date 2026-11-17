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
            },
            {
                "name": "answer_clarification",
                "description": "Answer clarification question(s) the pipeline asked the requestor "
                               "(task in awaiting_input). Answers are injected into re-planning.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "Task the questions belong to"},
                        "answers": {"type": "object",
                                    "description": "map of FIELD (as asked) -> answer text"},
                        "env_fields": {"type": "array", "items": {"type": "string"},
                                       "description": "answered FIELDS to inject into the "
                                                      "container env at deploy (metadata.deploy_env)"},
                        "secret_fields": {"type": "array", "items": {"type": "string"},
                                          "description": "answered FIELDS that are secrets: "
                                                         "masked in prompts, env-only"},
                        "answered_by": {"type": "string", "description": "Who answered",
                                        "default": "human_operator"}
                    },
                    "required": ["task_id", "answers"]
                }
            },
            {
                "name": "get_pending_clarifications",
                "description": "List unanswered clarification questions across tasks "
                               "(for the requestor's notification bell).",
                "inputSchema": {"type": "object", "properties": {}}
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
        elif tool_name == "answer_clarification":
            return self._answer_clarification(arguments)
        elif tool_name == "get_pending_clarifications":
            return self._get_pending_clarifications(arguments)

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

    def _answer_clarification(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Record the requestor's answers; the paused pipeline watcher picks
        them up and resumes planning."""
        task_id = arguments.get("task_id", "")
        answers = arguments.get("answers", {}) or {}
        if not self.task_storage:
            return {"success": False, "error": "task storage unavailable"}
        task = self.task_storage.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task not found: {task_id}"}
        md = task.get("metadata", {}) or {}
        if isinstance(md, str):
            try:
                md = json.loads(md)
            except Exception:
                md = {}
        cl = md.get("clarifications") or []
        norm = {str(k).strip().upper().replace(" ", "_"): str(v)
                for k, v in answers.items()}
        env_set = {str(f).strip().upper().replace(" ", "_")
                   for f in (arguments.get("env_fields") or [])}
        secret_set = {str(f).strip().upper().replace(" ", "_")
                      for f in (arguments.get("secret_fields") or [])}
        updated = 0
        for c in cl:
            if c.get("status") == "pending" and c.get("field") in norm:
                c["status"] = "answered"
                c["answer"] = norm[c["field"]]
                c["answered_at"] = time.time()
                c["answered_by"] = arguments.get("answered_by", "human_operator")
                c["in_env"] = c["field"] in env_set
                c["is_secret"] = c["field"] in secret_set
                updated += 1
        # V3: requestor-marked runtime values flow into deploy_env, which devops
        # merges into the container environment at every deploy (survives
        # contract re-planning). Secrets stay OUT of prompts and git artifacts.
        deploy_env = dict(md.get("deploy_env") or {})
        for c in cl:
            if c.get("status") == "answered" and c.get("in_env"):
                deploy_env[c["field"]] = c["answer"]
        if deploy_env:
            md["deploy_env"] = deploy_env
        md["clarifications"] = cl
        self.task_storage.update_task_status_only(
            task_id=task_id,
            status=task.get("status") or "awaiting_input",
            status_reason=f"{updated} clarification answer(s) recorded",
            metadata=md)
        if self.task_assignment_manager and updated:
            try:
                self.task_assignment_manager._log_activity(
                    task_id, "clarification_answered", agent="human_operator",
                    detail=", ".join(sorted(norm)))
            except Exception:
                pass
        pending = [c["field"] for c in cl if c.get("status") == "pending"]
        return {"success": True, "answered": updated, "still_pending": pending}

    def _get_pending_clarifications(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten pending questions across tasks for the UI bell."""
        out = []
        try:
            cursor = self.task_storage.connection.cursor()
            cursor.execute(
                "SELECT task_id, title, metadata::jsonb FROM task_registry "
                "WHERE metadata::jsonb->'clarifications' IS NOT NULL "
                "ORDER BY updated_at DESC LIMIT 200")
            rows = cursor.fetchall()
            cursor.close()
        except Exception as e:
            return {"success": False, "error": str(e), "clarifications": []}
        for tid, title, md in rows:
            if isinstance(md, str):
                try:
                    md = json.loads(md)
                except Exception:
                    continue
            for c in (md or {}).get("clarifications") or []:
                if c.get("status") == "pending":
                    out.append({"task_id": tid, "title": title,
                                "id": c.get("id"), "field": c.get("field"),
                                "question": c.get("question"), "why": c.get("why"),
                                "asked_by": c.get("asked_by"),
                                "asked_at": c.get("asked_at")})
        return {"success": True, "clarifications": out}