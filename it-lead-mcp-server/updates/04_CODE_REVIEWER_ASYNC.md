# Code Reviewer - Async Task Management Implementation

## Overview

This document describes the **Code Reviewer agent** specific implementation for async task management. Follow the common base implementation in `00_COMMON_BASE_IMPLEMENTATION.md` first, then apply these agent-specific configurations.

## Agent Identity

- **Agent ID**: `code-reviewer`
- **Agent Name**: `Code Reviewer MCP Server`
- **Default Port**: `3063`
- **Default Endpoint**: `http://localhost:3063/mcp`
- **IT Lead Endpoint**: `http://localhost:3061/mcp`

## Available Tools (Async Support)

The Code Reviewer should support these tools asynchronously:

| Tool Name | Description | Input Parameters | Output |
|-----------|-------------|------------------|--------|
| `review_code` | Review code submitted by team members | `pull_request_id`, `code_diff`, `reviewer` | Review summary, issues, recommendations |
| `perform_static_analysis` | Perform static code analysis | `code`, `language`, `ruleset` | Analysis report, violations |
| `check_security_vulnerabilities` | Check for security issues | `code`, `application_type` | Security findings, severity levels |
| `validate_coding_standards` | Validate coding standards compliance | `code`, `style_guide`, `language` | Compliance report, violations |

## Tool Executor Configuration

**File**: `utils/tool_executor.py` (Code Reviewer specific)

```python
from typing import Dict, Any
from .tool_executor import ToolExecutor


class CodeReviewerToolExecutor(ToolExecutor):
    """Tool executor for Code Reviewer agent"""

    def __init__(self, server_instance):
        # Map tool names to server handler methods
        available_tools = {
            "review_code": server_instance.handle_review_code_async,
            "perform_static_analysis": server_instance.handle_static_analysis_async,
            "check_security_vulnerabilities": server_instance.handle_security_check_async,
            "validate_coding_standards": server_instance.handle_standards_validation_async
        }
        super().__init__(available_tools)
```

## Async Tool Handlers

**File**: `handlers/async_tool_handlers.py` (new file)

