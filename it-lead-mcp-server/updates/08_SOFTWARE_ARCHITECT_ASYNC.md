# Software Architect - Async Task Management Implementation

## Overview

This document describes the **Software Architect agent** specific implementation for async task management.

## Agent Identity

- **Agent ID**: `software-architect`
- **Agent Name**: `Software Architect MCP Server`
- **Default Port**: `3067`
- **Default Endpoint**: `http://localhost:3067/mcp`
- **IT Lead Endpoint**: `http://localhost:3061/mcp`

## Available Tools (Async Support)

| Tool Name | Description | Input Parameters |
|-----------|-------------|------------------|
| `analyze_architecture` | Analyze software architecture | `current_architecture`, `requirements`, `constraints` |
| `design_system_components` | Design system components | `requirements`, `scalability_requirements`, `integration_points` |
| `evaluate_technology_stack` | Evaluate technology options | `requirements`, `constraints`, `team_expertise` |
| `create_adr` | Create architectural decision records | `decision_context`, `options`, `rationale` |

## Tool Executor Configuration

```python
class SoftwareArchitectToolExecutor(ToolExecutor):
    def __init__(self, server_instance):
        available_tools = {
            "analyze_architecture": server_instance.handle_architecture_analysis_async,
            "design_system_components": server_instance.handle_component_design_async,
            "evaluate_technology_stack": server_instance.handle_technology_evaluation_async,
            "create_adr": server_instance.handle_adr_creation_async
        }
        super().__init__(available_tools)
```

## Key Async Handlers

```python
class SoftwareArchitectAsyncHandlers:
    async def handle_architecture_analysis_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze architecture asynchronously"""
        current_architecture = arguments.get("current_architecture", "")
        requirements = arguments.get("requirements", "")
        constraints = arguments.get("constraints", "")

        prompt = f"""
        Analyze the following software architecture:

        CURRENT ARCHITECTURE:
        {current_architecture}

        REQUIREMENTS:
        {requirements}

        CONSTRAINTS:
        {constraints}

        Provide analysis covering:
        1. Architecture strengths
        2. Architecture weaknesses
        3. Scalability assessment
        4. Maintainability assessment
        5. Security considerations
        6. Recommended improvements

        Return JSON with strengths, weaknesses, recommendations, risk_assessment.
        """

        llm_response = await self._call_llm(prompt)
        parsed = self._parse_json_response(llm_response)

        return {
            "success": True,
            "architecture_analysis": parsed,
            "strengths": parsed.get("strengths", []),
            "weaknesses": parsed.get("weaknesses", []),
            "recommendations": parsed.get("recommendations", []),
            "risk_assessment": parsed.get("risk_assessment", {})
        }

    async def handle_component_design_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Design system components"""
        requirements = arguments.get("requirements", "")
        scalability_requirements = arguments.get("scalability_requirements", "")

        prompt = f"""
        Design system components:

        REQUIREMENTS: {requirements}
        SCALABILITY: {scalability_requirements}

        Provide:
        1. Component decomposition
        2. Component responsibilities
        3. Component interfaces
        4. Data flow between components

        Return JSON with components, interfaces, data_flows.
        """

        llm_response = await self._call_llm(prompt)
        return {"success": True, "design": self._parse_json_response(llm_response)}

    async def handle_technology_evaluation_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate technology stack"""
        requirements = arguments.get("requirements", [])
        constraints = arguments.get("constraints", [])

        prompt = f"""
        Evaluate technology stack options:

        REQUIREMENTS: {json.dumps(requirements)}
        CONSTRAINTS: {json.dumps(constraints)}

        Provide comparison of technology options with pros/cons.

        Return JSON with options, comparison_matrix, recommendation.
        """

        llm_response = await self._call_llm(prompt)
        return {"success": True, "evaluation": self._parse_json_response(llm_response)}

    async def handle_adr_creation_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Create architectural decision record"""
        decision_context = arguments.get("decision_context", "")
        options = arguments.get("options", [])

        prompt = f"""
        Create Architectural Decision Record:

        CONTEXT: {decision_context}
        OPTIONS: {json.dumps(options)}

        Generate ADR with:
        1. Title
        2. Status
        3. Context
        4. Decision
        5. Consequences

        Return JSON with adr_title, status, context, decision, consequences.
        """

        llm_response = await self._call_llm(prompt)
        return {"success": True, "adr": self._parse_json_response(llm_response)}
```

## Configuration

```bash
# Software Architect Async Configuration
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
        "task_id": "arch-analysis-001",
        "task_description": "Review microservices architecture",
        "assignee": "software-architect",
        "tool_to_invoke": "analyze_architecture",
        "tool_arguments": {
          "current_architecture": "Microservices with API gateway, service mesh...",
          "requirements": "Support 10k concurrent users, 99.9% uptime",
          "constraints": "AWS only, existing PostgreSQL investment"
        }
      }
    }
  }'
```

## Implementation Checklist

- [ ] Follow common base implementation
- [ ] Create async handlers for architecture analysis
- [ ] Create async handlers for component design
- [ ] Create async handlers for technology evaluation
- [ ] Create async handlers for ADR creation
- [ ] Configure IT Lead endpoint
- [ ] Test with architecture tasks

---

**Related Documents**:
- `00_COMMON_BASE_IMPLEMENTATION.md` - Common base implementation
- `../roles/SOFTWARE_ARCHITECT.md` - Full Software Architect documentation
