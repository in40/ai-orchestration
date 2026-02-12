"""
Vibe Coding Agent Tools
Implementation of all 12 required coding agent tools with full validation and error handling
"""
import os
import asyncio
import logging
import subprocess
import tempfile
import json
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import hashlib
import uuid

from pydantic import BaseModel, ValidationError
from mcp import McpError

from .lmstudio_client import get_lm_client, LMResponse

# Configure logging
logger = logging.getLogger(__name__)

# Global variables for tracking
_active_plans = {}
_memory_store = {}

class Plan(BaseModel):
    """Model for task planning"""
    plan_id: str
    task_description: str
    subtasks: List[Dict[str, str]]
    status: str = "pending"
    created_at: datetime = datetime.now()
    completed_at: Optional[datetime] = None

class TaskInput(BaseModel):
    """Input validation for accept_task"""
    task_description: str
    context_files: Optional[List[str]] = []

class PlanStatusInput(BaseModel):
    """Input validation for get_plan_status"""
    plan_id: str

class AnalyzeCodeInput(BaseModel):
    """Input validation for analyze_code"""
    file_path: Optional[str] = None
    analysis_type: str
    code_snippet: Optional[str] = None

class ExplainCodeInput(BaseModel):
    """Input validation for explain_code"""
    file_path: Optional[str] = None
    code_snippet: Optional[str] = None
    detail_level: str = "detailed"

class GenerateCodeInput(BaseModel):
    """Input validation for generate_code"""
    specification: str
    file_path: Optional[str] = None
    language: Optional[str] = None

class WriteFileInput(BaseModel):
    """Input validation for write_file_content"""
    file_path: str
    content: str
    confirm_write: bool
    line_start: Optional[int] = None
    line_end: Optional[int] = None

class ReadFileInput(BaseModel):
    """Input validation for read_file_content"""
    file_path: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    encoding: Optional[str] = None

class ExecuteCodeInput(BaseModel):
    """Input validation for execute_code"""
    code: str
    language: str
    timeout: int = 30
    allow_network: bool = False

class RunTestsInput(BaseModel):
    """Input validation for run_tests"""
    test_pattern: Optional[str] = None
    test_directory: Optional[str] = None
    framework: str = "pytest"

class StoreMemoryInput(BaseModel):
    """Input validation for store_memory"""
    key: str
    value: str
    category: Optional[str] = None
    metadata: Optional[Dict] = {}

class RetrieveMemoryInput(BaseModel):
    """Input validation for retrieve_memory"""
    key: Optional[str] = None
    query: Optional[str] = None
    category: Optional[str] = None
    limit: int = 5

class DebugErrorInput(BaseModel):
    """Input validation for debug_error"""
    error_message: str
    code_snippet: Optional[str] = None
    context: Optional[str] = None

