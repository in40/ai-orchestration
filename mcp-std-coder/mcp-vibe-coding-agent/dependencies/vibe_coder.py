import httpx
import os
import re
import json
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
from config import settings


class CodingTask(BaseModel):
    task_description: str = Field(..., description="What code should be generated?")
    language: Optional[str] = Field("python", description="Programming language")
    vibe_level: Optional[int] = Field(5, description="Creativity level 1-10")
    style_guide: Optional[str] = Field("", description="Additional style hints")


# =============================================================================
# Git Helper Functions for MCP Agent Results
# =============================================================================


def extract_code_from_llm_response(response: str, preferred_language: Optional[str] = None) -> str:
    """
    Extract code from LLM response.

    Tries to find code blocks in markdown format first, falls back to full response.
    Supports language-specific code blocks like ```html, ```javascript, ```python, etc.

    Args:
        response: The raw LLM response string
        preferred_language: Optional hint for which language block to prefer

    Returns:
        Extracted code string
    """
    if not response or not response.strip():
        return ""

    # Pattern 1: Match code blocks with language identifier: ```language\n...\n```
    # Pattern 2: Match code blocks without language: ```\n...\n```
    # Pattern 3: Match unclosed code blocks: ```language\n... (end of string)
    code_block_pattern = r'```(\w+)?\n(.*?)(?:```|$)'
    matches = re.findall(code_block_pattern, response, re.DOTALL)

    if matches:
        # matches is a list of tuples: [(language1, code1), (language2, code2), ...]

        # If preferred language is specified, try to find matching block
        if preferred_language:
            preferred_lower = preferred_language.lower()
            for lang, code in matches:
                if lang and lang.lower() == preferred_lower:
                    return _clean_extracted_code(code)

        # If no preferred language or no match, return first code block with language tag
        for lang, code in matches:
            if lang:  # Prefer blocks with language specification
                return _clean_extracted_code(code)

        # Fallback to first code block (even without language tag)
        return _clean_extracted_code(matches[0][1])

    # If no code blocks found, try to detect if response is mostly code
    # by checking for common code patterns
    if _looks_like_code(response):
        return _clean_extracted_code(response.strip())

    # If no code blocks found, return the full response
    return response.strip()


def _clean_extracted_code(code: str) -> str:
    """
    Clean extracted code by removing common natural language artifacts.

    Args:
        code: Raw extracted code string

    Returns:
        Cleaned code string
    """
    if not code:
        return ""

    lines = code.split('\n')
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()

        # Skip lines that are clearly natural language, not code
        # But be careful not to remove valid comments

        # Skip introductory/concluding phrases that sometimes slip into code blocks
        # Check both the raw line and line without comment markers
        line_for_check = stripped
        # Remove common comment prefixes for checking
        for comment_prefix in ['#', '//', '/*', '*', '--', ';']:
            if stripped.startswith(comment_prefix):
                line_for_check = stripped[len(comment_prefix):].strip()
                break

        skip_patterns = [
            r"^here\s+(is|are)\s+(the|your|a)",  # "Here is the code"
            r"^here's\s+(the|your|a)",  # "Here's the code"
            r"^i\s+hope\s+",  # "I hope this helps"
            r"^let\s+me\s+know",  # "Let me know if"
            r"^this\s+(code|function|script|program)\s+",  # "This code does..."
            r"^please\s+(let|note|see|check|feel)",  # "Please let me know"
            r"^note\s*:",  # "Note:"
            r"^important\s*:",  # "Important:"
            r"^enjoy\s+",  # "Enjoy coding"
            r"^you\s+can\s+",  # "You can modify..."
            r"^feel\s+free\s+",  # "Feel free to"
        ]

        should_skip = False
        for pattern in skip_patterns:
            if re.match(pattern, line_for_check, re.IGNORECASE):
                should_skip = True
                break

        if not should_skip:
            cleaned_lines.append(line)

    # Join lines back and strip
    result = '\n'.join(cleaned_lines).strip()

    # Remove trailing natural language paragraphs (common pattern: empty line + text)
    # Split by double newlines and take only the code part
    paragraphs = result.split('\n\n')
    if len(paragraphs) > 1:
        # Check if last paragraph is natural language (no code-like patterns)
        last_para = paragraphs[-1].strip()
        if last_para and not _looks_like_code(last_para):
            # Remove the last paragraph
            result = '\n\n'.join(paragraphs[:-1]).strip()

    return result