```python
"""
Async Tool Handlers for Code Reviewer
Wraps existing sync tools for async execution
"""
import json
import re
from typing import Dict, Any, List


class CodeReviewerAsyncHandlers:
    """Async wrappers for Code Reviewer tools"""

    def __init__(self, server_instance):
        self.server = server_instance
        self.llm_client = getattr(server_instance, 'llm_client', None)

    async def handle_review_code_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async wrapper for review_code tool"""
        code_diff = arguments.get("code_diff", "")
        pull_request_id = arguments.get("pull_request_id", "unknown")
        reviewer = arguments.get("reviewer", "auto")

        # Use LLM to review code
        prompt = f"""
        Review the following code changes for Pull Request #{pull_request_id}:

        CODE DIFF:
        {code_diff}

        Perform a comprehensive code review checking for:

        1. **Code Correctness**: Logic errors, bugs, edge cases
        2. **Coding Standards**: Style, naming conventions, formatting
        3. **Performance**: Inefficient algorithms, unnecessary operations
        4. **Security**: Vulnerabilities, input validation, data handling
        5. **Test Coverage**: Unit tests, integration tests
        6. **Documentation**: Comments, docstrings, README updates
        7. **Maintainability**: Code complexity, duplication, modularity

        Return your review in the following JSON format:
        {{
            "summary": "Brief summary of changes",
            "positive_aspects": ["list of good things"],
            "issues": [
                {{
                    "type": "bug|performance|security|style|test|documentation",
                    "severity": "critical|high|medium|low",
                    "location": "file:line or description",
                    "description": "Issue description",
                    "suggestion": "How to fix"
                }}
            ],
            "recommendation": "approve|request_changes|comment",
            "overall_score": 0-10
        }}
        """

        # Call LLM
        llm_response = await self._call_llm(prompt)

        # Parse response
        parsed = self._parse_json_response(llm_response)

        # Categorize issues
        issues = parsed.get("issues", [])
        critical_issues = [i for i in issues if i.get("severity") == "critical"]
        high_issues = [i for i in issues if i.get("severity") == "high"]

        return {
            "success": True,
            "pull_request_id": pull_request_id,
            "reviewer": reviewer,
            "review_summary": parsed.get("summary", ""),
            "positive_aspects": parsed.get("positive_aspects", []),
            "issues": issues,
            "critical_issues_count": len(critical_issues),
            "high_issues_count": len(high_issues),
            "recommendation": parsed.get("recommendation", "comment"),
            "overall_score": parsed.get("overall_score", 5),
            "full_review": llm_response
        }

    async def handle_static_analysis_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async wrapper for perform_static_analysis tool"""
        code = arguments.get("code", "")
        language = arguments.get("language", "python")
        ruleset = arguments.get("ruleset", "default")

        prompt = f"""
        Perform static code analysis on the following {language} code:

        CODE:
        {code}

        RULESET: {ruleset}

        Analyze for:
        1. Syntax errors
        2. Code smells
        3. Complexity issues
        4. Unused variables/functions
        5. Dead code
        6. Type safety issues
        7. Error handling gaps

        Return JSON format:
        {{
            "analysis_summary": "Summary of findings",
            "violations": [
                {{
                    "rule": "rule name",
                    "severity": "error|warning|info",
                    "line": line_number,
                    "message": "violation description",
                    "suggestion": "how to fix"
                }}
            ],
            "metrics": {{
                "complexity": 0-10,
                "maintainability_index": 0-100,
                "lines_of_code": number,
                "test_coverage_estimate": 0-100
            }}
        }}
        """

        llm_response = await self._call_llm(prompt)
        parsed = self._parse_json_response(llm_response)

        return {
            "success": True,
            "language": language,
            "ruleset": ruleset,
            "analysis_summary": parsed.get("analysis_summary", ""),
            "violations": parsed.get("violations", []),
            "metrics": parsed.get("metrics", {}),
            "violation_counts": {
                "error": len([v for v in parsed.get("violations", []) if v.get("severity") == "error"]),
                "warning": len([v for v in parsed.get("violations", []) if v.get("severity") == "warning"]),
                "info": len([v for v in parsed.get("violations", []) if v.get("severity") == "info"])
            }
        }

    async def handle_security_check_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async wrapper for check_security_vulnerabilities tool"""
        code = arguments.get("code", "")
        application_type = arguments.get("application_type", "web")

        prompt = f"""
        Perform security analysis on the following {application_type} application code:

        CODE:
        {code}

        Check for security vulnerabilities including:
        1. SQL Injection
        2. Cross-Site Scripting (XSS)
        3. Cross-Site Request Forgery (CSRF)
        4. Insecure Authentication
        5. Sensitive Data Exposure
        6. Insecure Dependencies
        7. Broken Access Control
        8. Security Misconfiguration

        Reference OWASP Top 10 for guidance.

        Return JSON format:
        {{
            "security_summary": "Overall security assessment",
            "vulnerabilities": [
                {{
                    "type": "vulnerability type",
                    "severity": "critical|high|medium|low",
                    "cwe_id": "CWE-XXX",
                    "location": "file:line or description",
                    "description": "Vulnerability description",
                    "remediation": "How to fix",
                    "owasp_category": "OWASP category"
                }}
            ],
            "security_score": 0-10,
            "recommendations": ["list of security recommendations"]
        }}
        """

        llm_response = await self._call_llm(prompt)
        parsed = self._parse_json_response(llm_response)

        vulnerabilities = parsed.get("vulnerabilities", [])

        return {
            "success": True,
            "application_type": application_type,
            "security_summary": parsed.get("security_summary", ""),
            "vulnerabilities": vulnerabilities,
            "vulnerability_counts": {
                "critical": len([v for v in vulnerabilities if v.get("severity") == "critical"]),
                "high": len([v for v in vulnerabilities if v.get("severity") == "high"]),
                "medium": len([v for v in vulnerabilities if v.get("severity") == "medium"]),
                "low": len([v for v in vulnerabilities if v.get("severity") == "low"])
            },
            "security_score": parsed.get("security_score", 5),
            "recommendations": parsed.get("recommendations", []),
            "owasp_compliance": self._check_owasp_compliance(vulnerabilities)
        }

    async def handle_standards_validation_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async wrapper for validate_coding_standards tool"""
        code = arguments.get("code", "")
        style_guide = arguments.get("style_guide", "PEP 8")
        language = arguments.get("language", "python")

        prompt = f"""
        Validate coding standards compliance for the following {language} code:

        CODE:
        {code}

        STYLE GUIDE: {style_guide}

        Check for compliance with {style_guide} standards including:
        1. Naming conventions (variables, functions, classes)
        2. Indentation and formatting
        3. Line length limits
        4. Import organization
        5. Documentation requirements
        6. Error handling patterns

        Return JSON format:
        {{
            "compliance_summary": "Overall compliance assessment",
            "violations": [
                {{
                    "rule": "rule name",
                    "category": "naming|formatting|documentation|organization",
                    "severity": "error|warning|style",
                    "line": line_number,
                    "message": "violation description",
                    "suggested_fix": "corrected code"
                }}
            ],
            "compliance_score": 0-100,
            "auto_fixable_count": number
        }}
        """

        llm_response = await self._call_llm(prompt)
        parsed = self._parse_json_response(llm_response)

        violations = parsed.get("violations", [])

        return {
            "success": True,
            "language": language,
            "style_guide": style_guide,
            "compliance_summary": parsed.get("compliance_summary", ""),
            "violations": violations,
            "compliance_score": parsed.get("compliance_score", 100),
            "violation_counts": {
                "error": len([v for v in violations if v.get("severity") == "error"]),
                "warning": len([v for v in violations if v.get("severity") == "warning"]),
                "style": len([v for v in violations if v.get("severity") == "style"])
            },
            "auto_fixable_count": parsed.get("auto_fixable_count", 0)
        }

    # Helper methods
    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt"""
        if not self.llm_client:
            return await self._call_llm_direct(prompt)

        try:
            import requests
            response = requests.post(
                self.server.llm_provider_url,
                json={
                    "model": self.server.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3  # Lower temperature for more consistent reviews
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

    async def _call_llm_direct(self, prompt: str) -> str:
        """Direct LLM call fallback"""
        try:
            import requests
            response = requests.post(
                self.server.llm_provider_url,
                json={
                    "model": self.server.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3
                },
                timeout=120
            )
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "")
            return ""
        except Exception as e:
            print(f"Direct LLM call failed: {e}")
            return f"Error: {str(e)}"

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response"""
        import json

        # Try to extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Fallback: return empty dict with raw response
        return {"raw_response": response}

    def _check_owasp_compliance(self, vulnerabilities: List[Dict]) -> Dict[str, Any]:
        """Check OWASP compliance based on vulnerabilities"""
        owasp_categories = set()
        for vuln in vulnerabilities:
            category = vuln.get("owasp_category", "")
            if category:
                owasp_categories.add(category)

        # OWASP Top 10 categories
        all_categories = {
            "A01:2021-Broken Access Control",
            "A02:2021-Cryptographic Failures",
            "A03:2021-Injection",
            "A04:2021-Insecure Design",
            "A05:2021-Security Misconfiguration",
            "A06:2021-Vulnerable and Outdated Components",
            "A07:2021-Identification and Authentication Failures",
            "A08:2021-Software and Data Integrity Failures",
            "A09:2021-Security Logging and Monitoring Failures",
            "A10:2021-Server-Side Request Forgery"
        }

        compliant_categories = all_categories - owasp_categories

        return {
            "compliant_categories": list(compliant_categories),
            "non_compliant_categories": list(owasp_categories),
            "compliance_percentage": len(compliant_categories) / len(all_categories) * 100 if all_categories else 100
        }
```

