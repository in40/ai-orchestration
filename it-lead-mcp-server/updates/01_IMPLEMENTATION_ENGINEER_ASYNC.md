# Implementation Engineer - Async Task Management Implementation

## Overview

This document describes the **Implementation Engineer agent** specific implementation for async task management. Follow the common base implementation in `00_COMMON_BASE_IMPLEMENTATION.md` first, then apply these agent-specific configurations.

## Agent Identity

- **Agent ID**: `implementation-engineer`
- **Agent Name**: `Implementation Engineer MCP Server`
- **Default Port**: `3060`
- **Default Endpoint**: `http://localhost:3060/mcp`

## Available Tools (Async Support)

The Implementation Engineer should support these tools asynchronously:

| Tool Name | Description | Input Parameters | Output |
|-----------|-------------|------------------|--------|
| `implement_feature` | Implement specific features following architectural guidelines | `feature_requirements`, `architectural_guidelines`, `dependencies`, `performance_requirements` | Generated code files |
| `generate_code_from_spec` | Generate code from architectural specifications | `specifications`, `programming_language`, `framework`, `coding_standards` | Generated code files |
| `generate_unit_tests` | Generate unit tests for code | `code`, `requirements`, `test_framework`, `coverage_requirements` | Test files |
| `refactor_code` | Refactor code for improvements | `code`, `refactoring_goals`, `constraints`, `existing_patterns` | Refactored code |
| `apply_coding_standards` | Apply coding standards to code | `code`, `style_guide`, `language`, `existing_patterns` | Formatted code |
| `git_checkout_branch` | Checkout a Git branch | `repository_path`, `branch_name`, `create_if_not_exists` | Git operation result |

## Tool Executor Configuration

**File**: `utils/tool_executor.py` (Implementation Engineer specific)

```python
class ImplementationEngineerToolExecutor(ToolExecutor):
    """Tool executor for Implementation Engineer agent"""

    def __init__(self, server_instance):
        # Map tool names to server handler methods
        available_tools = {
            "implement_feature": server_instance.handle_implement_feature_async,
            "generate_code_from_spec": server_instance.handle_generate_code_from_spec_async,
            "generate_unit_tests": server_instance.handle_generate_unit_tests_async,
            "refactor_code": server_instance.handle_refactor_code_async,
            "apply_coding_standards": server_instance.handle_apply_coding_standards_async,
            "git_checkout_branch": server_instance.handle_git_checkout_branch_async
        }
        super().__init__(available_tools)
```

## Async Tool Handlers

**File**: `handlers/async_tool_handlers.py` (new file)