def _looks_like_code(text: str) -> bool:
    """
    Heuristic check if text looks like programming code.

    Args:
        text: Text to analyze

    Returns:
        True if text appears to be code, False otherwise
    """
    if not text:
        return False

    text_lower = text.lower()

    # Check for common code patterns
    code_indicators = [
        r'\bdef\s+\w+\s*\(',  # Python function
        r'\bfunction\s+\w*\s*\(',  # JavaScript function
        r'\bconst\s+\w+\s*=',  # JavaScript const
        r'\bvar\s+\w+\s*=',  # JavaScript var
        r'\blet\s+\w+\s*=',  # JavaScript let
        r'\bclass\s+\w+',  # Class definition
        r'\bimport\s+',  # Import statement
        r'\bfrom\s+.*\s+import',  # Python from import
        r'\bpublic\s+(static\s+)?(void|int|string|class)',  # Java/C#
        r'\bprivate\s+',  # Private member
        r'\breturn\b',  # Return statement
        r'\bif\s*\(.*\)\s*{',  # If statement
        r'\bfor\s*\(.*\)\s*{',  # For loop
        r'\bwhile\s*\(.*\)\s*{',  # While loop
        r'<!DOCTYPE\s+html',  # HTML doctype
        r'<html[>\s]',  # HTML tag
        r'<script[>\s]',  # Script tag
        r'<style[>\s]',  # Style tag
        r'\{\s*\}',  # Empty object/brace
        r'=>',  # Arrow function
        r'console\.log',  # Console.log
        r'print\s*\(',  # Print function
        r'__name__\s*==\s*["\']__main__["\']',  # Python main
    ]

    # Count how many code indicators are present
    matches = sum(1 for pattern in code_indicators if re.search(pattern, text, re.IGNORECASE))

    # Also check for natural language indicators
    natural_language_indicators = [
        r'\bi\s+am\b', r'\bi\s+have\b', r'\bi\s+will\b',
        r'\bthis is a\b', r'\bhere is the\b',
        r'\bplease note\b', r'\bi hope\b',
        r'\blet me know\b', r'\bfeel free\b',
    ]

    natural_matches = sum(1 for pattern in natural_language_indicators
                         if re.search(pattern, text, re.IGNORECASE))

    # It looks like code if:
    # - Has at least 2 code indicators, OR
    # - Has 1 code indicator and fewer natural language indicators
    return matches >= 2 or (matches >= 1 and matches > natural_matches)


