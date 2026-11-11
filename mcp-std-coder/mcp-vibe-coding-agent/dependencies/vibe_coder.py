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


def _normalize_language(language: str) -> str:
    """Normalize LLM-reported language: first token, lowercased, common aliases."""
    lang = (language or "").lower().split(",")[0].strip().split()[0] if (language or "").strip() else ""
    aliases = {"html5": "html", "js": "javascript", "py": "python", "ts": "typescript", "golang": "go"}
    return aliases.get(lang, lang)


LANGUAGE_EXTENSIONS = {
    "python": ".py", "javascript": ".js", "typescript": ".ts", "java": ".java",
    "go": ".go", "rust": ".rs", "ruby": ".rb", "php": ".php", "swift": ".swift",
    "kotlin": ".kt", "terraform": ".tf", "yaml": ".yaml", "json": ".json",
    "html": ".html", "css": ".css", "sql": ".sql", "yml": ".yaml",
}


def _resolve_extension(language: str, code: str = "") -> str:
    lang = _normalize_language(language)
    if code.lstrip().lower().startswith(("<!doctype html", "<html")):
        lang = "html"
    if lang in LANGUAGE_EXTENSIONS:
        return LANGUAGE_EXTENSIONS[lang]
    sniffed = _normalize_language(detect_language_from_response(code))
    return LANGUAGE_EXTENSIONS.get(sniffed, ".py")


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

        files_written = []
        if response_data and isinstance(response_data.get("files"), list) and response_data["files"]:
            for f in response_data["files"]:
                rel = os.path.normpath(str(f.get("path", "")))
                if not rel or rel.startswith("..") or os.path.isabs(rel):
                    continue
                dest = result_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(str(f.get("content", "")))
                files_written.append(rel)
            filename = files_written[0] if files_written else "result.txt"
            filepath = result_dir / filename
            code = str(response_data["files"][0].get("content", ""))
        else:
            filename = f"result{_resolve_extension(language, code)}"
            filepath = result_dir / filename
            filepath.write_text(code)
            files_written = [filename]

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

        # Stage the files (whole per-task dir: covers single file, multi-file tree, response.json)
        subprocess.run(
            ["git", "add", str(result_dir.relative_to(local_repo_path))],
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


def _opencode_fix(work_dir, session_id, path, error_text, timeout=None):
    """Run an opencode fixer session in the task dir; agent edits files in place.

    Returns (ok, detail). ok=True only if the target file actually changed and
    (for .py) parses. Any failure -> caller falls back to the legacy path.
    """
    import shutil
    binary = shutil.which("opencode") or "/root/.opencode/bin/opencode"
    if not os.path.exists(binary):
        return False, "opencode binary not found"
    fp = work_dir / path
    if not fp.exists():
        return False, f"{path} missing"
    try:
        before = fp.read_bytes()
    except Exception as e:
        return False, str(e)
    py_hint = ".qa_venv/bin/python" if (work_dir / ".qa_venv").exists() else "python3"
    prompt = (f"Target file: {path}\nUse interpreter: {py_hint}\n\n"
              f"Reported error:\n{error_text}\n\nFix it now.")
    cmd = [binary, "run", "--agent", "fixer",
           "--model", "hallogen/qwen3.8-next",
           "--session", f"ses-fix-{session_id}",
           "--auto", "--title", f"fix-{session_id}", prompt]
    try:
        env = os.environ.copy()
        env["PWD"] = str(work_dir)  # opencode CLI resolves project from $PWD, not getcwd
        p = subprocess.run(cmd, cwd=str(work_dir), capture_output=True, text=True,
                           timeout=timeout or int(os.environ.get("OPENCODE_FIX_TIMEOUT", "900")),
                           env=env)
    except subprocess.TimeoutExpired:
        return False, f"opencode fix timeout"
    except Exception as e:
        return False, f"opencode spawn failed: {e}"
    if p.returncode != 0:
        return False, f"opencode rc={p.returncode}: {(p.stderr or p.stdout or '')[-300:]}"
    try:
        if fp.read_bytes() == before:
            return False, "opencode made no change to " + path
    except Exception as e:
        return False, str(e)
    if path.endswith(".py"):
        import ast as _ast
        try:
            _ast.parse(fp.read_text(errors="ignore"))
        except SyntaxError as e:
            fp.write_bytes(before)  # restore
            return False, f"opencode produced invalid python: line {e.lineno}: {e.msg}"
    return True, "fixed via opencode session " + str(session_id)


def _derive_requirements(task_id: str) -> str:
    """Deterministically build requirements.txt from sibling .py imports in the repo."""
    import ast as _ast
    import sys as _sys
    repo_url = getattr(settings, 'mcp_git_repo_url', None) or os.environ.get(
        "MCP_GIT_REPO_URL", "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git")
    local = Path(tempfile.gettempdir()) / "mcp-vibe-coding-git" / "repo"
    _get_or_clone_git_repo(repo_url, local)
    root = local / "results" / task_id
    aliases = {"yaml": "pyyaml", "PIL": "pillow", "sklearn": "scikit-learn",
               "bs4": "beautifulsoup4", "cv2": "opencv-python", "fitz": "pymupdf",
               "dateutil": "python-dateutil", "dotenv": "python-dotenv", "jwt": "PyJWT"}
    stdlib = getattr(_sys, "stdlib_module_names", set())
    pkgs = set()
    for py in root.rglob("*.py") if root.is_dir() else []:
        try:
            tree = _ast.parse(py.read_text(errors="ignore"))
        except SyntaxError:
            continue
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, _ast.ImportFrom) and node.module and node.level == 0:
                mods = [node.module.split(".")[0]]
            else:
                continue
            for m in mods:
                if m and m not in stdlib and m != task_id.replace("-", "_"):
                    pkgs.add(aliases.get(m, m))
    return ("\n".join(sorted(pkgs)) + "\n") if pkgs else "# dependencies (stdlib only)\n"


