"""
LLM Planning Module for IT Lead MCP Server
Handles complex task routing decisions that rule-based system cannot resolve
Uses dynamic MCP agent and tool discovery via MCP protocol.
"""
import json
import time
from typing import Dict, List, Any, Optional


class LLMTaskPlanner:
    """Uses LLM to plan task assignment for complex cases with dynamic agent discovery"""

    def __init__(self, llm_client, agent_registry=None, mcp_registry_client=None):
        self.llm_client = llm_client
        self.agent_registry = agent_registry  # Deprecated: kept for backward compatibility
        self.mcp_registry_client = mcp_registry_client  # NEW: Dynamic discovery via MCP protocol
    
    def plan_task_assignment(self, task_description: str, 
                            routing_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use LLM to plan task assignment when rule-based routing fails
        
        Args:
            task_description: The task description text
            routing_context: Context from rule evaluation (matched rules, failures, etc.)
        
        Returns:
            Planning result with agent assignment and reasoning
        """
        llm_reason = routing_context.get("llm_reason", "UNKNOWN")
        
        # Get available agents and tools via dynamic MCP discovery
        if self.mcp_registry_client:
            print(f"🔍 Using dynamic MCP agent discovery...")
            agents_with_tools = self.mcp_registry_client.discover_all_agents_with_tools(use_cache=True)
            print(f"📋 Discovered {len(agents_with_tools)} agents, {sum(1 for a in agents_with_tools if a['status'] == 'online')} online")
        else:
            print(f"⚠️  MCP Registry Client not available, using hardcoded tools (DEGRADED MODE)")
            agents_with_tools = None
        
        # Build the prompt based on the reason for LLM planning
        if llm_reason == "NO_RULES_MATCHED":
            prompt = self._build_no_match_prompt(task_description, routing_context, agents_with_tools)
        elif llm_reason == "LOW_CONFIDENCE_MATCH":
            prompt = self._build_low_confidence_prompt(task_description, routing_context, agents_with_tools)
        elif llm_reason == "CONFLICTING_RULES":
            prompt = self._build_conflict_prompt(task_description, routing_context, agents_with_tools)
        else:
            prompt = self._build_general_prompt(task_description, routing_context, agents_with_tools)
        
        # Call LLM
        try:
            print(f"📞 Calling LLM for task planning...")
            print(f"   Reason: {llm_reason}")
            print(f"   Prompt length: {len(prompt)} characters")
            response = self.llm_client.generate(prompt, temperature=0.3)
            print(f"✅ LLM response received ({len(response)} chars)")
            print(f"   Response preview: {response[:200]}...")
            return self._parse_llm_response(response, task_description, routing_context)
        except Exception as e:
            print(f"❌ Error in LLM task planning: {e}")
            return self._get_fallback_plan(task_description, routing_context)
    
    def _build_no_match_prompt(self, task_description: str,
                               routing_context: Dict[str, Any],
                               agents_with_tools: Optional[List[Dict[str, Any]]] = None) -> str:
        """Build prompt for when no rules matched"""
        failure_reasons = routing_context.get("failure_reasons", [])
        
        # Build agents section from dynamic discovery or use hardcoded fallback
        if agents_with_tools:
            agents_section = self._build_agents_section_from_discovery(agents_with_tools)
        else:
            agents_section = self._build_hardcoded_agents_section()
        
        return f"""You are an IT Lead Agent responsible for task assignment.

## Task Description
{task_description}

## Situation
The rule-based routing system could not find any matching rules for this task.

## Why Rules Didn't Match
{json.dumps(failure_reasons, indent=2)}

{agents_section}

## Important Instructions
- ALL coding, development, implementation, frontend, web, JavaScript, Python, React, HTML, CSS tasks MUST go to **implementation-engineer**
- Only use other agents for non-coding tasks (requirements analysis, code review, testing, security, deployment)
- When in doubt, choose **implementation-engineer** for any task involving code generation or implementation
- ONLY use tools listed above for each agent - DO NOT invent tool names

## Your Task
Analyze the task and determine:
1. Which agent(s) should handle this task?
2. If multiple agents, what is the recommended sequence?
3. What specific tool should each agent use? (MUST be from the list above)
4. **What programming language/technology is requested?** (e.g., Python, HTML, JavaScript, etc.)
5. What is the reasoning for this assignment?
6. What priority should this task have?
7. Are there any missing requirements or ambiguities that need clarification?

## Important
- **Detect language from task description** (e.g., "in HTML" → HTML, "Python script" → Python)
- **If NO language/technology specified**, assign to requirements-engineer for analysis

## Response Format
Respond in valid JSON format:
{{
    "primary_agent": "agent-name",
    "secondary_agents": ["agent2", "agent3"],
    "sequence": ["agent1", "agent2"],
    "tools": {{
        "agent1": "tool-name",
        "agent2": "tool-name"
    }},
    "language": "detected-language-or-null",
    "technology_stack": ["list", "of", "technologies"],
    "reasoning": "Detailed explanation of why this assignment was chosen",
    "priority": "low|medium|high|critical",
    "estimated_complexity": "simple|moderate|complex",
    "requires_clarification": true|false,
    "clarification_questions": ["question1", "question2"],
    "confidence": 0.0-1.0
}}
"""
    
    def _build_low_confidence_prompt(self, task_description: str,
                                     routing_context: Dict[str, Any],
                                     agents_with_tools: Optional[List[Dict[str, Any]]] = None) -> str:
        """Build prompt for low confidence rule match"""
        matched_rule = routing_context.get("matched_rule")
        confidence = routing_context.get("confidence", 0.0)
        
        # Build agents section from dynamic discovery or use hardcoded fallback
        if agents_with_tools:
            agents_section = self._build_agents_section_from_discovery(agents_with_tools)
        else:
            agents_section = self._build_hardcoded_agents_section()

        return f"""You are an IT Lead Agent responsible for task assignment.

## Task Description
{task_description}

## Situation
The rule-based routing system found a potential match but with low confidence.

## Matched Rule
- Rule ID: {matched_rule}
- Confidence: {confidence:.2f}

{agents_section}

## Your Task
Review this assignment and determine:
1. Is the rule-based assignment correct?
2. Should a different agent handle this task?
3. Are there ambiguities that need clarification?
4. **What programming language/technology is requested?**
5. What is your confidence in the assignment?

## Important
- **Detect language from task description**
- **If NO language specified**, recommend requirements-engineer for analysis

## Response Format
Respond in valid JSON format:
{{
    "agree_with_rule": true|false,
    "recommended_agent": "agent-name",
    "recommended_tool": "tool-name",
    "language": "detected-language-or-null",
    "reasoning": "Why you agree or disagree with the rule-based assignment",
    "priority": "low|medium|high|critical",
    "requires_clarification": true|false,
    "clarification_questions": ["question1"],
    "confidence": 0.0-1.0
}}
"""
    
    def _build_conflict_prompt(self, task_description: str,
                               routing_context: Dict[str, Any],
                               agents_with_tools: Optional[List[Dict[str, Any]]] = None) -> str:
        """Build prompt for conflicting rules"""
        matched_rules = routing_context.get("matched_rules", [])
        conflicting_assignees = routing_context.get("conflicting_assignees", [])
        
        # Build agents section from dynamic discovery
        if agents_with_tools:
            agents_section = self._build_agents_section_from_discovery(agents_with_tools)
        else:
            agents_section = self._build_hardcoded_agents_section()

        return f"""You are an IT Lead Agent responsible for task assignment.

## Task Description
{task_description}

## Situation
The rule-based routing system found multiple matching rules with CONFLICTING agent assignments.

## Conflicting Assignments
- Matched Rules: {json.dumps(matched_rules)}
- Conflicting Agents: {conflicting_assignees}

{agents_section}

## Your Task
Resolve this conflict by determining:
1. Which agent should PRIMARY handle this task?
2. Should other agents be involved in a sequence (workflow)?
3. What is the reasoning for resolving the conflict this way?
4. What is the proper workflow sequence?
5. **What programming language/technology is requested?** (e.g., Python, HTML, JavaScript, etc.)

## Available Agents
1. **implementation-engineer**: Writes code, implements features, generates code from specs - **ALL CODING TASKS MUST GO HERE**
2. **requirements-engineer**: Analyzes requirements, resolves ambiguities, **selects technology if not specified**
3. **code-reviewer**: Reviews code quality
4. **qa-test-engineer**: Testing and validation

## CRITICAL INSTRUCTION:
- ALL coding, development, implementation, frontend, web, JavaScript, Python, React, HTML, CSS tasks MUST go to implementation-engineer
- ONLY use tools listed under "Available Agents and Their Tools" above - DO NOT invent tool names
- For implementation-engineer coding tasks, use `vibe_code_async`
- **If task description does NOT specify a programming language/technology, assign to requirements-engineer for analysis and technology selection**
- **Detect language from task description** (e.g., "in HTML" → HTML, "Python script" → Python, "JavaScript function" → JavaScript)


## Response Format
Respond in valid JSON format:
{{
    "primary_agent": "agent-name",
    "workflow_sequence": ["agent1", "agent2", "agent3"],
    "tools": {{
        "agent1": "tool-name",
        "agent2": "tool-name"
    }},
    "language": "detected-language-or-null",
    "technology_stack": ["list", "of", "technologies"],
    "conflict_resolution": "Explanation of how you resolved the conflict",
    "reasoning": "Detailed reasoning for the assignment",
    "priority": "low|medium|high|critical",
    "estimated_complexity": "simple|moderate|complex",
    "confidence": 0.0-1.0
}}
"""
    
    def _build_general_prompt(self, task_description: str,
                              routing_context: Dict[str, Any],
                              agents_with_tools: Optional[List[Dict[str, Any]]] = None) -> str:
        """Build general prompt for LLM planning"""
        # Build agents section from dynamic discovery or use hardcoded fallback
        if agents_with_tools:
            agents_section = self._build_agents_section_from_discovery(agents_with_tools)
        else:
            agents_section = self._build_hardcoded_agents_section()
        
        return f"""You are an IT Lead Agent responsible for task assignment.

## Task Description
{task_description}

## Situation
The task requires intelligent routing analysis.

{agents_section}

## CRITICAL INSTRUCTION: ALL coding, development, implementation, frontend, web, JavaScript, Python, React, HTML, CSS tasks MUST go to implementation-engineer. Do NOT use requirements-engineer for coding tasks.

## Your Task
Analyze and provide optimal task assignment.

## Response Format
Respond in valid JSON format:
{{
    "primary_agent": "agent-name",
    "secondary_agents": [],
    "sequence": ["agent1"],
    "tools": {{"agent1": "tool-name"}},
    "reasoning": "Explanation",
    "priority": "low|medium|high|critical",
    "confidence": 0.0-1.0
}}
"""

    def _build_agents_section_from_discovery(self, agents_with_tools: List[Dict[str, Any]]) -> str:
        """
        Build agents section from dynamically discovered agents and tools.
        
        Args:
            agents_with_tools: List of agent info with tool schemas from MCP discovery
        
        Returns:
            Formatted string for LLM prompt
        """
        section = "## Available Agents and Their Tools (Discovered via MCP Protocol)\n\n"
        
        online_agents = [a for a in agents_with_tools if a["status"] == "online"]
        
        if not online_agents:
            section += "⚠️  No online agents discovered. Using fallback assignment.\n\n"
            return section
        
        for i, agent in enumerate(online_agents, 1):
            agent_name = agent["name"]
            description = agent.get("description", "No description")
            tools = agent.get("tools", [])
            
            section += f"{i}. **{agent_name}**: {description}\n"
            
            if tools:
                section += "   **Available Tools**:\n"
                for tool in tools:
                    tool_name = tool.get("name", "unknown")
                    tool_desc = tool.get("description", "No description")
                    input_schema = tool.get("inputSchema", {})
                    
                    section += f"   - `{tool_name}`: {tool_desc}\n"
                    
                    # Show required parameters
                    required = input_schema.get("required", [])
                    properties = input_schema.get("properties", {})
                    if required and properties:
                        params = []
                        for param_name in required:
                            if param_name in properties:
                                param_type = properties[param_name].get("type", "any")
                                params.append(f"{param_name} ({param_type})")
                        if params:
                            section += f"     Required: {', '.join(params)}\n"
            else:
                section += "   ⚠️  No tools discovered for this agent\n"
            
            section += "\n"
        
        return section

    def _build_hardcoded_agents_section(self) -> str:
        """
        Build hardcoded agents section (fallback when MCP discovery fails).
        
        Returns:
            Formatted string for LLM prompt
        """
        return """## Available Agents (Hardcoded Fallback)
1. **implementation-engineer**: Writes code, implements features, generates code from specs, applies coding standards, writes unit tests, refactors code - **ALL CODING TASKS (including frontend, web, JavaScript, React, HTML, CSS) should go here**
   **Available Tools**: `vibe_code_async`, `vibe_code`, `implement_feature`, `generate_code_from_spec`, `generate_unit_tests`

2. **requirements-engineer**: Analyzes requirements, resolves ambiguities, translates business needs to technical specs
   **Available Tools**: `analyze_requirements`, `requirements_tracker`

3. **code-reviewer**: Reviews code quality, validates architecture compliance, suggests improvements
   **Available Tools**: `review_code`, `static_analysis`

4. **qa-test-engineer**: Generates test suites, executes automated tests, analyzes test failures
   **Available Tools**: `test_execution_suite`, `generate_test_suite`, `browser_testing`

5. **security-engineer**: Performs security analysis, scans dependencies, validates compliance
   **Available Tools**: `perform_security_analysis`, `sast_scan`

6. **devops-engineer**: Orchestrates deployments, configures CI/CD, manages infrastructure
   **Available Tools**: `orchestrate_deployments`, `ci_cd_pipeline`

"""

    def _parse_llm_response(self, response: str, task_description: str,
                           routing_context: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LLM response and return structured planning result"""
        try:
            # Try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                
                # Add metadata
                result["planning_method"] = "llm"
                result["task_description"] = task_description
                result["timestamp"] = time.time()
                
                return result
            else:
                # No JSON found, use fallback
                return self._get_fallback_plan(task_description, routing_context)
                
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response JSON: {e}")
            return self._get_fallback_plan(task_description, routing_context)
    
    def _get_fallback_plan(self, task_description: str,
                          routing_context: Dict[str, Any]) -> Dict[str, Any]:
        """Get fallback plan when LLM fails"""
        description_lower = task_description.lower()
        
        # Simple keyword-based fallback
        if any(kw in description_lower for kw in ["python", "code", "implement", "create"]):
            agent = "implementation-engineer"
            tool = "vibe_code_async"
        elif any(kw in description_lower for kw in ["javascript", "js", "react", "frontend", "html", "css"]):
            agent = "implementation-engineer"
            tool = "vibe_code_async"
        elif any(kw in description_lower for kw in ["requirement", "spec"]):
            agent = "requirements-engineer"
            tool = "analyze_requirements"
        elif any(kw in description_lower for kw in ["review", "check"]):
            agent = "code-reviewer"
            tool = "review_code"
        elif any(kw in description_lower for kw in ["test"]):
            agent = "qa-test-engineer"
            tool = "generate_test_suite"
        elif any(kw in description_lower for kw in ["security"]):
            agent = "security-engineer"
            tool = "perform_security_analysis"
        elif any(kw in description_lower for kw in ["deploy"]):
            agent = "devops-engineer"
            tool = "orchestrate_deployments"
        else:
            # Default to implementation engineer for any coding task
            agent = "implementation-engineer"
            tool = "vibe_code_async"
        
        return {
            "primary_agent": agent,
            "secondary_agents": [],
            "sequence": [agent],
            "tools": {agent: tool},
            "reasoning": "Fallback assignment based on simple keyword matching (LLM planning failed)",
            "priority": "medium",
            "estimated_complexity": "moderate",
            "requires_clarification": False,
            "clarification_questions": [],
            "confidence": 0.5,
            "planning_method": "fallback",
            "task_description": task_description,
            "timestamp": time.time()
        }

    def _get_available_tools(self) -> Dict[str, List[str]]:
        """
        Get available tools for each agent from the service registry.
        
        DEPRECATED: Use mcp_registry_client.discover_all_agents_with_tools() instead.
        This method is kept for backward compatibility only.
        
        Returns:
            Dict of agent names to tool lists
        """
        print("⚠️  WARNING: _get_available_tools() is deprecated. Use mcp_registry_client.discover_all_agents_with_tools() instead.")
        available_tools = {}
        
        if self.agent_registry:
            try:
                services = self.agent_registry.list_services()
                for service in services:
                    service_name = service.get("name", "").lower()
                    
                    if "implementation" in service_name:
                        available_tools["implementation-engineer"] = [
                            "vibe_code_async",
                            "vibe_code",
                            "implement_feature",
                            "generate_code_from_spec",
                            "generate_unit_tests"
                        ]
                    elif "requirement" in service_name:
                        available_tools["requirements-engineer"] = [
                            "analyze_requirements",
                            "requirements_tracker"
                        ]
                    elif "review" in service_name:
                        available_tools["code-reviewer"] = [
                            "review_code",
                            "static_analysis"
                        ]
                    elif "qa" in service_name or "test" in service_name:
                        available_tools["qa-test-engineer"] = [
                            "test_execution_suite",
                            "generate_test_suite",
                            "browser_testing"
                        ]
                    elif "security" in service_name:
                        available_tools["security-engineer"] = [
                            "perform_security_analysis",
                            "sast_scan"
                        ]
                    elif "devops" in service_name:
                        available_tools["devops-engineer"] = [
                            "orchestrate_deployments",
                            "ci_cd_pipeline"
                        ]
            except Exception as e:
                print(f"⚠️ Error getting available tools: {e}")
        
        # If we couldn't get tools from registry, use defaults
        if not available_tools:
            available_tools = {
                "implementation-engineer": ["vibe_code_async", "vibe_code", "implement_feature"],
                "requirements-engineer": ["analyze_requirements"],
                "code-reviewer": ["review_code"],
                "qa-test-engineer": ["test_execution_suite"],
                "security-engineer": ["perform_security_analysis"],
                "devops-engineer": ["orchestrate_deployments"]
            }
        
        print(f"🛠 Available tools: {available_tools}")
        return available_tools
