# QA/Test Engineer - Async Task Management Implementation

## Overview

This document describes the **QA/Test Engineer agent** specific implementation for async task management. Follow the common base implementation in `00_COMMON_BASE_IMPLEMENTATION.md` first, then apply these agent-specific configurations.

## Agent Identity

- **Agent ID**: `qa-test-engineer`
- **Agent Name**: `QA/Test Engineer MCP Server`
- **Default Port**: `3064`
- **Default Endpoint**: `http://localhost:3064/mcp`
- **IT Lead Endpoint**: `http://localhost:3061/mcp`

## Available Tools (Async Support)

The QA/Test Engineer should support these tools asynchronously:

| Tool Name | Description | Input Parameters | Output |
|-----------|-------------|------------------|--------|
| `generate_test_suite` | Generate comprehensive test suites | `requirements`, `test_types`, `test_framework` | Test files, test cases |
| `execute_tests` | Execute automated tests | `test_suite`, `environment`, `test_data` | Test results, coverage |
| `analyze_test_results` | Analyze test execution results | `test_results`, `expected_results` | Analysis report, root causes |
| `generate_test_data` | Generate test data | `data_schema`, `volume`, `constraints` | Test data sets |

## Tool Executor Configuration

**File**: `utils/tool_executor.py` (QA/Test Engineer specific)

```python
from typing import Dict, Any
from .tool_executor import ToolExecutor


class QATestEngineerToolExecutor(ToolExecutor):
    """Tool executor for QA/Test Engineer agent"""

    def __init__(self, server_instance):
        available_tools = {
            "generate_test_suite": server_instance.handle_generate_test_suite_async,
            "execute_tests": server_instance.handle_execute_tests_async,
            "analyze_test_results": server_instance.handle_analyze_test_results_async,
            "generate_test_data": server_instance.handle_generate_test_data_async
        }
        super().__init__(available_tools)
```

## Async Tool Handlers

**File**: `handlers/async_tool_handlers.py` (new file)

