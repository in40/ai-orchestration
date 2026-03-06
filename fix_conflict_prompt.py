with open('/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/llm_task_planner.py', 'r') as f:
    content = f.read()

# Find and replace the conflict prompt function
old_func = '''    def _build_conflict_prompt(self, task_description: str,
                               routing_context: Dict[str, Any],
                               available_tools: Dict[str, List[str]] = None) -> str:
        """Build prompt for conflicting rules"""
        matched_rules = routing_context.get("matched_rules", [])
        conflicting_assignees = routing_context.get("conflicting_assignees", [])

        return f"""You are an IT Lead Agent responsible for task assignment.'''

new_func = '''    def _build_conflict_prompt(self, task_description: str,
                               routing_context: Dict[str, Any],
                               available_tools: Dict[str, List[str]] = None) -> str:
        """Build prompt for conflicting rules"""
        matched_rules = routing_context.get("matched_rules", [])
        conflicting_assignees = routing_context.get("conflicting_assignees", [])
        
        # Build available tools section
        if available_tools is None:
            available_tools = {}
        
        tools_section = "## Available Tools\\n"
        for agent, tools in available_tools.items():
            tools_list = ", ".join(f"`{tool}`" for tool in tools)
            tools_section += f"- **{agent}**: {tools_list}\\n"

        return f"""You are an IT Lead Agent responsible for task assignment.'''

if old_func in content:
    content = content.replace(old_func, new_func)
    print("✅ Fixed _build_conflict_prompt to generate tools section")
else:
    print("❌ Could not find function signature")
    print("Looking for pattern...")
    if "_build_conflict_prompt" in content:
        print("   Found _build_conflict_prompt")
    if "tools_section" in content:
        print("   Found tools_section placeholder")

with open('/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/llm_task_planner.py', 'w') as f:
    f.write(content)
