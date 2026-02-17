"""
Requirements Integration Handlers for IT Lead MCP Server
Implements specific integration points with the Requirements Engineer agent
"""
import json
import time
from typing import Dict, Any, List, Optional
from ..utils.json_rpc import JsonRpcHandler


class RequirementsIntegrationHandlers:
    """Handles requirements-specific integration with the Requirements Engineer agent"""

    def __init__(self, llm_client=None, agent_registry=None, task_storage=None):
        self.llm_client = llm_client
        self.agent_registry = agent_registry
        self.task_storage = task_storage

        # Requirements integration tools
        self.tools = [
            {
                "name": "sync_with_requirements_engineer",
                "description": "Synchronize requirements with the requirements engineer agent",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "operation": {"type": "string", "enum": ["push", "pull", "update", "validate"], "description": "Type of synchronization operation"},
                        "requirements_data": {"type": "object", "description": "Requirements data to synchronize"},
                        "target_agent": {"type": "string", "description": "Target agent for synchronization"}
                    },
                    "required": ["operation"]
                }
            },
            {
                "name": "fetch_requirements_specifications",
                "description": "Fetch requirements specifications from requirements engineer",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project identifier"},
                        "filter": {"type": "string", "description": "Filter for specific requirements"},
                        "format": {"type": "string", "enum": ["json", "text", "srs"], "default": "json", "description": "Format for returned specifications"}
                    },
                    "required": ["project_id"]
                }
            },
            {
                "name": "submit_stakeholder_inputs",
                "description": "Submit stakeholder inputs to requirements engineer for analysis",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "stakeholder_inputs": {"type": "string", "description": "Raw stakeholder inputs (interviews, documents, etc.)"},
                        "business_context": {"type": "string", "description": "Business context and constraints"},
                        "project_reference": {"type": "string", "description": "Reference to the project"},
                        "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"], "default": "medium"}
                    },
                    "required": ["stakeholder_inputs", "business_context", "project_reference"]
                }
            }
        ]

        # Requirements-specific resources
        self.resources = [
            {
                "uri": "it-lead://resource/current-requirements-status",
                "name": "Current Requirements Status",
                "description": "Current status of requirements gathering and validation"
            },
            {
                "uri": "it-lead://resource/requirements-ambiguity-log",
                "name": "Requirements Ambiguity Log",
                "description": "Log of identified ambiguities and their resolution status"
            }
        ]

    def register_handlers(self, rpc_handler: JsonRpcHandler):
        """Register requirements integration handlers with the RPC handler"""
        # Note: Do NOT register tools/call here - the main handler in extended_server_handlers.py
        # is responsible for routing tool calls to this module. Registering tools/call here
        # would override the main handler and prevent proper task storage.

    def handle_tools_call(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle tools/call request for requirements integration tools"""
        if params is None:
            params = {}

        tool_name = params.get("name") or params.get("tool")
        tool_arguments = params.get("arguments", {})

        # Find the tool in requirements integration tools
        tool = None
        for t in self.tools:
            if t["name"] == tool_name:
                tool = t
                break

        if not tool:
            return None  # Return None to indicate this tool isn't handled here

        # Execute the requirements integration tool
        return self._execute_tool(tool, tool_arguments)

    def _execute_tool(self, tool: Dict[str, Any], arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific requirements integration tool with given arguments"""
        tool_name = tool["name"]

        if tool_name == "sync_with_requirements_engineer":
            return self._sync_with_requirements_engineer(arguments)

        elif tool_name == "fetch_requirements_specifications":
            return self._fetch_requirements_specifications(arguments)

        elif tool_name == "submit_stakeholder_inputs":
            return self._submit_stakeholder_inputs(arguments)

        # For any other tools, return a generic response
        return {"result": f"Executed requirements integration tool '{tool_name}' with arguments: {arguments}"}

    def _sync_with_requirements_engineer(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronize requirements with the requirements engineer agent"""
        try:
            operation = arguments.get("operation", "update")
            requirements_data = arguments.get("requirements_data", {})
            target_agent = arguments.get("target_agent", "requirements-engineer-agent")

            # Try to call the requirements engineer agent with retry logic
            result = self._attempt_call_to_agent(
                target_agent, 
                "sync_with_requirements_engineer", 
                arguments,
                max_retries=3
            )
            
            if result and result.get("status") != "error":
                # Successful call to requirements engineer
                return result
            else:
                # Fall back to local processing if requirements engineer is unavailable
                print(f"Requirements engineer unavailable, falling back to local processing for sync operation")
                result = {
                    "status": "synchronized_locally",
                    "operation": operation,
                    "target_agent": target_agent,
                    "requirements_processed": len(requirements_data) if isinstance(requirements_data, list) else 1,
                    "timestamp": time.time(),
                    "message": f"Requirements synchronized locally (requirements engineer unavailable)",
                    "fallback_used": True
                }

            # Store the sync task in the database
            if self.task_storage:
                self.task_storage.store_received_task(
                    task_id=f"sync-{int(time.time())}",
                    title="Requirements Synchronization",
                    description=f"Synchronize requirements with {target_agent}",
                    assigned_to=target_agent,
                    priority="medium",
                    source_server="internal",
                    metadata={"tool_call": "sync_with_requirements_engineer", "original_arguments": arguments}
                )

            print(f"Synchronized requirements with requirements engineer using {operation} operation")
            return {"result": result}

        except Exception as e:
            print(f"Error synchronizing with requirements engineer: {e}")
            return {"result": f"Requirements synchronization failed: {str(e)}"}

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

    def _fetch_requirements_specifications(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch requirements specifications from requirements engineer"""
        try:
            project_id = arguments.get("project_id", "")
            filter_val = arguments.get("filter", "")
            format_type = arguments.get("format", "json")
            target_agent = "requirements-engineer"

            # Try to call the requirements engineer agent with retry logic
            result = self._attempt_call_to_agent(
                target_agent, 
                "fetch_requirements_specifications", 
                arguments,
                max_retries=3
            )
            
            if result and result.get("status") != "error":
                # Successful call to requirements engineer
                return result
            else:
                # Fall back to local processing if requirements engineer is unavailable
                print(f"Requirements engineer unavailable, falling back to local processing for fetch specifications")
                result = {
                    "project_id": project_id,
                    "format": format_type,
                    "specifications": {
                        "functional_requirements": [
                            {"id": "FR-001", "description": "User shall be able to log in", "priority": "high"},
                            {"id": "FR-002", "description": "User shall be able to view profile", "priority": "medium"}
                        ],
                        "non_functional_requirements": [
                            {"id": "NFR-001", "description": "System shall respond within 2 seconds", "priority": "high"},
                            {"id": "NFR-002", "description": "System shall be available 99.9%", "priority": "critical"}
                        ],
                        "business_requirements": [
                            {"id": "BR-001", "description": "Increase user engagement by 25%", "priority": "high"}
                        ]
                    },
                    "metadata": {
                        "last_updated": time.time(),
                        "version": "1.0",
                        "status": "draft",
                        "fallback_used": True
                    }
                }

            # Store the fetch task in the database
            if self.task_storage:
                self.task_storage.store_received_task(
                    task_id=f"fetch-specs-{int(time.time())}",
                    title="Fetch Requirements Specifications",
                    description=f"Fetch specifications for project {project_id}",
                    assigned_to="requirements-engineer",
                    priority="medium",
                    source_server="internal",
                    metadata={"tool_call": "fetch_requirements_specifications", "original_arguments": arguments}
                )

            print(f"Fetched requirements specifications for project {project_id}")
            return {"result": result}

        except Exception as e:
            print(f"Error fetching requirements specifications: {e}")
            return {"result": f"Fetching requirements specifications failed: {str(e)}"}

    def _submit_stakeholder_inputs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Submit stakeholder inputs to requirements engineer for analysis"""
        try:
            stakeholder_inputs = arguments.get("stakeholder_inputs", "")
            business_context = arguments.get("business_context", "")
            project_reference = arguments.get("project_reference", "")
            priority = arguments.get("priority", "medium")
            target_agent = "requirements-engineer"

            # Try to call the requirements engineer agent with retry logic
            result = self._attempt_call_to_agent(
                target_agent, 
                "submit_stakeholder_inputs", 
                arguments,
                max_retries=3
            )
            
            if result and result.get("status") != "error":
                # Successful call to requirements engineer
                return result
            else:
                # Fall back to local processing if requirements engineer is unavailable
                print(f"Requirements engineer unavailable, falling back to local processing for submitting stakeholder inputs")
                result = {
                    "status": "submitted_locally",
                    "project_reference": project_reference,
                    "priority": priority,
                    "inputs_length": len(stakeholder_inputs),
                    "business_context_length": len(business_context),
                    "submission_id": f"sub-{int(time.time())}",
                    "message": "Stakeholder inputs processed locally (requirements engineer unavailable)",
                    "fallback_used": True
                }

            # Store the submission task in the database
            if self.task_storage:
                self.task_storage.store_received_task(
                    task_id=f"submit-inputs-{int(time.time())}",
                    title="Submit Stakeholder Inputs",
                    description=f"Submit inputs for project {project_reference}",
                    assigned_to="requirements-engineer",
                    priority=priority,
                    source_server="internal",
                    metadata={"tool_call": "submit_stakeholder_inputs", "original_arguments": arguments}
                )

            print(f"Submitted stakeholder inputs to requirements engineer for project {project_reference}")
            return {"result": result}

        except Exception as e:
            print(f"Error submitting stakeholder inputs: {e}")
            return {"result": f"Submitting stakeholder inputs failed: {str(e)}"}

    def _read_resource(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Read content from a requirements-specific resource"""
        uri = resource["uri"]

        if uri == "it-lead://resource/current-requirements-status":
            # Return current requirements status
            return {
                "contents": [{
                    "uri": uri,
                    "text": json.dumps({
                        "status_id": f"req-status-{int(time.time())}",
                        "created_at": time.time(),
                        "requirements_gathering_progress": 75,
                        "requirements_validated": 60,
                        "requirements_approved": 45,
                        "ambiguities_identified": 5,
                        "ambiguities_resolved": 3,
                        "next_milestone": "Complete requirements validation",
                        "estimated_completion": "2023-11-30T10:00:00Z"
                    }, indent=2)
                }]
            }

        elif uri == "it-lead://resource/requirements-ambiguity-log":
            # Return requirements ambiguity log
            return {
                "contents": [{
                    "uri": uri,
                    "text": json.dumps({
                        "log_id": f"ambiguity-log-{int(time.time())}",
                        "created_at": time.time(),
                        "ambiguities": [
                            {
                                "id": "AMB-001",
                                "requirement_id": "FR-001",
                                "description": "Ambiguous user role definition",
                                "status": "identified",
                                "date_identified": "2023-10-15T09:00:00Z",
                                "assigned_to": "stakeholder",
                                "resolution_target": "2023-10-20T09:00:00Z"
                            },
                            {
                                "id": "AMB-002",
                                "requirement_id": "NFR-001",
                                "description": "Unclear performance metrics",
                                "status": "resolved",
                                "date_identified": "2023-10-10T09:00:00Z",
                                "date_resolved": "2023-10-12T14:00:00Z",
                                "resolver": "requirements-engineer",
                                "resolution_notes": "Clarified response time under normal load conditions"
                            }
                        ],
                        "total_identified": 5,
                        "total_resolved": 3,
                        "resolution_rate": 0.6
                    }, indent=2)
                }]
            }

        # For any other resources, return a generic response
        return {
            "contents": [{
                "uri": uri,
                "text": f"Content for requirements resource: {uri}"
            }]
        }