```python
"""
Async Tool Handlers for Implementation Engineer
Wraps existing sync tools for async execution
"""
import asyncio
from typing import Dict, Any


class AsyncToolHandlers:
    """Async wrappers for Implementation Engineer tools"""

    def __init__(self, server_instance):
        self.server = server_instance
        self.llm_client = server_instance.llm_client

    async def handle_implement_feature_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async wrapper for implement_feature tool"""
        # Call the existing sync implementation (or async if already available)
        feature_requirements = arguments.get("feature_requirements", "")
        architectural_guidelines = arguments.get("architectural_guidelines", "")
        dependencies = arguments.get("dependencies", [])
        performance_requirements = arguments.get("performance_requirements", [])

        # Use LLM to implement the feature
        result = await self._call_llm_for_implementation(
            feature_requirements,
            architectural_guidelines,
            dependencies,
            performance_requirements
        )

        return {
            "success": True,
            "code": result.get("code"),
            "files_created": result.get("files", []),
            "explanation": result.get("explanation")
        }

    async def handle_generate_code_from_spec_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async wrapper for generate_code_from_spec tool"""
        specifications = arguments.get("specifications", "")
        programming_language = arguments.get("programming_language", "python")
        framework = arguments.get("framework", "")
        coding_standards = arguments.get("coding_standards", "")

        result = await self._call_llm_for_code_generation(
            specifications,
            programming_language,
            framework,
            coding_standards
        )

        return {
            "success": True,
            "code": result.get("code"),
            "language": programming_language,
            "framework": framework
        }

    async def handle_generate_unit_tests_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async wrapper for generate_unit_tests tool"""
        code = arguments.get("code", "")
        requirements = arguments.get("requirements", "")
        test_framework = arguments.get("test_framework", "pytest")

        result = await self._call_llm_for_test_generation(
            code,
            requirements,
            test_framework
        )

        return {
            "success": True,
            "tests": result.get("tests"),
            "coverage_estimate": result.get("coverage_estimate", 0.85)
        }

    async def handle_refactor_code_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async wrapper for refactor_code tool"""
        code = arguments.get("code", "")
        refactoring_goals = arguments.get("refactoring_goals", [])

        result = await self._call_llm_for_refactoring(
            code,
            refactoring_goals
        )

        return {
            "success": True,
            "refactored_code": result.get("refactored_code"),
            "improvements": result.get("improvements", [])
        }

    async def handle_apply_coding_standards_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async wrapper for apply_coding_standards tool"""
        code = arguments.get("code", "")
        style_guide = arguments.get("style_guide", "")
        language = arguments.get("language", "python")

        result = await self._call_llm_for_standards_application(
            code,
            style_guide,
            language
        )

        return {
            "success": True,
            "formatted_code": result.get("formatted_code")
        }

    async def handle_git_checkout_branch_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async wrapper for git_checkout_branch tool"""
        repository_path = arguments.get("repository_path", "")
        branch_name = arguments.get("branch_name", "")
        create_if_not_exists = arguments.get("create_if_not_exists", False)

        # Execute git command
        import subprocess
        try:
            cmd = ["git", "-C", repository_path, "checkout"]
            if create_if_not_exists:
                cmd.extend(["-b", branch_name])
            else:
                cmd.append(branch_name)

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                return {"success": True, "message": f"Checked out branch: {branch_name}"}
            else:
                return {"success": False, "error": result.stderr}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # LLM helper methods
    async def _call_llm_for_implementation(self, requirements, guidelines, deps, perf_reqs):
        """Call LLM to implement a feature"""
        prompt = f"""
        Implement a feature with the following requirements:
        
        REQUIREMENTS:
        {requirements}
        
        ARCHITECTURAL GUIDELINES:
        {guidelines}
        
        DEPENDENCIES TO CONSIDER:
        {', '.join(deps) if deps else 'None specified'}
        
        PERFORMANCE REQUIREMENTS:
        {', '.join(perf_reqs) if perf_reqs else 'None specified'}
        
        Provide:
        1. Complete implementation code
        2. List of files created
        3. Brief explanation of the implementation
        """
        
        # Call LLM (use existing llm_client from server)
        response = await self._call_llm(prompt)
        return self._parse_llm_response(response)

    async def _call_llm_for_code_generation(self, specs, language, framework, standards):
        """Call LLM to generate code from specs"""
        prompt = f"""
        Generate code from the following specifications:
        
        SPECIFICATIONS:
        {specs}
        
        PROGRAMMING LANGUAGE: {language}
        FRAMEWORK: {framework}
        CODING STANDARDS: {standards}
        
        Provide production-ready code with proper structure.
        """
        
        response = await self._call_llm(prompt)
        return self._parse_llm_response(response)

    async def _call_llm_for_test_generation(self, code, requirements, framework):
        """Call LLM to generate tests"""
        prompt = f"""
        Generate unit tests for the following code:
        
        CODE:
        {code}
        
        REQUIREMENTS TO TEST:
        {requirements}
        
        TEST FRAMEWORK: {framework}
        
        Provide comprehensive test coverage.
        """
        
        response = await self._call_llm(prompt)
        return self._parse_llm_response(response)

    async def _call_llm_for_refactoring(self, code, goals):
        """Call LLM to refactor code"""
        prompt = f"""
        Refactor the following code with these goals:
        
        CODE:
        {code}
        
        REFACTORING GOALS:
        {', '.join(goals) if goals else 'Improve readability and maintainability'}
        
        Provide the refactored code and list of improvements.
        """
        
        response = await self._call_llm(prompt)
        return self._parse_llm_response(response)

    async def _call_llm_for_standards_application(self, code, style_guide, language):
        """Call LLM to apply coding standards"""
        prompt = f"""
        Apply coding standards to the following code:
        
        CODE:
        {code}
        
        STYLE GUIDE:
        {style_guide}
        
        LANGUAGE: {language}
        
        Provide the formatted code.
        """
        
        response = await self._call_llm(prompt)
        return self._parse_llm_response(response)

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt"""
        # Use existing llm_client from server
        try:
            import requests
            response = requests.post(
                self.server.llm_provider_url,
                json={
                    "model": self.server.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7
                },
                timeout=120
            )
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "")
            return ""
        except Exception as e:
            print(f"LLM call failed: {e}")
            return ""

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured data"""
        # Simple parsing - extract code blocks and explanations
        import re
        
        code_blocks = re.findall(r'```[\w]*\n(.*?)```', response, re.DOTALL)
        
        return {
            "code": code_blocks[0] if code_blocks else response,
            "files": [f"file_{i}.py" for i in range(len(code_blocks))],
            "explanation": response
        }
```

## Server Integration

**File**: `server.py` (modify existing Implementation Engineer server)

