# Requirements Engineer - Async Task Management Implementation

## Overview

This document describes the **Requirements Engineer agent** specific implementation for async task management. Follow the common base implementation in `00_COMMON_BASE_IMPLEMENTATION.md` first, then apply these agent-specific configurations.

## Agent Identity

- **Agent ID**: `requirements-engineer`
- **Agent Name**: `Requirements Engineer MCP Server`
- **Default Port**: `3062`
- **Default Endpoint**: `http://localhost:3062/mcp`
- **IT Lead Endpoint**: `http://localhost:3061/mcp`

## Available Tools (Async Support)

The Requirements Engineer should support these tools asynchronously:

| Tool Name | Description | Input Parameters | Output |
|-----------|-------------|------------------|--------|
| `analyze_requirements` | Analyze stakeholder inputs and extract structured requirements | `stakeholder_inputs`, `business_context`, `previous_requirements` | Structured requirements (functional, non-functional) |
| `resolve_ambiguity` | Identify ambiguous requirements and generate clarification requests | `requirements`, `stakeholder_context`, `clarification_history` | Clarification questions, resolved requirements |
| `translate_business_to_technical` | Convert business requirements to technical specifications | `business_requirements`, `technical_constraints`, `system_context` | Technical specifications |
| `generate_traceability_matrix` | Create requirement-to-implementation links | `requirements`, `design_elements`, `code_modules`, `test_cases` | Traceability matrix |
| `identify_edge_cases` | Identify non-functional requirements and edge cases | `functional_requirements`, `domain_context`, `security_requirements` | Edge cases, non-functional requirements |

## Tool Executor Configuration

**File**: `utils/tool_executor.py` (Requirements Engineer specific)

```python
from typing import Dict, Any
from .tool_executor import ToolExecutor


class RequirementsEngineerToolExecutor(ToolExecutor):
    """Tool executor for Requirements Engineer agent"""

    def __init__(self, server_instance):
        # Map tool names to server handler methods
        available_tools = {
            "analyze_requirements": server_instance.handle_analyze_requirements_async,
            "resolve_ambiguity": server_instance.handle_resolve_ambiguity_async,
            "translate_business_to_technical": server_instance.handle_translate_business_to_technical_async,
            "generate_traceability_matrix": server_instance.handle_generate_traceability_matrix_async,
            "identify_edge_cases": server_instance.handle_identify_edge_cases_async
        }
        super().__init__(available_tools)
```

## Async Tool Handlers

**File**: `handlers/async_tool_handlers.py` (new file)