def detect_language_from_response(response: str) -> str:
    """
    Detect programming language from LLM response by analyzing code blocks.

    Args:
        response: The raw LLM response string

    Returns:
        Detected language name (e.g., 'html', 'python', 'javascript')
    """
    # Pattern to match language identifiers in code blocks
    lang_pattern = r'```(\w+)\n'
    matches = re.findall(lang_pattern, response)
    
    if matches:
        # Return the first language found (most likely the primary one)
        return matches[0].lower()
    
    # Fallback: try to detect language from content
    response_lower = response.lower()
    
    # Check for HTML indicators
    if any(tag in response_lower for tag in ['<!doctype html', '<html', '<head>', '<body>', '<div', '<script']):
        return 'html'
    
    # Check for JavaScript indicators
    if any(kw in response_lower for kw in ['function(', 'const ', 'let ', 'var ', 'console.log', 'document.']):
        return 'javascript'
    
    # Check for Python indicators
    if any(kw in response_lower for kw in ['def ', 'import ', 'print(', 'class ', 'if __name__']):
        return 'python'
    
    # Check for CSS indicators
    if any(kw in response_lower for kw in ['{', '}', ':', ';']) and 'body {' in response_lower:
        return 'css'
    
    # Check for TypeScript indicators
    if any(kw in response_lower for kw in ['interface ', 'type ', ': string', ': number']):
        return 'typescript'
    
    # Check for Java indicators
    if any(kw in response_lower for kw in ['public class', 'public static void main', 'System.out']):
        return 'java'
    
    # Check for Go indicators
    if any(kw in response_lower for kw in ['func main()', 'package main', 'fmt.Println']):
        return 'go'
    
    # Check for Rust indicators
    if any(kw in response_lower for kw in ['fn main()', 'println!', 'let mut']):
        return 'rust'
    
    # Check for Ruby indicators
    if any(kw in response_lower for kw in ['def ', 'end', 'puts ']):
        return 'ruby'
    
    # Check for PHP indicators
    if '<?php' in response or '<?' in response:
        return 'php'
    
    # Default to python
    return 'python'


def _run_git_command(args: List[str], cwd: Path, env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
    """Run a git command with proper environment"""
    if env is None:
        env = os.environ.copy()
    
    cmd = ["git"] + args
    return subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True)


def _ensure_git_config(repo_path: Path, user_name: str = "mcp-agent", user_email: str = "mcp-agent@localhost"):
    """Ensure git user configuration exists"""
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = user_name
    env["GIT_AUTHOR_EMAIL"] = user_email
    env["GIT_COMMITTER_NAME"] = user_name
    env["GIT_COMMITTER_EMAIL"] = user_email
    
    # Check and set if not configured
    subprocess.run(
        ["git", "config", "user.name", user_name],
        cwd=str(repo_path),
        env=env,
        capture_output=True,
        check=False
    )
    subprocess.run(
        ["git", "config", "user.email", user_email],
        cwd=str(repo_path),
        env=env,
        capture_output=True,
        check=False
    )


