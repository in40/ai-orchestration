#!/usr/bin/env python3
"""
Test ping functionality to verify server connectivity.
"""
import asyncio
from mcp_explorer.streamable_http import StreamableHTTPClient

async def test_ping():
    """Test ping functionality."""
    print("Testing ping method...")
    
    client = StreamableHTTPClient("http://localhost:3031/mcp")
    try:
        await client.connect()
        
        # Initialize first
        init_result = await client.initialize()
        await client.initialized(init_result.get('result', {}))
        
        # Test ping
        ping_result = await client.ping()
        print(f"Ping result: {ping_result}")
        
        await client.close()
        return True
    except Exception as e:
        print(f"Error with ping: {e}")
        import traceback
        traceback.print_exc()
        try:
            await client.close()
        except:
            pass
        return False

if __name__ == "__main__":
    success = asyncio.run(test_ping())
    print(f"Ping test: {'SUCCESS' if success else 'FAILED'}")