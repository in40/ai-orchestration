"""
Task Routing Rules for IT Lead MCP Server
Defines rule-based routing for task assignment to specialized agents
"""

# Task routing rules configuration
# Each rule has: id, name, conditions, action, confidence_threshold
TASK_ROUTING_RULES = [
    # ===========================================
    # Category 1: Keyword-Based Rules (Simple)
    # ===========================================

    {
        "id": "rule-1.0",
        "name": "Website Creation Request",
        "category": "keyword",
        "conditions": {
            "keywords_any": ["website", "web application", "online site"],
            "keywords_all": [],
            "keywords_none": ["code review", "security audit"]
        },
        "action": {
            "assign_to": "requirements-engineer",
            "tool": "analyze_requirements",
            "priority": "high",
            "metadata": {"task_type": "website_decomposition"}
        },
        "confidence_threshold": 0.7
    },

    {
        "id": "rule-1.1",
        "name": "Python Code Implementation",
        "category": "keyword",
        "conditions": {
            "keywords_any": ["python", "py", "python script", "py script"],
            "keywords_all": [],
            "keywords_none": ["review", "audit", "test", "security scan", "deploy"],
            "action_verbs": ["write", "create", "build", "implement", "develop", "make", "generate"]
        },
        "action": {
            "assign_to": "implementation-engineer",
            "tool": "implement_feature",
            "priority": "medium",
            "metadata": {"task_type": "code_implementation", "language": "python"}
        },
        "confidence_threshold": 0.8
    },
    
    {
        "id": "rule-1.2",
        "name": "Code Review Request",
        "category": "keyword",
        "conditions": {
            "keywords_any": ["review", "check", "audit", "examine"],
            "keywords_all": ["code"],
            "keywords_none": ["implement", "write", "create", "build"],
            "has_code_diff": True
        },
        "action": {
            "assign_to": "code-reviewer",
            "tool": "review_code",
            "priority": "high",
            "metadata": {"task_type": "code_review"}
        },
        "confidence_threshold": 0.85
    },
    
    {
        "id": "rule-1.3",
        "name": "Requirements Analysis",
        "category": "keyword",
        "conditions": {
            "keywords_any": ["requirement", "specification", "spec", "business need", "user story"],
            "keywords_all": [],
            "keywords_none": ["code", "implement", "deploy", "build"]
        },
        "action": {
            "assign_to": "requirements-engineer",
            "tool": "analyze_requirements",
            "priority": "high",
            "metadata": {"task_type": "requirements_analysis"}
        },
        "confidence_threshold": 0.8
    },
    
    {
        "id": "rule-1.4",
        "name": "Test Generation",
        "category": "keyword",
        "conditions": {
            "keywords_any": ["test", "testing", "unit test", "integration test", "e2e test"],
            "keywords_all": [],
            "keywords_none": ["implement", "deploy", "review"],
            "action_verbs": ["write", "create", "generate"]
        },
        "action": {
            "assign_to": "qa-test-engineer",
            "tool": "generate_test_suite",
            "priority": "medium",
            "metadata": {"task_type": "test_generation"}
        },
        "confidence_threshold": 0.8
    },
    
    {
        "id": "rule-1.5",
        "name": "Security Analysis",
        "category": "keyword",
        "conditions": {
            "keywords_any": ["security", "vulnerability", "penetration test", "security audit", "OWASP"],
            "keywords_all": [],
            "keywords_none": ["implement", "deploy"]
        },
        "action": {
            "assign_to": "security-engineer",
            "tool": "perform_security_analysis",
            "priority": "high",
            "metadata": {"task_type": "security_analysis"}
        },
        "confidence_threshold": 0.85
    },
    
    {
        "id": "rule-1.6",
        "name": "Deployment Request",
        "category": "keyword",
        "conditions": {
            "keywords_any": ["deploy", "deployment", "release", "publish", "CI/CD"],
            "keywords_all": [],
            "keywords_none": ["implement", "write", "create"]
        },
        "action": {
            "assign_to": "devops-engineer",
            "tool": "orchestrate_deployments",
            "priority": "high",
            "metadata": {"task_type": "deployment"}
        },
        "confidence_threshold": 0.85
    },
    
    # ===========================================
    # Category 2: Pattern-Based Rules (Intermediate)
    # ===========================================
    
    {
        "id": "rule-2.1",
        "name": "Feature Implementation Pattern",
        "category": "pattern",
        "conditions": {
            "pattern_regex": r"(implement|create|build|develop)\s+(a|an|the)?\s*(feature|function|module|component|api|endpoint|service)",
            "has_acceptance_criteria": True,
            "has_architectural_constraints": False
        },
        "action": {
            "assign_to": "implementation-engineer",
            "tool": "implement_feature",
            "priority": "medium",
            "metadata": {"task_type": "feature_implementation"}
        },
        "confidence_threshold": 0.75
    },
    
    {
        "id": "rule-2.2",
        "name": "Bug Fix Pattern",
        "category": "pattern",
        "conditions": {
            "pattern_regex": r"(fix|bug|issue|error|broken|not working|crash|failure)",
            "has_error_message": True,
            "has_reproduction_steps": True,
            "severity": ["low", "medium"]
        },
        "action": {
            "assign_to": "implementation-engineer",
            "tool": "implement_feature",
            "priority": "high",
            "metadata": {"task_type": "bug_fix"}
        },
        "confidence_threshold": 0.8
    },
    
    {
        "id": "rule-2.3",
        "name": "Code Generation from Spec",
        "category": "pattern",
        "conditions": {
            "pattern_regex": r"(generate|create|write)\s+(code|application|program|script)",
            "has_specifications": True,
            "programming_language": True
        },
        "action": {
            "assign_to": "implementation-engineer",
            "tool": "generate_code_from_spec",
            "priority": "medium",
            "metadata": {"task_type": "code_generation"}
        },
        "confidence_threshold": 0.8
    },
    
    # ===========================================
    # Category 3: Multi-Step Workflow Rules
    # ===========================================
    
    {
        "id": "rule-3.1",
        "name": "Full SDLC Workflow",
        "category": "workflow",
        "conditions": {
            "keywords_any": ["first", "then", "after that", "finally", "sequence", "workflow"],
            "has_multiple_phases": True,
            "phases": [
                {"phase": 1, "keywords": ["requirement", "spec", "analyze"]},
                {"phase": 2, "keywords": ["implement", "code", "build"]},
                {"phase": 3, "keywords": ["test", "verify", "validate"]}
            ]
        },
        "action": {
            "assign_to": "MULTIPLE",
            "sequence": ["requirements-engineer", "implementation-engineer", "qa-test-engineer"],
            "tool": "execute_workflow",
            "priority": "high",
            "metadata": {"task_type": "full_sdlc_workflow"}
        },
        "confidence_threshold": 0.7
    },
    
    {
        "id": "rule-3.2",
        "name": "Code Review Workflow",
        "category": "workflow",
        "conditions": {
            "keywords_any": ["review", "then", "fix"],
            "has_multiple_phases": True,
            "phases": [
                {"phase": 1, "keywords": ["review", "check", "audit"]},
                {"phase": 2, "keywords": ["fix", "implement", "update"]}
            ]
        },
        "action": {
            "assign_to": "MULTIPLE",
            "sequence": ["code-reviewer", "implementation-engineer"],
            "tool": "execute_workflow",
            "priority": "high",
            "metadata": {"task_type": "review_and_fix_workflow"}
        },
        "confidence_threshold": 0.75
    },
    
    # ===========================================
    # Category 4: Explicit Assignee Rules
    # ===========================================
    
    {
        "id": "rule-4.1",
        "name": "Explicit Implementation Engineer",
        "category": "explicit",
        "conditions": {
            "assignee_explicit": "implementation-engineer"
        },
        "action": {
            "assign_to": "implementation-engineer",
            "tool": "implement_feature",
            "priority": "medium",
            "metadata": {"task_type": "explicit_assignment"}
        },
        "confidence_threshold": 1.0
    },
    
    {
        "id": "rule-4.2",
        "name": "Explicit Requirements Engineer",
        "category": "explicit",
        "conditions": {
            "assignee_explicit": "requirements-engineer"
        },
        "action": {
            "assign_to": "requirements-engineer",
            "tool": "analyze_requirements",
            "priority": "medium",
            "metadata": {"task_type": "explicit_assignment"}
        },
        "confidence_threshold": 1.0
    },
    
    {
        "id": "rule-4.3",
        "name": "Explicit Code Reviewer",
        "category": "explicit",
        "conditions": {
            "assignee_explicit": "code-reviewer"
        },
        "action": {
            "assign_to": "code-reviewer",
            "tool": "review_code",
            "priority": "medium",
            "metadata": {"task_type": "explicit_assignment"}
        },
        "confidence_threshold": 1.0
    },
    
    {
        "id": "rule-4.4",
        "name": "Explicit QA Test Engineer",
        "category": "explicit",
        "conditions": {
            "assignee_explicit": "qa-test-engineer"
        },
        "action": {
            "assign_to": "qa-test-engineer",
            "tool": "generate_test_suite",
            "priority": "medium",
            "metadata": {"task_type": "explicit_assignment"}
        },
        "confidence_threshold": 1.0
    },
    
    {
        "id": "rule-4.5",
        "name": "Explicit Security Engineer",
        "category": "explicit",
        "conditions": {
            "assignee_explicit": "security-engineer"
        },
        "action": {
            "assign_to": "security-engineer",
            "tool": "perform_security_analysis",
            "priority": "medium",
            "metadata": {"task_type": "explicit_assignment"}
        },
        "confidence_threshold": 1.0
    },
    
    {
        "id": "rule-4.6",
        "name": "Explicit DevOps Engineer",
        "category": "explicit",
        "conditions": {
            "assignee_explicit": "devops-engineer"
        },
        "action": {
            "assign_to": "devops-engineer",
            "tool": "orchestrate_deployments",
            "priority": "medium",
            "metadata": {"task_type": "explicit_assignment"}
        },
        "confidence_threshold": 1.0
    },
]