```python
"""
Async Tool Handlers for Requirements Engineer
Wraps existing sync tools for async execution
"""
import json
import asyncio
from typing import Dict, Any, List


class RequirementsEngineerAsyncHandlers:
    """Async wrappers for Requirements Engineer tools"""

    def __init__(self, server_instance):
        self.server = server_instance
        self.llm_client = getattr(server_instance, 'llm_client', None)

    async def handle_analyze_requirements_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async wrapper for analyze_requirements tool"""
        stakeholder_inputs = arguments.get("stakeholder_inputs", "")
        business_context = arguments.get("business_context", "")
        previous_requirements = arguments.get("previous_requirements", [])

        # Use LLM to analyze and extract requirements
        prompt = f"""
        Analyze the following stakeholder inputs and extract structured requirements:

        STAKEHOLDER INPUTS:
        {stakeholder_inputs}

        BUSINESS CONTEXT:
        {business_context}

        PREVIOUS REQUIREMENTS (for reference):
        {json.dumps(previous_requirements) if previous_requirements else 'None'}

        Return a structured analysis with:
        1. Functional requirements (numbered list with IDs like FR-001, FR-002)
        2. Non-functional requirements (numbered list with IDs like NFR-001, NFR-002)
        3. Identified ambiguities that need clarification
        4. Edge cases to consider
        5. Assumptions made

        Format as JSON with keys: functional_requirements, non_functional_requirements, ambiguities, edge_cases, assumptions
        """

        # Call LLM
        llm_response = await self._call_llm(prompt)

        # Parse response
        parsed = self._parse_json_response(llm_response)

        return {
            "success": True,
            "requirements": {
                "functional": parsed.get("functional_requirements", []),
                "non_functional": parsed.get("non_functional_requirements", [])
            },
            "ambiguities": parsed.get("ambiguities", []),
            "edge_cases": parsed.get("edge_cases", []),
            "assumptions": parsed.get("assumptions", []),
            "structured_spec": llm_response
        }

    async def handle_resolve_ambiguity_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async wrapper for resolve_ambiguity tool"""
        requirements = arguments.get("requirements", [])
        stakeholder_context = arguments.get("stakeholder_context", "")
        clarification_history = arguments.get("clarification_history", [])

        prompt = f"""
        Identify and resolve ambiguities in the following requirements:

        REQUIREMENTS:
        {json.dumps(requirements, indent=2)}

        STAKEHOLDER CONTEXT:
        {stakeholder_context}

        PREVIOUS CLARIFICATION ATTEMPTS:
        {json.dumps(clarification_history) if clarification_history else 'None'}

        For each ambiguous requirement:
        1. Identify the ambiguity
        2. Explain why it's ambiguous
        3. Generate clarifying questions for stakeholders
        4. Suggest possible interpretations

        Format as JSON with keys: ambiguous_requirements, clarifying_questions, suggestions
        """

        llm_response = await self._call_llm(prompt)
        parsed = self._parse_json_response(llm_response)

        return {
            "success": True,
            "ambiguous_requirements": parsed.get("ambiguous_requirements", []),
            "clarifying_questions": parsed.get("clarifying_questions", []),
            "suggestions": parsed.get("suggestions", []),
            "resolution_status": "pending_stakeholder_input"
        }

    async def handle_translate_business_to_technical_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async wrapper for translate_business_to_technical tool"""
        business_requirements = arguments.get("business_requirements", [])
        technical_constraints = arguments.get("technical_constraints", [])
        system_context = arguments.get("system_context", "")

        prompt = f"""
        Translate business requirements to technical specifications:

        BUSINESS REQUIREMENTS:
        {json.dumps(business_requirements, indent=2)}

        TECHNICAL CONSTRAINTS:
        {json.dumps(technical_constraints, indent=2)}

        SYSTEM CONTEXT:
        {system_context}

        For each business requirement, provide:
        1. Technical specification
        2. Required components/services
        3. Data models needed
        4. API endpoints (if applicable)
        5. Integration points

        Format as JSON with keys: technical_specifications, components, data_models, apis, integrations
        """

        llm_response = await self._call_llm(prompt)
        parsed = self._parse_json_response(llm_response)

        return {
            "success": True,
            "technical_specifications": parsed.get("technical_specifications", []),
            "components": parsed.get("components", []),
            "data_models": parsed.get("data_models", []),
            "apis": parsed.get("apis", []),
            "integrations": parsed.get("integrations", []),
            "traceability": self._create_business_to_technical_mapping(business_requirements, parsed)
        }

    async def handle_generate_traceability_matrix_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async wrapper for generate_traceability_matrix tool"""
        requirements = arguments.get("requirements", [])
        design_elements = arguments.get("design_elements", [])
        code_modules = arguments.get("code_modules", [])
        test_cases = arguments.get("test_cases", [])

        # Build traceability matrix
        matrix = {
            "requirements": [],
            "traceability_links": []
        }

        for req in requirements:
            req_id = req.get("id", req.get("requirement_id", "unknown"))
            matrix["requirements"].append({
                "id": req_id,
                "description": req.get("description", ""),
                "type": req.get("type", "functional")
            })

            # Link to design elements
            for design in design_elements:
                if self._check_relevance(req, design):
                    matrix["traceability_links"].append({
                        "requirement_id": req_id,
                        "design_element_id": design.get("id"),
                        "relationship": "implements"
                    })

            # Link to code modules
            for module in code_modules:
                if self._check_relevance(req, module):
                    matrix["traceability_links"].append({
                        "requirement_id": req_id,
                        "code_module_id": module.get("id"),
                        "relationship": "implements"
                    })

            # Link to test cases
            for test in test_cases:
                if self._check_relevance(req, test):
                    matrix["traceability_links"].append({
                        "requirement_id": req_id,
                        "test_case_id": test.get("id"),
                        "relationship": "validates"
                    })

        return {
            "success": True,
            "traceability_matrix": matrix,
            "coverage_stats": self._calculate_coverage(requirements, matrix["traceability_links"])
        }

    async def handle_identify_edge_cases_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async wrapper for identify_edge_cases tool"""
        functional_requirements = arguments.get("functional_requirements", [])
        domain_context = arguments.get("domain_context", "")
        security_requirements = arguments.get("security_requirements", [])

        prompt = f"""
        Identify edge cases and non-functional requirements:

        FUNCTIONAL REQUIREMENTS:
        {json.dumps(functional_requirements, indent=2)}

        DOMAIN CONTEXT:
        {domain_context}

        SECURITY REQUIREMENTS:
        {json.dumps(security_requirements, indent=2)}

        Identify:
        1. Edge cases (unusual scenarios, boundary conditions)
        2. Non-functional requirements (performance, scalability, reliability)
        3. Security considerations
        4. Error handling scenarios
        5. Data validation requirements

        Format as JSON with keys: edge_cases, non_functional_requirements, security_considerations, error_scenarios, validation_requirements
        """

        llm_response = await self._call_llm(prompt)
        parsed = self._parse_json_response(llm_response)

        return {
            "success": True,
            "edge_cases": parsed.get("edge_cases", []),
            "non_functional_requirements": parsed.get("non_functional_requirements", []),
            "security_considerations": parsed.get("security_considerations", []),
            "error_scenarios": parsed.get("error_scenarios", []),
            "validation_requirements": parsed.get("validation_requirements", [])
        }

    # Helper methods
    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt"""
        if not self.llm_client:
            # Fallback if llm_client not available
            return await self._call_llm_direct(prompt)

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

    async def _call_llm_direct(self, prompt: str) -> str:
        """Direct LLM call fallback"""
        # Use same pattern as server's llm_client
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
            print(f"Direct LLM call failed: {e}")
            return f"Error: {str(e)}"

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response"""
        import re
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

    def _create_business_to_technical_mapping(self, business_reqs: List[Dict], technical_spec: Dict) -> List[Dict]:
        """Create mapping between business and technical requirements"""
        mapping = []
        for i, req in enumerate(business_reqs):
            mapping.append({
                "business_requirement_id": req.get("id", f"BR-{i+1}"),
                "technical_specification_ids": [f"TR-{i+1}"],
                "components": technical_spec.get("components", []),
                "confidence": 0.9
            })
        return mapping

    def _check_relevance(self, requirement: Dict, element: Dict) -> bool:
        """Check if element is relevant to requirement (simple keyword matching)"""
        req_text = f"{requirement.get('description', '')} {requirement.get('title', '')}".lower()
        elem_text = f"{element.get('description', '')} {element.get('name', '')}".lower()

        # Simple keyword overlap check
        req_words = set(req_text.split())
        elem_words = set(elem_text.split())
        overlap = req_words.intersection(elem_words)

        return len(overlap) > 0

    def _calculate_coverage(self, requirements: List[Dict], links: List[Dict]) -> Dict[str, Any]:
        """Calculate traceability coverage statistics"""
        total_reqs = len(requirements)
        covered_reqs = len(set(link["requirement_id"] for link in links))

        return {
            "total_requirements": total_reqs,
            "covered_requirements": covered_reqs,
            "coverage_percentage": (covered_reqs / total_reqs * 100) if total_reqs > 0 else 0,
            "total_links": len(links)
        }
```

