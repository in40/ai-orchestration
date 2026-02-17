"""
Implementation Engineer Agent for MCP Server
Implements all required tools for code generation, feature implementation, and code management
"""
import subprocess
import tempfile
import os
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from config import settings


class GitCheckoutBranchArgs(BaseModel):
    repository_path: str = Field(..., description="Path to the Git repository")
    branch_name: str = Field(..., description="Name of the branch to checkout")
    create_if_not_exists: bool = Field(default=False, description="Create branch if it doesn't exist")
    remote_tracking: bool = Field(default=False, description="Track remote branch if creating new branch")


class GenerateCodeFromSpecArgs(BaseModel):
    specifications: str = Field(..., description="API specs, data models, and architectural decisions")
    programming_language: str = Field(..., description="Target programming language")
    framework: str = Field(..., description="Target framework or platform")
    coding_standards: str = Field(default="", description="Coding standards and style guides")
    existing_codebase_context: str = Field(default="", description="Context from existing codebase for consistency")


class ImplementFeatureArgs(BaseModel):
    feature_requirements: str = Field(..., description="Detailed feature requirements")
    architectural_guidelines: str = Field(..., description="Architectural patterns and guidelines to follow")
    dependencies: List[str] = Field(default=[], description="Dependencies and integration points")
    performance_requirements: List[str] = Field(default=[], description="Performance requirements for the feature")


class ApplyCodingStandardsArgs(BaseModel):
    code: str = Field(..., description="Code to apply standards to")
    style_guide: str = Field(..., description="Style guide and coding standards")
    language: str = Field(..., description="Programming language")
    existing_patterns: List[str] = Field(default=[], description="Patterns used in existing codebase")


class GenerateUnitTestsArgs(BaseModel):
    code: str = Field(..., description="Code to generate tests for")
    requirements: str = Field(..., description="Functional requirements to test")
    test_framework: str = Field(..., description="Target test framework")
    coverage_requirements: List[str] = Field(default=[], description="Coverage requirements")


class RefactorCodeArgs(BaseModel):
    code: str = Field(..., description="Code to refactor")
    refactoring_goals: List[str] = Field(..., description="Goals for refactoring (performance, readability, etc.)")
    constraints: List[str] = Field(default=[], description="Constraints and limitations for refactoring")
    existing_patterns: List[str] = Field(default=[], description="Patterns to maintain consistency with")


def git_checkout_branch(args: GitCheckoutBranchArgs) -> Dict[str, Any]:
    """
    Checkout a specific branch in a Git repository
    """
    try:
        repo_path = args.repository_path
        branch_name = args.branch_name
        
        # Change to the repository directory
        original_cwd = os.getcwd()
        os.chdir(repo_path)
        
        # Check if branch exists locally
        result = subprocess.run(['git', 'branch', '--list'], capture_output=True, text=True)
        local_branches = [line.strip().split()[0] for line in result.stdout.split('\n') if line.strip()]
        
        branch_exists_locally = branch_name in local_branches
        
        if not branch_exists_locally and args.create_if_not_exists:
            if args.remote_tracking:
                # Create new branch tracking remote
                cmd = ['git', 'checkout', '-b', branch_name, f'origin/{branch_name}']
            else:
                # Create new local branch
                cmd = ['git', 'checkout', '-b', branch_name]
        else:
            # Just checkout existing branch
            cmd = ['git', 'checkout', branch_name]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        os.chdir(original_cwd)
        
        if result.returncode == 0:
            return {
                "success": True,
                "message": f"Successfully checked out branch '{branch_name}'",
                "branch": branch_name,
                "repository_path": repo_path
            }
        else:
            os.chdir(original_cwd)
            return {
                "success": False,
                "error": result.stderr,
                "message": f"Failed to checkout branch '{branch_name}': {result.stderr}"
            }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Exception occurred while checking out branch: {str(e)}"
        }