## Server Integration

**File**: `server.py` (modify existing Code Reviewer server)

```python
# Add to Code Reviewer server __init__

# 1. Import async components
from .client import McpClient
from .handlers.notification_handlers import NotificationHandlers
from .handlers.async_tool_handlers import CodeReviewerAsyncHandlers
from .utils.task_queue import AsyncTaskQueue
from .utils.tool_executor import CodeReviewerToolExecutor

class CodeReviewerServer:
    def __init__(self, ...):
        # ... existing initialization ...

        # 2. Initialize MCP client for IT Lead communication
        self.mcp_client = McpClient()
        self.mcp_client.endpoint = self.it_lead_endpoint or "http://localhost:3061/mcp"
        self.mcp_client.connect()
        print(f"✅ Connected to IT Lead at {self.mcp_client.endpoint}")

        # 3. Initialize async tool handlers
        self.async_tool_handlers = CodeReviewerAsyncHandlers(self)

        # 4. Initialize tool executor with async handlers
        self.tool_executor = CodeReviewerToolExecutor(self)

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
# Code Reviewer Async Configuration
IT_LEAD_ENDPOINT=http://localhost:3061/mcp
ASYNC_TASKS_ENABLED=true
MAX_CONCURRENT_ASYNC_TASKS=10
TASK_QUEUE_SIZE=200
LLM_PROVIDER_URL=http://asus-tus:1234/v1/chat/completions
LLM_MODEL=qwen3-4b
```

