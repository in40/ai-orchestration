with open('/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/llm_task_planner.py', 'r') as f:
    content = f.read()

# Update _build_conflict_prompt to accept available_tools parameter
old_conflict_sig = '''    def _build_conflict_prompt(self, task_description: str,
                               routing_context: Dict[str, Any]) -> str:'''

new_conflict_sig = '''    def _build_conflict_prompt(self, task_description: str,
                               routing_context: Dict[str, Any],
                               available_tools: Dict[str, List[str]] = None) -> str:'''

if old_conflict_sig in content:
    content = content.replace(old_conflict_sig, new_conflict_sig)
    print("✅ Updated _build_conflict_prompt signature")
else:
    print("❌ Could not find _build_conflict_prompt signature")

# Add tools section to conflict prompt
old_conflict_end = '''## Available Agents
1. **implementation-engineer**: Writes code, implements features, generates code from specs - **ALL CODING TASKS MUST GO HERE**
2. **requirements-engineer**: Analyzes requirements, resolves ambiguities
3. **code-reviewer**: Reviews code quality
4. **qa-test-engineer**: Testing and validation

## CRITICAL INSTRUCTION: ALL coding, development, implementation, frontend, web, JavaScript, Python, React, HTML, CSS tasks MUST go to implementation-engineer. Only use other agents for non-coding tasks.'''

new_conflict_end = '''## Available Agents
1. **implementation-engineer**: Writes code, implements features, generates code from specs - **ALL CODING TASKS MUST GO HERE**
2. **requirements-engineer**: Analyzes requirements, resolves ambiguities
3. **code-reviewer**: Reviews code quality
4. **qa-test-engineer**: Testing and validation

## Available Tools
'''

# We'll add the tools dynamically later
if old_conflict_end in content:
    content = content.replace(old_conflict_end, new_conflict_end)
    print("✅ Updated conflict prompt base")

with open('/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/llm_task_planner.py', 'w') as f:
    f.write(content)

print("✅ Prompt updates applied")