def generate_code_from_spec(args: GenerateCodeFromSpecArgs) -> Dict[str, Any]:
    """
    Generate code from architectural specifications and requirements
    """
    try:
        # Create a prompt for the LLM to generate code from specifications
        prompt = f"""
        Generate code based on the following specifications:
        
        SPECIFICATIONS:
        {args.specifications}
        
        TARGET LANGUAGE: {args.programming_language}
        TARGET FRAMEWORK: {args.framework}
        
        CODING STANDARDS:
        {args.coding_standards}
        
        EXISTING CODEBASE CONTEXT:
        {args.existing_codebase_context}
        
        Please generate the code that implements these specifications following the target language, framework, and coding standards.
        """
        
        # Call the LLM to generate code
        from dependencies.vibe_coder import call_llm_sync
        llm_response = call_llm_sync(prompt, 7, None)  # Use medium-high creativity level
        
        # Extract code from the response (assuming it's in a markdown code block)
        import re
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', llm_response, re.DOTALL)
        
        if code_blocks:
            generated_code = code_blocks[0]
        else:
            generated_code = llm_response  # If no code block found, return the whole response
            
        return {
            "success": True,
            "generated_code": generated_code,
            "language": args.programming_language,
            "framework": args.framework,
            "specifications_used": args.specifications
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Exception occurred while generating code from specifications: {str(e)}"
        }


def implement_feature(args: ImplementFeatureArgs) -> Dict[str, Any]:
    """
    Implement specific features following architectural guidelines
    """
    try:
        # Create a prompt for the LLM to implement the feature
        prompt = f"""
        Implement the following feature following the architectural guidelines:
        
        FEATURE REQUIREMENTS:
        {args.feature_requirements}
        
        ARCHITECTURAL GUIDELINES:
        {args.architectural_guidelines}
        
        DEPENDENCIES:
        {', '.join(args.dependencies) if args.dependencies else 'None'}
        
        PERFORMANCE REQUIREMENTS:
        {', '.join(args.performance_requirements) if args.performance_requirements else 'None'}
        
        Please generate the code that implements this feature following the architectural guidelines and considering the dependencies and performance requirements.
        """
        
        # Call the LLM to implement the feature
        from dependencies.vibe_coder import call_llm_sync
        llm_response = call_llm_sync(prompt, 6, None)  # Use medium creativity level
        
        # Extract code from the response (assuming it's in a markdown code block)
        import re
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', llm_response, re.DOTALL)
        
        if code_blocks:
            implemented_code = code_blocks[0]
        else:
            implemented_code = llm_response  # If no code block found, return the whole response
            
        return {
            "success": True,
            "implemented_code": implemented_code,
            "feature_requirements": args.feature_requirements,
            "architectural_guidelines_followed": args.architectural_guidelines
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Exception occurred while implementing feature: {str(e)}"
        }


def apply_coding_standards(args: ApplyCodingStandardsArgs) -> Dict[str, Any]:
    """
    Apply consistent coding standards and patterns to code
    """
    try:
        # Create a prompt for the LLM to apply coding standards
        prompt = f"""
        Apply the following coding standards and style guide to the provided code:
        
        CODE TO STANDARDIZE:
        {args.code}
        
        STYLE GUIDE:
        {args.style_guide}
        
        PROGRAMMING LANGUAGE: {args.language}
        
        EXISTING PATTERNS:
        {', '.join(args.existing_patterns) if args.existing_patterns else 'None'}
        
        Please return the code with the coding standards applied, maintaining consistency with the existing patterns.
        """
        
        # Call the LLM to apply coding standards
        from dependencies.vibe_coder import call_llm_sync
        llm_response = call_llm_sync(prompt, 5, None)  # Use medium creativity level
        
        # Extract code from the response (assuming it's in a markdown code block)
        import re
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', llm_response, re.DOTALL)
        
        if code_blocks:
            standardized_code = code_blocks[0]
        else:
            standardized_code = llm_response  # If no code block found, return the whole response
            
        return {
            "success": True,
            "standardized_code": standardized_code,
            "original_code_length": len(args.code),
            "language": args.language,
            "style_guide_applied": args.style_guide
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Exception occurred while applying coding standards: {str(e)}"
        }