## Testing Async Implementation

### Test 1: Code Review Task

```bash
# Call IT Lead to assign async code review task
curl -X POST http://localhost:3061/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-1",
    "method": "tools/call",
    "params": {
      "name": "assign_task_async",
      "arguments": {
        "task_id": "review-async-test-001",
        "task_description": "Review PR #123 for authentication module",
        "assignee": "code-reviewer",
        "tool_to_invoke": "review_code",
        "tool_arguments": {
          "pull_request_id": "123",
          "code_diff": "@@ -1,5 +1,8 @@\n-def login(user, password):\n+def login(user, password, session_timeout=3600):\n+    if not user or not password:\n+        return None\n     # authenticate user\n     ..."
        }
      }
    }
  }'
```

### Test 2: Security Check Task

```bash
curl -X POST http://localhost:3061/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-2",
    "method": "tools/call",
    "params": {
      "name": "assign_task_async",
      "arguments": {
        "task_id": "security-check-001",
        "task_description": "Security review of user input handling",
        "assignee": "code-reviewer",
        "tool_to_invoke": "check_security_vulnerabilities",
        "tool_arguments": {
          "code": "def process_input(user_input):\n    query = f\"SELECT * FROM users WHERE name = '{user_input}'\"\n    db.execute(query)",
          "application_type": "web"
        }
      }
    }
  }'
```

### Test 3: Check Task Status

```bash
# Read task status resource
curl -X POST http://localhost:3061/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-3",
    "method": "resources/read",
    "params": {
      "uri": "it-lead://resource/task-status/review-async-test-001"
    }
  }'
```

## Implementation Checklist

- [ ] Follow common base implementation (`00_COMMON_BASE_IMPLEMENTATION.md`)
- [ ] Create `handlers/async_tool_handlers.py` with Code Reviewer specific handlers
- [ ] Create `utils/tool_executor.py` with tool mapping
- [ ] Update `server.py` with async initialization
- [ ] Configure IT Lead endpoint
- [ ] Configure LLM provider URL and model
- [ ] Test async code review task
- [ ] Test async static analysis task
- [ ] Test async security check task
- [ ] Test async standards validation task
- [ ] Test status tracking via resources
- [ ] Test task cancellation

## Troubleshooting (Code Reviewer Specific)

| Issue | Possible Cause | Solution |
|-------|----------------|----------|
| Code review fails | LLM not configured | Check `llm_provider_url` and `llm_model` |
| JSON parsing fails | Invalid JSON from LLM | Check `_parse_json_response()` method |
| Security check misses issues | Prompt too generic | Enhance prompt with specific vulnerability patterns |
| Review takes too long | Large code diff | Increase timeout or chunk code |
| False positives | LLM hallucination | Lower temperature, add validation |

---

**Related Documents**:
- `00_COMMON_BASE_IMPLEMENTATION.md` - Common base implementation
- `../roles/CODE_REVIEWER.md` - Full Code Reviewer documentation
