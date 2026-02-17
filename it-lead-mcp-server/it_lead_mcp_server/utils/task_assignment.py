"""
Task Assignment Module for IT Lead MCP Server
Handles intelligent task routing and forwarding to specialized agents
"""
import json
import time
import requests  # Use sync HTTP client to match existing server handler pattern
from typing import Dict, List, Any, Optional
from .task_routing_engine import TaskRoutingEngine, RoutingDecision
from .llm_task_planner import LLMTaskPlanner


class TaskAssignmentManager:
    """Manages task assignment and forwarding to specialized agents"""
    
    def __init__(self, llm_client=None, service_registry=None, task_storage=None):
        self.llm_client = llm_client
        self.service_registry = service_registry
        self.task_storage = task_storage
        
        # Initialize routing components
        self.routing_engine = TaskRoutingEngine(llm_client, service_registry)
        self.llm_planner = LLMTaskPlanner(llm_client, service_registry)
    
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
        
        # Step 1: Evaluate task against routing rules
        routing_context = {
            "code_diff": metadata.get("code_diff") if metadata else None,
            "document": metadata.get("document") if metadata else None,
        }
        
        routing_decision = self.routing_engine.evaluate_task(
            task_description, assignee, routing_context
        )
        
        # Step 2: Handle LLM planning if needed
        if routing_decision.requires_llm_planning:
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
            
            # Use LLM plan for assignment
            primary_agent = llm_plan.get("primary_agent")
            tool = llm_plan.get("tools", {}).get(primary_agent, "implement_feature")
            priority = llm_plan.get("priority", priority)
        else:
            primary_agent = routing_decision.assign_to
            tool = routing_decision.tool
            priority = routing_decision.priority or priority
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
            agent_endpoint = self.routing_engine.get_agent_endpoint(primary_agent)

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
                    
                    # Update task status in database
                    if self.task_storage:
                        self._update_task_status(
                            task_id, "forwarded",
                            f"Task forwarded to {primary_agent} at {agent_endpoint}",
                            {"agent_endpoint": agent_endpoint, "tool_used": tool}
                        )
                else:
                    result["status"] = "assigned_pending"
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
                timeout=30.0
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
            if tool == "implement_feature":
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
                    "target_environments": ["development"]
                }
        
        # Default fallback
        return {"description": task_description}
    
    def _update_task_status(self, task_id: str, status: str, 
                           status_reason: str, extra_metadata: Optional[Dict[str, Any]] = None):
        """Update task status in the database"""
        if not self.task_storage:
            return
        
        # Note: We would need to add an update_task_status method to TaskStorage
        # For now, this is a placeholder
        print(f"Updating task {task_id} status to {status}: {status_reason}")
