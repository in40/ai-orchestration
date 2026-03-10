#!/usr/bin/env python3
"""
Test script for Dynamic MCP Agent & Tool Discovery

This script tests the new dynamic discovery feature that:
1. Discovers all registered agents via MCP Registry Server
2. Introspects each agent's tools via MCP tools/list method
3. Returns complete agent info with full tool schemas

Usage:
    python3 test_dynamic_discovery.py
"""

import sys
sys.path.insert(0, '/root/qwen/base/it-lead-mcp-server')

from it_lead_mcp_server.utils.mcp_registry_client import McpRegistryClient

def test_discovery():
    """Test dynamic agent and tool discovery"""
    print("="*70)
    print("DYNAMIC MCP AGENT & TOOL DISCOVERY TEST")
    print("="*70)
    
    # Initialize MCP Registry Client
    print("\n📡 Initializing MCP Registry Client...")
    client = McpRegistryClient("http://127.0.0.1:3031/mcp")
    
    # Discover all agents with tools
    print("\n🔍 Discovering agents and tools via MCP protocol...")
    agents = client.discover_all_agents_with_tools(use_cache=False)
    
    print(f"\n📊 DISCOVERY RESULTS")
    print(f"   Total agents found: {len(agents)}")
    print(f"   Online agents: {sum(1 for a in agents if a['status'] == 'online')}")
    print(f"   Offline agents: {sum(1 for a in agents if a['status'] == 'offline')}")
    
    # Display each agent
    print("\n" + "="*70)
    print("AGENT DETAILS")
    print("="*70)
    
    for agent in agents:
        status_icon = "✅" if agent["status"] == "online" else "❌" if agent["status"] == "offline" else "⚠️"
        print(f"\n{status_icon} {agent['name']}")
        print(f"   Status: {agent['status']}")
        print(f"   Endpoint: {agent.get('endpoint', 'N/A')}")
        print(f"   Description: {agent.get('description', 'N/A')[:100]}...")
        
        if agent["status"] == "online":
            tools = agent.get("tools", [])
            print(f"   Tools ({len(tools)}):")
            for tool in tools[:5]:  # Show first 5 tools
                tool_name = tool.get("name", "unknown")
                tool_desc = tool.get("description", "No description")[:60]
                input_schema = tool.get("inputSchema", {})
                required = input_schema.get("required", [])
                
                print(f"     - `{tool_name}`: {tool_desc}...")
                if required:
                    print(f"       Required params: {', '.join(required)}")
            
            if len(tools) > 5:
                print(f"     ... and {len(tools) - 5} more tools")
        elif agent["status"] == "offline":
            print(f"   Error: {agent.get('error', 'Unknown error')}")
    
    # Test caching
    print("\n" + "="*70)
    print("CACHE TEST")
    print("="*70)
    print("\n🔄 Testing cache (second call should use cache)...")
    agents_cached = client.discover_all_agents_with_tools(use_cache=True)
    print(f"   Cached agents: {len(agents_cached)}")
    
    # Test specific agent tools
    print("\n" + "="*70)
    print("SPECIFIC AGENT TOOLS TEST")
    print("="*70)
    print("\n🔍 Getting tools for 'implementation-engineer'...")
    impl_tools = client.get_agent_tools_with_schemas("implementation-engineer", use_cache=True)
    print(f"   Found {len(impl_tools)} tools")
    for tool in impl_tools[:3]:
        print(f"   - {tool.get('name')}: {tool.get('description', 'N/A')[:50]}...")
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)
    
    # Summary
    online_count = sum(1 for a in agents if a["status"] == "online")
    total_tools = sum(len(a.get("tools", [])) for a in agents if a["status"] == "online")
    
    print(f"\n✅ SUCCESS: Discovered {online_count} online agents with {total_tools} total tools")
    print("\n📝 NOTES:")
    print("   - Tool schemas include name, description, and inputSchema")
    print("   - Results are cached for 5 minutes")
    print("   - Offline agents are marked but don't break discovery")
    
    return agents

if __name__ == "__main__":
    try:
        agents = test_discovery()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