```python
# Add to Implementation Engineer server __init__

# 1. Import async components
from .client import McpClient
from .handlers.notification_handlers import NotificationHandlers
from .handlers.async_tool_handlers import AsyncToolHandlers
from .utils.task_queue import AsyncTaskQueue
from .utils.tool_executor import ToolExecutor

class ImplementationEngineerServer:
    def __init__(self, ...):
        # ... existing initialization ...

        # 2. Initialize MCP client for IT Lead communication
        self.mcp_client = McpClient()
        self.mcp_client.endpoint = self.it_lead_endpoint or "http://localhost:3061/mcp"
        self.mcp_client.connect()
        print(f"✅ Connected to IT Lead at {self.mcp_client.endpoint}")

        # 3. Initialize async tool handlers
        self.async_tool_handlers = AsyncToolHandlers(self)

        # 4. Initialize tool executor with async handlers
        self.tool_executor = ImplementationEngineerToolExecutor(self)

        # 5. Initialize task queue
        self.task_queue = AsyncTaskQueue(
            task_storage=self.task_storage,
            mcp_client=self.mcp_client,
            tool_executor=self.tool_executor
        )

        # 6. Initialize notification handlers
        self.notification_handlers = NotificationHandlers(
            task_storage=self.task_storage,
            mcp_client=self.mcp_client,
            task_queue=self.task_queue
        )
        self.notification_handlers.register_handlers(self.rpc_handler)

        # 7. Start background worker
        asyncio.create_task(self.task_queue.start_worker())
        print("✅ Async task queue worker started")

    async def shutdown(self):
        """Graceful shutdown"""
        # ... existing shutdown ...
        
        # Stop task queue worker
        if hasattr(self, 'task_queue'):
            await self.task_queue.stop_worker()
        
        # Disconnect MCP client
        if hasattr(self, 'mcp_client'):
            self.mcp_client.disconnect()
```

## Configuration

**File**: `.env` or config file

```bash
# Implementation Engineer Async Configuration
IT_LEAD_ENDPOINT=http://localhost:3061/mcp
ASYNC_TASKS_ENABLED=true
MAX_CONCURRENT_ASYNC_TASKS=5
TASK_QUEUE_SIZE=100
```

## Testing Async Implementation

### Test 1: Basic Async Task Assignment

```bash
# Call IT Lead to assign async task
curl -X POST http://localhost:3061/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-1",
    "method": "tools/call",
    "params": {
      "name": "assign_task_async",
      "arguments": {
        "task_id": "impl-async-test-001",
        "task_description": "Create a Python function that calculates fibonacci sequence",
        "assignee": "implementation-engineer",
        "tool_to_invoke": "implement_feature",
        "tool_arguments": {
          "feature_requirements": "Fibonacci sequence calculator",
          "architectural_guidelines": "Use recursive approach with memoization"
        }
      }
    }
  }'
```

### Test 2: Check Task Status

```bash
# Read task status resource
curl -X POST http://localhost:3061/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-2",
    "method": "resources/read",
    "params": {
      "uri": "it-lead://resource/task-status/impl-async-test-001"
    }
  }'
```

### Test 3: Verify Agent Received Task

Check Implementation Engineer logs for:
```
📨 Received async task: impl-async-test-001 - Tool: implement_feature
📥 Task queued: impl-async-test-001
✅ Task queue worker started
🔧 Processing task: impl-async-test-001 - Tool: implement_feature
✅ Task completed: impl-async-test-001
```

## Implementation Checklist

- [ ] Follow common base implementation (`00_COMMON_BASE_IMPLEMENTATION.md`)
- [ ] Create `handlers/async_tool_handlers.py` with Implementation Engineer specific handlers
- [ ] Create `utils/tool_executor.py` with tool mapping
- [ ] Update `server.py` with async initialization
- [ ] Configure IT Lead endpoint
- [ ] Test async task assignment
- [ ] Test status tracking
- [ ] Test task cancellation
- [ ] Verify logs show proper flow

## Troubleshooting (Implementation Engineer Specific)

| Issue | Possible Cause | Solution |
|-------|----------------|----------|
| `implement_feature` fails | LLM not configured | Check `llm_provider_url` and `llm_model` |
| Code generation returns empty | LLM response parsing failed | Check `_parse_llm_response()` method |
| Git operations fail | Repository path incorrect | Verify `repository_path` parameter |
| Task stuck in progress | Worker crashed | Check worker logs, restart agent |

---

**Related Documents**:
- `00_COMMON_BASE_IMPLEMENTATION.md` - Common base implementation
- `../roles/IMPLEMENTATION_ENGINEER.md` - Full Implementation Engineer documentation
