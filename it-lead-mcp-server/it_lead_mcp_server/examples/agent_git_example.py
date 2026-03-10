"""
Example Implementation of Agent Git Push Integration

This example demonstrates how MCP agents can use AgentGitHelper to push
results directly to Git repositories.

Usage:
    python agent_git_example.py
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from it_lead_mcp_server.utils.agent_git_helper import AgentGitHelper, get_agent_git_helper


def example_direct_initialization():
    """Example 1: Direct initialization of AgentGitHelper"""
    print("=" * 60)
    print("Example 1: Direct Initialization")
    print("=" * 60)

    # Get repo URL from environment or use default
    repo_url = os.environ.get(
        "MCP_GIT_REPO_URL",
        "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git"
    )

    helper = AgentGitHelper(
        repo_url=repo_url,
        repo_path="/var/mcp-results",
        commit_user="mcp-agent",
        commit_email="mcp-agent@localhost",
        branch_prefix="agent/"
    )

    # Initialize for a specific agent
    success = helper.initialize_repo("implementation-engineer")

    if success:
        print("✅ Repository initialized successfully")
        print(f"   Branch: {helper.agent_branch}")
    else:
        print("❌ Failed to initialize repository")


def example_helper_function():
    """Example 2: Using get_agent_git_helper() with caching"""
    print("\n" + "=" * 60)
    print("Example 2: Helper Function with Caching")
    print("=" * 60)

    repo_url = os.environ.get(
        "MCP_GIT_REPO_URL",
        "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git"
    )

    # Get helper for Implementation Engineer
    impl_helper = get_agent_git_helper(
        agent_name="implementation-engineer",
        repo_url=repo_url
    )
    print(f"✅ Implementation Engineer helper: {impl_helper.agent_branch}")

    # Get helper for Requirements Engineer (same repo, cached)
    req_helper = get_agent_git_helper(
        agent_name="requirements-engineer",
        repo_url=repo_url
    )
    print(f"✅ Requirements Engineer helper: {req_helper.agent_branch}")

    print("\n   Note: Both helpers share the same repository clone")


def example_store_code_result():
    """Example 3: Store a code result"""
    print("\n" + "=" * 60)
    print("Example 3: Store Code Result")
    print("=" * 60)

    repo_url = os.environ.get(
        "MCP_GIT_REPO_URL",
        "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git"
    )

    helper = get_agent_git_helper(
        agent_name="implementation-engineer",
        repo_url=repo_url
    )

    # Sample Python code
    sample_code = '''def hello_world(name: str) -> str:
    """Greet the user with a personalized message."""
    return f"Hello, {name}! Welcome to the MCP system."

def calculate_sum(numbers: list) -> int:
    """Calculate the sum of a list of numbers."""
    return sum(numbers)

if __name__ == "__main__":
    # Test the functions
    print(hello_world("Developer"))
    print(f"Sum: {calculate_sum([1, 2, 3, 4, 5])}")
'''

    result = helper.store_code_result(
        task_id="example-task-001",
        code=sample_code,
        language="python",
        filename="hello_world",
        metadata={
            "agent": "implementation-engineer",
            "tool": "generate_code_from_spec",
            "specifications": "Create a simple greeting and sum calculation functions"
        }
    )

    print(f"\n   Result: {'✅ Success' if result['success'] else '❌ Failed'}")
    if result['success']:
        print(f"   Git URL: {result['git_url']}")
        print(f"   Commit:  {result['commit_msg']}")
    else:
        print(f"   Error:   {result.get('error', 'Unknown error')}")


def example_store_document_result():
    """Example 4: Store a document result"""
    print("\n" + "=" * 60)
    print("Example 4: Store Document Result")
    print("=" * 60)

    repo_url = os.environ.get(
        "MCP_GIT_REPO_URL",
        "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git"
    )

    helper = get_agent_git_helper(
        agent_name="requirements-engineer",
        repo_url=repo_url
    )

    # Sample requirements document
    sample_document = '''# Requirements Document

## Feature: User Authentication

### Overview
Implement user authentication with email and password.

### Requirements

1. **User Registration**
   - Email must be unique
   - Password must be at least 8 characters
   - Store password securely (hashing)

2. **User Login**
   - Accept email and password
   - Validate credentials
   - Return JWT token on success

3. **Security**
   - Use HTTPS for all authentication endpoints
   - Implement rate limiting
   - Store passwords using bcrypt

### Acceptance Criteria
- [ ] User can register with valid email and password
- [ ] Duplicate email registration is rejected
- [ ] User can login with valid credentials
- [ ] Invalid credentials return 401 status
- [ ] Passwords are hashed before storage
'''

    result = helper.store_document_result(
        task_id="example-task-002",
        content=sample_document,
        document_type="markdown",
        filename="auth_requirements",
        metadata={
            "agent": "requirements-engineer",
            "tool": "analyze_requirements",
            "stakeholder_inputs": "User needs to authenticate with email/password"
        }
    )

    print(f"\n   Result: {'✅ Success' if result['success'] else '❌ Failed'}")
    if result['success']:
        print(f"   Git URL: {result['git_url']}")
    else:
        print(f"   Error:   {result.get('error', 'Unknown error')}")


def example_store_config_result():
    """Example 5: Store a configuration result"""
    print("\n" + "=" * 60)
    print("Example 5: Store Config Result")
    print("=" * 60)

    repo_url = os.environ.get(
        "MCP_GIT_REPO_URL",
        "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git"
    )

    helper = get_agent_git_helper(
        agent_name="devops-engineer",
        repo_url=repo_url
    )

    # Sample deployment configuration
    sample_config = '''# Deployment Configuration
environment: production
region: us-east-1

resources:
  instances:
    - name: api-server
      type: t3.medium
      count: 3
    - name: worker
      type: t3.small
      count: 2

services:
  api:
    port: 8080
    health_check: /health
    restart: always

database:
  type: postgres
  version: 14
  storage: 100GB

monitoring:
  prometheus: enabled
  grafana: enabled
  alerts:
    - cpu_usage > 80%
    - memory_usage > 85%
'''

    result = helper.store_config_result(
        task_id="example-task-003",
        content=sample_config,
        config_type="yaml",
        filename="deployment",
        metadata={
            "agent": "devops-engineer",
            "tool": "orchestrate_deployments",
            "target_environments": ["production"]
        }
    )

    print(f"\n   Result: {'✅ Success' if result['success'] else '❌ Failed'}")
    if result['success']:
        print(f"   Git URL: {result['git_url']}")
    else:
        print(f"   Error:   {result.get('error', 'Unknown error')}")


def example_full_agent_workflow():
    """Example 6: Complete agent workflow with Git push"""
    print("\n" + "=" * 60)
    print("Example 6: Complete Agent Workflow")
    print("=" * 60)

    repo_url = os.environ.get(
        "MCP_GIT_REPO_URL",
        "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git"
    )

    class ExampleImplementationAgent:
        """Example agent that uses Git push for all results"""

        def __init__(self):
            self.git_helper = get_agent_git_helper(
                agent_name="implementation-engineer",
                repo_url=repo_url
            )
            self.current_task_id = None

        def generate_code(self, task_id: str, specifications: str, language: str) -> dict:
            """Simulate code generation with Git push"""
            self.current_task_id = task_id

            # Simulate LLM code generation
            code = f'''# Generated Code
# Task: {specifications[:50]}...
# Language: {language}

def solve_problem():
    """Solve the problem based on specifications."""
    # Implementation goes here
    return "Solution generated for: {specifications}"

if __name__ == "__main__":
    result = solve_problem()
    print(result)
'''

            # Store in Git
            result = self.git_helper.store_code_result(
                task_id=task_id,
                code=code,
                language=language,
                filename="generated_solution",
                metadata={
                    "specifications": specifications,
                    "agent": "implementation-engineer"
                }
            )

            # Return result with Git URL (not the code itself)
            if result['success']:
                return {
                    "status": "success",
                    "code_url": result['git_url'],
                    "message": "Code generated and stored in Git"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to store code: {result.get('error')}"
                }

        def write_tests(self, task_id: str, code_url: str) -> dict:
            """Generate tests with Git push"""
            self.current_task_id = task_id

            # Generate test file
            test_code = '''import pytest

def test_solve_problem():
    """Test the solve_problem function."""
    result = solve_problem()
    assert result.startswith("Solution generated")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
'''

            result = self.git_helper.store_code_result(
                task_id=task_id,
                code=test_code,
                language="python",
                filename="test_solution",
                metadata={
                    "code_reference": code_url,
                    "agent": "implementation-engineer"
                }
            )

            if result['success']:
                return {
                    "status": "success",
                    "test_url": result['git_url'],
                    "message": "Tests generated and stored in Git"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to store tests: {result.get('error')}"
                }

    # Simulate agent workflow
    agent = ExampleImplementationAgent()

    print("\n1️⃣  Generating code...")
    code_result = agent.generate_code(
        task_id="example-workflow-001",
        specifications="Create a function to solve a complex problem",
        language="python"
    )
    print(f"   {code_result['message']}")
    if code_result.get('code_url'):
        print(f"   📁 {code_result['code_url']}")

    print("\n2️⃣  Writing tests...")
    test_result = agent.write_tests(
        task_id="example-workflow-002",
        code_url=code_result.get('code_url', '')
    )
    print(f"   {test_result['message']}")
    if test_result.get('test_url'):
        print(f"   📁 {test_result['test_url']}")

    print("\n✅ Agent workflow completed successfully!")


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("Agent Git Push Integration Examples")
    print("=" * 60)

    # Note: These examples require Git access to the repository
    # Set MCP_GIT_REPO_URL environment variable if different from default

    try:
        example_direct_initialization()
        example_helper_function()
        example_store_code_result()
        example_store_document_result()
        example_store_config_result()
        example_full_agent_workflow()

        print("\n" + "=" * 60)
        print("All examples completed!")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\n⚠️  Examples interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