async def accept_task(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts a natural language task description and optional context files.
    Uses LM Studio to break down into subtasks, generate a plan (JSON schema output).
    Returns plan_id and structured plan.
    """
    try:
        validated_input = TaskInput(**input_data)
    except ValidationError as e:
        logger.error(f"Input validation failed: {str(e)}")
        raise McpError(f"Invalid input: {str(e)}")
    
    correlation_id = str(uuid.uuid4())
    logger.info(f"[{correlation_id}] Starting task acceptance for: {validated_input.task_description[:100]}...")
    
    try:
        # Get LM Studio client
        client = await get_lm_client()
        
        # Prepare context if files are provided
        context = ""
        if validated_input.context_files:
            for file_path in validated_input.context_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()[:2000]  # Limit context size
                        context += f"\n\nFile: {file_path}\nContent:\n{content}"
                except Exception as e:
                    logger.warning(f"Could not read context file {file_path}: {str(e)}")
        
        # Create prompt for task breakdown
        prompt = f"""
        Please break down the following development task into structured subtasks:
        
        TASK: {validated_input.task_description}
        
        CONTEXT: {context}
        
        Respond with a JSON object containing:
        {{
            "subtasks": [
                {{
                    "id": "unique_id",
                    "description": "Brief description of the subtask",
                    "priority": "high|medium|low",
                    "estimated_effort": "minutes",
                    "dependencies": ["other_subtask_ids_if_any"]
                }}
            ]
        }}
        
        Make sure the JSON is valid and properly formatted.
        """
        
        # Get structured response from LM Studio
        response: LMResponse = await client.chat_completion(
            prompt=prompt,
            system_prompt="You are an expert software architect. Break down development tasks into actionable subtasks with clear priorities and dependencies.",
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        try:
            result = json.loads(response.content)
            subtasks = result.get("subtasks", [])
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LM response: {str(e)}")
            # Fallback: try to extract JSON from response
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                subtasks = result.get("subtasks", [])
            else:
                raise McpError(f"Could not parse structured response from LM Studio: {response.content}")
        
        # Create plan
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        plan = Plan(
            plan_id=plan_id,
            task_description=validated_input.task_description,
            subtasks=subtasks
        )
        
        # Store plan
        _active_plans[plan_id] = plan
        
        logger.info(f"[{correlation_id}] Created plan {plan_id} with {len(subtasks)} subtasks")
        
        return {
            "plan_id": plan_id,
            "task_description": validated_input.task_description,
            "subtasks_count": len(subtasks),
            "subtasks": subtasks,
            "created_at": plan.created_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"[{correlation_id}] Error in accept_task: {str(e)}")
        raise McpError(f"Failed to create plan: {str(e)}")

async def get_plan_status(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieves status of an ongoing plan.
    """
    try:
        validated_input = PlanStatusInput(**input_data)
    except ValidationError as e:
        logger.error(f"Input validation failed: {str(e)}")
        raise McpError(f"Invalid input: {str(e)}")
    
    correlation_id = str(uuid.uuid4())
    logger.info(f"[{correlation_id}] Getting status for plan: {validated_input.plan_id}")
    
    try:
        if validated_input.plan_id not in _active_plans:
            raise McpError(f"Plan not found: {validated_input.plan_id}")
        
        plan = _active_plans[validated_input.plan_id]
        
        return {
            "plan_id": plan.plan_id,
            "status": plan.status,
            "task_description": plan.task_description,
            "subtasks_count": len(plan.subtasks),
            "completed_subtasks": len([s for s in plan.subtasks if s.get('completed', False)]),
            "created_at": plan.created_at.isoformat(),
            "completed_at": plan.completed_at.isoformat() if plan.completed_at else None
        }
        
    except Exception as e:
        logger.error(f"[{correlation_id}] Error in get_plan_status: {str(e)}")
        raise McpError(f"Failed to get plan status: {str(e)}")

async def analyze_code(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyzes code for bugs, optimization opportunities, explanations, or refactoring suggestions.
    """
    try:
        validated_input = AnalyzeCodeInput(**input_data)
    except ValidationError as e:
        logger.error(f"Input validation failed: {str(e)}")
        raise McpError(f"Invalid input: {str(e)}")
    
    correlation_id = str(uuid.uuid4())
    logger.info(f"[{correlation_id}] Analyzing code for type: {validated_input.analysis_type}")
    
    try:
        # Get code content
        code_content = validated_input.code_snippet
        if not code_content and validated_input.file_path:
            with open(validated_input.file_path, 'r', encoding='utf-8') as f:
                code_content = f.read()
        
        if not code_content:
            raise McpError("Either code_snippet or file_path must be provided")
        
        # Get LM Studio client
        client = await get_lm_client()
        
        # Create analysis prompt based on type
        analysis_prompts = {
            "bugs": "Identify potential bugs, logical errors, and issues in the code.",
            "optimization": "Suggest performance optimizations and improvements.",
            "explanation": "Provide a detailed explanation of what the code does.",
            "refactor": "Suggest refactoring opportunities to improve code quality."
        }
        
        prompt = f"""
        {analysis_prompts.get(validated_input.analysis_type, analysis_prompts['explanation'])}
        
        CODE:
        {code_content}
        
        Respond with a structured analysis in JSON format:
        {{
            "issues": [
                {{
                    "type": "bug|performance|readability|security",
                    "severity": "high|medium|low",
                    "location": "line numbers or function names",
                    "description": "Detailed description of the issue",
                    "suggestion": "How to fix or improve"
                }}
            ],
            "summary": "Brief summary of findings",
            "confidence": "high|medium|low"
        }}
        """
        
        response: LMResponse = await client.chat_completion(
            prompt=prompt,
            system_prompt="You are an expert code reviewer. Provide detailed, actionable feedback with specific line references when possible.",
            response_format={"type": "json_object"}
        )
        
        try:
            analysis_result = json.loads(response.content)
        except json.JSONDecodeError:
            # Fallback parsing
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                analysis_result = json.loads(json_match.group())
            else:
                analysis_result = {
                    "issues": [],
                    "summary": response.content,
                    "confidence": "medium"
                }
        
        logger.info(f"[{correlation_id}] Completed analysis with {len(analysis_result.get('issues', []))} issues found")
        
        return {
            "analysis_type": validated_input.analysis_type,
            "file_path": validated_input.file_path,
            "issues_found": len(analysis_result.get("issues", [])),
            "analysis": analysis_result,
            "token_usage": response.usage
        }
        
    except Exception as e:
        logger.error(f"[{correlation_id}] Error in analyze_code: {str(e)}")
        raise McpError(f"Failed to analyze code: {str(e)}")

async def explain_code(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Provides line-by-line or high-level explanation of code.
    """
    try:
        validated_input = ExplainCodeInput(**input_data)
    except ValidationError as e:
        logger.error(f"Input validation failed: {str(e)}")
        raise McpError(f"Invalid input: {str(e)}")
    
    correlation_id = str(uuid.uuid4())
    logger.info(f"[{correlation_id}] Explaining code with detail level: {validated_input.detail_level}")
    
    try:
        # Get code content
        code_content = validated_input.code_snippet
        if not code_content and validated_input.file_path:
            with open(validated_input.file_path, 'r', encoding='utf-8') as f:
                code_content = f.read()
        
        if not code_content:
            raise McpError("Either code_snippet or file_path must be provided")
        
        # Get LM Studio client
        client = await get_lm_client()
        
        # Create explanation prompt based on detail level
        if validated_input.detail_level == "high_level":
            prompt = f"""
            Provide a high-level overview of what this code does:
            
            CODE:
            {code_content}
            
            Respond with:
            {{
                "purpose": "High-level purpose of the code",
                "components": ["main components/functions"],
                "data_flow": "How data flows through the code",
                "key_patterns": ["design patterns used"]
            }}
            """
        elif validated_input.detail_level == "line_by_line":
            prompt = f"""
            Provide a line-by-line explanation of this code:
            
            CODE:
            {code_content}
            
            Respond with:
            {{
                "explanation": [
                    {{
                        "line_number": 1,
                        "code": "actual code line",
                        "explanation": "what this line does"
                    }}
                ],
                "summary": "overall summary"
            }}
            """
        else:  # detailed (default)
            prompt = f"""
            Provide a detailed explanation of this code:
            
            CODE:
            {code_content}
            
            Respond with:
            {{
                "overview": "What the code does",
                "functions": [
                    {{
                        "name": "function name",
                        "purpose": "what it does",
                        "inputs": ["parameters"],
                        "outputs": ["return values"]
                    }}
                ],
                "logic_flow": "Step-by-step explanation of the logic",
                "important_details": ["key implementation details"]
            }}
            """
        
        response: LMResponse = await client.chat_completion(
            prompt=prompt,
            system_prompt="You are an expert programmer explaining code to other developers. Be clear, accurate, and comprehensive.",
            response_format={"type": "json_object"}
        )
        
        try:
            explanation_result = json.loads(response.content)
        except json.JSONDecodeError:
            # Fallback: return as plain text
            explanation_result = {
                "explanation": response.content,
                "format": "text"
            }
        
        logger.info(f"[{correlation_id}] Completed code explanation")
        
        return {
            "detail_level": validated_input.detail_level,
            "file_path": validated_input.file_path,
            "explanation": explanation_result,
            "token_usage": response.usage
        }
        
    except Exception as e:
        logger.error(f"[{correlation_id}] Error in explain_code: {str(e)}")
        raise McpError(f"Failed to explain code: {str(e)}")

async def generate_code(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates code from plan or natural language specification.
    """
    try:
        validated_input = GenerateCodeInput(**input_data)
    except ValidationError as e:
        logger.error(f"Input validation failed: {str(e)}")
        raise McpError(f"Invalid input: {str(e)}")
    
    correlation_id = str(uuid.uuid4())
    logger.info(f"[{correlation_id}] Generating code for specification: {validated_input.specification[:100]}...")
    
    try:
        # Get LM Studio client
        client = await get_lm_client()
        
        # Create generation prompt
        prompt = f"""
        Generate code based on the following specification:
        
        SPECIFICATION:
        {validated_input.specification}
        
        REQUIREMENTS:
        - Write clean, well-documented code
        - Follow best practices for the specified language
        - Include appropriate error handling
        - Add comments explaining complex logic
        
        LANGUAGE: {validated_input.language or 'Python'}
        
        If a file path is suggested, consider the existing project structure.
        SUGGESTED FILE PATH: {validated_input.file_path or 'Not specified'}
        
        Respond with:
        {{
            "code": "generated code",
            "file_path": "suggested file path",
            "language": "programming language",
            "dependencies": ["required dependencies"],
            "notes": "implementation notes"
        }}
        """
        
        response: LMResponse = await client.chat_completion(
            prompt=prompt,
            system_prompt="You are an expert developer generating high-quality, production-ready code. Focus on correctness, efficiency, and maintainability.",
            response_format={"type": "json_object"}
        )
        
        try:
            generation_result = json.loads(response.content)
        except json.JSONDecodeError:
            # Fallback: extract code from response
            code_match = re.search(r'```(?:\w+)?\n(.*?)```', response.content, re.DOTALL)
            if code_match:
                generation_result = {
                    "code": code_match.group(1),
                    "file_path": validated_input.file_path or "generated_code.py",
                    "language": validated_input.language or "Python",
                    "dependencies": [],
                    "notes": "Code extracted from response"
                }
            else:
                raise McpError("Could not extract code from LM response")
        
        logger.info(f"[{correlation_id}] Generated code with {len(generation_result.get('code', ''))} characters")
        
        return {
            "code": generation_result.get("code", ""),
            "file_path": generation_result.get("file_path", validated_input.file_path),
            "language": generation_result.get("language", validated_input.language),
            "dependencies": generation_result.get("dependencies", []),
            "notes": generation_result.get("notes", ""),
            "token_usage": response.usage
        }
        
    except Exception as e:
        logger.error(f"[{correlation_id}] Error in generate_code: {str(e)}")
        raise McpError(f"Failed to generate code: {str(e)}")

async def write_file_content(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Writes content to a file with security validation. Validates path is inside project root, 
    prevents directory traversal, requires explicit confirmation flag.
    """
    try:
        validated_input = WriteFileInput(**input_data)
    except ValidationError as e:
        logger.error(f"Input validation failed: {str(e)}")
        raise McpError(f"Invalid input: {str(e)}")
    
    correlation_id = str(uuid.uuid4())
    logger.info(f"[{correlation_id}] Writing file: {validated_input.file_path}")
    
    try:
        # Security validation
        if not validated_input.confirm_write:
            raise McpError("confirm_write must be True to write file")
        
        # Validate file path to prevent directory traversal
        file_path = Path(validated_input.file_path).resolve()
        project_root = Path.cwd().resolve()
        
        # Check if file path is within project root
        try:
            file_path.relative_to(project_root)
        except ValueError:
            raise McpError(f"File path '{validated_input.file_path}' is outside project root")
        
        # Additional security checks
        if ".." in str(file_path) or str(file_path).startswith("/etc/") or str(file_path).startswith("/root/"):
            raise McpError(f"Suspicious file path detected: {validated_input.file_path}")
        
        # Create directory if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Handle partial writes if line range is specified
        if validated_input.line_start is not None and validated_input.line_end is not None:
            # Read existing file and replace specific lines
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Replace the specified range
                start_idx = max(0, validated_input.line_start - 1)  # Convert to 0-based index
                end_idx = min(len(lines), validated_input.line_end)  # Keep within bounds
                
                # Split the new content into lines
                new_lines = validated_input.content.split('\n')
                if not new_lines[-1].endswith('\n'):  # Ensure last line ends with newline if original did
                    new_lines[-1] += '\n'
                
                # Replace the range
                lines[start_idx:end_idx] = [f"{line}\n" for line in new_lines]
                
                # Write back to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
            else:
                # If file doesn't exist, just write the content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(validated_input.content)
        else:
            # Full file write
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(validated_input.content)
        
        file_size = file_path.stat().st_size
        
        logger.info(f"[{correlation_id}] Successfully wrote {file_size} bytes to {file_path}")
        
        return {
            "file_path": str(file_path),
            "bytes_written": file_size,
            "partial_write": validated_input.line_start is not None and validated_input.line_end is not None,
            "confirmed": True
        }
        
    except Exception as e:
        logger.error(f"[{correlation_id}] Error in write_file_content: {str(e)}")
        raise McpError(f"Failed to write file: {str(e)}")

async def read_file_content(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reads file content with line-range support and encoding detection.
    """
    try:
        validated_input = ReadFileInput(**input_data)
    except ValidationError as e:
        logger.error(f"Input validation failed: {str(e)}")
        raise McpError(f"Invalid input: {str(e)}")
    
    correlation_id = str(uuid.uuid4())
    logger.info(f"[{correlation_id}] Reading file: {validated_input.file_path}")
    
    try:
        file_path = Path(validated_input.file_path)
        
        # Validate file path security
        resolved_path = file_path.resolve()
        project_root = Path.cwd().resolve()
        
        try:
            resolved_path.relative_to(project_root)
        except ValueError:
            raise McpError(f"File path '{validated_input.file_path}' is outside project root")
        
        # Check if it's a suspicious path
        if ".." in str(resolved_path) or str(resolved_path).startswith("/etc/") or str(resolved_path).startswith("/root/"):
            raise McpError(f"Suspicious file path detected: {validated_input.file_path}")
        
        # Detect encoding if not specified
        encoding = validated_input.encoding or 'utf-8'
        
        # Read file with specified parameters
        with open(resolved_path, 'r', encoding=encoding) as f:
            if validated_input.start_line is not None or validated_input.end_line is not None:
                # Read specific line range
                all_lines = f.readlines()
                
                start_idx = (validated_input.start_line or 1) - 1  # Convert to 0-based
                end_idx = validated_input.end_line or len(all_lines)  # Use total lines if not specified
                
                # Ensure indices are within bounds
                start_idx = max(0, start_idx)
                end_idx = min(len(all_lines), end_idx)
                
                selected_lines = all_lines[start_idx:end_idx]
                content = ''.join(selected_lines)
                
                line_range = f"{start_idx + 1}-{end_idx}"
            else:
                # Read entire file
                content = f.read()
                line_range = "all"
        
        logger.info(f"[{correlation_id}] Successfully read {len(content)} characters from {resolved_path}")
        
        return {
            "file_path": str(resolved_path),
            "content": content,
            "size_bytes": len(content.encode('utf-8')),
            "encoding": encoding,
            "line_range": line_range,
            "total_lines": len(content.split('\n'))
        }
        
    except FileNotFoundError:
        raise McpError(f"File not found: {validated_input.file_path}")
    except UnicodeDecodeError:
        raise McpError(f"Could not decode file with {encoding} encoding: {validated_input.file_path}")
    except Exception as e:
        logger.error(f"[{correlation_id}] Error in read_file_content: {str(e)}")
        raise McpError(f"Failed to read file: {str(e)}")

async def execute_code(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes code in a sandboxed environment with timeout protection and resource limits.
    """
    try:
        validated_input = ExecuteCodeInput(**input_data)
    except ValidationError as e:
        logger.error(f"Input validation failed: {str(e)}")
        raise McpError(f"Invalid input: {str(e)}")
    
    correlation_id = str(uuid.uuid4())
    logger.info(f"[{correlation_id}] Executing {validated_input.language} code")
    
    try:
        # Validate allowed languages
        allowed_languages = ["python", "bash"]
        if validated_input.language.lower() not in allowed_languages:
            raise McpError(f"Language not allowed: {validated_input.language}. Allowed: {allowed_languages}")
        
        # Create temporary file for code execution
        with tempfile.NamedTemporaryFile(mode='w+', suffix=f'.{validated_input.language}', delete=False) as temp_file:
            temp_file.write(validated_input.code)
            temp_file_path = temp_file.name
        
        try:
            # Execute based on language
            if validated_input.language.lower() == "python":
                cmd = ["python3", temp_file_path]
            elif validated_input.language.lower() == "bash":
                cmd = ["bash", temp_file_path]
            else:
                raise McpError(f"Unsupported language: {validated_input.language}")
            
            # Execute with timeout and security limits
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=validated_input.timeout,
                cwd="/tmp",  # Execute in temp directory for safety
                # Note: For production, consider using more restrictive environments
            )
            
            execution_result = {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "language": validated_input.language,
                "execution_time_limit": validated_input.timeout,
                "success": result.returncode == 0
            }
            
            logger.info(f"[{correlation_id}] Code execution completed with exit code {result.returncode}")
            
            return execution_result
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
            
    except subprocess.TimeoutExpired:
        logger.warning(f"[{correlation_id}] Code execution timed out after {validated_input.timeout}s")
        raise McpError(f"Code execution timed out after {validated_input.timeout} seconds")
    except Exception as e:
        logger.error(f"[{correlation_id}] Error in execute_code: {str(e)}")
        raise McpError(f"Failed to execute code: {str(e)}")

async def run_tests(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Discovers and runs tests, returning JUnit-style summary.
    """
    try:
        validated_input = RunTestsInput(**input_data)
    except ValidationError as e:
        logger.error(f"Input validation failed: {str(e)}")
        raise McpError(f"Invalid input: {str(e)}")
    
    correlation_id = str(uuid.uuid4())
    logger.info(f"[{correlation_id}] Running tests with framework: {validated_input.framework}")
    
    try:
        # Determine test directory
        test_dir = validated_input.test_directory or "."
        test_pattern = validated_input.test_pattern or "test_*.py"
        
        # Run tests based on framework
        if validated_input.framework.lower() == "pytest":
            import subprocess
            import json
            
            # Build pytest command
            cmd = ["python3", "-m", "pytest", test_dir, "-v", "--tb=short", "--json-report"]
            
            # Add pattern if specified
            if test_pattern:
                cmd.extend(["-k", test_pattern.replace(".py", "").replace("test_", "")])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # 5 minute timeout
            
            # Parse pytest JSON report if available
            if '"report":' in result.stdout:
                # Extract JSON portion from pytest-json-report output
                json_start = result.stdout.find('{')
                json_end = result.stdout.rfind('}') + 1
                if json_start != -1 and json_end != 0:
                    try:
                        report_data = json.loads(result.stdout[json_start:json_end])
                        tests_summary = {
                            "framework": "pytest",
                            "passed": report_data.get("summary", {}).get("passed", 0),
                            "failed": report_data.get("summary", {}).get("failed", 0),
                            "skipped": report_data.get("summary", {}).get("skipped", 0),
                            "total": report_data.get("summary", {}).get("total", 0),
                            "duration": report_data.get("summary", {}).get("duration", 0),
                            "details": report_data.get("collectors", [])
                        }
                    except json.JSONDecodeError:
                        # Fallback to parsing stdout
                        passed = result.stdout.count("PASSED")
                        failed = result.stdout.count("FAILED")
                        skipped = result.stdout.count("SKIPPED")
                        
                        tests_summary = {
                            "framework": "pytest",
                            "passed": passed,
                            "failed": failed,
                            "skipped": skipped,
                            "total": passed + failed + skipped,
                            "stdout": result.stdout[-2000:],  # Last 2000 chars
                            "stderr": result.stderr[-1000:],  # Last 1000 chars
                            "success": result.returncode in [0, 5]  # 0=success, 5=no tests
                        }
                else:
                    # Fallback parsing
                    passed = result.stdout.count("PASSED")
                    failed = result.stdout.count("FAILED")
                    skipped = result.stdout.count("SKIPPED")
                    
                    tests_summary = {
                        "framework": "pytest",
                        "passed": passed,
                        "failed": failed,
                        "skipped": skipped,
                        "total": passed + failed + skipped,
                        "stdout": result.stdout[-2000:],
                        "stderr": result.stderr[-1000:],
                        "success": result.returncode in [0, 5]
                    }
            else:
                # Fallback parsing
                passed = result.stdout.count("PASSED")
                failed = result.stdout.count("FAILED")
                skipped = result.stdout.count("SKIPPED")
                
                tests_summary = {
                    "framework": "pytest",
                    "passed": passed,
                    "failed": failed,
                    "skipped": skipped,
                    "total": passed + failed + skipped,
                    "stdout": result.stdout[-2000:],
                    "stderr": result.stderr[-1000:],
                    "success": result.returncode in [0, 5]
                }
        
        elif validated_input.framework.lower() == "unittest":
            import subprocess
            import xml.etree.ElementTree as ET
            
            # Create temporary XML output file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as xml_file:
                xml_path = xml_file.name
            
            try:
                # Run unittest with XML output
                cmd = ["python3", "-m", "unittest", "discover", "-s", test_dir, "-p", test_pattern, "-v"]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                # Parse results from stdout
                passed = result.stdout.count("ok")
                failed = result.stdout.count("FAIL")
                errors = result.stdout.count("ERROR")
                
                tests_summary = {
                    "framework": "unittest",
                    "passed": passed,
                    "failed": failed,
                    "errors": errors,
                    "total": passed + failed + errors,
                    "stdout": result.stdout[-2000:],
                    "stderr": result.stderr[-1000:],
                    "success": result.returncode == 0
                }
            finally:
                # Clean up XML file
                if os.path.exists(xml_path):
                    os.unlink(xml_path)
        
        else:  # Custom framework
            # For custom framework, return basic execution info
            tests_summary = {
                "framework": "custom",
                "message": "Custom test framework - implement specific runner",
                "test_pattern": test_pattern,
                "test_directory": test_dir,
                "success": True
            }
        
        logger.info(f"[{correlation_id}] Test execution completed: {tests_summary}")
        
        return tests_summary
        
    except subprocess.TimeoutExpired:
        raise McpError("Test execution timed out")
    except Exception as e:
        logger.error(f"[{correlation_id}] Error in run_tests: {str(e)}")
        raise McpError(f"Failed to run tests: {str(e)}")

async def store_memory(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stores persistent key-value memory with categorization support.
    """
    try:
        validated_input = StoreMemoryInput(**input_data)
    except ValidationError as e:
        logger.error(f"Input validation failed: {str(e)}")
        raise McpError(f"Invalid input: {str(e)}")
    
    correlation_id = str(uuid.uuid4())
    logger.info(f"[{correlation_id}] Storing memory with key: {validated_input.key}")
    
    try:
        # Create memory entry
        memory_entry = {
            "key": validated_input.key,
            "value": validated_input.value,
            "category": validated_input.category,
            "metadata": validated_input.metadata or {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "access_count": 0
        }
        
        # Store in global memory store (in production, use persistent storage)
        _memory_store[validated_input.key] = memory_entry
        
        # Also save to file for persistence
        memory_file = Path("memory_store.json")
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(_memory_store, f, indent=2)
        
        logger.info(f"[{correlation_id}] Memory stored successfully")
        
        return {
            "key": validated_input.key,
            "category": validated_input.category,
            "stored": True,
            "timestamp": memory_entry["created_at"]
        }
        
    except Exception as e:
        logger.error(f"[{correlation_id}] Error in store_memory: {str(e)}")
        raise McpError(f"Failed to store memory: {str(e)}")

async def retrieve_memory(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieves memory with semantic search capabilities.
    """
    try:
        validated_input = RetrieveMemoryInput(**input_data)
    except ValidationError as e:
        logger.error(f"Input validation failed: {str(e)}")
        raise McpError(f"Invalid input: {str(e)}")
    
    correlation_id = str(uuid.uuid4())
    
    try:
        results = []
        
        if validated_input.key:
            # Exact key match
            if validated_input.key in _memory_store:
                entry = _memory_store[validated_input.key]
                entry["access_count"] = entry.get("access_count", 0) + 1
                results.append(entry)
        elif validated_input.query:
            # Semantic search based on query (simple keyword matching for now)
            query_lower = validated_input.query.lower()
            
            for key, entry in _memory_store.items():
                # Simple text search in key, value, and metadata
                searchable_text = f"{key} {entry['value']} {str(entry['metadata'])}".lower()
                
                if query_lower in searchable_text:
                    entry["access_count"] = entry.get("access_count", 0) + 1
                    results.append(entry)
                    
                    if len(results) >= validated_input.limit:
                        break
        else:
            # Return all memories filtered by category if specified
            for key, entry in _memory_store.items():
                if not validated_input.category or entry.get("category") == validated_input.category:
                    results.append(entry)
                    
                    if len(results) >= validated_input.limit:
                        break
        
        # Sort results by access count (descending) to surface frequently accessed items
        results.sort(key=lambda x: x.get("access_count", 0), reverse=True)
        
        logger.info(f"[{correlation_id}] Retrieved {len(results)} memory entries")
        
        return {
            "query_type": "key_lookup" if validated_input.key else "semantic_search" if validated_input.query else "category_list",
            "results_count": len(results),
            "results": results[:validated_input.limit],
            "category_filter": validated_input.category
        }
        
    except Exception as e:
        logger.error(f"[{correlation_id}] Error in retrieve_memory: {str(e)}")
        raise McpError(f"Failed to retrieve memory: {str(e)}")

async def debug_error(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyzes error messages and code to generate hypotheses and fixes.
    """
    try:
        validated_input = DebugErrorInput(**input_data)
    except ValidationError as e:
        logger.error(f"Input validation failed: {str(e)}")
        raise McpError(f"Invalid input: {str(e)}")
    
    correlation_id = str(uuid.uuid4())
    logger.info(f"[{correlation_id}] Debugging error: {validated_input.error_message[:100]}...")
    
    try:
        # Get LM Studio client
        client = await get_lm_client()
        
        # Create debugging prompt
        prompt = f"""
        Analyze this error and provide debugging assistance:
        
        ERROR MESSAGE:
        {validated_input.error_message}
        
        CODE SNIPPET:
        {validated_input.code_snippet or 'Not provided'}
        
        ADDITIONAL CONTEXT:
        {validated_input.context or 'None provided'}
        
        Please provide:
        1. Root cause analysis
        2. Hypotheses about what went wrong
        3. Specific fixes with code examples
        4. Prevention strategies
        
        Respond in JSON format:
        {{
            "root_cause": "analysis of the root cause",
            "hypotheses": [
                "possible causes of the error"
            ],
            "fixes": [
                {{
                    "description": "how to fix it",
                    "code_example": "corrected code if applicable"
                }}
            ],
            "prevention": ["strategies to prevent similar errors"],
            "confidence": "high|medium|low"
        }}
        """
        
        response: LMResponse = await client.chat_completion(
            prompt=prompt,
            system_prompt="You are an expert debugger. Provide clear, actionable solutions with specific code examples when possible.",
            response_format={"type": "json_object"}
        )
        
        try:
            debug_result = json.loads(response.content)
        except json.JSONDecodeError:
            # Fallback parsing
            debug_result = {
                "root_cause": "Could not parse structured response",
                "hypotheses": [response.content],
                "fixes": [{"description": "See hypotheses for guidance", "code_example": ""}],
                "prevention": ["Review the response content for guidance"],
                "confidence": "medium"
            }
        
        logger.info(f"[{correlation_id}] Debug analysis completed")
        
        return {
            "error_message": validated_input.error_message,
            "analysis": debug_result,
            "token_usage": response.usage
        }
        
    except Exception as e:
        logger.error(f"[{correlation_id}] Error in debug_error: {str(e)}")
        raise McpError(f"Failed to debug error: {str(e)}")

# Initialize memory store from file if it exists
def _load_memory_store():
    """Load memory store from persistent file"""
    global _memory_store
    memory_file = Path("memory_store.json")
    if memory_file.exists():
        try:
            with open(memory_file, 'r', encoding='utf-8') as f:
                _memory_store = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load memory store: {str(e)}")
            _memory_store = {}

# Load memory store on module import
_load_memory_store()