def _looks_like_pkg_list(spec: str) -> bool:
    """True if spec is plausibly a bare comma/space-separated package list."""
    toks = [t for t in re.split(r"[,\s]+", (spec or "").strip()) if t]
    return bool(toks) and len(toks) <= 12 and all(
        re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,40}", t) for t in toks)


def _strip_code_fences(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        nl = t.find("\n")
        if nl != -1:
            t = t[nl + 1:]
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
        return t.strip("\n")
    return t


def git_push_single_file(task_id: str, rel_path: str, content: str) -> Dict[str, Any]:
    """Push one raw file into results/<task_id>/<rel_path> (fan-out flow: one LLM
    call per file keeps every output far below the engine output cap)."""
    rel = os.path.normpath(str(rel_path))
    if not rel or rel.startswith("..") or os.path.isabs(rel):
        return {"success": False, "error": f"invalid path: {rel_path}"}
    repo_url = getattr(settings, 'mcp_git_repo_url', None) or \
        os.environ.get("MCP_GIT_REPO_URL", "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git")
    local_repo_path = Path(tempfile.gettempdir()) / "mcp-vibe-coding-git" / "repo"
    try:
        _get_or_clone_git_repo(repo_url, local_repo_path)
        _ensure_git_config(local_repo_path)
        dest = local_repo_path / "results" / task_id / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
        env = os.environ.copy()
        env["GIT_AUTHOR_NAME"] = env["GIT_COMMITTER_NAME"] = "mcp-agent"
        env["GIT_AUTHOR_EMAIL"] = env["GIT_COMMITTER_EMAIL"] = "mcp-agent@localhost"
        subprocess.run(["git", "add", f"results/{task_id}"], cwd=str(local_repo_path),
                       env=env, capture_output=True, check=False)
        subprocess.run(["git", "commit", "-m", f"[generate_file] {task_id}: {rel}"],
                       cwd=str(local_repo_path), env=env, capture_output=True, check=False)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=str(local_repo_path),
                       env=env, capture_output=True, check=False)
        push = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=str(local_repo_path),
                              env=env, capture_output=True, text=True, check=False)
        if push.returncode != 0:
            print(f"⚠️ generate_file push warning: {push.stderr}")
        return {"success": True,
                "git_url": f"{repo_url.rstrip('.git')}/tree/main/results/{task_id}/{rel}",
                "file_path": f"results/{task_id}/{rel}",
                "bytes": len(content)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def validate_llm_artifact(llm_response: str) -> None:
    """Raise ValueError if the response is a truncated envelope or invalid code."""
    if not llm_response or len(llm_response.strip()) < 50:
        raise ValueError("invalid_artifact: empty or trivial response")
    response_data = _parse_llm_json_response(llm_response)
    if response_data and "code" in response_data:
        code = response_data["code"]
        lang = str(response_data.get("language", "")).lower()
    elif response_data and isinstance(response_data.get("files"), list) and response_data["files"]:
        import ast as _ast
        errors = []
        for f in response_data["files"]:
            c = str(f.get("content", ""))
            p = str(f.get("path", ""))
            if p.endswith(".py"):
                try:
                    _ast.parse(c)
                except SyntaxError as e:
                    errors.append(f"{p} line {e.lineno}: {e.msg}")
            elif p.endswith(".html") and "</html>" not in c.lower():
                errors.append(f"{p}: missing closing tag")
        if errors:
            raise ValueError("invalid_artifact: " + "; ".join(errors))
        return
    elif llm_response.lstrip().startswith("{"):
        raise ValueError("invalid_artifact: JSON envelope failed to parse (truncated?)")
    else:
        code = llm_response
        lang = ""
    if not code or len(code.strip()) < 100:
        raise ValueError("invalid_artifact: extracted code too short")
    stripped = code.lstrip().lower()
    if stripped.startswith(("<!doctype html", "<html")):
        if "</html>" not in stripped:
            raise ValueError("invalid_artifact: HTML missing closing tag (truncated)")
    elif "javascript" not in lang and "js" not in lang.split(",")[0]:
        import ast
        try:
            ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"invalid_artifact: python syntax error line {e.lineno}: {e.msg}")


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

