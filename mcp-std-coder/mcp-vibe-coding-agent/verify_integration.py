"""
Simple verification that the Implementation Engineer Agent tools are properly integrated
"""
import json
from mcp_std_server.handlers.server_handlers import McpServerHandlers
from implementation_engineer import register_implementation_engineer_tools

def test_tools_registered():
    """Verify that Implementation Engineer tools are registered with the server"""
    print("Testing Implementation Engineer tools registration...")
    
    # Create a server handlers instance
    handlers = McpServerHandlers()
    
    # Register the implementation engineer tools
    register_implementation_engineer_tools(handlers)
    
    # Get all tool names
    tool_names = [tool["name"] for tool in handlers.tools]
    
    # Required Implementation Engineer tools
    required_tools = [
        "git_checkout_branch",
        "generate_code_from_spec",
        "implement_feature",
        "apply_coding_standards",
        "generate_unit_tests",
        "refactor_code"
    ]
    
    print(f"Found {len(handlers.tools)} total tools in server")
    print(f"Required Implementation Engineer tools: {required_tools}")
    
    missing_tools = []
    for tool_name in required_tools:
        if tool_name not in tool_names:
            missing_tools.append(tool_name)
        else:
            print(f"  ✓ {tool_name}")
    
    if missing_tools:
        print(f"  ✗ Missing tools: {missing_tools}")
        return False
    else:
        print("  ✓ All Implementation Engineer tools are registered")
        return True

def test_tool_schemas():
    """Verify that the tools have correct input schemas"""
    print("\nTesting tool input schemas...")
    
    handlers = McpServerHandlers()
    register_implementation_engineer_tools(handlers)
    
    # Find the tools
    tools_by_name = {tool["name"]: tool for tool in handlers.tools}
    
    required_tools = [
        "git_checkout_branch",
        "generate_code_from_spec",
        "implement_feature",
        "apply_coding_standards",
        "generate_unit_tests",
        "refactor_code"
    ]
    
    all_good = True
    for tool_name in required_tools:
        if tool_name not in tools_by_name:
            print(f"  ✗ {tool_name}: NOT FOUND")
            all_good = False
            continue
            
        tool = tools_by_name[tool_name]
        if "inputSchema" not in tool:
            print(f"  ✗ {tool_name}: NO INPUT SCHEMA")
            all_good = False
        else:
            print(f"  ✓ {tool_name}: HAS INPUT SCHEMA")
    
    return all_good

if __name__ == "__main__":
    print("Verifying Implementation Engineer Agent integration...\n")
    
    test1_passed = test_tools_registered()
    test2_passed = test_tool_schemas()
    
    if test1_passed and test2_passed:
        print("\n🎉 All verification tests passed!")
        print("The Implementation Engineer Agent is properly integrated with the MCP server.")
    else:
        print("\n❌ Some verification tests failed.")
        exit(1)