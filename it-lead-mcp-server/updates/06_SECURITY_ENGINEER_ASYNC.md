# Security Engineer - Async Task Management Implementation

## Overview

This document describes the **Security Engineer agent** specific implementation for async task management.

## Agent Identity

- **Agent ID**: `security-engineer`
- **Agent Name**: `Security Engineer MCP Server`
- **Default Port**: `3065`
- **Default Endpoint**: `http://localhost:3065/mcp`
- **IT Lead Endpoint**: `http://localhost:3061/mcp`

## Available Tools (Async Support)

| Tool Name | Description | Input Parameters |
|-----------|-------------|------------------|
| `perform_security_analysis` | Perform security analysis on code | `code`, `application_type`, `analysis_type` |
| `scan_dependencies` | Scan dependencies for vulnerabilities | `dependency_file`, `ecosystem` |
| `generate_threat_model` | Generate threat model | `architecture`, `data_flows`, `assets` |
| `validate_security_standards` | Validate security standards compliance | `code`, `standards`, `compliance_requirements` |

## Tool Executor Configuration

```python
class SecurityEngineerToolExecutor(ToolExecutor):
    def __init__(self, server_instance):
        available_tools = {
            "perform_security_analysis": server_instance.handle_security_analysis_async,
            "scan_dependencies": server_instance.handle_dependency_scan_async,
            "generate_threat_model": server_instance.handle_threat_modeling_async,
            "validate_security_standards": server_instance.handle_security_validation_async
        }
        super().__init__(available_tools)
```

## Key Async Handlers

```python
class SecurityEngineerAsyncHandlers:
    async def handle_security_analysis_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Perform security analysis"""
        code = arguments.get("code", "")
        application_type = arguments.get("application_type", "web")

        prompt = f"""
        Perform comprehensive security analysis on {application_type} application code:

        CODE:
        {code}

        Check for OWASP Top 10 vulnerabilities:
        1. Injection (SQL, NoSQL, OS, LDAP)
        2. Broken Authentication
        3. Sensitive Data Exposure
        4. XML External Entities (XXE)
        5. Broken Access Control
        6. Security Misconfiguration
        7. Cross-Site Scripting (XSS)
        8. Insecure Deserialization
        9. Using Components with Known Vulnerabilities
        10. Insufficient Logging & Monitoring

        Return JSON with vulnerabilities, severity, CWE IDs, and remediation.
        """

        llm_response = await self._call_llm(prompt)
        parsed = self._parse_json_response(llm_response)

        return {
            "success": True,
            "application_type": application_type,
            "vulnerabilities": parsed.get("vulnerabilities", []),
            "security_score": parsed.get("security_score", 0),
            "owasp_compliance": parsed.get("owasp_compliance", {})
        }

    async def handle_dependency_scan_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Scan dependencies for vulnerabilities"""
        dependency_file = arguments.get("dependency_file", "")
        ecosystem = arguments.get("ecosystem", "npm")

        prompt = f"""
        Scan {ecosystem} dependencies for known vulnerabilities:

        DEPENDENCY FILE:
        {dependency_file}

        Check for:
        1. Known CVEs
        2. Outdated packages
        3. Deprecated packages
        4. License issues

        Return JSON with vulnerable dependencies, CVE IDs, severity, and upgrade recommendations.
        """

        llm_response = await self._call_llm(prompt)
        return {"success": True, "vulnerabilities": self._parse_json_response(llm_response)}

    async def handle_threat_modeling_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Generate threat model"""
        architecture = arguments.get("architecture", "")
        data_flows = arguments.get("data_flows", [])

        prompt = f"""
        Generate threat model using STRIDE methodology:

        ARCHITECTURE:
        {architecture}

        DATA FLOWS:
        {json.dumps(data_flows)}

        For each component identify:
        - Spoofing threats
        - Tampering threats
        - Repudiation threats
        - Information disclosure threats
        - Denial of service threats
        - Elevation of privilege threats

        Return JSON with threats, risk ratings, and mitigations.
        """

        llm_response = await self._call_llm(prompt)
        return {"success": True, "threat_model": self._parse_json_response(llm_response)}
```

## Configuration

```bash
# Security Engineer Async Configuration
IT_LEAD_ENDPOINT=http://localhost:3061/mcp
ASYNC_TASKS_ENABLED=true
MAX_CONCURRENT_ASYNC_TASKS=5
LLM_PROVIDER_URL=http://asus-tus:1234/v1/chat/completions
LLM_MODEL=qwen3-4b
```

## Testing

```bash
curl -X POST http://localhost:3061/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "assign_task_async",
      "arguments": {
        "task_id": "sec-analysis-001",
        "task_description": "Security review of authentication module",
        "assignee": "security-engineer",
        "tool_to_invoke": "perform_security_analysis",
        "tool_arguments": {
          "code": "def login(user, password): ...",
          "application_type": "web"
        }
      }
    }
  }'
```

## Implementation Checklist

- [ ] Follow common base implementation
- [ ] Create async handlers for security analysis
- [ ] Create async handlers for dependency scanning
- [ ] Create async handlers for threat modeling
- [ ] Configure IT Lead endpoint
- [ ] Test with security analysis tasks

---

**Related Documents**:
- `00_COMMON_BASE_IMPLEMENTATION.md` - Common base implementation
- `../roles/SECURITY_ENGINEER.md` - Full Security Engineer documentation
