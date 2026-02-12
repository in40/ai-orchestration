#!/usr/bin/env python3
"""
Simple Streamable HTTP test server for MCP Explorer.
Runs on localhost:3031 by default.
"""

import json
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import argparse
import sys


class StreamableHTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests - primarily for health check or initial connection."""
        if self.path == '/mcp' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            response = {
                "status": "Streamable HTTP server ready",
                "endpoint": "/mcp",
                "supported_methods": ["initialize", "tools/list", "tools/call", "ping"]
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        """Handle POST requests - all MCP JSON-RPC messages come via POST."""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            request = json.loads(post_data.decode('utf-8'))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        # Extract request details
        req_id = request.get('id')
        method = request.get('method')
        params = request.get('params', {})

        # Process the request based on method
        response = self.handle_method(method, params)
        response['id'] = req_id  # Echo back the request ID

        # Send response
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Mcp-Session-Id', getattr(self, 'session_id', 'test-session'))
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def handle_method(self, method, params):
        """Handle different MCP methods."""
        if method == 'initialize':
            return {
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "2025-03-26",
                    "serverInfo": {
                        "name": "test-server",
                        "version": "1.0.0"
                    },
                    "capabilities": {
                        "experimental": {}
                    }
                }
            }
        elif method == 'initialized':
            return {
                "jsonrpc": "2.0",
                "result": {}
            }
        elif method == 'tools/list':
            return {
                "jsonrpc": "2.0",
                "result": {
                    "tools": [
                        {
                            "name": "echo_tool",
                            "description": "Echoes back the input parameters",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "message": {
                                        "type": "string",
                                        "description": "Message to echo back"
                                    },
                                    "repeat_count": {
                                        "type": "integer", 
                                        "description": "Number of times to repeat the message",
                                        "default": 1
                                    }
                                },
                                "required": ["message"]
                            }
                        },
                        {
                            "name": "math_operation",
                            "description": "Performs basic math operations",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "operation": {
                                        "type": "string",
                                        "enum": ["add", "subtract", "multiply", "divide"],
                                        "description": "Mathematical operation to perform"
                                    },
                                    "a": {
                                        "type": "number",
                                        "description": "First operand"
                                    },
                                    "b": {
                                        "type": "number", 
                                        "description": "Second operand"
                                    }
                                },
                                "required": ["operation", "a", "b"]
                            }
                        }
                    ]
                }
            }
        elif method == 'tools/call':
            tool_id = params.get('tool')
            arguments = params.get('arguments', {})
            
            # Simulate tool execution
            if tool_id == 'echo_tool':
                msg = arguments.get('message', 'No message provided')
                count = arguments.get('repeat_count', 1)
                result = msg * count
            elif tool_id == 'math_operation':
                op = arguments.get('operation')
                a = arguments.get('a', 0)
                b = arguments.get('b', 0)
                
                if op == 'add':
                    result = a + b
                elif op == 'subtract':
                    result = a - b
                elif op == 'multiply':
                    result = a * b
                elif op == 'divide':
                    if b != 0:
                        result = a / b
                    else:
                        result = "Error: Division by zero"
                else:
                    result = f"Unknown operation: {op}"
            else:
                result = f"Unknown tool: {tool_id}"
            
            return {
                "jsonrpc": "2.0",
                "result": {
                    "output": result
                }
            }
        elif method == 'ping':
            return {
                "jsonrpc": "2.0",
                "result": {
                    "message": "pong"
                }
            }
        elif method == 'resources/list':
            return {
                "jsonrpc": "2.0",
                "result": {
                    "resources": []
                }
            }
        else:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Method {method} not supported"
                }
            }


def run_server(port=3031):
    """Run the test server."""
    server = HTTPServer(('localhost', port), StreamableHTTPHandler)
    print(f"MCP Streamable HTTP test server running on http://localhost:{port}/mcp")
    print("Press Ctrl+C to stop the server")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='MCP Streamable HTTP Test Server')
    parser.add_argument('--port', type=int, default=3031, help='Port to run the server on (default: 3031)')
    
    args = parser.parse_args()
    
    run_server(args.port)