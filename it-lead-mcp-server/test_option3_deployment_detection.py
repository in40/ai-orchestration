#!/usr/bin/env python3
"""
Test script to verify Option 3: Post-processing deployment keyword detection
This tests that rule-based routing (high confidence matches) still includes
devops-engineer in workflow when deployment keywords are detected.
"""

import re

def check_deployment_keywords(task_description: str) -> bool:
    """Check if task description contains deployment keywords"""
    deployment_keywords = [
        "deploy", "deployment", "publish", "make accessible", "run as website",
        "host online", "make it live", "container", "docker", "production"
    ]
    return any(keyword in task_description.lower() for keyword in deployment_keywords)


def check_deploy_flag(metadata: dict) -> bool:
    """Check for deploy_after_implementation flag in metadata"""
    if not metadata:
        return False
    
    # Direct check
    if metadata.get("deploy_after_implementation", False):
        return True
    
    # Nested check
    if metadata.get("original_arguments"):
        orig_args = metadata.get("original_arguments", {})
        if orig_args.get("metadata", {}).get("deploy_after_implementation", False):
            return True
        if orig_args.get("original_arguments", {}).get("metadata", {}).get("deploy_after_implementation", False):
            return True
    
    return False


def create_workflow_for_rule_based_routing(primary_agent: str, tool: str, 
                                           task_description: str, metadata: dict):
    """
    Simulate Option 3: Post-processing check for deployment keywords
    in rule-based routing (when LLM planning is skipped)
    """
    needs_deployment = check_deployment_keywords(task_description)
    deploy_flag = check_deploy_flag(metadata)
    
    if needs_deployment or deploy_flag:
        # Create workflow sequence with devops-engineer
        llm_plan = {
            "workflow_sequence": [primary_agent, "devops-engineer"],
            "tools": {
                primary_agent: tool if tool != "vibe_code" else "vibe_code_async",
                "devops-engineer": "deploy_web_application"
            },
            "primary_agent": primary_agent,
            "reasoning": "Rule-based routing with auto-detected deployment requirement"
        }
        return llm_plan
    else:
        return None


# Test cases
test_cases = [
    # Test 1: Deployment keywords
    {
        "task": "Create a website to deploy my game online",
        "metadata": {},
        "expected_workflow": ["implementation-engineer", "devops-engineer"],
        "description": "Task with 'deploy' keyword"
    },
    # Test 2: No deployment keywords
    {
        "task": "Write a Python script to calculate fibonacci",
        "metadata": {},
        "expected_workflow": None,
        "description": "Task without deployment keywords"
    },
    # Test 3: deploy_after_implementation flag
    {
        "task": "Create a flappy bird game in Python",
        "metadata": {"deploy_after_implementation": True},
        "expected_workflow": ["implementation-engineer", "devops-engineer"],
        "description": "Task with deploy flag in metadata"
    },
    # Test 4: Nested deploy flag
    {
        "task": "Create a pacman game",
        "metadata": {
            "original_arguments": {
                "metadata": {"deploy_after_implementation": True}
            }
        },
        "expected_workflow": ["implementation-engineer", "devops-engineer"],
        "description": "Task with nested deploy flag"
    },
    # Test 5: Publishing keyword
    {
        "task": "Build a website and publish it online",
        "metadata": {},
        "expected_workflow": ["implementation-engineer", "devops-engineer"],
        "description": "Task with 'publish' keyword"
    },
    # Test 6: Docker keyword
    {
        "task": "Create a web app and run it in a docker container",
        "metadata": {},
        "expected_workflow": ["implementation-engineer", "devops-engineer"],
        "description": "Task with 'docker' keyword"
    },
    # Test 7: Production keyword
    {
        "task": "Make a website accessible in production",
        "metadata": {},
        "expected_workflow": ["implementation-engineer", "devops-engineer"],
        "description": "Task with 'production' keyword"
    },
]

print("=" * 70)
print("Option 3: Post-Processing Deployment Detection - Test Suite")
print("=" * 70)

passed = 0
failed = 0

for i, test in enumerate(test_cases, 1):
    print(f"\nTest {i}: {test['description']}")
    print("-" * 70)
    
    result = create_workflow_for_rule_based_routing(
        primary_agent="implementation-engineer",
        tool="vibe_code_async",
        task_description=test["task"],
        metadata=test["metadata"]
    )
    
    if test["expected_workflow"] is None:
        # Should NOT create workflow
        if result is None:
            print(f"✅ PASS: No workflow created (as expected)")
            passed += 1
        else:
            print(f"❌ FAIL: Workflow created when it shouldn't be: {result['workflow_sequence']}")
            failed += 1
    else:
        # Should create workflow with devops-engineer
        if result and result["workflow_sequence"] == test["expected_workflow"]:
            print(f"✅ PASS: Workflow created: {result['workflow_sequence']}")
            print(f"   Tools: {result['tools']}")
            passed += 1
        else:
            print(f"❌ FAIL: Expected {test['expected_workflow']}, got {result['workflow_sequence'] if result else 'None'}")
            failed += 1

print("\n" + "=" * 70)
print(f"Results: {passed} passed, {failed} failed")
print("=" * 70)

if failed == 0:
    print("\n✅ All tests passed! Option 3 implementation is correct.")
    exit(0)
else:
    print(f"\n❌ {failed} test(s) failed!")
    exit(1)
