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

        # CRITICAL: Force cache refresh BEFORE initializing routing engine
        # This ensures routing_engine gets fresh service data, not stale cache
        try:
            self.mcp_registry_client.list_services(use_cache=False)
            print("✅ MCP Registry cache refreshed with fresh service data")
        except Exception as e:
            print(f"⚠️  Could not refresh MCP Registry cache: {e}")

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
                    elif "devops" in service_name and endpoint:
                        self.routing_engine.agent_endpoints["devops-engineer"] = endpoint
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

    def _poll_async_task_result(self, agent_endpoint: str, task_id: str, max_retries: int = 7200) -> Optional[Dict[str, Any]]:
        """
        Poll the agent's tasks/result endpoint to get async task result.

        Args:
            agent_endpoint: Agent's MCP endpoint
            task_id: Async task ID from the agent's response
            max_retries: Maximum number of poll attempts (default: 7200 = 4 hours at 2s intervals)

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
        print(f"🔥🔥🔥 assign_and_forward_task CALLED for {task_id} 🔥🔥🔥")
        print(f"   metadata received: {metadata}")
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

            try:
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
                print(f"✅ LLM planner returned, llm_plan type: {type(llm_plan)}")
            except Exception as e:
                print(f"❌ LLM planner ERROR: {e}")
                import traceback
                traceback.print_exc()
                # Fallback plan - check deployment flag FIRST
                llm_plan = {"workflow_sequence": ["requirements-engineer", "implementation-engineer"], "tools": {"primary_agent": "vibe_code_async"}}

                # Check if deployment is required even in fallback
                deploy_flag = False
                if metadata and metadata.get("deploy_after_implementation", False):
                    deploy_flag = True
                elif metadata and metadata.get("original_arguments", {}).get("metadata", {}).get("deploy_after_implementation", False):
                    deploy_flag = True
                elif metadata and metadata.get("original_arguments", {}).get("original_arguments", {}).get("metadata", {}).get("deploy_after_implementation", False):
                    deploy_flag = True

                if deploy_flag:
                    llm_plan["workflow_sequence"].append("devops-engineer")
                    llm_plan["tools"]["devops-engineer"] = "deploy_web_application"
                    print(f"🚀 Fallback plan: Added devops-engineer for deployment workflow")

            result["requires_llm_planning"] = True
            result["llm_plan"] = llm_plan

            print(f"✅ LLM planning completed for task {task_id}")
            print(f"   LLM plan keys: {list(llm_plan.keys())}")
            try:
                print(f"   LLM plan content: {json.dumps(llm_plan, indent=2)}")
            except Exception as e:
                print(f"   LLM plan content (str): {str(llm_plan)[:500]}...")
                print(f"   JSON dump error: {e}")

            # Try to get primary_agent (with fallback to recommended_agent)
            primary_agent = llm_plan.get("primary_agent") or llm_plan.get("recommended_agent")
            print(f"   primary_agent from LLM: {primary_agent}")

            # Extract detected language from LLM plan
            detected_language = llm_plan.get("language")
            if detected_language:
                print(f"   Detected language: {detected_language}")
                # Add to metadata for passing to implementation engineer
                if metadata is None:
                    metadata = {}
                metadata["language"] = detected_language

            # CHECK FOR DEPLOYMENT FLAG: If deploy_after_implementation is set, force add devops-engineer
            # This MUST run BEFORE tool extraction to ensure vibe_code_async is used
            # Check in multiple locations - the flag can be deeply nested!
            print(f"🔍 DEBUG: About to check for deployment flag...")
            print(f"   metadata type: {type(metadata)}, metadata is None: {metadata is None}")
            print(f"   llm_plan type: {type(llm_plan)}, llm_plan is None: {llm_plan is None}")
            print(f"🔍 DEBUG: Checking for deployment flag in metadata...")
            print(f"   metadata keys: {list(metadata.keys()) if metadata else 'None'}")
            deploy_flag = False
            
            # Level 1: In original_arguments.original_arguments.metadata (Web UI sends it here)
            # This is the MOST COMMON case - check FIRST!
            # Structure: metadata -> original_arguments -> original_arguments -> metadata -> deploy_after_implementation
            if metadata and metadata.get("original_arguments"):
                orig_args = metadata.get("original_arguments", {})
                print(f"   original_arguments keys: {list(orig_args.keys())}")
                
                # Go one level deeper: original_arguments.original_arguments
                inner_args = orig_args.get("original_arguments", {})
                print(f"   inner original_arguments keys: {list(inner_args.keys()) if inner_args else 'None'}")
                
                # Check in inner original_arguments.metadata
                if inner_args.get("metadata", {}).get("deploy_after_implementation", False):
                    deploy_flag = True
                    print(f"   ✅ Found deploy_after_implementation in original_arguments.original_arguments.metadata")
                elif inner_args.get("deploy_after_implementation", False):
                    deploy_flag = True
                    print(f"   ✅ Found deploy_after_implementation in original_arguments.original_arguments directly")

                # Level 2.5: Check for THREE levels of nesting (Web UI double-wraps)
                # Structure: metadata -> original_arguments -> original_arguments -> original_arguments -> metadata -> deploy_after_implementation
                elif inner_args.get("original_arguments", {}).get("metadata", {}).get("deploy_after_implementation", False):
                    deploy_flag = True
                    print(f"   ✅ Found deploy_after_implementation in original_arguments.original_arguments.original_arguments.metadata")
                elif inner_args.get("original_arguments", {}).get("original_arguments", {}).get("metadata", {}).get("deploy_after_implementation", False):
                    deploy_flag = True
                    print(f"   ✅ Found deploy_after_implementation in original_arguments.original_arguments.original_arguments.original_arguments.metadata")

                # Level 2: In original_arguments.metadata (fallback - one level less nesting)
                elif orig_args.get("metadata", {}).get("deploy_after_implementation", False):
                    deploy_flag = True
                    print(f"   ✅ Found deploy_after_implementation in original_arguments.metadata")
                elif orig_args.get("deploy_after_implementation", False):
                    deploy_flag = True
                    print(f"   ✅ Found deploy_after_implementation in original_arguments directly")
            
            # Level 3: Direct in metadata (fallback - rare case)
            if not deploy_flag and metadata and metadata.get("deploy_after_implementation", False):
                deploy_flag = True
                print(f"   ✅ Found deploy_after_implementation in metadata directly")

            print(f"   deploy_flag = {deploy_flag}")
            print(f"🔍 DEBUG: Deployment flag check completed, deploy_flag={deploy_flag}")

            if deploy_flag:
                print(f"🚀 DEPLOYMENT FLAG DETECTED: deploy_after_implementation=True")
                workflow_sequence = llm_plan.get("workflow_sequence", [])
                # Use correct agent name: devops-engineer (not devops-release-engineer)
                if "devops-engineer" not in workflow_sequence and "devops-release-engineer" not in workflow_sequence:
                    workflow_sequence.append("devops-engineer")
                    llm_plan["workflow_sequence"] = workflow_sequence
                    # Ensure devops has the right tool
                    if "tools" not in llm_plan:
                        llm_plan["tools"] = {}
                    llm_plan["tools"]["devops-engineer"] = "deploy_web_application"
                    print(f"🔧 Added devops-engineer to workflow: {workflow_sequence}")
                else:
                    print(f"✅ DevOps already in workflow")

                # ALSO: Ensure implementation-engineer uses vibe_code_async for git storage
                # This MUST change recommended_tool BEFORE tool extraction below
                if "tools" not in llm_plan:
                    llm_plan["tools"] = {}
                if llm_plan.get("recommended_tool") == "vibe_code":
                    llm_plan["recommended_tool"] = "vibe_code_async"
                    print(f"🔧 Changed recommended_tool to vibe_code_async for git storage")
                llm_plan["tools"]["implementation-engineer"] = "vibe_code_async"

            # Get tool from LLM plan - try multiple formats
            # Format 1: Direct recommended_tool field
            # Format 2: tools dict keyed by agent name
            # Fallback: vibe_code_async
            tool = llm_plan.get("recommended_tool") or \
                   llm_plan.get("tools", {}).get(primary_agent, "vibe_code_async")
            
            # CRITICAL FIX: If deploy_flag is set, FORCE use vibe_code_async for implementation-engineer
            # This ensures code is stored in git for DevOps deployment
            if deploy_flag and primary_agent == "implementation-engineer":
                tool = "vibe_code_async"
                print(f"🔧 FORCED tool to vibe_code_async for deployment workflow")
            
            # CRITICAL FIX: Handle sync tasks with deployment workflow
            if deploy_flag and primary_agent == "implementation-engineer":
                self._handle_sync_implementation_with_deployment_workflow(task_id)
            
            print(f"   tool: {tool}")
            priority = llm_plan.get("priority", priority) if llm_plan else priority
            print(f"   priority: {priority}")
        else:
            # No deployment flag - standard sync path
            print(f"✅ LLM planning NOT required for task {task_id}")
            primary_agent = routing_decision.assign_to
            tool = routing_decision.tool
            priority = routing_decision.priority or priority
            print(f"DEBUG: routing_decision: assign_to={primary_agent}, tool={tool}, priority={priority}")
            
            # OPTION 3: Post-processing check for deployment keywords even in rule-based routing
            # This ensures devops-engineer is added to workflow even when LLM planning is skipped
            print(f"🔍 POST-PROCESSING: Checking for deployment keywords in rule-based routing...")
            deployment_keywords = [
                "deploy", "deployment", "publish", "make accessible", "run as website",
                "host online", "make it live", "container", "docker", "production"
            ]
            
            needs_deployment = any(keyword in task_description.lower() for keyword in deployment_keywords)
            
            # Also check for deploy_after_implementation flag in metadata
            deploy_flag = False
            print(f"🔍 Checking deploy_after_implementation flag...")
            print(f"   metadata keys: {list(metadata.keys()) if metadata else 'None'}")
            print(f"   metadata.deploy_after_implementation: {metadata.get('deploy_after_implementation') if metadata else 'N/A'}")
            
            if metadata and metadata.get("deploy_after_implementation", False):
                deploy_flag = True
                print(f"   ✅ Found deploy_after_implementation in metadata directly")
            elif metadata and metadata.get("original_arguments"):
                orig_args = metadata.get("original_arguments", {})
                print(f"   original_arguments keys: {list(orig_args.keys())}")
                print(f"   original_arguments.metadata.deploy_after_implementation: {orig_args.get('metadata', {}).get('deploy_after_implementation')}")
                print(f"   original_arguments.original_arguments: {orig_args.get('original_arguments')}")
                if orig_args.get("metadata", {}).get("deploy_after_implementation", False):
                    deploy_flag = True
                    print(f"   ✅ Found deploy_after_implementation in original_arguments.metadata")
                elif orig_args.get("original_arguments", {}).get("metadata", {}).get("deploy_after_implementation", False):
                    deploy_flag = True
                    print(f"   ✅ Found deploy_after_implementation in original_arguments.original_arguments.metadata")
                elif orig_args.get("original_arguments", {}).get("original_arguments", {}).get("metadata", {}).get("deploy_after_implementation", False):
                    deploy_flag = True
                    print(f"   ✅ Found deploy_after_implementation in original_arguments.original_arguments.original_arguments.metadata")
                elif orig_args.get("original_arguments", {}).get("original_arguments", {}).get("metadata", {}).get("original_arguments", {}).get("metadata", {}).get("deploy_after_implementation", False):
                    deploy_flag = True
                    print(f"   ✅ Found deploy_after_implementation in original_arguments.original_arguments.metadata.original_arguments.metadata")
                else:
                    # Debug: show full structure
                    inner = orig_args.get("original_arguments", {})
                    print(f"   DEBUG: inner keys: {list(inner.keys()) if inner else 'None'}")
                    if inner:
                        inner_meta = inner.get("metadata", {})
                        print(f"   DEBUG: inner.metadata: {inner_meta}")
                        print(f"   DEBUG: inner.metadata.deploy_after_implementation: {inner_meta.get('deploy_after_implementation')}")
                        # Check deeper nesting
                        deeper = inner_meta.get("original_arguments", {})
                        if deeper:
                            deeper_meta = deeper.get("original_arguments", {})
                            if deeper_meta:
                                deepest_meta = deeper_meta.get("metadata", {})
                                print(f"   DEBUG: deepest metadata: {deepest_meta}")
                                print(f"   DEBUG: deepest metadata.deploy_after_implementation: {deepest_meta.get('deploy_after_implementation')}")
                                if deepest_meta.get("deploy_after_implementation", False):
                                    deploy_flag = True
                                    print(f"   ✅ Found deploy_after_implementation at deepest level")
            
            if needs_deployment or deploy_flag:
                print(f"🚀 DEPLOYMENT DETECTED in rule-based routing!")
                print(f"   needs_deployment={needs_deployment}, deploy_flag={deploy_flag}")
                print(f"   Task will include devops-engineer in workflow")
                
                # Create a minimal llm_plan structure to support workflow sequence
                llm_plan = {
                    "workflow_sequence": [primary_agent, "devops-engineer"],
                    "tools": {
                        primary_agent: tool,
                        "devops-engineer": "deploy_web_application"
                    },
                    "primary_agent": primary_agent,
                    "reasoning": "Rule-based routing with auto-detected deployment requirement"
                }
                
                # Change tool to async version for git storage
                if tool == "vibe_code":
                    tool = "vibe_code_async"
                    print(f"🔧 Changed tool to vibe_code_async for git storage")
                
                print(f"📋 Updated workflow_sequence: {llm_plan['workflow_sequence']}")
            else:
                print(f"ℹ️  No deployment keywords detected, using simple routing")
                llm_plan = None

            # Debug: Print execution flow marker
            print(f"DEBUG: After deployment detection, before Step 3 task storage")

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

            print(f"DEBUG: After Step 3 task storage, before Step 4 forwarding")

        # Step 4: Forward task to agent if agent is available
        print(f"DEBUG: Step 4 - Checking primary_agent: {primary_agent}")
        if primary_agent:
            print(f"DEBUG: Step 4 - Entering forwarding logic for {primary_agent}")
            # Get agent endpoint from the dynamic agent list (NOT hardcoded)
            # First, try to get the agent list from routing_engine's mcp_registry_client
            agent_endpoint = None
            
            if hasattr(self.routing_engine, 'mcp_registry_client') and self.routing_engine.mcp_registry_client:
                # Get the dynamic agent list
                agents_list = self.routing_engine.mcp_registry_client.discover_all_agents_with_tools(use_cache=True)
                
                # Find the agent by matching agent_id or name
                # Normalize primary_agent for comparison: "Requirements Engineer" -> "requirements-engineer"
                primary_agent_normalized = primary_agent.lower().replace(" ", "-").replace("_", "-")

                for agent in agents_list:
                    agent_id = agent.get("agent_id", agent.get("name", ""))
                    agent_name = agent.get("name", "")
                    endpoint = agent.get("endpoint")

                    # Normalize agent_id for comparison (in case it's not already normalized)
                    agent_id_normalized = agent_id.lower().replace(" ", "-").replace("_", "-") if agent_id else ""

                    # Match by normalized agent_id or by normalized name
                    if (agent_id and (agent_id_normalized == primary_agent_normalized or agent_id.lower() == primary_agent.lower())) or \
                       (agent_name and agent_name.lower().replace(" ", "-").replace("_", "-") == primary_agent_normalized):
                        agent_endpoint = endpoint
                        print(f"✅ Found endpoint for {primary_agent}: {agent_endpoint}")
                        break
            
            # Fallback to routing_engine.get_agent_endpoint() if dynamic lookup failed
            if not agent_endpoint:
                agent_endpoint = self.routing_engine.get_agent_endpoint(primary_agent)
                print(f"⚠️  Using fallback endpoint for {primary_agent}: {agent_endpoint}")
            
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
                                """Background thread to poll for async task result and handle workflow sequence"""
                                print(f"🔄 Background thread started for task {task_id}, polling for {async_task_id}...")
                                # Increased polling to 360 retries (12 minutes) to handle longer-running tasks
                                async_result = self._poll_async_task_result(agent_endpoint, async_task_id, max_retries=360)
                                
                                if async_result and async_result.get("git_url"):
                                    git_url = async_result["git_url"]
                                    print(f"✅ Background thread found Git URL for task {task_id}: {git_url}")
                                    # Update task with Git URL
                                    self.task_storage.update_task_with_git_url(task_id, git_url)
                                    
                                    # Check if there's a workflow sequence and forward to next agent
                                    self._handle_workflow_sequence(task_id, task_description, primary_agent, llm_plan, git_url)
                                    
                                elif async_result:
                                    print(f"⚠️ Background thread completed but no Git URL found for task {task_id}")
                                    # Still check workflow sequence even without git_url
                                    self._handle_workflow_sequence(task_id, task_description, primary_agent, llm_plan, None)
                                else:
                                    print(f"❌ Background thread failed to get result for task {task_id}")

                            threading.Thread(target=background_poller, daemon=True).start()
                            print(f"✅ Background polling thread spawned for task {task_id}")
                        else:
                            # Sync task or error, handle inline
                            print(f"⚠️ Task {task_id} is not async or already completed, handling inline")
                            print(f"   forward_result keys: {list(forward_result.keys())}")
                            print(f"   forward_result.success: {forward_result.get('success')}")
                            print(f"   forward_result.error: {forward_result.get('error')}")
                            
                            # Extract result_data from response
                            agent_response = forward_result.get("response", {})
                            result_data = agent_response.get("result", {})
                            
                            # ✅ CRITICAL FIX: Check for workflow sequence even if agent returned error or unexpected response
                            workflow_sequence = llm_plan.get("workflow_sequence", []) if llm_plan else []
                            
                            if workflow_sequence and len(workflow_sequence) > 1:
                                print(f"🔄 Task {task_id} has workflow sequence: {workflow_sequence}")
                                print(f"   Checking if we should forward to next agent...")
                                
                                # Extract git_url from result_data if available
                                sync_git_url = None
                                if isinstance(result_data, dict):
                                    sync_git_url = result_data.get("git_url")
                                
                                # Check if agent returned success OR if we have a git_url
                                if forward_result.get("success") or sync_git_url:
                                    print(f"   ✅ Agent completed successfully, git_url={sync_git_url}")
                                    # Store result if we have one
                                    if result_data and self.task_storage:
                                        storage_ref = {
                                            "storage_type": "inline" if not sync_git_url else "git",
                                            "result": str(result_data)[:500] if result_data else "No result",
                                            "git_url": sync_git_url
                                        }
                                        # ✅ CRITICAL FIX: Don't update status to 'done' for workflow sequences!
                                        # Keep status as 'in_progress' until ALL agents in workflow complete
                                        self.task_storage.update_task_result_reference(
                                            task_id=task_id,
                                            storage_ref=storage_ref,
                                            metadata={
                                                "routing_decision": {
                                                    "matched_rule_id": routing_decision.matched_rule_id,
                                                    "confidence": routing_decision.confidence,
                                                    "requires_llm_planning": routing_decision.requires_llm_planning
                                                }
                                            },
                                            update_status=False  # Don't set to 'done' - workflow still in progress!
                                        )

                                    # ✅ Forward to next agent in workflow
                                    self._handle_workflow_sequence(task_id, task_description, primary_agent, llm_plan, sync_git_url)
                                else:
                                    # Agent failed but we have workflow sequence - log and mark task for manual review
                                    error_msg = forward_result.get("error", "Unknown error")
                                    print(f"   ❌ Agent failed but workflow sequence exists: {error_msg}")
                                    print(f"   ⚠️  Task requires manual intervention")
                                    
                                    if self.task_storage:
                                        self.task_storage.update_task_status(
                                            task_id, "failed",
                                            f"Agent {primary_agent} failed in workflow: {error_msg}. Manual review required."
                                        )
                            else:
                                # No workflow sequence, handle as simple sync task
                                if result_data and self.task_storage:
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
                                    print(f"✅ Sync task {task_id} result stored")
                                
                                # Mark as done
                                status_value = "done"
                                self._update_task_status(
                                    task_id, status_value,
                                    "Task completed (sync processing)",
                                    {"storage_type": "inline"}
                                )
                                print(f"✅ Sync task {task_id} marked as done")

                else:
                    result["status"] = "assigned"
                    result["assigned_to"] = primary_agent
                    result["message"] = f"Task assigned to {primary_agent} but forwarding failed: {forward_result.get('error')}"

                    if self.task_storage:
                        self._update_task_status(
                            task_id, "assigned",
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

    def _handle_sync_implementation_with_deployment_workflow(self, task_id: str):
        """
        Handle sync Implementation results when deployment is required.

        When Implementation processes synchronously (no async_task_id), the code
        is returned inline. This method extracts it, stores it in git, and forwards
        to DevOps for deployment.

        Args:
            task_id: Task identifier
        """
        print(f"🔧 Handling sync implementation with deployment workflow for {task_id}")

        try:
            # Get task from storage
            task = self.task_storage.get_task(task_id)
            if not task:
                print(f"❌ Task {task_id} not found")
                return

            # Get LLM plan with workflow sequence
            llm_plan = task.get("metadata", {}).get("llm_plan")
            if not llm_plan:
                print(f"⚠️ No LLM plan found for task {task_id}")
                return

            workflow_sequence = llm_plan.get("workflow_sequence", [])
            if "devops-engineer" not in workflow_sequence:
                print(f"⚠️ DevOps not in workflow sequence for {task_id}")
                return

            # Get inline result from task
            result_reference = task.get("result_reference", {})
            if not result_reference:
                print(f"⚠️ No result_reference found for task {task_id}")
                return

            storage_type = result_reference.get("storage_type", "")
            if storage_type != "inline":
                print(f"⚠️ Result already stored in git (storage_type={storage_type})")
                return

            # Extract code from inline result
            result_data = result_reference.get("result", "")
            if not result_data:
                print(f"⚠️ No inline result content found")
                return

            # Try to extract code from JSON string
            try:
                if isinstance(result_data, str):
                    # Try to parse as JSON
                    import json
                    try:
                        parsed = json.loads(result_data)
                        if isinstance(parsed, dict):
                            result_data = parsed.get("code") or parsed.get("result", result_data)
                    except:
                        pass  # Keep as string
            except:
                pass

            if not result_data or len(str(result_data)) < 10:
                print(f"⚠️ Code content too short or invalid: {str(result_data)[:100]}")
                return

            print(f"📝 Extracted {len(str(result_data))} bytes of code from inline result")

            # Store code in git
            import subprocess
            import uuid
            import os

            result_uuid = str(uuid.uuid4())
            git_workdir = "/tmp/mcp-vibe-coding-git/repo"

            # Ensure git workdir exists
            if not os.path.exists(git_workdir):
                os.makedirs(git_workdir, exist_ok=True)
                subprocess.run(["git", "init"], cwd=git_workdir, check=True, capture_output=True)
                subprocess.run(["git", "config", "user.email", "mcp@local"], cwd=git_workdir, check=True, capture_output=True)
                subprocess.run(["git", "config", "user.name", "MCP Agent"], cwd=git_workdir, check=True, capture_output=True)

            # Get git repo URL
            git_repo_url = os.environ.get("MCP_GIT_REPO_URL", "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git")

            # Clone/pull repo
            if not os.path.exists(os.path.join(git_workdir, ".git")):
                subprocess.run(["git", "clone", git_repo_url, "."], cwd=git_workdir, check=True, capture_output=True, timeout=30)
            subprocess.run(["git", "pull"], cwd=git_workdir, check=True, capture_output=True, timeout=30)

            # Create result file
            result_dir = os.path.join(git_workdir, "results", result_uuid)
            os.makedirs(result_dir, exist_ok=True)
            result_file = os.path.join(result_dir, "result.py")
            with open(result_file, "w") as f:
                f.write(str(result_data))

            # Commit and push
            subprocess.run(["git", "add", "."], cwd=git_workdir, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", f"Result for {task_id} (sync extraction)"], cwd=git_workdir, check=True, capture_output=True)
            subprocess.run(["git", "push", git_repo_url, "main"], cwd=git_workdir, check=True, capture_output=True, timeout=30)

            # Construct git_url
            git_url = f"{git_repo_url}/tree/main/results/{result_uuid}/result.py"
            print(f"✅ Code stored in git: {git_url}")

            # Update task with git_url
            self.task_storage.update_task_with_git_url(task_id, git_url, None)

            # Forward to DevOps
            print(f"🔄 Forwarding to DevOps for deployment...")
            task_description = task.get("description", "")
            self._handle_workflow_sequence(task_id, task_description, "implementation-engineer", llm_plan, git_url)

        except Exception as e:
            print(f"❌ Error handling sync implementation: {e}")
            import traceback
            traceback.print_exc()

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
        tool_arguments = self._build_tool_arguments(agent_id, tool, task_description, metadata, task_id)

        # Retry configuration for failed forwarding
        max_retries = 5
        base_delay = 5  # seconds

        for attempt in range(max_retries):
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
                    if attempt == max_retries - 1:
                        return {
                            "success": False,
                            "error": f"Agent returned status {response.status_code}: {response.text}"
                        }
                    # Retry on non-200 status
                    print(f"⚠️ Attempt {attempt + 1}/{max_retries} failed with status {response.status_code}, retrying in {base_delay}s...")
                    time.sleep(base_delay * (2 ** attempt))

            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    return {"success": False, "error": f"Request failed: {str(e)}"}
                # Retry on timeout/connection errors
                print(f"⚠️ Attempt {attempt + 1}/{max_retries} failed: {e}, retrying in {base_delay}s...")
                time.sleep(base_delay * (2 ** attempt))
            except Exception as e:
                if attempt == max_retries - 1:
                    return {"success": False, "error": f"Unexpected error: {str(e)}"}
                print(f"⚠️ Attempt {attempt + 1}/{max_retries} failed: {e}, retrying in {base_delay}s...")
                time.sleep(base_delay * (2 ** attempt))

        return {"success": False, "error": f"Max retries ({max_retries}) exceeded"}

    def _build_tool_arguments(self, agent_id: str, tool: str, task_description: str,
                             metadata: Optional[Dict[str, Any]], task_id: Optional[str] = None) -> Dict[str, Any]:
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
            elif tool == "deploy_web_application":
                # deploy_web_application needs task_id and git_url
                return {
                    "task_id": metadata.get("task_id", task_id) if metadata else task_id,
                    "git_url": metadata.get("git_url", "") if metadata else ""
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

    def _handle_workflow_sequence(self, task_id: str, task_description: str, current_agent: str, llm_plan: Optional[Dict[str, Any]], git_url: Optional[str]):
        """
        Handle workflow sequence - forward task to next agent in sequence if applicable.

        Args:
            task_id: Task identifier
            task_description: Original task description
            current_agent: Agent that just completed
            llm_plan: LLM planning result with workflow_sequence
            git_url: Git URL from completed agent (if any)
        """
        if not llm_plan:
            print(f"⚠️  No LLM plan available for workflow sequence check")
            return

        # Get workflow sequence from LLM plan
        workflow_sequence = llm_plan.get("workflow_sequence") or llm_plan.get("sequence", [])

        # AUTO-ADD DEVOPS: If task mentions deployment OR has deploy_after_implementation flag
        task_lower = task_description.lower()
        deployment_keywords = ["deploy", "deployment", "accessible via url", "publish", "run as website", "make it available"]
        current_agent_normalized = current_agent.lower().replace("_", "-").replace(" ", "-")

        # Check for deploy_after_implementation flag in task metadata (deeply nested!)
        deploy_flag_enabled = False
        try:
            task_obj = self.task_storage.get_task(task_id)
            if task_obj:
                metadata = task_obj.get("metadata", {}) or {}
                # Check multiple locations for the flag
                if metadata.get("deploy_after_implementation", False):
                    deploy_flag_enabled = True
                elif metadata.get("original_arguments", {}).get("metadata", {}).get("deploy_after_implementation", False):
                    deploy_flag_enabled = True
                elif metadata.get("original_arguments", {}).get("original_arguments", {}).get("metadata", {}).get("deploy_after_implementation", False):
                    deploy_flag_enabled = True
                if deploy_flag_enabled:
                    print(f"✅ Deployment flag enabled for task {task_id} (from UI checkbox)")
        except Exception as e:
            print(f"⚠️  Could not check deployment flag: {e}")

        if (any(kw in task_lower for kw in deployment_keywords) or deploy_flag_enabled) and "implementation-engineer" in current_agent_normalized:
            if not workflow_sequence or workflow_sequence[-1] != "devops-engineer":
                # Add devops-engineer to the end of workflow (use correct agent name!)
                if not workflow_sequence:
                    workflow_sequence = ["devops-engineer"]
                else:
                    workflow_sequence.append("devops-engineer")
                print(f"🔧 Auto-added devops-engineer to workflow (task mentions deployment or UI checkbox enabled)")
                # Update llm_plan with new workflow
                llm_plan["workflow_sequence"] = workflow_sequence
                if "tools" not in llm_plan:
                    llm_plan["tools"] = {}
                llm_plan["tools"]["devops-engineer"] = "deploy_web_application"

        if not workflow_sequence or len(workflow_sequence) < 2:
            # No sequence or only one agent - task is complete
            print(f"✅ Task {task_id} workflow complete (no sequence or single agent)")
            return
        
        # Find current agent position in sequence
        current_index = -1
        for i, agent in enumerate(workflow_sequence):
            agent_normalized = agent.lower().replace(" ", "-").replace("_", "-")
            current_normalized = current_agent.lower().replace(" ", "-").replace("_", "-")
            if agent_normalized == current_normalized:
                current_index = i
                break
        
        if current_index < 0:
            print(f"⚠️  Current agent {current_agent} not found in workflow sequence: {workflow_sequence}")
            return
        
        # Check if there's a next agent
        if current_index >= len(workflow_sequence) - 1:
            # Current agent is the last in sequence - task is complete
            print(f"✅ Task {task_id} workflow complete (agent {current_agent} is last in sequence)")
            return
        
        # Get next agent in sequence
        next_agent = workflow_sequence[current_index + 1]
        print(f"🔄 Forwarding task {task_id} to next agent in sequence: {next_agent}")

        # ✅ CRITICAL: Refresh agent endpoints from registry BEFORE looking up next agent
        # This prevents race conditions where IT Lead started before other agents registered
        print(f"   Refreshing agent endpoints from registry before forwarding...")
        try:
            if hasattr(self, 'mcp_registry_client') and self.mcp_registry_client:
                services = self.mcp_registry_client.list_services(use_cache=False)
                print(f"   📋 Refreshed: {len(services)} services from registry")
                
                # Update routing engine with fresh endpoints
                for service in services:
                    service_name = service.get("name", "").lower()
                    endpoint = service.get("endpoint")
                    
                    if "registry" in service_name and "mcp registry" in service_name:
                        continue
                    
                    if "devops" in service_name and endpoint:
                        old = self.routing_engine.agent_endpoints.get("devops-engineer")
                        self.routing_engine.agent_endpoints["devops-engineer"] = endpoint
                        if old != endpoint:
                            print(f"   ✅ Updated devops-engineer: {endpoint} (was: {old})")
                    elif "implementation" in service_name and endpoint:
                        self.routing_engine.agent_endpoints["implementation-engineer"] = endpoint
                    elif "requirement" in service_name and endpoint:
                        self.routing_engine.agent_endpoints["requirements-engineer"] = endpoint
        except Exception as e:
            print(f"   ⚠️  Could not refresh endpoints: {e}")

        # Get next agent's endpoint (now with refreshed data)
        next_agent_endpoint = self.routing_engine.get_agent_endpoint(next_agent)
        if not next_agent_endpoint:
            print(f"❌ Could not find endpoint for next agent: {next_agent}")
            print(f"   Available endpoints: {self.routing_engine.agent_endpoints}")
            return
        
        # Get tool for next agent from LLM plan
        tools = llm_plan.get("tools", {})
        next_tool = tools.get(next_agent, "vibe_code_async")

        # Forward task to next agent
        print(f"   Forwarding to {next_agent} at {next_agent_endpoint} with tool {next_tool}")

        # Build context from previous agent's result
        context_for_next = {
            "previous_agent": current_agent,
            "previous_git_url": git_url,
            "workflow_position": f"{current_index + 2}/{len(workflow_sequence)}"
        }

        # Special handling for devops-release-engineer - pass git_url and result path
        next_agent_normalized = next_agent.lower().replace("_", "-")
        if "devops" in next_agent_normalized:
            # Extract UUID from git_url for devops
            import re
            uuid_match = re.search(r'/results/([a-f0-9-]+)/', git_url) if git_url else None
            if uuid_match:
                context_for_next["result_uuid"] = uuid_match.group(1)
                context_for_next["git_url"] = git_url
                # Use deploy_web_application tool for devops
                next_tool = "deploy_web_application"
                print(f"   DevOps deployment: UUID={context_for_next['result_uuid']}, GitURL={git_url}")

        # Forward to next agent
        forward_result = self._forward_task_to_agent(
            task_id, task_description, next_agent, next_tool,
            "medium", None, context_for_next
        )
        
        if forward_result.get("success"):
            print(f"✅ Task {task_id} forwarded to {next_agent} in workflow sequence")

            # Update assigned_to to next agent
            try:
                import json
                cursor = self.task_storage.connection.cursor()
                if self.task_storage.use_sqlite:
                    cursor.execute(
                        "UPDATE task_registry SET assigned_to = ? WHERE task_id = ?",
                        (next_agent, task_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE task_registry SET assigned_to = %s WHERE task_id = %s",
                        (next_agent, task_id)
                    )
                self.task_storage.connection.commit()
                cursor.close()
                print(f"✅ Task {task_id} assigned_to updated to {next_agent}")
            except Exception as e:
                print(f"⚠️  Could not update assigned_to: {e}")

            # Update status_history to show workflow handoff
            try:
                task = self.task_storage.get_task(task_id)
                if task:
                    status_history = task.get("status_history", [])
                    if isinstance(status_history, str):
                        import json as json_module
                        try:
                            status_history = json_module.loads(status_history)
                        except:
                            status_history = []

                    status_history_entry = {
                        "status": "in_progress",
                        "timestamp": time.time(),
                        "reason": f"Task forwarded from {current_agent} to {next_agent} (step {current_index + 2}/{len(workflow_sequence)} in workflow)"
                    }
                    status_history.append(status_history_entry)

                    cursor = self.task_storage.connection.cursor()
                    if self.task_storage.use_sqlite:
                        cursor.execute(
                            "UPDATE task_registry SET status_history = ? WHERE task_id = ?",
                            (json.dumps(status_history), task_id)
                        )
                    else:
                        cursor.execute(
                            "UPDATE task_registry SET status_history = %s WHERE task_id = %s",
                            (json.dumps(status_history), task_id)
                        )
                    self.task_storage.connection.commit()
                    cursor.close()
                    print(f"✅ Task {task_id} status_history updated with workflow handoff")
            except Exception as e:
                print(f"⚠️  Could not update status_history: {e}")
            
            agent_response = forward_result.get("response", {})
            result_data = agent_response.get("result", {})

            # Check if task is async (has taskId) or sync (completed inline)
            async_task_id = result_data.get("taskId") if isinstance(result_data, dict) else None

            if async_task_id and result_data.get("status") == "submitted":
                print(f"⏳ Async task submitted to {next_agent}: {async_task_id}, starting background polling...", flush=True)

                def workflow_poller():
                    """Background thread to poll for async task result in workflow"""
                    import sys
                    import traceback
                    # Log to file for debugging
                    try:
                        with open("/tmp/poller_debug.log", "a") as f:
                            f.write(f"[{time.time()}] Poller started for task {task_id}, async_task_id={async_task_id}\n")
                    except:
                        pass
                    
                    print(f"🔄 Workflow poller started for task {task_id}, polling for {async_task_id}...", flush=True)
                    sys.stdout.flush()
                    
                    print(f"🔍 Starting to poll async task result...", flush=True)
                    # Increased polling to 360 retries (12 minutes) to handle longer-running tasks
                    async_result = self._poll_async_task_result(next_agent_endpoint, async_task_id, max_retries=360)
                    
                    # Log result to file
                    try:
                        with open("/tmp/poller_debug.log", "a") as f:
                            f.write(f"[{time.time()}] Poller result: async_result type={type(async_result)}, has_git_url={bool(async_result and async_result.get('git_url'))}\n")
                            if async_result:
                                f.write(f"[{time.time()}] async_result keys: {list(async_result.keys()) if isinstance(async_result, dict) else 'N/A'}\n")
                    except:
                        pass
                    
                    print(f"📬 Poller returned: async_result type={type(async_result)}, has_git_url={bool(async_result and async_result.get('git_url'))}", flush=True)

                    if async_result and async_result.get("git_url"):
                        git_url = async_result["git_url"]
                        deployment_url = async_result.get("deployment_url")
                        print(f"✅ Workflow poller found Git URL for task {task_id}: {git_url}", flush=True)
                        
                        # Log to file
                        try:
                            with open("/tmp/poller_debug.log", "a") as f:
                                f.write(f"[{time.time()}] Found git_url: {git_url}\n")
                        except:
                            pass
                        
                        # Update task with Git URL and mark as done
                        self.task_storage.update_task_with_git_url(task_id, git_url, deployment_url)
                        msg = f"✅ Task {task_id} completed in workflow"
                        if deployment_url:
                            msg += f", deployment: {deployment_url}"
                        print(msg, flush=True)

                        # Check if there's a next agent in workflow BEFORE marking as done
                        # CRITICAL FIX: Only mark task as "done" when ALL agents have completed
                        should_mark_done = True  # Default to marking done unless we find a next agent

                        print(f"🔍 Checking for next agent in workflow...", flush=True)
                        if llm_plan:
                            updated_workflow = llm_plan.get("workflow_sequence", [])

                            # CRITICAL FIX APPLIED: Handle sync tasks with deployment workflow
                            # Check if deployment is required from the llm_plan metadata
                            deploy_flag = llm_plan.get("deploy_after_implementation", False) if llm_plan else False
                            print(f"   Checking critical conditions: deploy_flag={deploy_flag}, async_task_id={async_task_id}")
                            
                            # If deployment required but Implementation processed synchronously (no async_task_id)
                            implementation_agent = "implementation-engineer"
                            next_agent_normalized = next_agent.lower().replace("_", "-").replace(" ", "-") if next_agent else ""
                            is_implementation_step = "implementation" in next_agent_normalized
                            needs_devops_deployment = deploy_flag and is_implementation_step
                            
                            print(f"   Critical conditions met: needs_devops_deployment={needs_devops_deployment}")
                            
                            # Manually handle sync Implementation results when deployment required
                            if needs_devops_deployment:
                                self._handle_sync_implementation_with_deployment_workflow(task_id)
                            
                            # CRITICAL FIX: Recalculate current_index based on next_agent
                            actual_current_index = -1
                            for i, agent in enumerate(updated_workflow):
                                agent_normalized = agent.lower().replace(" ", "-").replace("_", "-")
                                if agent_normalized == next_agent_normalized:
                                    actual_current_index = i
                                    break

                            # Use actual_current_index if found, otherwise fall back to captured value
                            effective_index = actual_current_index if actual_current_index >= 0 else current_index

                            print(f"   Workflow: {updated_workflow}, actual_current_index: {actual_current_index}, effective_index: {effective_index}, len-1: {len(updated_workflow) - 1}", flush=True)
                            if effective_index < len(updated_workflow) - 1:
                                # There's another agent after this one - DO NOT mark as done yet!
                                should_mark_done = False
                                print(f"🔄 Workflow poller: next agent exists after {next_agent}, keeping task in_progress", flush=True)
                                print(f"   effective_index={effective_index}, workflow_length={len(updated_workflow)}, workflow={updated_workflow}", flush=True)

                                # Log to file
                                try:
                                    with open("/tmp/poller_debug.log", "a") as f:
                                        f.write(f"[{time.time()}] Calling _handle_workflow_sequence for next agent\n")
                                except:
                                    pass

                                self._handle_workflow_sequence(task_id, task_description, next_agent, llm_plan, git_url)
                                print(f"✅ _handle_workflow_sequence called successfully", flush=True)
                            else:
                                print(f"⚠️ No more agents in workflow (current_index={current_index}, len={len(updated_workflow)})", flush=True)
                        else:
                            print(f"⚠️ llm_plan is None, cannot check for next agent", flush=True)

                        # Only mark task as done if there's no next agent
                        if should_mark_done:
                            print(f"✅ Task {task_id} workflow complete, marking as done", flush=True)
                            try:
                                import json

                                # CRITICAL FIX: Calculate effective_index BEFORE using it
                                # This must happen before status_history update
                                updated_workflow_for_index = llm_plan.get("workflow_sequence", []) if llm_plan else []
                                actual_current_index_for_status = -1
                                for i, agent in enumerate(updated_workflow_for_index):
                                    agent_normalized = agent.lower().replace(" ", "-").replace("_", "-")
                                    next_agent_normalized = next_agent.lower().replace(" ", "-").replace("_", "-")
                                    if agent_normalized == next_agent_normalized:
                                        actual_current_index_for_status = i
                                        break
                                effective_index_for_status = actual_current_index_for_status if actual_current_index_for_status >= 0 else current_index

                                task = self.task_storage.get_task(task_id)
                                if task:
                                    status_history = task.get("status_history", [])
                                    if isinstance(status_history, str):
                                        import json as json_module
                                        try:
                                            status_history = json_module.loads(status_history)
                                        except:
                                            status_history = []

                                    status_history_entry = {
                                        "status": "done",
                                        "timestamp": time.time(),
                                        "reason": f"Task completed by {next_agent} (step {effective_index_for_status + 2}/{len(updated_workflow_for_index)} in workflow)"
                                    }
                                    status_history.append(status_history_entry)

                                    cursor = self.task_storage.connection.cursor()
                                    if self.task_storage.use_sqlite:
                                        cursor.execute(
                                            "UPDATE task_registry SET status = ?, status_history = ? WHERE task_id = ?",
                                            ('done', json.dumps(status_history), task_id)
                                        )
                                    else:
                                        cursor.execute(
                                            "UPDATE task_registry SET status = %s, status_history = %s WHERE task_id = %s",
                                            ('done', json.dumps(status_history), task_id)
                                        )
                                    self.task_storage.connection.commit()
                                    cursor.close()
                                    print(f"✅ Task {task_id} marked as done in workflow poller", flush=True)
                            except Exception as e:
                                print(f"⚠️  Could not update status_history in workflow poller: {e}", flush=True)
                                import traceback
                                traceback.print_exc()
                    elif async_result:
                        print(f"⚠️ Workflow poller completed but no Git URL for task {task_id}", flush=True)

                import threading
                threading.Thread(target=workflow_poller, daemon=True).start()
                print(f"✅ Workflow polling thread spawned for task {task_id}")
            else:
                # Sync task - handle inline
                print(f"⚠️ Task {task_id} is not async or already completed, handling inline")
                git_url = None
                deployment_url = None

                if isinstance(result_data, dict):
                    git_url = result_data.get("git_url")
                    deployment_url = result_data.get("deployment_url")
                    
                    # SPECIAL CASE: DevOps returns deployment_url directly
                    # But we should NOT overwrite git_url with deployment_url!
                    # The git_url should come from the task's existing metadata
                    if deployment_url and not git_url:
                        # DevOps completed - get git_url from existing task metadata
                        task_obj = self.task_storage.get_task(task_id)
                        if task_obj:
                            metadata = task_obj.get("metadata", {})
                            git_url = metadata.get("git_url")
                        print(f"🚀 DevOps sync task completed with deployment_url: {deployment_url}, git_url: {git_url}")
                    
                    if git_url:
                        print(f"✅ Sync task {task_id} completed with git_url: {git_url}")
                        if deployment_url:
                            print(f"🚀 Deployment URL: {deployment_url}")
                        self.task_storage.update_task_with_git_url(task_id, git_url, deployment_url)
                    elif deployment_url:
                        # Only deployment_url, no git_url - still save it
                        print(f"🚀 DevOps task completed with deployment_url only: {deployment_url}")
                        self.task_storage.update_task_with_git_url(task_id, None, deployment_url)
                    else:
                        print(f"⚠️ Sync task {task_id} completed but no git_url or deployment_url")
                        # Check if DevOps is in workflow - if so, we need to store code in git first
                        if workflow_sequence and "devops-engineer" in workflow_sequence:
                            print(f"🔧 DevOps in workflow but no git_url - extracting code from inline result")
                        # Extract code from result_data if available
                        code_content = None
                        language = "python"
                        if isinstance(result_data, dict):
                            code_content = result_data.get("code") or result_data.get("result", "")
                            language = result_data.get("language", "python")
                        
                        if code_content:
                            # Store code in git manually
                            print(f"📝 Storing inline code to git for DevOps deployment")
                            try:
                                import subprocess
                                import uuid
                                import os
                                
                                # Generate UUID for this result
                                result_uuid = str(uuid.uuid4())
                                git_workdir = f"/tmp/mcp-vibe-coding-git/repo"
                                
                                # Ensure git workdir exists
                                if not os.path.exists(git_workdir):
                                    os.makedirs(git_workdir, exist_ok=True)
                                    subprocess.run(["git", "init"], cwd=git_workdir, check=True, capture_output=True)
                                    subprocess.run(["git", "config", "user.email", "mcp@local"], cwd=git_workdir, check=True, capture_output=True)
                                    subprocess.run(["git", "config", "user.name", "MCP Agent"], cwd=git_workdir, check=True, capture_output=True)
                                
                                # Get the git_url from metadata or use default
                                task_obj = self.task_storage.get_task(task_id)
                                metadata = task_obj.get("metadata", {}) if task_obj else {}
                                original_args = metadata.get("original_arguments", {})
                                inner_metadata = original_args.get("original_arguments", {}).get("metadata", {})
                                deploy_flag = inner_metadata.get("deploy_after_implementation", False)
                                
                                # Use the configured git repo URL
                                git_repo_url = os.environ.get("MCP_GIT_REPO_URL", "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git")
                                
                                # Clone/pull repo
                                if not os.path.exists(os.path.join(git_workdir, ".git")):
                                    subprocess.run(["git", "pull", git_repo_url, "main"], cwd=git_workdir, check=True, capture_output=True, timeout=30)
                                else:
                                    subprocess.run(["git", "pull"], cwd=git_workdir, check=True, capture_output=True, timeout=30)
                                
                                # Create result file
                                result_dir = os.path.join(git_workdir, "results", result_uuid)
                                os.makedirs(result_dir, exist_ok=True)
                                result_file = os.path.join(result_dir, f"result.{language if language != 'python' else 'py'}")
                                with open(result_file, "w") as f:
                                    f.write(code_content)
                                
                                # Commit and push
                                subprocess.run(["git", "add", "."], cwd=git_workdir, check=True, capture_output=True)
                                subprocess.run(["git", "commit", "-m", f"Result for {task_id}"], cwd=git_workdir, check=True, capture_output=True)
                                subprocess.run(["git", "push", git_repo_url, "main"], cwd=git_workdir, check=True, capture_output=True, timeout=30)
                                
                                # Construct git_url
                                git_url = f"{git_repo_url}/tree/main/results/{result_uuid}/result.{language if language != 'python' else 'py'}"
                                print(f"✅ Code stored in git: {git_url}")
                                
                                # Update task with git_url
                                self.task_storage.update_task_with_git_url(task_id, git_url, None)
                                
                            except Exception as e:
                                print(f"❌ Failed to store inline code to git: {e}")
                                import traceback
                                traceback.print_exc()

                # Update status history for workflow completion
                if self.task_storage:
                    task = self.task_storage.get_task(task_id)
                    if task:
                        metadata = task.get("metadata", {})
                        status_history = task.get("status_history", [])
                        if isinstance(status_history, str):
                            import json as json_module
                            try:
                                status_history = json_module.loads(status_history)
                            except:
                                status_history = []

                        status_history_entry = {
                            "status": "done",
                            "timestamp": time.time(),
                            "reason": f"Task completed by {next_agent} (step {current_index + 2}/{len(workflow_sequence)} in workflow)"
                        }
                        status_history.append(status_history_entry)

                        try:
                            import json
                            cursor = self.task_storage.connection.cursor()
                            if self.task_storage.use_sqlite:
                                cursor.execute(
                                    "UPDATE task_registry SET status = ?, status_history = ? WHERE task_id = ?",
                                    ('done', json.dumps(status_history), task_id)
                                )
                            else:
                                cursor.execute(
                                    "UPDATE task_registry SET status = %s, status_history = %s WHERE task_id = %s",
                                    ('done', json.dumps(status_history), task_id)
                                )
                            self.task_storage.connection.commit()
                            cursor.close()
                            print(f"✅ Task {task_id} marked as done in workflow")
                        except Exception as e:
                            print(f"⚠️  Could not update status: {e}")
        else:
            print(f"❌ Failed to forward task {task_id} to {next_agent}: {forward_result.get('error')}")
