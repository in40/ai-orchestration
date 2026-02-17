"""
Agent Status Checker for IT Lead MCP Server
Queries assigned agents for real-time task status updates
"""
import json
import time
import requests
from typing import Dict, List, Any, Optional


class AgentStatusChecker:
    """Checks task status with assigned agents via MCP"""
    
    def __init__(self, service_registry=None, task_storage=None):
        self.service_registry = service_registry
        self.task_storage = task_storage
        self.agent_cache = {}  # Cache agent endpoints
    
    def check_task_status_with_agent(self, task_id: str, assigned_agent: str) -> Dict[str, Any]:
        """
        Check task status directly with the assigned agent
        
        Args:
            task_id: Task identifier
            assigned_agent: Agent name (e.g., "implementation-engineer")
        
        Returns:
            Status information from agent
        """
        # Get agent endpoint
        agent_endpoint = self._get_agent_endpoint(assigned_agent)
        
        if not agent_endpoint:
            return {
                "success": False,
                "error": f"Agent {assigned_agent} endpoint not found",
                "task_id": task_id,
                "agent": assigned_agent,
                "local_status": self._get_local_task_status(task_id)
            }
        
        # Try to get task status from agent
        try:
            # First, try tasks/get if agent supports it
            status = self._query_agent_task_status(agent_endpoint, task_id)
            
            if status.get("success"):
                # Update local database with new status
                self._update_task_status(task_id, status.get("status"), status)
                
                return {
                    "success": True,
                    "task_id": task_id,
                    "agent": assigned_agent,
                    "agent_status": status.get("status"),
                    "agent_progress": status.get("progress"),
                    "agent_details": status.get("details", {}),
                    "last_updated": status.get("updated_at"),
                    "source": "agent"
                }
            else:
                # Agent doesn't have task or doesn't support status query
                return {
                    "success": False,
                    "error": status.get("error", "Unknown error"),
                    "task_id": task_id,
                    "agent": assigned_agent,
                    "local_status": self._get_local_task_status(task_id),
                    "source": "fallback"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task_id": task_id,
                "agent": assigned_agent,
                "local_status": self._get_local_task_status(task_id),
                "source": "error"
            }
    
    def _get_agent_endpoint(self, agent_name: str) -> Optional[str]:
        """Get MCP endpoint for an agent"""
        # Normalize agent name
        agent_name_lower = agent_name.lower().replace(" ", "-").replace("_", "-")
        
        # Check cache first
        if agent_name_lower in self.agent_cache:
            return self.agent_cache[agent_name_lower]
        
        # Map common agent names
        agent_mapping = {
            "implementation-engineer": ["implementation", "implementation-engineer"],
            "requirements-engineer": ["requirements", "requirements-engineer"],
            "code-reviewer": ["code-reviewer", "reviewer"],
            "qa-test-engineer": ["qa", "qa-test-engineer", "tester"],
            "security-engineer": ["security", "security-engineer"],
            "devops-engineer": ["devops", "devops-engineer"],
        }
        
        # Try to find endpoint from registry
        if self.service_registry:
            try:
                services = self.service_registry.list_services()
                for service in services:
                    service_name = service.get("name", "").lower()
                    endpoint = service.get("endpoint")
                    
                    for alias in agent_mapping.get(agent_name_lower, [agent_name_lower]):
                        if alias in service_name and endpoint:
                            self.agent_cache[agent_name_lower] = endpoint
                            return endpoint
            except Exception as e:
                print(f"Error getting agent endpoint from registry: {e}")
        
        # Fallback to known endpoints
        known_endpoints = {
            "implementation-engineer": "http://127.0.0.1:3060/mcp",
            "requirements-engineer": "http://127.0.0.1:3062/mcp",
        }
        
        endpoint = known_endpoints.get(agent_name_lower)
        if endpoint:
            self.agent_cache[agent_name_lower] = endpoint
        
        return endpoint
    
    def _query_agent_task_status(self, agent_endpoint: str, task_id: str) -> Dict[str, Any]:
        """Query agent for task status using MCP protocol"""
        
        # Try tasks/get method first (standard MCP task protocol)
        try:
            response = requests.post(
                agent_endpoint,
                json={
                    "jsonrpc": "2.0",
                    "id": f"status-check-{task_id}",
                    "method": "tools/call",
                    "params": {"name": "tasks/get", "arguments": {"task_id": task_id}}
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result and result["result"]:
                    task_data = result["result"]
                    return {
                        "success": True,
                        "status": task_data.get("status", "unknown"),
                        "progress": task_data.get("progress", 0),
                        "details": task_data,
                        "updated_at": task_data.get("updated_at") or time.time()
                    }
                elif "error" in result and result["error"].get("code") == -32601:
                    # Method not found - agent doesn't support task tracking
                    pass  # Try next method
        except requests.RequestException:
            pass  # Try next method
        
        # Try tasks/list to see if task is in agent's queue
        try:
            response = requests.post(
                agent_endpoint,
                json={
                    "jsonrpc": "2.0",
                    "id": f"task-list-{task_id}",
                    "method": "tools/call",
                    "params": {"name": "tasks/list", "arguments": {}}
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result and result["result"]:
                    tasks = result["result"].get("tasks", [])
                    for task in tasks:
                        if task.get("id") == task_id or task.get("task_id") == task_id:
                            return {
                                "success": True,
                                "status": task.get("status", "unknown"),
                                "progress": task.get("progress", 0),
                                "details": task,
                                "updated_at": task.get("updated_at") or time.time()
                            }
        except requests.RequestException:
            pass
        
        # Agent doesn't support task status queries for this task
        # This is normal for synchronous tool calls like implement_feature
        return {
            "success": False,
            "error": "Task was processed synchronously - no ongoing status tracking available",
            "note": "For async task tracking, use vibe_code_async which returns a task_id for status queries"
        }
    
    def _get_local_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status from local database"""
        if not self.task_storage:
            return None
        
        try:
            tasks = self.task_storage.get_all_tasks()
            for task in tasks:
                if task.get("task_id") == task_id:
                    return {
                        "task_id": task.get("task_id"),
                        "status": task.get("status"),
                        "assigned_to": task.get("assigned_to"),
                        "created_at": task.get("created_at"),
                        "updated_at": task.get("updated_at"),
                        "source": "local"
                    }
        except Exception as e:
            print(f"Error getting local task status: {e}")
        
        return None
    
    def _update_task_status(self, task_id: str, new_status: str, agent_data: Dict[str, Any]):
        """Update task status in local database based on agent data"""
        if not self.task_storage:
            return
        
        try:
            # Note: This would need an update_task_status method in TaskStorage
            # For now, this is a placeholder
            print(f"Updating task {task_id} status to {new_status} from agent data")
            # TODO: Implement actual status update in task_storage.py
        except Exception as e:
            print(f"Error updating task status: {e}")
    
    def check_all_assigned_tasks(self) -> List[Dict[str, Any]]:
        """Check status of all tasks assigned to agents"""
        if not self.task_storage:
            return []
        
        results = []
        try:
            tasks = self.task_storage.get_all_tasks()
            for task in tasks:
                assigned_to = task.get("assigned_to", "")
                task_id = task.get("task_id")
                status = task.get("status", "received")
                
                # Only check tasks assigned to specific agents (not "system" or "unassigned")
                if assigned_to and assigned_to.lower() not in ["system", "unassigned", "unknown"]:
                    if status in ["received", "assigned", "forwarded", "in_progress"]:
                        result = self.check_task_status_with_agent(task_id, assigned_to)
                        results.append(result)
        except Exception as e:
            print(f"Error checking all assigned tasks: {e}")
        
        return results