def generate_unit_tests(args: GenerateUnitTestsArgs) -> Dict[str, Any]:
    """
    Generate unit tests for code following test-first approach
    """
    try:
        # Create a prompt for the LLM to generate unit tests
        prompt = f"""
        Generate unit tests for the following code following the test-first approach:
        
        CODE TO TEST:
        {args.code}
        
        FUNCTIONAL REQUIREMENTS TO TEST:
        {args.requirements}
        
        TARGET TEST FRAMEWORK: {args.test_framework}
        
        COVERAGE REQUIREMENTS:
        {', '.join(args.coverage_requirements) if args.coverage_requirements else 'None'}
        
        Please generate comprehensive unit tests that cover the functionality based on the requirements and meet the coverage requirements.
        """
        
        # Call the LLM to generate unit tests
        from dependencies.vibe_coder import call_llm_sync
        llm_response = call_llm_sync(prompt, 6, None)  # Use medium creativity level
        
        # Extract code from the response (assuming it's in a markdown code block)
        import re
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', llm_response, re.DOTALL)
        
        if code_blocks:
            test_code = code_blocks[0]
        else:
            test_code = llm_response  # If no code block found, return the whole response
            
        return {
            "success": True,
            "generated_tests": test_code,
            "test_framework": args.test_framework,
            "tested_code_snippet": args.code[:100] + "..." if len(args.code) > 100 else args.code
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Exception occurred while generating unit tests: {str(e)}"
        }


def refactor_code(args: RefactorCodeArgs) -> Dict[str, Any]:
    """
    Refactor code for maintainability and performance improvements
    """
    try:
        # Create a prompt for the LLM to refactor code
        prompt = f"""
        Refactor the following code based on the specified goals:
        
        CODE TO REFACTOR:
        {args.code}
        
        REFACTORING GOALS:
        {', '.join(args.refactoring_goals)}
        
        CONSTRAINTS:
        {', '.join(args.constraints) if args.constraints else 'None'}
        
        EXISTING PATTERNS TO MAINTAIN:
        {', '.join(args.existing_patterns) if args.existing_patterns else 'None'}
        
        Please return the refactored code that achieves the refactoring goals while respecting the constraints and maintaining consistency with existing patterns.
        """
        
        # Call the LLM to refactor code
        from dependencies.vibe_coder import call_llm_sync
        llm_response = call_llm_sync(prompt, 7, None)  # Use medium-high creativity level
        
        # Extract code from the response (assuming it's in a markdown code block)
        import re
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', llm_response, re.DOTALL)
        
        if code_blocks:
            refactored_code = code_blocks[0]
        else:
            refactored_code = llm_response  # If no code block found, return the whole response
            
        return {
            "success": True,
            "refactored_code": refactored_code,
            "original_code_length": len(args.code),
            "refactoring_goals_achieved": args.refactoring_goals,
            "constraints_respected": args.constraints
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Exception occurred while refactoring code: {str(e)}"
        }


