"""
Test suite for the Implementation Engineer Agent
Verifies that all tools work correctly and integrate with the MCP server
"""
import json
import subprocess
import time
from implementation_engineer import (
    git_checkout_branch,
    generate_code_from_spec,
    implement_feature,
    apply_coding_standards,
    generate_unit_tests,
    refactor_code,
    GitCheckoutBranchArgs,
    GenerateCodeFromSpecArgs,
    ImplementFeatureArgs,
    ApplyCodingStandardsArgs,
    GenerateUnitTestsArgs,
    RefactorCodeArgs
)


def test_git_checkout_branch():
    """Test the git_checkout_branch functionality"""
    print("Testing git_checkout_branch...")
    
    # This test would require an actual git repository to work properly
    # For now, we'll just verify the function exists and can be called
    try:
        # Create a temporary directory for testing
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize a git repo for testing
            os.chdir(tmpdir)
            subprocess.run(['git', 'init'], check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Test User'], check=True, capture_output=True)
            
            # Create an initial commit
            with open('README.md', 'w') as f:
                f.write('# Test Repo\n')
            subprocess.run(['git', 'add', 'README.md'], check=True, capture_output=True)
            subprocess.run(['git', 'commit', '-m', 'Initial commit'], check=True, capture_output=True)
            
            # Create a test branch
            subprocess.run(['git', 'checkout', '-b', 'test-branch'], check=True, capture_output=True)
            
            # Now test checking out the branch
            args = GitCheckoutBranchArgs(
                repository_path=tmpdir,
                branch_name="main",
                create_if_not_exists=False,
                remote_tracking=False
            )
            result = git_checkout_branch(args)
            print(f"Git checkout result: {result}")
            assert result["success"] == True
            print("✓ git_checkout_branch test passed")
    except Exception as e:
        print(f"✗ git_checkout_branch test failed: {e}")
        return False
    
    return True


def test_generate_code_from_spec():
    """Test the generate_code_from_spec functionality"""
    print("\nTesting generate_code_from_spec...")
    
    try:
        args = GenerateCodeFromSpecArgs(
            specifications="Create a simple calculator class with add, subtract, multiply, and divide methods",
            programming_language="Python",
            framework="None",
            coding_standards="Follow PEP 8 guidelines",
            existing_codebase_context="Simple utility classes in the project follow snake_case naming"
        )
        result = generate_code_from_spec(args)
        print(f"Generate code from spec result: {result['success']}")
        assert result["success"] == True
        assert "generated_code" in result
        print("✓ generate_code_from_spec test passed")
    except Exception as e:
        print(f"✗ generate_code_from_spec test failed: {e}")
        return False
    
    return True


def test_implement_feature():
    """Test the implement_feature functionality"""
    print("\nTesting implement_feature...")
    
    try:
        args = ImplementFeatureArgs(
            feature_requirements="Implement a user authentication system with login and logout functionality",
            architectural_guidelines="Follow MVC pattern, use dependency injection, implement proper error handling",
            dependencies=["database", "session management"],
            performance_requirements=["response time < 200ms", "support 1000 concurrent users"]
        )
        result = implement_feature(args)
        print(f"Implement feature result: {result['success']}")
        assert result["success"] == True
        assert "implemented_code" in result
        print("✓ implement_feature test passed")
    except Exception as e:
        print(f"✗ implement_feature test failed: {e}")
        return False
    
    return True


def test_apply_coding_standards():
    """Test the apply_coding_standards functionality"""
    print("\nTesting apply_coding_standards...")
    
    sample_code = """
def bad_func( x,y ):
    result=x+y
    return result
"""
    
    try:
        args = ApplyCodingStandardsArgs(
            code=sample_code,
            style_guide="Follow PEP 8: use 4 spaces for indentation, space around operators, proper function naming",
            language="Python",
            existing_patterns=["snake_case", "4 space indentation", "space around operators"]
        )
        result = apply_coding_standards(args)
        print(f"Apply coding standards result: {result['success']}")
        assert result["success"] == True
        assert "standardized_code" in result
        print("✓ apply_coding_standards test passed")
    except Exception as e:
        print(f"✗ apply_coding_standards test failed: {e}")
        return False
    
    return True


def test_generate_unit_tests():
    """Test the generate_unit_tests functionality"""
    print("\nTesting generate_unit_tests...")
    
    sample_code = """
class Calculator:
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
"""
    
    try:
        args = GenerateUnitTestsArgs(
            code=sample_code,
            requirements="Test all methods of the Calculator class with positive, negative, and zero values",
            test_framework="pytest",
            coverage_requirements=["all_methods_covered", "edge_cases_tested"]
        )
        result = generate_unit_tests(args)
        print(f"Generate unit tests result: {result['success']}")
        assert result["success"] == True
        assert "generated_tests" in result
        print("✓ generate_unit_tests test passed")
    except Exception as e:
        print(f"✗ generate_unit_tests test failed: {e}")
        return False
    
    return True


def test_refactor_code():
    """Test the refactor_code functionality"""
    print("\nTesting refactor_code...")
    
    sample_code = """
def calculate_total(items):
    total = 0
    for i in range(len(items)):
        total += items[i]['price']
    return total
"""
    
    try:
        args = RefactorCodeArgs(
            code=sample_code,
            refactoring_goals=["improve readability", "use more pythonic approach", "better performance"],
            constraints=["don't change function signature", "maintain same functionality"],
            existing_patterns=["list comprehensions", "built-in functions"]
        )
        result = refactor_code(args)
        print(f"Refactor code result: {result['success']}")
        assert result["success"] == True
        assert "refactored_code" in result
        print("✓ refactor_code test passed")
    except Exception as e:
        print(f"✗ refactor_code test failed: {e}")
        return False
    
    return True


def test_integration_with_mcp_server():
    """Test that the Implementation Engineer tools are properly integrated with the MCP server"""
    print("\nTesting MCP server integration...")
    
    try:
        # Import the registration function
        from implementation_engineer import register_implementation_engineer_tools
        from mcp_std_server.handlers.server_handlers import McpServerHandlers
        
        # Create a server handlers instance
        handlers = McpServerHandlers()
        
        # Register the implementation engineer tools
        register_implementation_engineer_tools(handlers)
        
        # Check that the tools were added
        tool_names = [tool["name"] for tool in handlers.tools]
        
        required_tools = [
            "git_checkout_branch",
            "generate_code_from_spec",
            "implement_feature",
            "apply_coding_standards",
            "generate_unit_tests",
            "refactor_code"
        ]
        
        for tool_name in required_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not found in server handlers"
        
        print(f"Found {len([t for t in required_tools if t in tool_names])}/{len(required_tools)} required tools in server")
        print("✓ MCP server integration test passed")
        return True
    except Exception as e:
        print(f"✗ MCP server integration test failed: {e}")
        return False


def run_all_tests():
    """Run all tests for the Implementation Engineer Agent"""
    print("Running Implementation Engineer Agent tests...\n")
    
    tests = [
        test_git_checkout_branch,
        test_generate_code_from_spec,
        test_implement_feature,
        test_apply_coding_standards,
        test_generate_unit_tests,
        test_refactor_code,
        test_integration_with_mcp_server
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        time.sleep(0.5)  # Brief pause between tests
    
    print(f"\nTest Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Implementation Engineer Agent is working correctly.")
        return True
    else:
        print(f"❌ {total - passed} tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)