## Server Integration

**File**: `server.py` (modify existing Requirements Engineer server)

```python
# Add to Requirements Engineer server __init__

# 1. Import async components
from .client import McpClient
from .handlers.notification_handlers import NotificationHandlers
from .handlers.async_tool_handlers import RequirementsEngineerAsyncHandlers
from .utils.task_queue import AsyncTaskQueue
from .utils.tool_executor import RequirementsEngineerToolExecutor

class RequirementsEngineerServer:
    def __init__(self, ...):
        # ... existing initialization ...

        # 2. Initialize MCP client for IT Lead communication
        self.mcp_client = McpClient()
        self.mcp_client.endpoint = self.it_lead_endpoint or "http://localhost:3061/mcp"
        self.mcp_client.connect()
        print(f"✅ Connected to IT Lead at {self.mcp_client.endpoint}")

        # 3. Initialize async tool handlers
        self.async_tool_handlers = RequirementsEngineerAsyncHandlers(self)

        # 4. Initialize tool executor with async handlers
        self.tool_executor = RequirementsEngineerToolExecutor(self)

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
# Requirements Engineer Async Configuration
IT_LEAD_ENDPOINT=http://localhost:3061/mcp
ASYNC_TASKS_ENABLED=true
MAX_CONCURRENT_ASYNC_TASKS=5
TASK_QUEUE_SIZE=100
LLM_PROVIDER_URL=http://asus-tus:1234/v1/chat/completions
LLM_MODEL=qwen3-4b
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
        "task_id": "req-async-test-001",
        "task_description": "Analyze stakeholder inputs for new e-commerce feature",
        "assignee": "requirements-engineer",
        "tool_to_invoke": "analyze_requirements",
        "tool_arguments": {
          "stakeholder_inputs": "We need a shopping cart with checkout, payment integration, and order tracking",
          "business_context": "E-commerce platform for retail business"
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
      "uri": "it-lead://resource/task-status/req-async-test-001"
    }
  }'
```

