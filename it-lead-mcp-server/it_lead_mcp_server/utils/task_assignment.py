"""
Task Assignment Module for IT Lead MCP Server - FIXED VERSION
Handles intelligent task routing and forwarding to specialized agents
Uses background threads for async task polling

ARCHITECTURE NOTE:
This module uses the MCP Registry Client to discover agent endpoints via MCP protocol.
It communicates with the central MCP Registry Server (port 3031) via HTTP POST to /mcp,
following proper MCP architecture - NOT direct database access.
"""
import json
import time
import requests  # Use sync HTTP client to match existing server handler pattern
import threading  # Added for background polling
from typing import Dict, List, Any, Optional
from .task_routing_engine import TaskRoutingEngine, RoutingDecision
from .llm_task_planner import LLMTaskPlanner
from .mcp_registry_client import McpRegistryClient  # NEW: MCP protocol-based registry client


class TaskAssignmentManager:
    """Manages task assignment and forwarding to specialized agents"""

    def __init__(self, llm_client=None, service_registry=None, task_storage=None, mcp_registry_endpoint: Optional[str] = None):
        self.llm_client = llm_client
        self.service_registry = service_registry  # Deprecated: kept for backward compatibility
        
        # NEW: Initialize MCP Registry Client for proper MCP protocol-based agent discovery
        if mcp_registry_endpoint:
            self.mcp_registry_client = McpRegistryClient(mcp_registry_endpoint)
            print(f"✅ MCP Registry Client initialized: {mcp_registry_endpoint}")
        else:
            # Default to local MCP Registry Server on port 3031
            self.mcp_registry_client = McpRegistryClient("http://127.0.0.1:3031/mcp")
            print("✅ MCP Registry Client initialized (default: http://127.0.0.1:3031/mcp)")
        self.task_storage = task_storage

        # Initialize routing components with MCP Registry Client
        # Pass mcp_registry_client to TaskRoutingEngine for proper agent discovery via MCP protocol
        self.routing_engine = TaskRoutingEngine(
            llm_client=llm_client,
            service_registry=service_registry,  # Deprecated, kept for backward compatibility
            mcp_registry_client=self.mcp_registry_client  # NEW: MCP protocol-based discovery
        )
        # Pass MCP Registry Client to LLM Planner for dynamic agent/tool discovery
        self.llm_planner = LLMTaskPlanner(
            llm_client=llm_client,
            agent_registry=service_registry,  # Deprecated, kept for backward compatibility
            mcp_registry_client=self.mcp_registry_client  # NEW: Dynamic discovery via MCP protocol
        )

        # Initialize result router
        self._init_result_router()

        # Update agent endpoints from registry if available
        if service_registry:
            try:
                services = service_registry.list_services()
                for service in services:
                    service_name = service.get("name", "").lower()
                    endpoint = service.get("endpoint")
                    if "implementation" in service_name and endpoint:
                        self.routing_engine.agent_endpoints["implementation-engineer"] = endpoint
                    elif "requirement" in service_name and endpoint:
                        self.routing_engine.agent_endpoints["requirements-engineer"] = endpoint
            except Exception as e:
                print(f"Error updating agent endpoints from registry: {e}")

    def _init_result_router(self):
        """Initialize result router for storing agent results"""
        try:
            from .result_router import get_result_router
            self.result_router = get_result_router()
            print("✅ Result router initialized")
        except ImportError as e:
            print(f"⚠️ Result router not available: {e}")
            self.result_router = None
        except Exception as e:
            print(f"⚠️ Error initializing result router: {e}")

    def _poll_async_task_result(self, agent_endpoint: str, task_id: str, max_retries: int = 120) -> Optional[Dict[str, Any]]:
        """
        Poll the agent's tasks/result endpoint to get async task result.

        Args:
            agent_endpoint: Agent's MCP endpoint
            task_id: Async task ID from the agent's response
            max_retries: Maximum number of poll attempts (increased to 120 for 60s+ timeouts)

        Returns:
            Result dict with git_url or None if polling failed
        """
        import time

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    agent_endpoint,
                    json={
                        "jsonrpc": "2.0",
                        "id": f"poll-{task_id}",
                        "method": "tools/call",
                        "params": {
                            "name": "tasks/result",
                            "arguments": {"taskId": task_id}
                        }
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    if "result" in result and isinstance(result["result"], dict):
                        result_data = result["result"]
                        # Check if result contains git_url (from git_push_llm_response)
                        if result_data.get("git_url"):
                            print(f"✅ Async task result retrieved: {result_data['git_url']}")
                            return result_data
                        # Check for error
                        if result_data.get("error"):
                            error_msg = result_data.get("error", "")
                            # Only return None if it's a real error, not "working" status
                            if "not completed" in error_msg.lower() or "working" in error_msg.lower():
                                print(f"⏳ Task still {error_msg}, continuing to poll...")
                            else:
                                print(f"❌ Async task error: {error_msg}")
                                return None
                        # Task still working, continue polling
                        task_status = result_data.get("status", "unknown")
                        if task_status == "working" and attempt < max_retries - 1:
                            wait_time = min(2 + (attempt * 2), 10)  # Exponential backoff, max 10s
                            print(f"⏳ Task still {task_status}, waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                            time.sleep(wait_time)
            except Exception as e:
                print(f"⚠️ Poll attempt {attempt + 1} failed: {e}")

            # Wait before next poll
            if attempt < max_retries - 1:
                time.sleep(2)

        print(f"⚠️ Failed to retrieve async task result after {max_retries} attempts")
        return None

    def assign_and_forward_task(self, task_id: str, task_description: str,
                                      assignee: Optional[str] = None,
                                      priority: str = "medium",
                                      deadline: Optional[str] = None,
                                      metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Assign a task and forward it to the appropriate agent

        Args:
            task_id: Unique task identifier
            task_description: Task description
            assignee: Explicit assignee (optional)
            priority: Task priority
            deadline: Task deadline
            metadata: Additional metadata

        Returns:
            Assignment result with status and details
        """
        result = {
            "task_id": task_id,
            "status": "unknown",
            "message": "",
            "assigned_to": None,
            "forwarded_to_agent": False,
            "agent_response": None,
            "requires_llm_planning": False,
            "llm_plan": None
        }

        # Step 1: Determine which agent should handle the task
        effective_assignee = assignee
        if assignee and assignee.lower() in ('it-lead', 'it lead', 'itlead'):
            print(f"DEBUG: Task assigned to IT Lead - using routing rules to determine specialized agent")
            effective_assignee = None

        # Step 1: Evaluate task against routing rules
        routing_context = {
            "code_diff": metadata.get("code_diff") if metadata else None,
            "document": metadata.get("document") if metadata else None,
        }

        routing_decision = self.routing_engine.evaluate_task(
            task_description, effective_assignee, routing_context
        )
        print(f"DEBUG: routing_decision: assign_to={routing_decision.assign_to}, tool={routing_decision.tool}, confidence={routing_decision.confidence}, requires_llm_planning={routing_decision.requires_llm_planning}")

        # Set primary_agent based on routing decision
        primary_agent = routing_decision.assign_to
        print(f"DEBUG: effective_assignee={effective_assignee}, primary_agent={primary_agent}")

        # Step 2: Handle LLM planning if needed
        if routing_decision.requires_llm_planning:
            print(f"🔍 LLM planning REQUIRED for task {task_id}")
            print(f"   Reason: {routing_decision.llm_reason}")
            print(f"   Confidence: {routing_decision.confidence}")

            llm_plan = self.llm_planner.plan_task_assignment(
                task_description,
                {
                    "llm_reason": routing_decision.llm_reason,
                    "failure_reasons": routing_decision.metadata.get("failure_reasons", []),
                    "matched_rule": routing_decision.metadata.get("matched_rule"),
                    "confidence": routing_decision.confidence,
                    "matched_rules": routing_decision.metadata.get("matched_rules", []),
                    "conflicting_assignees": routing_decision.metadata.get("conflicting_assignees", [])
                }
            )

            result["requires_llm_planning"] = True
            result["llm_plan"] = llm_plan

            print(f"✅ LLM planning completed for task {task_id}")
            print(f"   LLM plan keys: {list(llm_plan.keys())}")
            print(f"   LLM plan content: {json.dumps(llm_plan, indent=2)}")

            # Try to get primary_agent (with fallback to recommended_agent)
            primary_agent = llm_plan.get("primary_agent") or llm_plan.get("recommended_agent")
            print(f"   primary_agent from LLM: {primary_agent}")

            # Use vibe_code_async for async LLM processing
            tool = llm_plan.get("tools", {}).get(primary_agent, "vibe_code_async")
            print(f"   tool: {tool}")
            priority = llm_plan.get("priority", priority)
            print(f"   priority: {priority}")
            
            # Extract detected language from LLM plan
            detected_language = llm_plan.get("language")
            if detected_language:
                print(f"   Detected language: {detected_language}")
                # Add to metadata for passing to implementation engineer
                if metadata is None:
                    metadata = {}
                metadata["language"] = detected_language
        else:
            print(f"✅ LLM planning NOT required for task {task_id}")
            primary_agent = routing_decision.assign_to
            tool = routing_decision.tool
            priority = routing_decision.priority or priority
            print(f"DEBUG: routing_decision: assign_to={primary_agent}, tool={tool}, priority={priority}")
            llm_plan = None

        # Step 3: Store task in database with initial status
        if self.task_storage:
            status_history_entry = {
                "status": "received",
                "timestamp": time.time(),
                "reason": f"Task assigned via assign_task tool, routed to {primary_agent}"
            }

            self.task_storage.store_received_task(
                task_id=task_id,
                title=f"Task: {task_id}",
                description=task_description,
                submitter="api_user",
                submitter_type="api",
                transport_channel="streamable-http",
                assigned_to=primary_agent if primary_agent else "unassigned",
                priority=priority,
                deadline=deadline if deadline else None,
                source_server="internal",
                metadata={
                    "tool_call": "assign_task",
                    "routing_decision": {
                        "matched_rule_id": routing_decision.matched_rule_id,
                        "confidence": routing_decision.confidence,
                        "requires_llm_planning": routing_decision.requires_llm_planning
                    },
                    "llm_plan": llm_plan
                },
                status="received",
                status_reason=f"Task received, routing to {primary_agent}"
            )

        # Step 4: Forward task to agent if agent is available
        if primary_agent:
            # Validate that primary_agent is a known agent
            known_agents = ["implementation-engineer", "requirements-engineer", "code-reviewer",
                           "qa-test-engineer", "security-engineer", "devops-engineer", "it-lead"]

            # Normalize primary_agent for comparison
            normalized_agent = primary_agent.lower().replace(" ", "-").replace("_", "-")

            if normalized_agent not in known_agents:
                print(f"⚠️  Warning: Unknown agent '{primary_agent}' - falling back to implementation-engineer")
                primary_agent = "implementation-engineer"
                tool = "vibe_code_async"
                agent_endpoint = self.routing_engine.get_agent_endpoint(primary_agent)
            else:
                agent_endpoint = self.routing_engine.get_agent_endpoint(primary_agent)
                print(f"DEBUG: agent_endpoint for {primary_agent}: {agent_endpoint}")

            # Initialize forward_result for later use
            forward_result = {"success": False, "error": "No agent endpoint available"}

            if agent_endpoint:
                # Forward task to agent (sync call)
                forward_result = self._forward_task_to_agent(
                    task_id, task_description, primary_agent, tool,
                    priority, deadline, metadata
                )

                if forward_result.get("success"):
                    result["forwarded_to_agent"] = True
                    result["agent_response"] = forward_result.get("response")
                    result["status"] = "forwarded"
                    result["message"] = f"Task assigned and forwarded to {primary_agent}"

                    # Update task status to in_progress
                    if self.task_storage:
                        status_value = "in_progress"
                        self._update_task_status(
                            task_id, status_value,
                            f"Task forwarded to {primary_agent} at {agent_endpoint}",
                            {"agent_endpoint": agent_endpoint, "tool_used": tool}
                        )
                        print(f"✅ Task {task_id} status updated to {status_value}")

                    # Handle async task polling in background thread
                    agent_response = forward_result.get("response", {})
                    result_data = agent_response.get("result", {})

                    async_task_id = None
                    if isinstance(result_data, dict):
                        async_task_id = result_data.get("taskId")
                        if async_task_id and result_data.get("status") == "submitted":
                            print(f"⏳ Async task submitted: {async_task_id}, starting background polling...")
                            
                            def background_poller():
                                """Background thread to poll for async task result"""
                                print(f"🔄 Background thread started for task {task_id}, polling for {async_task_id}...")
                                async_result = self._poll_async_task_result(agent_endpoint, async_task_id, max_retries=120)
                                if async_result and async_result.get("git_url"):
                                    git_url = async_result["git_url"]
                                    print(f"✅ Background thread found Git URL for task {task_id}: {git_url}")
                                    # Update task with Git URL
                                    self.task_storage.update_task_with_git_url(task_id, git_url)
                                elif async_result:
                                    print(f"⚠️ Background thread completed but no Git URL found for task {task_id}")
                                else:
                                    print(f"❌ Background thread failed to get result for task {task_id}")
                            
                            threading.Thread(target=background_poller, daemon=True).start()
                            print(f"✅ Background polling thread spawned for task {task_id}")
                        else:
                            # Sync task or error, handle inline
                            print(f"⚠️ Task {task_id} is not async or already completed, handling inline")
                            if self.task_storage:
                                storage_ref = {
                                    "storage_type": "inline",
                                    "result": str(result_data)[:500] if result_data else "No result"
                                }
                                self.task_storage.update_task_result_reference(
                                    task_id=task_id,
                                    storage_ref=storage_ref,
                                    metadata={
                                        "routing_decision": {
                                            "matched_rule_id": routing_decision.matched_rule_id,
                                            "confidence": routing_decision.confidence,
                                            "requires_llm_planning": routing_decision.requires_llm_planning
                                        }
                                    }
                                )
                                status_value = "done"
                                self._update_task_status(
                                    task_id, status_value,
                                    "Task completed (sync processing)",
                                    {"storage_type": "inline"}
                                )
                                print(f"✅ Sync task {task_id} marked as done")

                else:
                    result["status"] = "assigned_pending"
                    result["assigned_to"] = primary_agent
                    result["message"] = f"Task assigned to {primary_agent} but forwarding failed: {forward_result.get('error')}"

                    if self.task_storage:
                        self._update_task_status(
                            task_id, "assigned_pending",
                            f"Agent forwarding failed: {forward_result.get('error')}"
                        )
            else:
                result["status"] = "assigned"
                result["assigned_to"] = primary_agent
                result["message"] = f"Task assigned to {primary_agent} (agent not currently available for forwarding)"
                print(f"DEBUG: Task {task_id} not forwarded - forward_result.success={forward_result.get('success')}, forward_result.error={forward_result.get('error')}")

                if self.task_storage:
                    self._update_task_status(
                        task_id, "assigned",
                        f"Task assigned to {primary_agent} (agent offline)"
                    )
        else:
            result["status"] = "pending_routing"
            result["message"] = "Task could not be routed - requires human intervention"

            if self.task_storage:
                self._update_task_status(
                    task_id, "pending_routing",
                    "Automatic routing failed, requires human review"
                )

        return result

    def _forward_task_to_agent(self, task_id: str, task_description: str,
                                     agent_id: str, tool: str,
                                     priority: str, deadline: Optional[str],
                                     metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Forward a task to a specific agent via MCP (sync HTTP)"""

        agent_endpoint = self.routing_engine.get_agent_endpoint(agent_id)
        print(f"DEBUG: _forward_task_to_agent: agent_id={agent_id}, tool={tool}, endpoint={agent_endpoint}")

        if not agent_endpoint:
            return {"success": False, "error": f"Agent {agent_id} endpoint not found"}

        # Build tool arguments based on agent and tool
        tool_arguments = self._build_tool_arguments(agent_id, tool, task_description, metadata)

        try:
            # Use sync requests to match existing server handler pattern
            response = requests.post(
                agent_endpoint,
                json={
                    "jsonrpc": "2.0",
                    "id": f"forward-{task_id}",
                    "method": "tools/call",
                    "params": {
                        "name": tool,
                        "arguments": tool_arguments
                    }
                },
                timeout=120.0  # Increased from 30 to 120 seconds for LLM processing time
            )

            if response.status_code == 200:
                response_data = response.json()
                return {
                    "success": True,
                    "response": response_data,
                    "agent_id": agent_id,
                    "tool": tool
                }
            else:
                return {
                    "success": False,
                    "error": f"Agent returned status {response.status_code}: {response.text}"
                }

        except requests.RequestException as e:
            return {"success": False, "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

    def _build_tool_arguments(self, agent_id: str, tool: str, task_description: str,
                             metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build appropriate tool arguments for an agent"""

        # Common arguments for all tools
        base_args = {}

        # Agent-specific argument building
        if agent_id == "implementation-engineer":
            # Use vibe_code_async for async processing with LLM
            if tool == "vibe_code_async":
                return {
                    "task_description": task_description,
                    "language": metadata.get("language", "python") if metadata else "python",
                    "vibe_level": metadata.get("vibe_level", 5) if metadata else 5,
                    "style_guide": metadata.get("style_guide", "") if metadata else ""
                }
            elif tool == "implement_feature" or tool == "generate_code_from_spec":
                return {
                    "feature_requirements": task_description,
                    "architectural_guidelines": "Follow project coding standards and best practices",
                    "dependencies": metadata.get("dependencies", []) if metadata else [],
                    "performance_requirements": metadata.get("performance_requirements", []) if metadata else []
                }
            elif tool == "generate_code_from_spec":
                return {
                    "specifications": task_description,
                    "programming_language": metadata.get("programming_language", "python") if metadata else "python",
                    "framework": metadata.get("framework", "") if metadata else "",
                    "coding_standards": "PEP 8" if metadata.get("programming_language", "").lower() == "python" else "Standard"
                }
            elif tool == "generate_unit_tests":
                return {
                    "code": metadata.get("code", "") if metadata else "",
                    "requirements": task_description,
                    "test_framework": metadata.get("test_framework", "pytest") if metadata else "pytest"
                }

        elif agent_id == "requirements-engineer":
            if tool == "analyze_requirements":
                return {
                    "stakeholder_inputs": task_description,
                    "business_context": metadata.get("business_context", "New feature request") if metadata else "New feature request"
                }

        elif agent_id == "code-reviewer":
            if tool == "review_code":
                return {
                    "pull_request_id": metadata.get("pull_request_id", task_id) if metadata else task_id,
                    "code_diff": metadata.get("code_diff", "") if metadata else ""
                }

        elif agent_id == "qa-test-engineer":
            if tool == "generate_test_suite":
                return {
                    "requirements": task_description,
                    "test_types": ["unit", "integration"],
                    "test_framework": metadata.get("test_framework", "pytest") if metadata else "pytest"
                }

        elif agent_id == "security-engineer":
            if tool == "perform_security_analysis":
                return {
                    "code": metadata.get("code", "") if metadata else "",
                    "application_type": metadata.get("application_type", "web") if metadata else "web",
                    "analysis_type": ["sast"]
                }

        elif agent_id == "devops-engineer":
            if tool == "orchestrate_deployments":
                return {
                    "application_artifacts": metadata.get("artifacts", "") if metadata else "",
                    "deployment_target": metadata.get("deployment_target", "production") if metadata else "production",
                    "infrastructure_as_code": metadata.get("infrastructure_as_code", False) if metadata else False
                }

        # Default
        return {"description": task_description}

    def _update_task_status(self, task_id: str, status: str, status_reason: str,
                          metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update task status with history tracking"""
        try:
            if not self.task_storage:
                return False

            # Get current task to merge metadata
            task = self.task_storage.get_task(task_id)
            if not task:
                print(f"⚠️ Task {task_id} not found for status update")
                return False

            # Merge metadata
            merged_metadata = task.get("metadata", {}).copy() if task.get("metadata") else {}
            if metadata:
                merged_metadata.update(metadata)

            # Update status history
            status_history_entry = {
                "status": status,
                "timestamp": time.time(),
                "reason": status_reason
            }
            status_history = task.get("status_history", [])
            if isinstance(status_history, str):
                import json as json_module
                try:
                    status_history = json_module.loads(status_history)
                except:
                    status_history = []
            status_history.append(status_history_entry)

            # Update task status only (don't add duplicate history entry)
            self.task_storage.update_task_status_only(
                task_id=task_id,
                status=status,
                status_reason=status_reason,
                metadata=merged_metadata
            )

            print(f"✅ Task {task_id} status updated to {status}")
            return True
        except Exception as e:
            print(f"❌ Error updating task status: {e}")
            import traceback
            traceback.print_exc()
            return False
