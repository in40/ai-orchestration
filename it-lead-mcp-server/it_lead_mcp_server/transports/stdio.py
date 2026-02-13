"""
Stdio Transport for MCP Server
Handles communication via standard input/output streams
"""
import sys
import json
import threading
from typing import Callable, Any
from ..utils.json_rpc import JsonRpcMessage, MessageType


class StdioTransport:
    """Transport implementation using standard input/output streams"""

    def __init__(self, rpc_handler):
        self.rpc_handler = rpc_handler
        self.running = False
        self.input_thread = None
        self.output_lock = threading.Lock()

    def start(self, message_callback: Callable[[JsonRpcMessage], None]):
        """Start the stdio transport"""
        self.running = True
        self.message_callback = message_callback
        
        # Start a thread to read from stdin
        self.input_thread = threading.Thread(target=self._read_from_stdin, daemon=True)
        self.input_thread.start()

    def stop(self):
        """Stop the stdio transport"""
        self.running = False
        if self.input_thread:
            self.input_thread.join(timeout=1.0)  # Wait up to 1 second for thread to finish

    def _read_from_stdin(self):
        """Read messages from stdin in a separate thread"""
        try:
            for line in iter(sys.stdin.readline, ''):
                if not self.running:
                    break
                
                line = line.strip()
                if line:
                    try:
                        # Parse the JSON message
                        message = JsonRpcMessage(line, MessageType.REQUEST)
                        
                        # Process the message
                        self.message_callback(message)
                    except json.JSONDecodeError:
                        # Invalid JSON, skip this message
                        self.send_error(f"Invalid JSON: {line}")
                    except Exception as e:
                        self.send_error(f"Error processing message: {e}")
        except Exception as e:
            self.send_error(f"Error reading from stdin: {e}")

    def send_message(self, message: JsonRpcMessage):
        """Send a message to stdout"""
        if self.running:
            try:
                json_str = message.to_json()
                with self.output_lock:
                    print(json_str, flush=True)
            except Exception as e:
                self.send_error(f"Error sending message: {e}")

    def _send_response(self, response):
        """Send a response message"""
        self.send_message(response)

    def send_error(self, error_msg: str):
        """Send an error message to stderr"""
        print(f"ERROR: {error_msg}", file=sys.stderr, flush=True)