# Agent endpoint mapping (will be populated from registry)
AGENT_ENDPOINTS = {
    "implementation-engineer": "http://127.0.0.1:3060/mcp",
    "requirements-engineer": None,  # Will be discovered from registry
    "code-reviewer": None,
    "qa-test-engineer": None,
    "security-engineer": None,
    "devops-engineer": None,
}

# Agent tool mappings
AGENT_TOOL_MAPPING = {
    "implementation-engineer": {
        "implement_feature": "implement_feature",
        "generate_code_from_spec": "generate_code_from_spec",
        "apply_coding_standards": "apply_coding_standards",
        "generate_unit_tests": "generate_unit_tests",
        "refactor_code": "refactor_code",
    },
    "requirements-engineer": {
        "analyze_requirements": "analyze_requirements",
        "resolve_ambiguity": "resolve_ambiguity",
        "translate_business_to_technical": "translate_business_to_technical",
    },
    "code-reviewer": {
        "review_code": "perform_static_analysis",
        "validate_architecture": "validate_architecture_compliance",
    },
    "qa-test-engineer": {
        "generate_test_suite": "generate_test_suite",
        "execute_tests": "execute_automated_tests",
    },
    "security-engineer": {
        "perform_security_analysis": "perform_security_analysis",
        "scan_dependencies": "scan_dependencies",
    },
    "devops-engineer": {
        "orchestrate_deployments": "orchestrate_deployments",
        "configure_ci_cd": "configure_ci_cd_pipeline",
    },
}
