"""
Communication interfaces for the Implementation Engineer Agent
Enables communication with other agents in the team (IT Lead, Software Architect, etc.)
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import json
import requests
from config import settings


class CommunicationResult(BaseModel):
    """Result of a communication operation"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AgentCommunicator:
    """Handles communication with other agents in the team"""
    
    def __init__(self, registry_url: Optional[str] = None):
        self.registry_url = registry_url or settings.registry_url
        self.session = requests.Session()
        
    def call_agent_tool(self, agent_name: str, tool_name: str, arguments: Dict[str, Any]) -> CommunicationResult:
        """
        Call a tool on another agent via the registry
        """
        try:
            # First, get the agent's endpoint from the registry
            agent_info = self.find_agent(agent_name)
            if not agent_info:
                return CommunicationResult(
                    success=False,
                    message=f"Agent {agent_name} not found in registry",
                    error="Agent not found"
                )
            
            # Prepare the tool call
            payload = {
                "jsonrpc": "2.0",
                "id": f"call-{tool_name}-{hash(json.dumps(arguments))}",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            # Call the agent's endpoint
            response = self.session.post(
                agent_info["endpoint"],
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    return CommunicationResult(
                        success=True,
                        message=f"Successfully called {tool_name} on {agent_name}",
                        data=result["result"]
                    )
                elif "error" in result:
                    return CommunicationResult(
                        success=False,
                        message=f"Error calling {tool_name} on {agent_name}: {result['error']['message']}",
                        error=result["error"]["message"]
                    )
                else:
                    return CommunicationResult(
                        success=False,
                        message=f"Unexpected response format from {agent_name}",
                        error="Unexpected response format"
                    )
            else:
                return CommunicationResult(
                    success=False,
                    message=f"HTTP {response.status_code} calling {agent_name}",
                    error=response.text
                )
                
        except Exception as e:
            return CommunicationResult(
                success=False,
                message=f"Exception calling {tool_name} on {agent_name}: {str(e)}",
                error=str(e)
            )
    
    def find_agent(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Find an agent in the registry by name
        """
        try:
            if not self.registry_url:
                return None
                
            # Query the registry for the agent
            payload = {
                "jsonrpc": "2.0",
                "id": f"find-{agent_name}",
                "method": "registry/list",
                "params": {
                    "filter": agent_name
                }
            }
            
            response = self.session.post(
                self.registry_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result and "services" in result["result"]:
                    for service in result["result"]["services"]:
                        if agent_name.lower() in service.get("name", "").lower():
                            return service
                return None
            else:
                print(f"Registry query failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Exception querying registry for {agent_name}: {str(e)}")
            return None
    
    def notify_completion(self, task_id: str, result: Any, recipients: List[str] = None) -> CommunicationResult:
        """
        Notify other agents of task completion
        """
        try:
            # If no specific recipients, notify all relevant agents
            if not recipients:
                recipients = ["IT Lead Agent", "Code Reviewer Agent", "QA/Test Engineer Agent"]
            
            notifications_sent = []
            for recipient in recipients:
                agent_info = self.find_agent(recipient)
                if agent_info:
                    # Prepare notification payload
                    notification_payload = {
                        "jsonrpc": "2.0",
                        "method": "notifications/task_completed",
                        "params": {
                            "task_id": task_id,
                            "result": result,
                            "sender": "Implementation Engineer Agent"
                        }
                    }
                    
                    # Send notification (in a real implementation, this would use proper notification mechanisms)
                    response = self.session.post(
                        agent_info["endpoint"],
                        json=notification_payload,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        notifications_sent.append({"recipient": recipient, "status": "sent"})
                    else:
                        notifications_sent.append({"recipient": recipient, "status": "failed", "error": response.text})
                else:
                    notifications_sent.append({"recipient": recipient, "status": "failed", "error": "Agent not found"})
            
            return CommunicationResult(
                success=True,
                message=f"Sent completion notifications to {len(notifications_sent)} agents",
                data={"notifications": notifications_sent}
            )
            
        except Exception as e:
            return CommunicationResult(
                success=False,
                message=f"Exception sending completion notifications: {str(e)}",
                error=str(e)
            )


class ImplementationEngineerCommunicator:
    """Specialized communicator for the Implementation Engineer Agent"""
    
    def __init__(self):
        self.communicator = AgentCommunicator()
    
    def request_architectural_guidance(self, feature_description: str) -> CommunicationResult:
        """
        Request architectural guidance from the Software Architect Agent
        """
        return self.communicator.call_agent_tool(
            agent_name="Software Architect Agent",
            tool_name="design_system_architecture",
            arguments={
                "requirements": feature_description,
                "non_functional_requirements": ["scalability", "security", "maintainability"]
            }
        )
    
    def submit_for_code_review(self, code: str, feature_description: str) -> CommunicationResult:
        """
        Submit code for review to the Code Reviewer Agent
        """
        return self.communicator.call_agent_tool(
            agent_name="Code Reviewer Agent",
            tool_name="perform_static_analysis",
            arguments={
                "code_diff": code,
                "programming_language": "python",  # This would be determined dynamically in practice
                "security_checklist": [],
                "bug_patterns": [],
                "anti_patterns": []
            }
        )
    
    def request_test_requirements(self, feature_description: str) -> CommunicationResult:
        """
        Request test requirements from the QA/Test Engineer Agent
        """
        return self.communicator.call_agent_tool(
            agent_name="QA/Test Engineer Agent",
            tool_name="generate_test_suite",
            arguments={
                "requirements": feature_description,
                "test_types": ["unit", "integration"],
                "test_framework": "pytest",
                "coverage_requirements": ["all_functions_covered", "edge_cases_included"]
            }
        )
    
    def coordinate_with_devops(self, deployment_requirements: Dict[str, Any]) -> CommunicationResult:
        """
        Coordinate with DevOps/Release Engineer Agent for deployment
        """
        return self.communicator.call_agent_tool(
            agent_name="DevOps/Release Engineer Agent",
            tool_name="orchestrate_deployments",
            arguments={
                "application_artifacts": deployment_requirements.get("artifacts", ""),
                "target_environments": deployment_requirements.get("environments", ["staging"]),
                "deployment_strategy": deployment_requirements.get("strategy", "rolling"),
                "environment_configurations": deployment_requirements.get("configs", {}),
                "rollback_procedures": deployment_requirements.get("rollback", {})
            }
        )
    
    def report_progress_to_it_lead(self, task_status: Dict[str, Any]) -> CommunicationResult:
        """
        Report progress to the IT Lead Agent
        """
        return self.communicator.call_agent_tool(
            agent_name="IT Lead Agent",
            tool_name="track_task_progress",
            arguments=task_status
        )
    
    def request_security_review(self, code: str, feature_description: str) -> CommunicationResult:
        """
        Request security review from the Security Engineer Agent
        """
        return self.communicator.call_agent_tool(
            agent_name="Security Engineer Agent",
            tool_name="perform_security_analysis",
            arguments={
                "code": code,
                "application_type": "web_api",  # This would be determined dynamically
                "analysis_type": ["sast"],
                "security_frameworks": ["OWASP"],
                "custom_rules": []
            }
        )
    
    def notify_task_completion(self, task_id: str, result: Any, notify_agents: List[str] = None) -> CommunicationResult:
        """
        Notify relevant agents of task completion
        """
        return self.communicator.notify_completion(task_id, result, notify_agents)