def _get_or_clone_git_repo(repo_url: str, local_path: Path) -> Path:
    """
    Get or clone a git repository.
    
    Args:
        repo_url: SSH or HTTPS URL of the repository
        local_path: Local path where repo should be cloned
        
    Returns:
        Path to the local repository
    """
    local_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not (local_path / ".git").exists():
        # Clone the repository
        result = subprocess.run(
            ["git", "clone", repo_url, str(local_path)],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise Exception(f"Failed to clone repository: {result.stderr}")
        print(f"✅ Cloned repository {repo_url} to {local_path}")
    
    return local_path


def git_push_llm_response(
    task_id: str,
    llm_response: str,
    language: str = "python"
) -> Dict[str, Any]:
    """
    Push LLM response to Git repository and return structured result with Git URL.

    This function is used by the vibe_code_async tool to store generated code
    in a Git repository and return the Git URL for retrieval.

    Args:
        task_id: The async task ID for this code generation
        llm_response: The response from LLM (expected to be valid JSON)
        language: The programming language (default: python)

    Returns:
        Dict with structure:
        {
            "git_url": "https://.../tree/branch/results/task_id/result.py",
            "code_preview": "First 100 chars of code",
            "language": "python",
            "success": True,
            "file_path": "results/task_id/result.py",
            "json_file_path": "results/task_id/response.json"
        }
    """
    # Try to parse LLM response as JSON
    response_data = _parse_llm_json_response(llm_response)
    
    # Extract code from JSON response or fall back to old extraction
    if response_data and "code" in response_data:
        code = response_data["code"]
        # Use language from JSON response if available
        if "language" in response_data:
            language = response_data["language"]
    else:
        # Fallback: extract code using old method (markdown blocks)
        code = extract_code_from_llm_response(llm_response, preferred_language=language)
        # Detect language from response
        detected = detect_language_from_response(llm_response)
        if detected != "python":
            language = detected
    
    # Get repository URL from settings or environment
    repo_url = getattr(settings, 'mcp_git_repo_url', None)
    if not repo_url:
        repo_url = os.environ.get("MCP_GIT_REPO_URL", "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git")

    # Configure local clone path
    local_repo_path = Path(tempfile.gettempdir()) / "mcp-vibe-coding-git" / "repo"

    try:
        # Clone or get the repository
        _get_or_clone_git_repo(repo_url, local_repo_path)

        # Ensure git user configuration
        _ensure_git_config(local_repo_path)

        # Create result directory
        result_dir = local_repo_path / "results" / task_id
        result_dir.mkdir(parents=True, exist_ok=True)

        # Determine file extension based on language
        language_extensions = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "java": ".java",
            "go": ".go",
            "rust": ".rs",
            "ruby": ".rb",
            "php": ".php",
            "swift": ".swift",
            "kotlin": ".kt",
            "terraform": ".tf",
            "yaml": ".yaml",
            "yml": ".yaml",
            "json": ".json",
            "html": ".html",
            "css": ".css",
            "sql": ".sql",
        }
        extension = language_extensions.get(language.lower(), ".py")

        # Write code to file
        filename = f"result{extension}"
        filepath = result_dir / filename
        filepath.write_text(code)

        # Create comprehensive JSON response file
        json_response = {
            "task_id": task_id,
            "original_llm_response": llm_response,  # Store raw LLM response
            "parsed_data": response_data if response_data else None,
            "code": {
                "content": code,
                "language": language,
                "filename": filename
            },
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "source": "vibe_code_async",
                "run_instructions": response_data.get("run_instructions", "") if response_data else "",
                "notes": response_data.get("notes", "") if response_data else "",
                "vibe_check": response_data.get("vibe_check", "") if response_data else ""
            },
            "task_understanding": response_data.get("task_understanding", "") if response_data else ""
        }
        
        # Write JSON response file
        json_filepath = result_dir / "response.json"
        json_filepath.write_text(json.dumps(json_response, indent=2, ensure_ascii=False))

        # Set up git environment
        env = os.environ.copy()
        env["GIT_AUTHOR_NAME"] = "mcp-agent"
        env["GIT_AUTHOR_EMAIL"] = "mcp-agent@localhost"
        env["GIT_COMMITTER_NAME"] = "mcp-agent"
        env["GIT_COMMITTER_EMAIL"] = "mcp-agent@localhost"

        # Stage the files
        subprocess.run(
            ["git", "add", str(filepath.relative_to(local_repo_path)), 
             str(json_filepath.relative_to(local_repo_path))],
            cwd=str(local_repo_path),
            env=env,
            capture_output=True,
            check=False
        )

        # Commit the changes
        commit_msg = f"[vibe_code] Add result for task {task_id}: {filename} + response.json"
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=str(local_repo_path),
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0 and "nothing to commit" not in result.stderr.lower():
            print(f"⚠️  Git commit warning: {result.stderr}")

        # Get current branch
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(local_repo_path),
            capture_output=True,
            text=True
        )
        current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "main"

        # Push to remote - push to main branch explicitly
        result = subprocess.run(
            ["git", "push", "origin", "HEAD:main"],
            cwd=str(local_repo_path),
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"⚠️  Git push warning: {result.stderr}")

        # Use main as the branch for URL
        branch = current_branch if current_branch in ["main", "master"] else "main"

        git_url = f"{repo_url.rstrip('.git')}/tree/{branch}/results/{task_id}/{filename}"
        json_git_url = f"{repo_url.rstrip('.git')}/tree/{branch}/results/{task_id}/response.json"

        # Return structured result
        return {
            "success": True,
            "git_url": git_url,
            "json_git_url": json_git_url,
            "code_preview": code[:200] + "..." if len(code) > 200 else code,
            "language": language,
            "file_path": f"results/{task_id}/{filename}",
            "json_file_path": f"results/{task_id}/response.json",
            "full_file_path": str(filepath),
            "json_full_path": str(json_filepath)
        }

    except Exception as e:
        print(f"❌ Git push failed: {e}")
        import traceback
        traceback.print_exc()
        # Return error result with code included for fallback
        return {
            "success": False,
            "error": str(e),
            "code_preview": code[:200] + "..." if len(code) > 200 else code,
            "language": language,
            "fallback_code": code  # Include code for task result
        }


