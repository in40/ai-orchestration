with open('/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/llm_task_planner.py', 'r') as f:
    content = f.read()

# Update _build_no_match_prompt
old_no_match = '''## Your Task
Analyze the task and determine:
1. Which agent(s) should handle this task?
2. If multiple agents, what is the recommended sequence?
3. What specific tool should each agent use?
4. What is the reasoning for this assignment?
5. What priority should this task have?
6. Are there any missing requirements or ambiguities that need clarification?

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
    "reasoning": "Detailed explanation of why this assignment was chosen",
    "priority": "low|medium|high|critical",
    "estimated_complexity": "simple|moderate|complex",
    "requires_clarification": true|false,
    "clarification_questions": ["question1", "question2"],
    "confidence": 0.0-1.0
}}'''

new_no_match = '''## Your Task
Analyze the task and determine:
1. Which agent(s) should handle this task?
2. If multiple agents, what is the recommended sequence?
3. What specific tool should each agent use?
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
}}'''

if old_no_match in content:
    content = content.replace(old_no_match, new_no_match)
    print("✅ Updated _build_no_match_prompt")
else:
    print("❌ Could not find _build_no_match_prompt")

# Update _build_low_confidence_prompt
old_low_conf = '''## Your Task
Review this assignment and determine:
1. Is the rule-based assignment correct?
2. Should a different agent handle this task?
3. Are there ambiguities that need clarification?
4. What is your confidence in the assignment?

## Response Format
Respond in valid JSON format:
{{
    "agree_with_rule": true|false,
    "recommended_agent": "agent-name",
    "recommended_tool": "tool-name",
    "reasoning": "Why you agree or disagree with the rule-based assignment",
    "priority": "low|medium|high|critical",
    "requires_clarification": true|false,
    "clarification_questions": ["question1"],
    "confidence": 0.0-1.0
}}'''

new_low_conf = '''## Your Task
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
}}'''

if old_low_conf in content:
    content = content.replace(old_low_conf, new_low_conf)
    print("✅ Updated _build_low_confidence_prompt")
else:
    print("❌ Could not find _build_low_confidence_prompt")

with open('/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/llm_task_planner.py', 'w') as f:
    f.write(content)

print("✅ All LLM prompts updated with language detection")
