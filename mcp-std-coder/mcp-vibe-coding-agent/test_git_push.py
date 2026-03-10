#!/usr/bin/env python3
"""
Test script for git_push_llm_response function

This script tests the git_push_llm_response function with sample LLM responses
to verify that code is properly extracted and pushed to Git.
"""

import sys
import os
from pathlib import Path

# Add the dependencies directory to the path
sys.path.insert(0, str(Path(__file__).parent / "dependencies"))

from vibe_coder import (
    extract_code_from_llm_response,
    git_push_llm_response
)


def test_extract_code_from_llm_response():
    """Test code extraction from various LLM response formats"""
    print("=" * 60)
    print("Test: extract_code_from_llm_response")
    print("=" * 60)
    
    # Test 1: Markdown code block with python
    response1 = """Here is the solution:

```python
def hello_world():
    print("Hello, World!")

hello_world()
```

Let me know if you need any changes!
"""
    result1 = extract_code_from_llm_response(response1)
    expected1 = 'def hello_world():\n    print("Hello, World!")\n\nhello_world()'
    print(f"\n1. Markdown code block (Python): {'✅ PASS' if result1 == expected1 else '❌ FAIL'}")
    print(f"   Expected: {expected1[:50]}...")
    print(f"   Got: {result1[:50]}...")
    
    # Test 2: Markdown code block with no language specified
    response2 = """```
def add(a, b):
    return a + b
```"""
    result2 = extract_code_from_llm_response(response2)
    expected2 = 'def add(a, b):\n    return a + b'
    print(f"\n2. Code block without language: {'✅ PASS' if result2 == expected2 else '❌ FAIL'}")
    print(f"   Result: {result2[:50]}...")
    
    # Test 3: No code blocks (raw response)
    response3 = """The function should be something like this:

def process_data(data):
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result

This function multiplies positive numbers by 2."""
    result3 = extract_code_from_llm_response(response3)
    print(f"\n3. Raw response (fallback): {'✅ PASS' if result3 == response3 else '❌ FAIL'}")
    print(f"   Returns full response: {result3 == response3}")
    
    # Test 4: Multiple code blocks (should return first)
    response4 = """Here's the main function:

```python
def main():
    pass
```

And here's a helper:

```javascript
function helper() {
    return true;
}
```"""
    result4 = extract_code_from_llm_response(response4)
    expected4 = 'def main():\n    pass'
    print(f"\n4. Multiple code blocks (first returned): {'✅ PASS' if result4 == expected4 else '❌ FAIL'}")
    print(f"   Got Python block: {'def main()' in result4}")
    
    print("\n" + "=" * 60)


def test_git_push_llm_response():
    """Test git_push_llm_response with sample data"""
    print("\n" + "=" * 60)
    print("Test: git_push_llm_response")
    print("=" * 60)
    
    # Set the Git repository URL
    os.environ["MCP_GIT_REPO_URL"] = "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git"
    
    # Test 1: Simple Python code
    sample_code = '''def greet(name: str) -> str:
    """Greet the user with a personalized message."""
    return f"Hello, {name}! Welcome to the MCP system."

def calculate_sum(numbers: list) -> int:
    """Calculate the sum of a list of numbers."""
    return sum(numbers)

if __name__ == "__main__":
    print(greet("Developer"))
    print(f"Sum: {calculate_sum([1, 2, 3])}")
'''
    
    llm_response = f"""```python
{sample_code}
```"""
    
    print("\n1. Testing with simple Python code...")
    print(f"   Sample size: {len(sample_code)} characters")
    
    result = git_push_llm_response(
        task_id="test-git-push-001",
        llm_response=llm_response,
        language="python"
    )
    
    print(f"\n   Result:")
    print(f"   - success: {result.get('success', 'N/A')}")
    print(f"   - git_url: {result.get('git_url', 'N/A')}")
    print(f"   - file_path: {result.get('file_path', 'N/A')}")
    print(f"   - language: {result.get('language', 'N/A')}")
    print(f"   - code_preview: {result.get('code_preview', '')[:100]}...")
    if 'error' in result:
        print(f"   - error: {result['error']}")
    
    # Test 2: JavaScript code with markdown
    js_code = '''function greet(name) {
    return `Hello, ${name}! Welcome to the MCP system.`;
}

function calculateSum(numbers) {
    return numbers.reduce((acc, curr) => acc + curr, 0);
}

console.log(greet("Developer"));
console.log(`Sum: ${calculateSum([1, 2, 3])}`);'''
    
    llm_response_js = f"""```javascript
{js_code}
```"""
    
    print("\n2. Testing with JavaScript code...")
    result_js = git_push_llm_response(
        task_id="test-git-push-002",
        llm_response=llm_response_js,
        language="javascript"
    )
    
    print(f"\n   Result:")
    print(f"   - success: {result_js.get('success', 'N/A')}")
    print(f"   - file_path: {result_js.get('file_path', 'N/A')}")
    print(f"   - language: {result_js.get('language', 'N/A')}")
    if 'error' in result_js:
        print(f"   - error: {result_js['error']}")
    
    print("\n" + "=" * 60)


def test_with_vibe_code_async_workflow():
    """Simulate the vibe_code_async workflow"""
    print("\n" + "=" * 60)
    print("Test: vibe_code_async Workflow Simulation")
    print("=" * 60)
    
    os.environ["MCP_GIT_REPO_URL"] = "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git"
    
    # Simulate an LLM response (as if from LM Studio)
    simulated_llm_response = '''I'll create a simple function that calculates factorial.

```python
def factorial(n):
    """Calculate the factorial of a number."""
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    if n == 0 or n == 1:
        return 1
    return n * factorial(n - 1)

# Test the function
if __name__ == "__main__":
    for i in range(6):
        print(f"factorial({i}) = {factorial(i)}")
```'''
    
    print("\nSimulating vibe_code_async workflow:")
    print("1. LLM generates code...")
    print(f"   Response length: {len(simulated_llm_response)} chars")
    
    print("2. Extracting code...")
    extracted = extract_code_from_llm_response(simulated_llm_response)
    print(f"   Extracted length: {len(extracted)} chars")
    print(f"   Preview: {extracted[:80]}...")
    
    print("3. Pushing to Git...")
    result = git_push_llm_response(
        task_id="workflow-test-001",
        llm_response=simulated_llm_response,
        language="python"
    )
    
    print(f"\n4. Result:")
    print(f"   - success: {result.get('success')}")
    print(f"   - git_url: {result.get('git_url')}")
    
    print("\n" + "=" * 60)


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Git Push LLM Response Tests")
    print("=" * 60)
    
    try:
        test_extract_code_from_llm_response()
        test_git_push_llm_response()
        test_with_vibe_code_async_workflow()
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error running tests: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