def _parse_llm_json_response(response: str) -> Optional[Dict[str, Any]]:
    """
    Parse LLM response as JSON.
    
    Tries multiple strategies:
    1. Direct JSON parse
    2. Extract JSON from markdown code blocks (```json ... ```)
    3. Extract JSON object from text
    
    Args:
        response: Raw LLM response string
        
    Returns:
        Parsed JSON dict or None if parsing fails
    """
    if not response:
        return None
    
    # Strategy 1: Try direct JSON parse
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Look for JSON in markdown code blocks (```json ... ```)
    json_block_pattern = r'```json\s*(.*?)\s*```'
    matches = re.findall(json_block_pattern, response, re.DOTALL)
    if matches:
        try:
            return json.loads(matches[0].strip())
        except json.JSONDecodeError as e:
            print(f"DEBUG: JSON block parse error: {e}")
            pass
    
    # Strategy 3: Look for any JSON object with required fields
    # This handles nested/malformed JSON better
    start = response.find('{')
    end = response.rfind('}') + 1
    if start >= 0 and end > start:
        # Try progressively larger chunks
        for i in range(end, start, -1):
            json_str = response[start:i]
            try:
                parsed = json.loads(json_str)
                # Check if it has expected fields
                if isinstance(parsed, dict) and ("code" in parsed or "task_understanding" in parsed):
                    return parsed
            except json.JSONDecodeError:
                continue
    
    # Strategy 4: Try to extract from ``` without language tag
    generic_block_pattern = r'```\s*(\{.*?\})\s*```'
    matches = re.findall(generic_block_pattern, response, re.DOTALL)
    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue
    
    return None


import requests

def call_llm_sync(prompt: str, vibe: int, server_handlers=None, max_retries: int = 5, retry_delay: int = 10) -> str:
    """
    Call LM Studio's OpenAI-compatible endpoint using synchronous requests.
    
    Includes retry logic for transient LLM server errors.
    
    Args:
        prompt: The prompt to send to the LLM
        vibe: Creativity level (1-10)
        server_handlers: Optional server handlers for system prompt
        max_retries: Maximum number of retry attempts (default: 3)
        retry_delay: Delay between retries in seconds (default: 5)
    
    Returns:
        LLM response content string
    
    Raises:
        Exception: If all retry attempts fail
    """
    # Get the system prompt from the server handlers if available, otherwise use default
    system_prompt = "You are a vibe coding assistant. Generate clean, working code with brief explanations."

    if server_handlers:
        # Look for the system prompt in the available prompts
        for p in server_handlers.prompts:
            if p.get("name") == "vibe_coding_system_prompt":
                # Use the prompt content if arguments are provided, otherwise use the content directly
                if "content" in p:
                    system_prompt = p["content"]
                break

    last_error = None

    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{settings.llm_base_url}/chat/completions",
                json={
                    "model": settings.llm_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": vibe / 10,  # 0.1 to 1.0
                    "max_tokens": 8192  # Increased for longer code outputs
                },
                timeout=300
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < max_retries - 1:
                print(f"⚠️ LLM call failed (attempt {attempt + 1}/{max_retries}): {e}")
                print(f"🔄 Retrying in {retry_delay} seconds...")
                import time
                time.sleep(retry_delay)
            else:
                print(f"❌ LLM call failed after {max_retries} attempts: {e}")
    
    # If we get here, all retries failed
    raise last_error


