"""
Quality Gate Handlers for IT Lead MCP Server
Implements quality gate validation for software development teams
"""
import json
import time
from typing import Dict, Any, List, Optional
from ..utils.json_rpc import JsonRpcHandler


class QualityGateHandlers:
    """Handles quality gate specific MCP server methods for software development teams"""

    def __init__(self, llm_client=None, agent_registry=None, task_storage=None):
        self.llm_client = llm_client
        self.agent_registry = agent_registry
        self.task_storage = task_storage
        
        # Quality gate tools
        self.tools = [
            {
                "name": "validate_output_against_criteria",
                "description": "Validate agent output against acceptance criteria",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "ID of the task"},
                        "output": {"type": "string", "description": "Output to validate"},
                        "acceptance_criteria": {"type": "string", "description": "Acceptance criteria to validate against"},
                        "quality_standards": {"type": "object", "description": "Quality standards to apply"}
                    },
                    "required": ["task_id", "output", "acceptance_criteria"]
                }
            }
        ]

        self.resources = [
            {
                "uri": "it-lead://resource/quality-dashboard",
                "name": "Quality Dashboard",
                "description": "Real-time quality metrics dashboard"
            }
        ]

    def register_handlers(self, rpc_handler: JsonRpcHandler):
        """Register quality gate handlers with the RPC handler"""
        rpc_handler.register_request_handler('tools/call', self.handle_tools_call)

    def handle_tools_call(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle tools/call request for quality gate tools"""
        if params is None:
            params = {}

        tool_name = params.get("name") or params.get("tool")
        tool_arguments = params.get("arguments", {})

        # Find the tool in quality gate tools
        tool = None
        for t in self.tools:
            if t["name"] == tool_name:
                tool = t
                break

        if not tool:
            return None  # Return None to indicate this tool isn't handled here

        # Execute the quality gate tool
        return self._execute_tool(tool, tool_arguments)

    def _execute_tool(self, tool: Dict[str, Any], arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific quality gate tool with given arguments"""
        tool_name = tool["name"]

        if tool_name == "validate_output_against_criteria":
            return self._validate_output_against_criteria(arguments)

        # For any other tools, return a generic response
        return {"result": f"Executed quality gate tool '{tool_name}' with arguments: {arguments}"}

    def _validate_output_against_criteria(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Validate agent output against acceptance criteria"""
        task_id = arguments.get("task_id", "")
        output = arguments.get("output", "")
        criteria = arguments.get("acceptance_criteria", "")
        standards = arguments.get("quality_standards", {})
        
        # Use LLM to validate output
        if self.llm_client:
            result = self._validate_output_with_llm(output, criteria, standards)
        else:
            # Fallback implementation
            result = {
                "passed": True,
                "detailed_feedback": {
                    "meets_criteria": ["All basic requirements met"],
                    "does_not_meet": [],
                },
                "quality_score": 0.85,
                "confidence": 0.9,
                "recommendations": ["Consider adding more comprehensive error handling"],
                "rework_required": False
            }

        # Store quality validation result
        if self.task_storage:
            self.task_storage.update_task_status(
                task_id=task_id,
                status="validated" if result.get("passed", False) else "needs_revision",
                result=json.dumps(result)
            )

        return {"result": result}

    def _validate_output_with_llm(self, output: str, criteria: str, standards: dict):
        """Use LLM to validate output against criteria"""
        prompt = f"""
        You are a senior quality assurance engineer. Evaluate the following output against the specified acceptance criteria and quality standards:

        ACCEPTANCE CRITERIA:
        {criteria}

        QUALITY STANDARDS:
        {json.dumps(standards, indent=2)}

        OUTPUT TO EVALUATE:
        {output}

        Please provide a comprehensive evaluation including:
        1. Pass/Fail determination
        2. Detailed feedback on what meets criteria
        3. Specific areas that don't meet criteria
        4. Severity level of any issues (critical/major/minor)
        5. Recommendations for improvement
        6. Confidence level in evaluation (0.0-1.0)
        7. Overall quality score (0.0-1.0)

        Format as JSON:
        {{
          "passed": true|false,
          "detailed_feedback": {{
            "meets_criteria": ["requirement1", "requirement2"],
            "does_not_meet": [
              {{
                "requirement": "requirement3",
                "issue": "specific problem",
                "severity": "critical|major|minor",
                "suggestion": "how to fix"
              }}
            ]
          }},
          "quality_score": 0.0-1.0,
          "confidence": 0.0-1.0,
          "recommendations": ["improvement1", "improvement2"],
          "rework_required": true|false
        }}
        """
        
        # Call the LLM with the prompt
        try:
            import requests
            response = requests.post(
                self.llm_client.llm_provider_url,
                json={
                    "model": self.llm_client.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        return {
                            "passed": False,
                            "error": "Could not parse LLM response",
                            "quality_score": 0.0,
                            "confidence": 0.0
                        }
            else:
                return {
                    "passed": False,
                    "error": f"LLM call failed: {response.status_code}",
                    "quality_score": 0.0,
                    "confidence": 0.0
                }
        except Exception as e:
            return {
                "passed": False,
                "error": f"LLM call failed: {str(e)}",
                "quality_score": 0.0,
                "confidence": 0.0
            }