def register_implementation_engineer_tools(server_handlers):
    """
    Register all Implementation Engineer tools with the server handlers
    """
    # Define all the tools for the Implementation Engineer Agent
    implementation_engineer_tools = [
        {
            "name": "git_checkout_branch",
            "description": "Checkout a specific branch in a Git repository",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repository_path": {"type": "string", "description": "Path to the Git repository"},
                    "branch_name": {"type": "string", "description": "Name of the branch to checkout"},
                    "create_if_not_exists": {"type": "boolean", "default": False, "description": "Create branch if it doesn't exist"},
                    "remote_tracking": {"type": "boolean", "default": False, "description": "Track remote branch if creating new branch"}
                },
                "required": ["repository_path", "branch_name"]
            }
        },
        {
            "name": "generate_code_from_spec",
            "description": "Generate code from architectural specifications and requirements",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "specifications": {"type": "string", "description": "API specs, data models, and architectural decisions"},
                    "programming_language": {"type": "string", "description": "Target programming language"},
                    "framework": {"type": "string", "description": "Target framework or platform"},
                    "coding_standards": {"type": "string", "description": "Coding standards and style guides"},
                    "existing_codebase_context": {"type": "string", "description": "Context from existing codebase for consistency"}
                },
                "required": ["specifications", "programming_language", "framework"]
            }
        },
        {
            "name": "implement_feature",
            "description": "Implement specific features following architectural guidelines",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "feature_requirements": {"type": "string", "description": "Detailed feature requirements"},
                    "architectural_guidelines": {"type": "string", "description": "Architectural patterns and guidelines to follow"},
                    "dependencies": {"type": "array", "items": {"type": "string"}, "description": "Dependencies and integration points"},
                    "performance_requirements": {"type": "array", "items": {"type": "string"}, "description": "Performance requirements for the feature"}
                },
                "required": ["feature_requirements", "architectural_guidelines"]
            }
        },
        {
            "name": "apply_coding_standards",
            "description": "Apply consistent coding standards and patterns to code",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Code to apply standards to"},
                    "style_guide": {"type": "string", "description": "Style guide and coding standards"},
                    "language": {"type": "string", "description": "Programming language"},
                    "existing_patterns": {"type": "array", "items": {"type": "string"}, "description": "Patterns used in existing codebase"}
                },
                "required": ["code", "style_guide", "language"]
            }
        },
        {
            "name": "generate_unit_tests",
            "description": "Generate unit tests for code following test-first approach",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Code to generate tests for"},
                    "requirements": {"type": "string", "description": "Functional requirements to test"},
                    "test_framework": {"type": "string", "description": "Target test framework"},
                    "coverage_requirements": {"type": "array", "items": {"type": "string"}, "description": "Coverage requirements"}
                },
                "required": ["code", "requirements", "test_framework"]
            }
        },
        {
            "name": "refactor_code",
            "description": "Refactor code for maintainability and performance improvements",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Code to refactor"},
                    "refactoring_goals": {"type": "array", "items": {"type": "string"}, "description": "Goals for refactoring (performance, readability, etc.)"},
                    "constraints": {"type": "array", "items": {"type": "string"}, "description": "Constraints and limitations for refactoring"},
                    "existing_patterns": {"type": "array", "items": {"type": "string"}, "description": "Patterns to maintain consistency with"}
                },
                "required": ["code", "refactoring_goals"]
            }
        }
    ]

    # Add the Implementation Engineer tools to the server handlers
    server_handlers.tools.extend(implementation_engineer_tools)

    # Notify that tools have changed
    if hasattr(server_handlers, 'notification_manager') and server_handlers.notification_manager:
        server_handlers.notification_manager.mark_tools_changed()

    # Enhance the _execute_tool method to handle Implementation Engineer tools
    original_execute_tool = server_handlers._execute_tool

    def enhanced_execute_tool(tool, arguments):
        tool_name = tool["name"]

        if tool_name == "git_checkout_branch":
            try:
                args = GitCheckoutBranchArgs(**arguments)
                return git_checkout_branch(args)
            except Exception as e:
                return {"error": f"Failed to execute git_checkout_branch: {str(e)}"}

        elif tool_name == "generate_code_from_spec":
            try:
                args = GenerateCodeFromSpecArgs(**arguments)
                return generate_code_from_spec(args)
            except Exception as e:
                return {"error": f"Failed to execute generate_code_from_spec: {str(e)}"}

        elif tool_name == "implement_feature":
            try:
                args = ImplementFeatureArgs(**arguments)
                return implement_feature(args)
            except Exception as e:
                return {"error": f"Failed to execute implement_feature: {str(e)}"}

        elif tool_name == "apply_coding_standards":
            try:
                args = ApplyCodingStandardsArgs(**arguments)
                return apply_coding_standards(args)
            except Exception as e:
                return {"error": f"Failed to execute apply_coding_standards: {str(e)}"}

        elif tool_name == "generate_unit_tests":
            try:
                args = GenerateUnitTestsArgs(**arguments)
                return generate_unit_tests(args)
            except Exception as e:
                return {"error": f"Failed to execute generate_unit_tests: {str(e)}"}

        elif tool_name == "refactor_code":
            try:
                args = RefactorCodeArgs(**arguments)
                return refactor_code(args)
            except Exception as e:
                return {"error": f"Failed to execute refactor_code: {str(e)}"}

        else:
            # Call the original method for other tools
            return original_execute_tool(tool, arguments)

    server_handlers._execute_tool = enhanced_execute_tool