def call_llm_sync(prompt: str, vibe: int, server_handlers=None, max_retries: int = 1, retry_delay: int = 10, timeout: int = 3600, max_tokens: int = 65536, reasoning_effort: Optional[str] = None, allow_continuations: bool = True, return_partial_on_cap: bool = False) -> str:
    """
    Call LM Studio's OpenAI-compatible endpoint using synchronous requests.

    Includes retry logic for transient LLM server errors.

    Args:
        prompt: The prompt to send to the LLM
        vibe: Creativity level (1-10)
        server_handlers: Optional server handlers for system prompt
        max_retries: Maximum number of retry attempts (default: 1 - no retry, let LLM finish)
        retry_delay: Delay between retries in seconds (default: 10)
        timeout: Request timeout in seconds per LLM call (default: 1800)

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
    max_continuations = 3 if allow_continuations else 0
    prev_piece = ""

    for attempt in range(max_retries):
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            full_content = ""
            for cont in range(max_continuations + 1):
                payload = {
                    "model": settings.llm_model,
                    "messages": messages,
                    "temperature": vibe / 10,  # 0.1 to 1.0
                    "max_tokens": max_tokens
                }
                if reasoning_effort:
                    payload["reasoning_effort"] = reasoning_effort
                response = requests.post(
                    f"{settings.llm_base_url}/chat/completions",
                    json=payload,
                    timeout=timeout
                )
                response.raise_for_status()
                choice = response.json()["choices"][0]
                piece = choice["message"].get("content") or ""
                for k in range(min(100, len(full_content), len(piece)), 0, -1):
                    if full_content[-k:] == piece[:k]:
                        piece = piece[k:]
                        break
                full_content += piece
                if choice.get("finish_reason") != "length":
                    return full_content
                if cont == max_continuations:
                    if return_partial_on_cap:
                        return full_content
                    raise RuntimeError(
                        f"truncated_output: LLM hit token cap after {max_continuations} continuations "
                        f"({len(full_content)} chars)")
                if piece[:200] and piece[:200] == prev_piece[:200]:
                    raise RuntimeError(
                        f"truncated_output: repetitive generation loop detected ({len(full_content)} chars)")
                prev_piece = piece
                print(f"⚠️ LLM output truncated at token cap (continuation {cont + 1}/{max_continuations})", flush=True)
                messages.append({"role": "assistant", "content": piece})
                tail = piece[-200:]
                messages.append({"role": "user", "content":
                    "Your output was cut off. The LAST characters you produced were exactly:\n"
                    f"...{tail}\n"
                    "Continue from that exact point: output ONLY the remaining text that follows "
                    "those characters. Do NOT repeat anything already written. Do NOT restart "
                    "from the beginning. No preamble."})
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

MULTI-FILE DELIVERABLES: if the task requires more than one file (e.g. a project
template, library with docs, app with config), replace "code"/"filename" with:
"files": [{{"path": "relative/path.ext", "content": "file contents"}}, ...]
Paths must be relative (no leading /, no ..). Include a README.md with run
instructions. The first file is treated as the primary artifact.

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
8. **🚨 CRITICAL: Web servers MUST bind to 0.0.0.0 for Docker deployment 🚨**
   - **Flask**: `app.run(host='0.0.0.0', port=PORT, debug=True)` ❌ NEVER use `app.run()` alone
   - **FastAPI/uvicorn**: `uvicorn.run(app, host='0.0.0.0', port=PORT)`
   - **http.server**: `HTTPServer(('0.0.0.0', PORT), Handler)`
   - **socketserver**: `TCPServer(('0.0.0.0', PORT), Handler)` or `TCPServer(('', PORT), Handler)`
   - **Node.js/Express**: `app.listen(PORT, '0.0.0.0')`
   - **NEVER bind to**: `127.0.0.1`, `localhost`, or `127.0.0.1` - these will FAIL in Docker!
   - **Port selection**: Use `PORT = int(os.environ.get("PORT", 5000))` or default to 5000
9. **Include main block** for Python scripts:
   - `if __name__ == "__main__":` with server startup code
   - Ensure the server actually starts and runs (e.g., `app.run()` or `httpd.serve_forever()`)

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
            # NOTE: import under an alias — a bare `settings` here would make it
            # local to register_vibe_coding_tool and shadow the module-level
            # import inside enhanced_execute_tool (NameError in patch_file).
            from ..config import settings as _pg_settings
            task_postgres_config = {
                "host": _pg_settings.postgres_host,
                "port": _pg_settings.postgres_port,
                "database": _pg_settings.postgres_db,
                "user": _pg_settings.postgres_user,
                "password": _pg_settings.postgres_password
            }
            # Use PostgreSQL for tasks if it's configured and available
            use_postgres = bool(_pg_settings.postgres_password and _pg_settings.postgres_password.strip())
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

    # Define the generate_file tool (fan-out flow: one file per LLM call)
    generate_file_tool = {
        "name": "generate_file",
        "description": "Generate exactly ONE file for a multi-file project and push it to "
                       "results/<task_id>/<path>. Output stays small by design (no envelope).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Parent task id (shared by all files of one deliverable)"},
                "path": {"type": "string", "description": "Relative file path, e.g. server.py or docs/README.md"},
                "spec": {"type": "string", "description": "What this file must contain/do"},
                "manifest": {"type": "string", "description": "Manifest of sibling files for consistency"},
                "project_description": {"type": "string", "description": "Overall project goal"},
            },
            "required": ["task_id", "path", "spec"]
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
    if not any(t["name"] == "generate_file" for t in server_handlers.tools):
        server_handlers.tools.append(generate_file_tool)
    if not any(t["name"] == "patch_file" for t in server_handlers.tools):
        server_handlers.tools.append({
            "name": "patch_file",
            "description": "Surgically fix an existing result file given a reported error. "
                           "Keeps all existing exports; changes only what the error requires.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "path": {"type": "string", "description": "Path relative to results/<task_id>/"},
                    "error": {"type": "string", "description": "Error text / traceback to fix"},
                },
                "required": ["task_id", "path", "error"],
            },
        })

    # Notify that tools have changed
    if hasattr(server_handlers, 'notification_manager') and server_handlers.notification_manager:
        server_handlers.notification_manager.mark_tools_changed()

    # Add the tool execution logic to the _execute_tool method by extending it
    original_execute_tool = server_handlers._execute_tool

    def enhanced_execute_tool(tool, arguments):
        if tool["name"] == "generate_file":
            path = arguments.get("path", "")
            base = path.rsplit("/", 1)[-1]
            spec_txt = str(arguments.get("spec", ""))
            # S3: boilerplate files need no LLM round-trip
            if base == "requirements.txt":
                try:
                    content = _derive_requirements(arguments.get("task_id", "unassigned"))
                except Exception:
                    content = "# dependencies\n"
                return git_push_single_file(arguments.get("task_id", "unassigned"), path, content)
            if base == ".env.example":
                return git_push_single_file(arguments.get("task_id", "unassigned"), path,
                                            "# Environment configuration\nPORT=5000\n")
            try:
                content = call_llm_sync(
                f"""Generate exactly ONE file for a software project. Output ONLY the raw file content — no markdown fences, no commentary, no JSON wrapper.

