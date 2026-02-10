"""
Stdio Transport for MCP Server
Handles communication over stdin/stdout as per MCP specification
"""
import sys
import threading
from typing import Callable, Optional
from ..utils.json_rpc import JsonRpcHandler, JsonRpcMessage


class StdioTransport:
    """Transport mechanism using stdin/stdout as per MCP specification"""
    
    def __init__(self, rpc_handler: JsonRpcHandler):
        self.rpc_handler = rpc_handler
        self.running = False
        self.input_thread: Optional[threading.Thread] = None
        self.message_callback: Optional[Callable[[JsonRpcMessage], None]] = None
    
    def start(self, message_callback: Callable[[JsonRpcMessage], None]):
        """Start the stdio transport"""
        self.running = True
        self.message_callback = message_callback
        
        # Start input reader thread
        self.input_thread = threading.Thread(target=self._read_input, daemon=True)
        self.input_thread.start()
    
    def stop(self):
        """Stop the stdio transport"""
        self.running = False
        if self.input_thread and self.input_thread.is_alive():
            self.input_thread.join(timeout=1.0)
    
    def _read_input(self):
        """Read messages from stdin"""
        while self.running:
            try:
                line = sys.stdin.readline()
                
                if not line:
                    # EOF reached, exit
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                # Parse and handle the message
                message = self.rpc_handler.parse_message(line)
                if self.message_callback:
                    self.message_callback(message)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                # Log error to stderr as per MCP spec
                print(f"Error reading from stdin: {e}", file=sys.stderr)
                continue
    
    def send_message(self, message: JsonRpcMessage):
        """Send a message to stdout"""
        if not self.running:
            return
            
        try:
            json_str = message.to_json()
            print(json_str, flush=True)  # Write to stdout as per MCP spec
        except Exception as e:
            print(f"Error writing to stdout: {e}", file=sys.stderr)
    
    def send_error(self, error_msg: str):
        """Send an error message to stderr (for logging purposes)"""
        print(error_msg, file=sys.stderr)