def create_vibe_code_prompt(arguments: dict) -> str:
    """Create the prompt for the LLM based on arguments."""
    task_desc = arguments.get("task_description", "")
    language = arguments.get("language", "python")
    vibe_level = arguments.get("vibe_level", 5)
    style_guide = arguments.get("style_guide", "")

    prompt = f"""You are a professional code generation assistant. Generate clean, working code in response to the task below.

## Task
Task: {task_desc}
Language: {language}
Vibe level (creativity): {vibe_level}/10
Style guide: {style_guide if style_guide else 'No specific style'}

## OUTPUT FORMAT - MUST RETURN VALID JSON

You MUST respond with a valid JSON object with the following structure:

```json
{{
    "task_understanding": "Brief 1-sentence summary of what you understood from the request",
    "code": "The complete, working code here. Do NOT use markdown code blocks inside this string. Just the raw code.",
    "language": "{language.lower()}",
    "filename": "result.{_get_extension_for_language(language)}",
    "run_instructions": "Brief instructions on how to run/use this code (1 sentence)",
    "notes": "Any additional notes, suggestions, or limitations (optional, can be empty string)",
    "vibe_check": "A fun comment showing creativity level {vibe_level}"
}}
```

## CRITICAL RULES

1. **Return ONLY valid JSON** - no text before or after the JSON
2. **Do NOT use markdown code blocks** (no ``` around your response)
3. **The "code" field must contain raw code** - not wrapped in any markdown
4. **Escape special characters** in the code field properly for JSON:
   - Use \\\" for double quotes inside strings
   - Use \\\\ for backslashes
   - Use \\n for newlines
5. **Ensure the code is complete and working** - include all necessary parts
6. **IMPORTANT: Ensure your complete JSON response is sent** - do not truncate the output
7. For longer code, ensure ALL code is included - the response must be complete

## EXAMPLE RESPONSE

{{
    "task_understanding": "Create a simple Python function to greet users",
    "code": "def greet(name):\\n    return f\"Hello, {{name}}!\"\\n\\nif __name__ == \"__main__\":\\n    print(greet(\"World\"))",
    "language": "python",
    "filename": "result.py",
    "run_instructions": "Run with: python result.py",
    "notes": "",
    "vibe_check": "Level 5 creativity - keeping it simple and clean!"
}}

Now generate the code for the requested task. Return ONLY the JSON object, nothing else."""

    return prompt


def _get_extension_for_language(language: str) -> str:
    """Get file extension for a programming language."""
    extensions = {
        "python": "py",
        "javascript": "js",
        "typescript": "ts",
        "java": "java",
        "go": "go",
        "rust": "rs",
        "ruby": "rb",
        "php": "php",
        "swift": "swift",
        "kotlin": "kt",
        "html": "html",
        "css": "css",
        "sql": "sql",
        "yaml": "yaml",
        "json": "json",
    }
    return extensions.get(language.lower(), "py")


import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading

# Global thread pool executor for async operations
executor = ThreadPoolExecutor(max_workers=10)

