# MCP Explorer Verification Protocol

## Verification Steps

### 1. Verify No Legacy Transport Code Exists

```bash
grep -r "sse\|event-stream\|endpoint\|Server-Sent Events\|sse_client\|SSEClient\|text/event-stream\|GET /sse\|POST /message\|legacy\|stdio" --include="*.py" .
```

This command must return zero matches to confirm no legacy SSE or stdio transport code exists.

### 2. Verify Default Registry Connection on Startup

```bash
# Start a mock Streamable HTTP server on port 3031
python -c "
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading

class MockMCPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/mcp':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {'result': 'ok'}
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/mcp':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request = json.loads(post_data.decode('utf-8'))
            
            # Echo back the request for testing
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Mcp-Session-Id', 'test-session-id')
            self.end_headers()
            
            response = {
                'jsonrpc': '2.0',
                'id': request.get('id'),
                'result': {'message': f'Received {request.get(\"method\", \"unknown\")} request'}
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

def start_server():
    server = HTTPServer(('localhost', 3031), MockMCPHandler)
    server.serve_forever()

thread = threading.Thread(target=start_server, daemon=True)
thread.start()
print('Mock Streamable HTTP server running on http://localhost:3031/mcp')
input('Press Enter to stop server...')
"

# Launch mcp-explorer in another terminal
# The server logs should show an incoming GET /mcp or POST /mcp request
```

### 3. Verify Tool Invocation Uses HTTP POST to Single Endpoint

Using Wireshark/tcpdump:

```bash
sudo tcpdump -i lo -s 0 -w mcp_explorer_traffic.pcap port 3031
# Run mcp-explorer and perform tool invocation
# Stop tcpdump and analyze capture
# Should show no connections to /sse or /message
# All client-to-server JSON-RPC should be HTTP POST to the configured endpoint
```

### 4. Verify Schema Validation is Real

```bash
# Point the tool at a server that returns an invalid/malformed tool schema
# The TUI must display an error, not silently ignore or default to mock data
```

### 5. Verify Canonical Naming

All tools must be displayed and callable using the format: `<server-name>__<tool-name>`

Example: `localhost-registry__get_weather`, `github__create_issue`

### 6. Verify Streamable HTTP Compliance

- All JSON-RPC messages must be sent via HTTP POST to the single endpoint
- Session IDs must be properly handled
- No WebSocket upgrade logic
- No fallback transports