#!/usr/bin/env python3
"""
Test registry functionality for DNS server
"""
import asyncio
import json
import aiohttp


async def test_registry():
    registry_url = "http://localhost:3031"
    
    async with aiohttp.ClientSession() as session:
        # Start SSE listener to capture responses
        sse_responses = []
        
        async def listen_sse():
            try:
                async with session.get(f"{registry_url}/sse") as response:
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: ') and line_str != 'data: ':
                            data_part = line_str[6:]  # Remove 'data: ' prefix
                            if data_part.startswith('{'):  # It's a JSON object
                                try:
                                    json_data = json.loads(data_part)
                                    sse_responses.append(json_data)
                                    print(f"SSE Response: {json_data}")
                                except json.JSONDecodeError:
                                    print(f"SSE Data (non-JSON): {data_part}")
            except Exception as e:
                print(f"Error reading SSE: {e}")
        
        # Start SSE listener in background
        sse_task = asyncio.create_task(listen_sse())
        await asyncio.sleep(1)  # Allow SSE to connect
        
        # Request list of services from registry
        print("\nRequesting list of registered services...")
        list_payload = {
            "jsonrpc": "2.0",
            "id": "list_services_test",
            "method": "registry/list",
            "params": {}
        }
        
        try:
            async with session.post(f"{registry_url}/send", json=list_payload) as response:
                result = await response.json()
                print(f"Registry list request sent: {result}")
        except Exception as e:
            print(f"Error sending registry list request: {e}")
        
        # Wait to collect responses
        await asyncio.sleep(3)
        
        # Cancel SSE listener
        sse_task.cancel()
        try:
            await sse_task
        except asyncio.CancelledError:
            pass
        
        # Print collected responses
        print(f"\nCollected {len(sse_responses)} SSE responses:")
        for i, resp in enumerate(sse_responses):
            if 'list_services_test' in str(resp.get('id', '')):
                print(f"  Matching response {i+1}: {resp}")


if __name__ == "__main__":
    asyncio.run(test_registry())