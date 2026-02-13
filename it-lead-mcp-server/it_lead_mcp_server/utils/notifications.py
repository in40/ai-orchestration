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