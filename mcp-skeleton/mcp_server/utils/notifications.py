"""
Notification Support for MCP Server
Implements standard notification methods for dynamic updates as per MCP specification
"""
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import threading
import time


class NotificationManager:
    """Manages notifications for dynamic updates as per MCP specification"""
    
    def __init__(self, rpc_handler):
        self.rpc_handler = rpc_handler
        self.clients = {}  # Track connected clients
        self.notification_callbacks = {}
        self.lock = threading.Lock()
        
        # Track changes to send appropriate notifications
        self.tools_changed = False
        self.resources_changed = False
        self.prompts_changed = False
    
    def register_notification_callback(self, method: str, callback: Callable):
        """Register a callback for when specific notifications need to be sent"""
        self.notification_callbacks[method] = callback
    
    def notify_tools_list_changed(self):
        """Send notifications/tools/list_changed as per MCP specification"""
        notification = self.rpc_handler.create_notification(
            "notifications/tools/list_changed",
            {}
        )
        
        # Call registered callback to send the notification
        if "notifications/tools/list_changed" in self.notification_callbacks:
            self.notification_callbacks["notifications/tools/list_changed"](notification)
        
        with self.lock:
            self.tools_changed = False
    
    def notify_resources_list_changed(self):
        """Send notifications/resources/list_changed as per MCP specification"""
        notification = self.rpc_handler.create_notification(
            "notifications/resources/list_changed",
            {}
        )
        
        # Call registered callback to send the notification
        if "notifications/resources/list_changed" in self.notification_callbacks:
            self.notification_callbacks["notifications/resources/list_changed"](notification)
        
        with self.lock:
            self.resources_changed = False
    
    def notify_prompts_list_changed(self):
        """Send notifications/prompts/list_changed as per MCP specification"""
        notification = self.rpc_handler.create_notification(
            "notifications/prompts/list_changed",
            {}
        )
        
        # Call registered callback to send the notification
        if "notifications/prompts/list_changed" in self.notification_callbacks:
            self.notification_callbacks["notifications/prompts/list_changed"](notification)
        
        with self.lock:
            self.prompts_changed = False
    
    def mark_tools_changed(self):
        """Mark that tools have changed and notification should be sent"""
        with self.lock:
            self.tools_changed = True
    
    def mark_resources_changed(self):
        """Mark that resources have changed and notification should be sent"""
        with self.lock:
            self.resources_changed = True
    
    def mark_prompts_changed(self):
        """Mark that prompts have changed and notification should be sent"""
        with self.lock:
            self.prompts_changed = True
    
    def get_changes_status(self):
        """Get the current status of changes that need notification"""
        with self.lock:
            return {
                "tools_changed": self.tools_changed,
                "resources_changed": self.resources_changed,
                "prompts_changed": self.prompts_changed
            }
    
    def handle_ping(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Handle ping request - not part of standard MCP but useful for health checks
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "alive"
        }
    
    def register_handlers(self, rpc_handler):
        """Register notification-related handlers"""
        # Register ping handler for health checks
        rpc_handler.register_request_handler('ping', self.handle_ping)