### Test 3: Verify Agent Received Task

Check Requirements Engineer logs for:
```
📨 Received async task: req-async-test-001 - Tool: analyze_requirements
📥 Task queued: req-async-test-001
✅ Task queue worker started
🔧 Processing task: req-async-test-001 - Tool: analyze_requirements
✅ Task completed: req-async-test-001
```

## Implementation Checklist

- [ ] Follow common base implementation (`00_COMMON_BASE_IMPLEMENTATION.md`)
- [ ] Create `handlers/async_tool_handlers.py` with Requirements Engineer specific handlers
- [ ] Create `utils/tool_executor.py` with tool mapping
- [ ] Update `server.py` with async initialization
- [ ] Configure IT Lead endpoint
- [ ] Configure LLM provider URL and model
- [ ] Test async task assignment for requirements analysis
- [ ] Test async task assignment for ambiguity resolution
- [ ] Test async task assignment for business-to-technical translation
- [ ] Test status tracking via resources
- [ ] Test task cancellation

## Troubleshooting (Requirements Engineer Specific)

| Issue | Possible Cause | Solution |
|-------|----------------|----------|
| `analyze_requirements` fails | LLM not configured | Check `llm_provider_url` and `llm_model` |
| Requirements parsing fails | JSON parsing error | Check `_parse_json_response()` method |
| Traceability matrix empty | No matching keywords | Improve `_check_relevance()` method |
| Task stuck in progress | Worker crashed | Check worker logs, restart agent |
| Ambiguities not identified | Prompt too vague | Enhance prompt with examples |

---

**Related Documents**:
- `00_COMMON_BASE_IMPLEMENTATION.md` - Common base implementation
- `../roles/REQUIREMENT_ENGINEER.md` - Full Requirements Engineer documentation
