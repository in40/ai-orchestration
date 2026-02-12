# HTTP/SSE Client Implementation Guide for MCP Protocol

## Overview
This document outlines the proper implementation of an HTTP/SSE client for the Model Context Protocol (MCP) based on the AI Coding Agent implementation.

## HTTP/SSE Transport Architecture

The MCP HTTP/SSE transport consists of two main endpoints:
- **SSE endpoint** (`/sse`): Used for server-to-client communication via Server-Sent Events
- **HTTP endpoint** (`/send`): Used for client-to-server communication via HTTP POST

## Client Implementation Steps

### 1. Establish SSE Connection
Before sending any requests, establish an SSE connection to receive responses:

```python
async with sse_client.stream("GET", f"{base_url}/sse", timeout=timeout) as response:
    # Process incoming SSE events here
```

### 2. Send Requests via HTTP POST
Send requests to the `/send` endpoint with proper headers:

```python
headers = {
    "Content-Type": "application/json",
    "X-MCP-Session-ID": session_id  # Optional but recommended
}
response = await client.post(
    f"{base_url}/send",
    json=payload,
    headers=headers
)
```

### 3. Process SSE Data Stream
The SSE stream follows the Server-Sent Events format with specific patterns:

#### Initial Endpoint Announcement
```
event: endpoint
data: {"uri": "http://127.0.0.1:3060/send", "sessionId": "uuid"}
```

#### Response Messages
```
data: {"jsonrpc": "2.0", "id": "request-uuid", "result": {...}}
```

#### Ping Messages
```
data: : ping
data: 
```

### 4. SSE Data Parsing Algorithm

```python
async def _listen_for_response(self, sse_client, sse_url, expected_id: str, timeout: int):
    async with sse_client.stream("GET", sse_url, timeout=timeout) as response:
        start_time = asyncio.get_event_loop().time()
        
        # Buffer to accumulate SSE data
        buffer = ""
        
        async for chunk in response.aiter_text():
            # Check if we've timed out
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise asyncio.TimeoutError()
            
            buffer += chunk
            
            # Split by newlines to process individual SSE lines
            lines = buffer.split('\n')
            # Keep the last incomplete line in the buffer
            buffer = lines[-1]
            
            # Process all complete lines except the last one (which might be incomplete)
            for line in lines[:-1]:
                line = line.rstrip()  # Remove trailing whitespace
                
                if line.startswith('data: '):
                    data_str = line[len('data: '):].strip()
                    
                    # Skip ping messages (they have ': ping' in the data)
                    if data_str == ': ping':
                        continue
                    
                    try:
                        data = json.loads(data_str)
                        
                        # Check if this response matches our request ID
                        if 'id' in data and data['id'] == expected_id:
                            return data
                    except json.JSONDecodeError:
                        # Skip invalid JSON
                        continue
                elif line.startswith('event: '):
                    # Process event type if needed
                    event_type = line[len('event: '):].strip()
                    if event_type == 'endpoint':
                        # This is the initial endpoint announcement, skip it
                        continue
                elif line.strip() == '':
                    # Empty line separates SSE events, ignore
                    continue
```

## Key Implementation Points

### Session Management
- Generate a unique session ID for each client session
- Include the session ID in the `X-MCP-Session-ID` header when making requests
- This helps the server route responses back to the correct client

### Request-Response Correlation
- Generate a unique request ID for each request
- Match responses to requests by comparing the `id` field in the JSON-RPC response
- Store the mapping between request IDs and expected responses

### Error Handling
- Implement proper timeout handling for both SSE connections and HTTP requests
- Handle JSON parsing errors gracefully
- Manage event loop lifecycle properly

### Concurrency Considerations
- Use separate HTTP clients for SSE and regular HTTP requests to avoid conflicts
- Properly close clients in finally blocks
- Use asyncio tasks for concurrent operations

## Complete Example Implementation

```python
import asyncio
import json
import httpx
import uuid

class McpHttpClient:
    def __init__(self, base_url: str = "http://localhost:3060"):
        self.base_url = base_url
        self.session_id = str(uuid.uuid4())  # Create a session ID for this client
        self.client = httpx.AsyncClient(timeout=30.0)

    async def send_request_and_wait_for_response(self, method: str, params: dict, timeout: int = 30):
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        
        # Create the JSON-RPC payload
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }

        # Establish SSE connection to listen for responses
        sse_url = f"{self.base_url}/sse"
        
        # Create a separate client for SSE to avoid conflicts
        sse_client = httpx.AsyncClient(timeout=timeout)
        
        try:
            # Start the SSE connection
            sse_task = asyncio.create_task(self._listen_for_response(sse_client, sse_url, request_id, timeout))
            
            # Give the SSE connection a moment to establish
            await asyncio.sleep(0.2)
            
            # Send the request with the session ID
            response = await self.client.post(
                f"{self.base_url}/send",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-MCP-Session-ID": self.session_id
                }
            )
            response.raise_for_status()
            
            # Wait for the response from SSE
            result = await sse_task
            return result
            
        except Exception as e:
            return {"error": str(e)}
        finally:
            await sse_client.aclose()

    async def _listen_for_response(self, sse_client, sse_url, expected_id: str, timeout: int):
        async with sse_client.stream("GET", sse_url, timeout=timeout) as response:
            start_time = asyncio.get_event_loop().time()
            
            # Buffer to accumulate SSE data
            buffer = ""
            
            async for chunk in response.aiter_text():
                # Check if we've timed out
                if asyncio.get_event_loop().time() - start_time > timeout:
                    raise asyncio.TimeoutError()
                
                buffer += chunk
                
                # Split by newlines to process individual SSE lines
                lines = buffer.split('\n')
                # Keep the last incomplete line in the buffer
                buffer = lines[-1]
                
                # Process all complete lines except the last one (which might be incomplete)
                for line in lines[:-1]:
                    line = line.rstrip()  # Remove trailing whitespace
                    
                    if line.startswith('data: '):
                        data_str = line[len('data: '):].strip()
                        
                        # Skip ping messages (they have ': ping' in the data)
                        if data_str == ': ping':
                            continue
                        
                        try:
                            data = json.loads(data_str)
                            
                            # Check if this response matches our request ID
                            if 'id' in data and data['id'] == expected_id:
                                return data
                        except json.JSONDecodeError:
                            # Skip invalid JSON
                            continue
                    elif line.startswith('event: '):
                        # Process event type if needed
                        event_type = line[len('event: '):].strip()
                        if event_type == 'endpoint':
                            # This is the initial endpoint announcement, skip it
                            continue
                    elif line.strip() == '':
                        # Empty line separates SSE events, ignore
                        continue
```

## Common Pitfalls to Avoid

1. **Not establishing SSE connection first**: Always establish the SSE connection before sending requests
2. **Incorrect data parsing**: SSE data comes in "data: {json}" format, not raw JSON
3. **Missing session ID**: Include X-MCP-Session-ID header for proper response routing
4. **Buffer management**: Properly handle partial SSE lines by buffering incomplete data
5. **Event loop issues**: Ensure proper cleanup of async resources
6. **Timeout handling**: Implement proper timeouts to prevent hanging connections

## Testing the Implementation

Test each endpoint separately:
- Verify SSE connection establishment
- Test request/response correlation
- Validate timeout handling
- Confirm proper error handling

Use tools like curl to inspect the raw SSE stream:
```bash
curl -N http://localhost:3060/sse
```

This will show you the exact format of the SSE events being sent by the server.