File path: {path}
File spec: {arguments.get('spec', '')}

Sibling files generated by teammates (keep imports and paths consistent, do NOT create them):
{arguments.get('manifest', 'none')}

Rules:
- Define EXACTLY the exports your spec promises; import from siblings only what their spec says they export.
- Prefer lazy imports inside functions for sibling modules, so importing this file never fails.
- If this file starts a network server, it MUST bind 0.0.0.0 (not 127.0.0.1) and read the port from env PORT (default 5000).
- Use ONLY the Python stdlib or packages explicitly listed in this project's requirements. NEVER mimic third-party SDK APIs on your own classes (e.g. do not add SDK-style decorators/methods to your own Server object) - implement exactly what the sibling specs say.

Overall project goal:
{arguments.get('project_description', '')}""",
                arguments.get("vibe_level", 3), server_handlers,
                    max_tokens=16384,
                    reasoning_effort="low",
                    allow_continuations=base.endswith((".py", ".js", ".ts", ".html", ".htm", ".css")),
                    return_partial_on_cap=not base.endswith((".py", ".js", ".ts", ".html", ".htm", ".css")))
                content = _strip_code_fences(content)
                if not content.strip():
                    return {"error": "generate_file produced empty content"}
                if path.endswith(".py"):
                    import ast as _ast
                    try:
                        _ast.parse(content)
                    except SyntaxError as e:
                        return {"error": f"generated {path} invalid python: line {e.lineno}: {e.msg}"}
                return git_push_single_file(arguments.get("task_id", "unassigned"), path, content)
            except Exception as e:
                if base in ("requirements.txt", ".env.example"):
                    fb = ("# dependencies\n" if base == "requirements.txt"
                          else "# Environment configuration\nPORT=5000\n")
                    return git_push_single_file(arguments.get("task_id", "unassigned"), path, fb)
                return {"error": f"generate_file {path} failed: {type(e).__name__}: {e}"}

        if tool["name"] == "patch_file":
            path = arguments.get("path", "")
            tid = arguments.get("task_id", "unassigned")
            try:
                repo_url = getattr(settings, 'mcp_git_repo_url', None) or os.environ.get(
                    "MCP_GIT_REPO_URL", "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git")
                local = Path(tempfile.gettempdir()) / "mcp-vibe-coding-git" / "repo"
                _get_or_clone_git_repo(repo_url, local)
                fp = local / "results" / tid / path
                if not fp.exists():
                    return {"error": f"patch_file: {path} not found in results/{tid}"}
                original = fp.read_text()
                oc_via = ""
                if os.environ.get("OPENCODE_PATCH", "1") != "0":
                    ok, detail = _opencode_fix(local / "results" / tid, tid, path,
                                               str(arguments.get("error", ""))[-2000:])
                    if ok:
                        oc_via = detail
                    else:
                        print(f"⚠️ patch_file opencode fell back to single-shot: {detail}", flush=True)
                if not oc_via:
                    fixed = _strip_code_fences(call_llm_sync(
                        "Fix this file. Keep every existing export and behavior; change only what "
                        "is needed to resolve the reported error. Output ONLY the complete fixed "
                        "file content, no fences or commentary.\n\nFile path: " + path +
                        "\nReported error:\n" + str(arguments.get("error", ""))[-2000:] +
                        "\n\nCurrent file:\n" + original,
                        2, server_handlers, max_tokens=16384, reasoning_effort="low"))
                    if not fixed.strip():
                        return {"error": "patch_file produced empty output"}
                    if path.endswith(".py"):
                        import ast as _ast
                        try:
                            _ast.parse(fixed)
                        except SyntaxError as e:
                            return {"error": f"patched {path} invalid: line {e.lineno}: {e.msg}"}
                    fp.write_text(fixed)
                _ensure_git_config(local)
                env = os.environ.copy()
                env["GIT_AUTHOR_NAME"] = env["GIT_COMMITTER_NAME"] = "mcp-agent"
                env["GIT_AUTHOR_EMAIL"] = env["GIT_COMMITTER_EMAIL"] = "mcp-agent@localhost"
                subprocess.run(["git", "add", f"results/{tid}"], cwd=str(local), env=env, capture_output=True)
                subprocess.run(["git", "commit", "-m", f"[patch_file] {tid}: {path}"],
                               cwd=str(local), env=env, capture_output=True)
                subprocess.run(["git", "pull", "--rebase", "origin", "main"],
                               cwd=str(local), env=env, capture_output=True)
                push = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=str(local),
                                      env=env, capture_output=True, text=True)
                if push.returncode != 0:
                    return {"error": f"patch_file push failed: {(push.stderr or '')[-200:]}"}
                return {"success": True, "patched": True,
                        "file_path": f"results/{tid}/{path}", "via": oc_via or "single-shot"}
            except Exception as e:
                return {"error": f"patch_file failed: {type(e).__name__}: {e}"}

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
                    try:
                        prompt = create_vibe_code_prompt(input_args)
                        print(f"DEBUG: Calling LLM for async task {task_id}")
                        llm_response = call_llm_sync(prompt, input_args.get("vibe_level", 5), server_handlers)
                        validate_llm_artifact(llm_response)
                        print(f"DEBUG: LLM response received for task {task_id}, calling git_push_llm_response")
                        # Push to Git and return Git URL
                        result = git_push_llm_response(task_id, llm_response, input_args.get("language", "python"))
                        print(f"DEBUG: git_push_llm_response returned: {result.get('git_url', 'NO GIT URL')}")
                        return result
                    except Exception as e:
                        print(f"❌ ERROR in llm_call_wrapper for task {task_id}: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        raise  # Re-raise so task_manager can capture the error

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
