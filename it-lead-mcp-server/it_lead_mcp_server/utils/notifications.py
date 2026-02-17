"""
Notification Manager for MCP Server
Handles MCP notifications for dynamic updates
"""
from typing import Dict, Callable, Any
from ..utils.json_rpc import JsonRpcMessage, MessageType


class NotificationManager:
    """Manages MCP notifications for dynamic updates"""

    def __init__(self, rpc_handler):
        self.rpc_handler = rpc_handler
        self.notification_callbacks: Dict[str, Callable] = {}
        self.changes_tracker = {
            "tools_changed": False,
            "resources_changed": False,
            "prompts_changed": False
        }

    def register_handlers(self, rpc_handler):
        """Register notification-related handlers"""
        # Currently no specific handlers to register
        pass

    def register_notification_callback(self, notification_type: str, callback: Callable):
        """Register a callback for a specific notification type"""
        self.notification_callbacks[notification_type] = callback

    def notify_tools_list_changed(self):
        """Notify that the tools list has changed"""
        self.changes_tracker["tools_changed"] = False
        notification = JsonRpcMessage({
            "jsonrpc": "2.0",
            "method": "notifications/tools/list_changed",
            "params": {}
        }, MessageType.NOTIFICATION)
        
        # Call registered callbacks
        if "notifications/tools/list_changed" in self.notification_callbacks:
            self.notification_callbacks["notifications/tools/list_changed"](notification)

    def notify_resources_list_changed(self):
        """Notify that the resources list has changed"""
        self.changes_tracker["resources_changed"] = False
        notification = JsonRpcMessage({
            "jsonrpc": "2.0",
            "method": "notifications/resources/list_changed",
            "params": {}
        }, MessageType.NOTIFICATION)
        
        # Call registered callbacks
        if "notifications/resources/list_changed" in self.notification_callbacks:
            self.notification_callbacks["notifications/resources/list_changed"](notification)

    def notify_prompts_list_changed(self):
        """Notify that the prompts list has changed"""
        self.changes_tracker["prompts_changed"] = False
        notification = JsonRpcMessage({
            "jsonrpc": "2.0",
            "method": "notifications/prompts/list_changed",
            "params": {}
        }, MessageType.NOTIFICATION)
        
        # Call registered callbacks
        if "notifications/prompts/list_changed" in self.notification_callbacks:
            self.notification_callbacks["notifications/prompts/list_changed"](notification)

    def mark_tools_changed(self):
        """Mark that tools have changed"""
        self.changes_tracker["tools_changed"] = True

    def mark_resources_changed(self):
        """Mark that resources have changed"""
        self.changes_tracker["resources_changed"] = True

    def mark_prompts_changed(self):
        """Mark that prompts have changed"""
        self.changes_tracker["prompts_changed"] = True

    def get_changes_status(self) -> Dict[str, bool]:
        """Get the current status of changes"""
        return self.changes_tracker.copy()

    def notify_task_assigned(self, task_id: str, agent_id: str, tool: str, 
                             arguments: dict, callback_url: str = None) -> dict:
        """Notify agent about a new task assignment
        
        Args:
            task_id: Unique task identifier
            agent_id: Target agent identifier
            tool: Tool to invoke on agent
            arguments: Tool arguments
            callback_url: Optional callback URL for responses
            
        Returns:
            Notification result dict
        """
        params = {
            "task_id": task_id,
            "tool": tool,
            "arguments": arguments
        }
        
        if callback_url:
            params["callback_url"] = callback_url
            
        notification = JsonRpcMessage({
            "jsonrpc": "2.0",
            "method": "notifications/tasks/new",
            "params": params
        }, MessageType.NOTIFICATION)
        
        # Call registered callbacks if any
        if "notifications/tasks/new" in self.notification_callbacks:
            self.notification_callbacks["notifications/tasks/new"](notification)
        
        return {
            "success": True,
            "task_id": task_id,
            "agent_id": agent_id,
            "notification_type": "notifications/tasks/new"
        }

    def notify_task_status_update(self, task_id: str, status: str, 
                                   progress: int = 0, result: dict = None,
                                   error: str = None) -> dict:
        """Send task status update notification
        
        Args:
            task_id: Unique task identifier
            status: Task status (queued, in_progress, completed, failed)
            progress: Progress percentage (0-100)
            result: Task result (if completed)
            error: Error message (if failed)
            
        Returns:
            Notification result dict
        """
        params = {
            "task_id": task_id,
            "status": status,
            "progress": progress,
            "timestamp": time.time()
        }
        
        if result is not None:
            params["result"] = result
        if error is not None:
            params["error"] = error
        
        notification = JsonRpcMessage({
            "jsonrpc": "2.0",
            "method": "notifications/tasks/status",
            "params": params
        }, MessageType.NOTIFICATION)
        
        # Call registered callbacks if any
        if "notifications/tasks/status" in self.notification_callbacks:
            self.notification_callbacks["notifications/tasks/status"](notification)
        
        return {
            "success": True,
            "task_id": task_id,
            "status": status
        }

    def notify_task_acknowledged(self, task_id: str, agent_id: str, 
                                  ack_status: str = "received") -> dict:
        """Notify that a task has been acknowledged by an agent
        
        Args:
            task_id: Unique task identifier
            agent_id: Agent that acknowledged the task
            ack_status: Acknowledgment status
            
        Returns:
            Notification result dict
        """
        notification = JsonRpcMessage({
            "jsonrpc": "2.0",
            "method": "notifications/tasks/ack",
            "params": {
                "task_id": task_id,
                "agent_id": agent_id,
                "status": ack_status
            }
        }, MessageType.NOTIFICATION)
        
        # Call registered callbacks if any
        if "notifications/tasks/ack" in self.notification_callbacks:
            self.notification_callbacks["notifications/tasks/ack"](notification)
        
        return {
            "success": True,
            "task_id": task_id,
            "agent_id": agent_id
        }

    def register_task_notification_callbacks(self, on_new=None, on_status=None, on_ack=None):
        """Register callbacks for task-related notifications
        
        Args:
            on_new: Callback for notifications/tasks/new
            on_status: Callback for notifications/tasks/status
            on_ack: Callback for notifications/tasks/ack
        """
        if on_new:
            self.register_notification_callback("notifications/tasks/new", on_new)
        if on_status:
            self.register_notification_callback("notifications/tasks/status", on_status)
        if on_ack:
            self.register_notification_callback("notifications/tasks/ack", on_ack)