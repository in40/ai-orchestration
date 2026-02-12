#!/usr/bin/env python3
"""
Comprehensive test script for MCP Explorer functionality.
"""
import asyncio
import sys
from mcp_explorer.registry_adapters import RegistryManager, LocalhostRegistryAdapter
from mcp_explorer.streamable_http import StreamableHTTPClient
from mcp_explorer.form_generator import SchemaFormGenerator

async def test_registry_functionality():
    """Test registry functionality."""
    print("=== Testing Registry Functionality ===")
    
    # Test individual localhost adapter
    print("\n1. Testing LocalhostRegistryAdapter...")
    adapter = LocalhostRegistryAdapter()
    try:
        servers = await adapter.search_servers()
        print(f"   ✓ Found {len(servers)} servers with localhost adapter")
        for server in servers:
            print(f"     - {server['name']}: {server['url']}")
    except Exception as e:
        print(f"   ✗ Error with localhost adapter: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test registry manager
    print("\n2. Testing RegistryManager...")
    manager = RegistryManager()
    try:
        all_servers = await manager.search_all_servers()
        print(f"   ✓ RegistryManager found {len(all_servers)} servers")
        for server in all_servers:
            print(f"     - {server['name']}: {server['url']}")
    except Exception as e:
        print(f"   ✗ Error with registry manager: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

async def test_streamable_http_client():
    """Test Streamable HTTP client functionality."""
    print("\n=== Testing Streamable HTTP Client ===")
    
    client = StreamableHTTPClient("http://localhost:3031/mcp")
    try:
        print("\n1. Testing client connection...")
        await client.connect()
        print("   ✓ Client connected successfully")
        
        print("\n2. Testing initialize method...")
        init_result = await client.initialize()
        print(f"   ✓ Initialize successful: {init_result.get('result', {}).get('serverInfo', {}).get('name', 'Unknown')}")
        
        print("\n3. Testing initialized handshake...")
        await client.initialized(init_result.get('result', {}))
        print("   ✓ Initialized handshake completed")
        
        print("\n4. Testing tools/list method...")
        tools_result = await client.list_tools()
        tools = tools_result.get('result', {}).get('tools', [])
        print(f"   ✓ Found {len(tools)} tools")
        for tool in tools:
            print(f"     - {tool.get('name', 'unnamed')}: {tool.get('description', 'No description')}")
        
        await client.close()
        print("   ✓ Client disconnected successfully")
        return True
        
    except Exception as e:
        print(f"   ✗ Error with Streamable HTTP client: {e}")
        import traceback
        traceback.print_exc()
        try:
            await client.close()
        except:
            pass
        return False

def test_form_generator():
    """Test form generator functionality."""
    print("\n=== Testing Form Generator ===")
    
    # Example schema for testing
    test_schema = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "A message to send"
            },
            "count": {
                "type": "integer",
                "description": "Number of times to repeat",
                "default": 1
            },
            "enabled": {
                "type": "boolean",
                "description": "Whether to enable the feature"
            }
        },
        "required": ["message"]
    }
    
    try:
        print("\n1. Testing form field generation...")
        fields = SchemaFormGenerator.generate_form_fields(test_schema, "test")
        print(f"   ✓ Generated {len(fields)} form fields")
        
        print("\n2. Testing form validation...")
        # Simulate collecting values
        values = {
            "message": "Hello World",
            "count": 5,
            "enabled": True
        }
        is_valid, errors = SchemaFormGenerator.validate_against_schema(values, test_schema)
        if is_valid:
            print("   ✓ Form validation passed")
        else:
            print(f"   ✗ Form validation failed: {errors}")
            return False
        
        return True
    except Exception as e:
        print(f"   ✗ Error with form generator: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests."""
    print("Starting comprehensive MCP Explorer testing...\n")
    
    all_passed = True
    
    # Test registry functionality
    registry_ok = await test_registry_functionality()
    all_passed &= registry_ok
    
    # Test Streamable HTTP client
    client_ok = await test_streamable_http_client()
    all_passed &= client_ok
    
    # Test form generator
    form_ok = test_form_generator()
    all_passed &= form_ok
    
    print(f"\n=== Test Summary ===")
    print(f"Registry functionality: {'PASS' if registry_ok else 'FAIL'}")
    print(f"Streamable HTTP client: {'PASS' if client_ok else 'FAIL'}")
    print(f"Form generator: {'PASS' if form_ok else 'FAIL'}")
    print(f"Overall result: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)