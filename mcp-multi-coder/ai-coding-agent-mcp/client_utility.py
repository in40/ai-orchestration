#!/usr/bin/env python3
"""
Client utility for accessing AI Coding Agent MCP endpoints.

This utility provides a command-line interface to interact with the AI Coding Agent MCP server.
"""

import argparse
import asyncio
import json
import sys
import httpx
import os
from typing import Dict, Any, Optional
import uuid


class AiCodingAgentClient:
    """Client for interacting with the AI Coding Agent MCP server."""

    def __init__(self, base_url: str = "http://localhost:3060"):
        self.base_url = base_url
        self.session_id = str(uuid.uuid4())  # Create a session ID for this client
        self.client = httpx.AsyncClient(timeout=30.0)

    async def _send_request_and_wait_for_response(self, method: str, params: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        """Send a request to the MCP server and wait for the response via SSE."""
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        
        # Payload for the request
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
            
        except httpx.RequestError as e:
            print(f"Request error: {e}")
            return {"error": str(e)}
        except httpx.HTTPStatusError as e:
            print(f"HTTP error: {e}")
            return {"error": str(e)}
        except asyncio.TimeoutError:
            return {"error": "Timeout waiting for response"}
        finally:
            await sse_client.aclose()

    async def _listen_for_response(self, sse_client, sse_url, expected_id: str, timeout: int):
        """Listen to the SSE stream for a response with the expected ID."""
        try:
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
        except Exception as e:
            return {"error": f"SSE error: {str(e)}"}

    async def submit_coding_task(self, task: str, language: str = "python", max_tokens: int = 512) -> Dict[str, Any]:
        """Submit a coding task to the server."""
        params = {
            "name": "submit_coding_task",
            "arguments": {
                "task": task,
                "language": language,
                "max_tokens": max_tokens
            }
        }
        return await self._send_request_and_wait_for_response("tools/call", params)

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a coding task."""
        params = {
            "name": "get_task_status",
            "arguments": {
                "task_id": task_id
            }
        }
        return await self._send_request_and_wait_for_response("tools/call", params)

    async def list_tasks(self, status: Optional[str] = None) -> Dict[str, Any]:
        """List all tasks, optionally filtered by status."""
        params = {
            "name": "list_tasks",
            "arguments": {}
        }
        if status:
            params["arguments"]["status"] = status
        return await self._send_request_and_wait_for_response("tools/call", params)

    async def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """Cancel a pending task."""
        params = {
            "name": "cancel_task",
            "arguments": {
                "task_id": task_id
            }
        }
        return await self._send_request_and_wait_for_response("tools/call", params)

    async def render_prompt(self, template_name: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Render a prompt template."""
        params = {
            "name": "render_prompt",
            "arguments": {
                "template_name": template_name,
                "variables": variables
            }
        }
        return await self._send_request_and_wait_for_response("tools/call", params)

    async def check_lmstudio_health(self) -> Dict[str, Any]:
        """Check LM Studio health."""
        params = {
            "name": "lmstudio_health",
            "arguments": {}
        }
        return await self._send_request_and_wait_for_response("tools/call", params)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


async def main():
    parser = argparse.ArgumentParser(description="AI Coding Agent MCP Client")
    parser.add_argument("--url", default="http://localhost:3060", help="Base URL of the MCP server")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Submit task command
    submit_parser = subparsers.add_parser("submit-task", help="Submit a coding task")
    submit_parser.add_argument("--task", required=True, help="The coding task description")
    submit_parser.add_argument("--language", default="python", help="Programming language (default: python)")
    submit_parser.add_argument("--max-tokens", type=int, default=512, help="Max tokens to generate (default: 512)")

    # Get task status command
    status_parser = subparsers.add_parser("get-status", help="Get task status")
    status_parser.add_argument("--task-id", required=True, help="Task ID to check")

    # List tasks command
    list_parser = subparsers.add_parser("list-tasks", help="List all tasks")
    list_parser.add_argument("--status", help="Filter by status (pending, processing, completed, failed, cancelled)")

    # Cancel task command
    cancel_parser = subparsers.add_parser("cancel-task", help="Cancel a task")
    cancel_parser.add_argument("--task-id", required=True, help="Task ID to cancel")

    # Render prompt command
    render_parser = subparsers.add_parser("render-prompt", help="Render a prompt template")
    render_parser.add_argument("--template", required=True, help="Template name")
    render_parser.add_argument("--variables", required=True, help="Variables as JSON string")

    # Check health command
    health_parser = subparsers.add_parser("health", help="Check LM Studio health")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    client = AiCodingAgentClient(base_url=args.url)

    try:
        if args.command == "submit-task":
            result = await client.submit_coding_task(
                task=args.task,
                language=args.language,
                max_tokens=args.max_tokens
            )
            print(json.dumps(result, indent=2))

        elif args.command == "get-status":
            result = await client.get_task_status(task_id=args.task_id)
            print(json.dumps(result, indent=2))

        elif args.command == "list-tasks":
            result = await client.list_tasks(status=args.status)
            print(json.dumps(result, indent=2))

        elif args.command == "cancel-task":
            result = await client.cancel_task(task_id=args.task_id)
            print(json.dumps(result, indent=2))

        elif args.command == "render-prompt":
            try:
                variables = json.loads(args.variables)
            except json.JSONDecodeError:
                print("Error: Variables must be valid JSON")
                sys.exit(1)
            result = await client.render_prompt(args.template, variables)
            print(json.dumps(result, indent=2))

        elif args.command == "health":
            result = await client.check_lmstudio_health()
            print(json.dumps(result, indent=2))

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())