```python
"""
Async Tool Handlers for QA/Test Engineer
Wraps existing sync tools for async execution
"""
import json
import re
from typing import Dict, Any, List


class QATestEngineerAsyncHandlers:
    """Async wrappers for QA/Test Engineer tools"""

    def __init__(self, server_instance):
        self.server = server_instance
        self.llm_client = getattr(server_instance, 'llm_client', None)

    async def handle_generate_test_suite_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async wrapper for generate_test_suite tool"""
        requirements = arguments.get("requirements", "")
        test_types = arguments.get("test_types", ["unit", "integration"])
        test_framework = arguments.get("test_framework", "pytest")

        prompt = f"""
        Generate a comprehensive test suite for the following requirements:

        REQUIREMENTS:
        {requirements}

        TEST TYPES: {', '.join(test_types)}
        TEST FRAMEWORK: {test_framework}

        Generate:
        1. Unit tests for individual functions/methods
        2. Integration tests for component interactions
        3. Test fixtures and setup/teardown methods
        4. Mock objects and stubs
        5. Test data generators

        Return JSON format:
        {{
            "test_suite_summary": "Overview of generated tests",
            "test_files": [
                {{
                    "filename": "test_module.py",
                    "test_type": "unit|integration",
                    "test_count": number,
                    "code": "full test file content"
                }}
            ],
            "total_tests": number,
            "coverage_estimate": 0-100,
            "test_categories": {{
                "happy_path": number,
                "edge_cases": number,
                "error_handling": number
            }}
        }}
        """

        llm_response = await self._call_llm(prompt)
        parsed = self._parse_json_response(llm_response)

        return {
            "success": True,
            "test_suite_summary": parsed.get("test_suite_summary", ""),
            "test_files": parsed.get("test_files", []),
            "total_tests": parsed.get("total_tests", 0),
            "coverage_estimate": parsed.get("coverage_estimate", 0),
            "test_categories": parsed.get("test_categories", {}),
            "test_framework": test_framework
        }

    async def handle_execute_tests_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async wrapper for execute_tests tool"""
        test_suite = arguments.get("test_suite", "")
        environment = arguments.get("environment", "local")
        test_data = arguments.get("test_data", {})

        # In a real implementation, this would actually execute tests
        # For now, simulate test execution with LLM-based analysis

        prompt = f"""
        Simulate test execution for the following test suite:

        TEST SUITE:
        {test_suite}

        ENVIRONMENT: {environment}
        TEST DATA: {json.dumps(test_data)}

        Analyze the tests and simulate execution results including:
        1. Which tests would pass/fail
        2. Execution time estimates
        3. Coverage information
        4. Any potential issues

        Return JSON format:
        {{
            "execution_summary": "Summary of test execution",
            "results": [
                {{
                    "test_name": "test_function_name",
                    "status": "passed|failed|skipped",
                    "duration_ms": number,
                    "message": "failure message or notes"
                }}
            ],
            "statistics": {{
                "total": number,
                "passed": number,
                "failed": number,
                "skipped": number,
                "total_duration_ms": number
            }},
            "coverage": {{
                "lines": 0-100,
                "branches": 0-100,
                "functions": 0-100
            }}
        }}
        """

        llm_response = await self._call_llm(prompt)
        parsed = self._parse_json_response(llm_response)

        return {
            "success": True,
            "execution_summary": parsed.get("execution_summary", ""),
            "results": parsed.get("results", []),
            "statistics": parsed.get("statistics", {}),
            "coverage": parsed.get("coverage", {}),
            "environment": environment
        }

    async def handle_analyze_test_results_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async wrapper for analyze_test_results tool"""
        test_results = arguments.get("test_results", [])
        expected_results = arguments.get("expected_results", {})

        prompt = f"""
        Analyze the following test results:

        TEST RESULTS:
        {json.dumps(test_results, indent=2)}

        EXPECTED RESULTS:
        {json.dumps(expected_results, indent=2)}

        Provide analysis including:
        1. Summary of pass/fail rates
        2. Root cause analysis for failures
        3. Patterns in failures
        4. Recommendations for fixes
        5. Flaky test identification

        Return JSON format:
        {{
            "analysis_summary": "Overall analysis summary",
            "pass_rate": 0-100,
            "failed_tests": [
                {{
                    "test_name": "test_name",
                    "failure_reason": "why it failed",
                    "root_cause": "underlying cause",
                    "suggested_fix": "how to fix",
                    "priority": "critical|high|medium|low"
                }}
            ],
            "patterns": ["identified patterns in failures"],
            "flaky_tests": ["potentially flaky tests"],
            "recommendations": ["actionable recommendations"]
        }}
        """

        llm_response = await self._call_llm(prompt)
        parsed = self._parse_json_response(llm_response)

        return {
            "success": True,
            "analysis_summary": parsed.get("analysis_summary", ""),
            "pass_rate": parsed.get("pass_rate", 0),
            "failed_tests": parsed.get("failed_tests", []),
            "patterns": parsed.get("patterns", []),
            "flaky_tests": parsed.get("flaky_tests", []),
            "recommendations": parsed.get("recommendations", [])
        }

    async def handle_generate_test_data_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async wrapper for generate_test_data tool"""
        data_schema = arguments.get("data_schema", {})
        volume = arguments.get("volume", 100)
        constraints = arguments.get("constraints", [])

        prompt = f"""
        Generate test data based on the following schema:

        DATA SCHEMA:
        {json.dumps(data_schema, indent=2)}

        VOLUME: {volume} records
        CONSTRAINTS: {', '.join(constraints) if constraints else 'None'}

        Generate realistic test data that includes:
        1. Valid data matching the schema
        2. Edge cases (boundary values, nulls, empty strings)
        3. Invalid data for negative testing
        4. Special characters and Unicode

        Return JSON format:
        {{
            "data_summary": "Description of generated data",
            "valid_records": [
                {{/* valid data records */}}
            ],
            "edge_case_records": [
                {{/* edge case records */}}
            ],
            "invalid_records": [
                {{/* invalid data for negative testing */}}
            ],
            "total_generated": number
        }}
        """

        llm_response = await self._call_llm(prompt)
        parsed = self._parse_json_response(llm_response)

        return {
            "success": True,
            "data_summary": parsed.get("data_summary", ""),
            "valid_records": parsed.get("valid_records", []),
            "edge_case_records": parsed.get("edge_case_records", []),
            "invalid_records": parsed.get("invalid_records", []),
            "total_generated": parsed.get("total_generated", 0),
            "schema_compliance": self._validate_schema_compliance(parsed, data_schema)
        }

    # Helper methods
    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt"""
        try:
            import requests
            response = requests.post(
                self.server.llm_provider_url,
                json={
                    "model": self.server.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.5
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

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response"""
        import json

        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        return {"raw_response": response}

    def _validate_schema_compliance(self, data: Dict, schema: Dict) -> Dict[str, Any]:
        """Validate generated data against schema"""
        valid_records = data.get("valid_records", [])
        
        if not valid_records:
            return {"compliance_rate": 0, "issues": ["No valid records generated"]}

        # Simple schema validation (can be enhanced)
        compliant = 0
        issues = []
        
        for record in valid_records[:10]:  # Check first 10 records
            is_compliant = True
            for field, field_type in schema.get("fields", {}).items():
                if field not in record:
                    issues.append(f"Missing field: {field}")
                    is_compliant = False
                    break
            if is_compliant:
                compliant += 1

        return {
            "compliance_rate": (compliant / min(len(valid_records), 10)) * 100,
            "issues": issues[:5]  # Limit issues reported
        }
```