def register_vibe_coding_tool(server_handlers):
    """Register the vibe coding tools with the server handlers."""
    # Import the task manager (could be in-memory or PostgreSQL-based)
    from .postgres_task_manager import create_task_manager, TaskStatus

    # Create task manager based on server configuration
    # Check if PostgreSQL is configured for task storage (separate from registry)
    # Prioritize server_handlers postgres_config if available, otherwise use settings
    try:
        # First check if server_handlers has postgres_config
        server_postgres_config = getattr(server_handlers, 'postgres_config', {})
        print(f"DEBUG: server_handlers.postgres_config = {server_postgres_config}")
        if server_postgres_config and server_postgres_config.get('host'):
            # Use server's postgres configuration
            task_postgres_config = server_postgres_config
            use_postgres = True
            print(f"DEBUG: Using server postgres config: {task_postgres_config}")
        else:
            # Fall back to settings configuration
            from ..config import settings
            task_postgres_config = {
                "host": settings.postgres_host,
                "port": settings.postgres_port,
                "database": settings.postgres_db,
                "user": settings.postgres_user,
                "password": settings.postgres_password
            }
            # Use PostgreSQL for tasks if it's configured and available
            use_postgres = bool(settings.postgres_password and settings.postgres_password.strip())
    except Exception as e:
        # If config is not available, use in-memory storage
        print(f"Error configuring PostgreSQL task storage: {e}")
        task_postgres_config = {}
        use_postgres = False

    task_manager = create_task_manager(use_postgres=use_postgres, **task_postgres_config)

    # Define the synchronous vibe_code tool
    vibe_code_tool = {
        "name": "vibe_code",
        "description": "Accept a natural language coding task, invoke the local LLM (LM Studio), and return the generated code with any explanation. This tool implements the 'vibe coding' methodology.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_description": {"type": "string", "description": "What code should be generated?"},
                "language": {"type": "string", "description": "Programming language", "default": "python"},
                "vibe_level": {"type": "integer", "description": "Creativity level 1-10", "default": 5},
                "style_guide": {"type": "string", "description": "Additional style hints", "default": ""}
            },
            "required": ["task_description"]
        }
    }

    # Define the asynchronous vibe_code tool
    vibe_code_async_tool = {
        "name": "vibe_code_async",
        "description": "Submit a natural language coding task to be processed asynchronously. Returns a task ID for tracking progress. Use tasks/get to check status and tasks/result to retrieve the generated code.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_description": {"type": "string", "description": "What code should be generated?"},
                "language": {"type": "string", "description": "Programming language", "default": "python"},
                "vibe_level": {"type": "integer", "description": "Creativity level 1-10", "default": 5},
                "style_guide": {"type": "string", "description": "Additional style hints", "default": ""}
            },
            "required": ["task_description"]
        }
    }

    # Define the tasks/list tool
    tasks_list_tool = {
        "name": "tasks/list",
        "description": "List all async tasks with optional status filtering",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Filter tasks by status (submitted, working, completed, failed, cancelled)"},
                "limit": {"type": "integer", "description": "Maximum number of tasks to return", "default": 100}
            }
        }
    }

    # Define the tasks/get tool
    tasks_get_tool = {
        "name": "tasks/get",
        "description": "Get the status of a specific async task",
        "inputSchema": {
            "type": "object",
            "properties": {
                "taskId": {"type": "string", "description": "The ID of the task to get status for"}
            },
            "required": ["taskId"]
        }
    }

    # Define the tasks/result tool
    tasks_result_tool = {
        "name": "tasks/result",
        "description": "Retrieve the result of a completed async task",
        "inputSchema": {
            "type": "object",
            "properties": {
                "taskId": {"type": "string", "description": "The ID of the task to get result for"}
            },
            "required": ["taskId"]
        }
    }

    # Define the tasks/cancel tool
    tasks_cancel_tool = {
        "name": "tasks/cancel",
        "description": "Cancel a running async task",
        "inputSchema": {
            "type": "object",
            "properties": {
                "taskId": {"type": "string", "description": "The ID of the task to cancel"}
            },
            "required": ["taskId"]
        }
    }

    # Add vibe coding tools to existing tools (not replacing) to avoid overwriting other tools
    existing_vibe_tools = [t["name"] for t in server_handlers.tools if t.get("name").startswith(("vibe_code", "tasks/"))]

    if not existing_vibe_tools:
        server_handlers.tools.extend([
            vibe_code_tool,
            vibe_code_async_tool,
            tasks_list_tool,
            tasks_get_tool,
            tasks_result_tool,
            tasks_cancel_tool
        ])

    # Notify that tools have changed
    if hasattr(server_handlers, 'notification_manager') and server_handlers.notification_manager:
        server_handlers.notification_manager.mark_tools_changed()

    # Add the tool execution logic to the _execute_tool method by extending it
    original_execute_tool = server_handlers._execute_tool

    def enhanced_execute_tool(tool, arguments):
        if tool["name"] == "vibe_code":
            # Construct prompt with style and vibe
            prompt = create_vibe_code_prompt(arguments)

            try:
                # Call the synchronous LLM function
                llm_response = call_llm_sync(prompt, arguments.get("vibe_level", 5), server_handlers)
                return {"result": llm_response}
            except Exception as e:
                return {"error": f"Failed to call LLM: {str(e)}"}

        elif tool["name"] == "vibe_code_async":
            # Create an async task
            try:
                task_id = task_manager.create_task(arguments)

                # Submit for background processing
                def llm_call_wrapper(input_args):
                    prompt = create_vibe_code_prompt(input_args)
                    llm_response = call_llm_sync(prompt, input_args.get("vibe_level", 5), server_handlers)
                    print(f"DEBUG: LLM response received, calling git_push_llm_response for task {task_id}")
                    # Push to Git and return Git URL
                    result = git_push_llm_response(task_id, llm_response, input_args.get("language", "python"))
                    print(f"DEBUG: git_push_llm_response returned: {result.get('git_url', 'NO GIT URL')}")
                    return result

                task_manager.submit_for_processing(task_id, llm_call_wrapper)

                return {"taskId": task_id, "status": "submitted"}
            except Exception as e:
                return {"error": f"Failed to create async task: {str(e)}"}

        elif tool["name"] == "tasks/list":
            # List tasks
            try:
                status_filter = arguments.get("status")
                limit = arguments.get("limit", 100)

                tasks = task_manager.list_tasks(status_filter=status_filter, limit=limit)
                result_tasks = []

                for task in tasks:
                    result_tasks.append({
                        "taskId": task.taskId,
                        "status": task.status.value,
                        "createdAt": task.createdAt,
                        "updatedAt": task.updatedAt,
                        "progress": task.progress,
                        "input": task.input
                    })

                return {"tasks": result_tasks}
            except Exception as e:
                return {"error": f"Failed to list tasks: {str(e)}"}

        elif tool["name"] == "tasks/get":
            # Get specific task status
            try:
                task_id = arguments.get("taskId")
                task = task_manager.get_task(task_id)

                if not task:
                    return {"error": "Task not found"}

                return {
                    "taskId": task.taskId,
                    "status": task.status.value,
                    "createdAt": task.createdAt,
                    "updatedAt": task.updatedAt,
                    "progress": task.progress,
                    "input": task.input
                }
            except Exception as e:
                return {"error": f"Failed to get task: {str(e)}"}

        elif tool["name"] == "tasks/result":
            # Get task result
            try:
                task_id = arguments.get("taskId")
                task = task_manager.get_task(task_id)

                if not task:
                    return {"error": "Task not found"}

                if task.status != TaskStatus.COMPLETED:
                    return {"error": f"Task is not completed. Current status: {task.status.value}"}

                # Return the result directly (not wrapped) so IT Lead can extract git_url
                return task.result
            except Exception as e:
                return {"error": f"Failed to get task result: {str(e)}"}

        elif tool["name"] == "tasks/cancel":
            # Cancel a task
            try:
                task_id = arguments.get("taskId")
                success = task_manager.cancel_task(task_id)

                if success:
                    return {"status": "cancelled", "taskId": task_id}
                else:
                    return {"error": "Task not found or could not be cancelled"}
            except Exception as e:
                return {"error": f"Failed to cancel task: {str(e)}"}

        else:
            # Call the original method for other tools
            return original_execute_tool(tool, arguments)

    server_handlers._execute_tool = enhanced_execute_tool
