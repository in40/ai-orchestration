"""
Client Methods Handlers for MCP Server
Implements client-initiated methods that the server can call as per MCP specification
"""
from typing import Dict, Any, List, Optional
from datetime import datetime


class ClientMethodsHandlers:
    """Handler class for client methods that the server can initiate"""
    
    def __init__(self, rpc_handler):
        self.rpc_handler = rpc_handler
        self.client_callbacks = {}
    
    def handle_sampling_complete(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Handle sampling/complete request as per MCP specification
        This is typically called by the client, but server might need to handle responses
        """
        # This method would be called when the client responds to a server-initiated sampling request
        completion_result = params.get('completion', {})
        
        # Process the completion result
        result = {
            "status": "received",
            "received_at": datetime.now().isoformat()
        }
        
        return result
    
    def handle_elicitation_request(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Handle elicitation/request response as per MCP specification
        This handles the client's response to a server-initiated elicitation request
        """
        # This method would be called when the client responds to a server-initiated elicitation request
        response = params.get('response', {})
        
        # Process the elicitation response
        result = {
            "status": "received",
            "received_at": datetime.now().isoformat(),
            "response_processed": True
        }
        
        return result
    
    def handle_logging_message(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Handle logging/message as per MCP specification
        This handles log messages sent from the client to the server
        """
        level = params.get('level', 'info')
        message = params.get('message', '')
        data = params.get('data', {})
        
        # Log the message appropriately
        print(f"[CLIENT LOG - {level.upper()}] {message}", data)
        
        return {
            "logged": True,
            "timestamp": datetime.now().isoformat()
        }
    
    def send_sampling_request(self, prompt: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a sampling/complete request to the client as per MCP specification
        """
        params = {
            "prompt": prompt
        }
        
        if options:
            params["options"] = options
        
        request = self.rpc_handler.create_request("sampling/complete", params)
        return request
    
    def send_elicitation_request(self, 
                                description: str, 
                                type_hint: str = "string", 
                                suggestions: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Send an elicitation/request to the client as per MCP specification
        """
        params = {
            "description": description,
            "type": type_hint
        }
        
        if suggestions:
            params["suggestions"] = suggestions
        
        request = self.rpc_handler.create_request("elicitation/request", params)
        return request
    
    def send_log_message(self, level: str, message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a logging/message notification to the client as per MCP specification
        """
        params = {
            "level": level,
            "message": message
        }
        
        if data:
            params["data"] = data
        
        notification = self.rpc_handler.create_notification("logging/message", params)
        return notification
    
    def register_handlers(self, rpc_handler):
        """Register client method handlers with the RPC handler"""
        # These are handlers for when the client sends responses to server-initiated requests
        rpc_handler.register_request_handler('sampling/complete', self.handle_sampling_complete)
        rpc_handler.register_request_handler('elicitation/request', self.handle_elicitation_request)
        rpc_handler.register_notification_handler('logging/message', self.handle_logging_message)