## Server Integration

**File**: `server.py` (modify existing QA/Test Engineer server)

```python
# Add to QA/Test Engineer server __init__

# 1. Import async components
from .client import McpClient
from .handlers.notification_handlers import NotificationHandlers
from .handlers.async_tool_handlers import QATestEngineerAsyncHandlers
from .utils.task_queue import AsyncTaskQueue
from .utils.tool_executor import QATestEngineerToolExecutor

class QATestEngineerServer:
    def __init__(self, ...):
        # ... existing initialization ...

        # 2. Initialize MCP client for IT Lead communication
        self.mcp_client = McpClient()
        self.mcp_client.endpoint = self.it_lead_endpoint or "http://localhost:3061/mcp"
        self.mcp_client.connect()
        print(f"✅ Connected to IT Lead at {self.mcp_client.endpoint}")

        # 3. Initialize async tool handlers
        self.async_tool_handlers = QATestEngineerAsyncHandlers(self)

        # 4. Initialize tool executor with async handlers
        self.tool_executor = QATestEngineerToolExecutor(self)

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

```bash
# QA/Test Engineer Async Configuration
IT_LEAD_ENDPOINT=http://localhost:3061/mcp
ASYNC_TASKS_ENABLED=true
MAX_CONCURRENT_ASYNC_TASKS=10
TASK_QUEUE_SIZE=200
LLM_PROVIDER_URL=http://asus-tus:1234/v1/chat/completions
LLM_MODEL=qwen3-4b
```

## Testing

### Test 1: Generate Test Suite

```bash
curl -X POST http://localhost:3061/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-1",
    "method": "tools/call",
    "params": {
      "name": "assign_task_async",
      "arguments": {
        "task_id": "qa-test-001",
        "task_description": "Generate tests for user authentication module",
        "assignee": "qa-test-engineer",
        "tool_to_invoke": "generate_test_suite",
        "tool_arguments": {
          "requirements": "User login with email/password, password reset, session management",
          "test_types": ["unit", "integration"],
          "test_framework": "pytest"
        }
      }
    }
  }'
```

## Implementation Checklist

- [ ] Follow common base implementation
- [ ] Create async handlers for test generation
- [ ] Create async handlers for test execution
- [ ] Create async handlers for result analysis
- [ ] Create async handlers for test data generation
- [ ] Configure IT Lead endpoint
- [ ] Test all async tools

---

**Related Documents**:
- `00_COMMON_BASE_IMPLEMENTATION.md` - Common base implementation
- `../roles/QA_TEST_ENGINEER.md` - Full QA/Test Engineer documentation
