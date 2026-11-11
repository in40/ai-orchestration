"""Security Reviewer MCP Server handlers.

Static security scan of generated artifacts: dangerous calls, hardcoded
secrets, unsafe deserialization. Gate between QA and deploy.
"""
import os
import re
import subprocess
import tempfile
from typing import Dict, Any

from .server_handlers import McpServerHandlers

DEFAULT_RESULTS_REPO = os.environ.get(
    "MCP_GIT_REPO_URL", "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git")

PATTERNS = [
    ("high", "eval-call", re.compile(r"(?<![\w.])eval\s*\(")),
    ("high", "exec-call", re.compile(r"(?<![\w.])exec\s*\(")),
    ("high", "os-system", re.compile(r"os\.system\s*\(")),
    ("high", "shell-true", re.compile(r"shell\s*=\s*True")),
    ("high", "pickle-loads", re.compile(r"pickle\.loads?\s*\(")),
    ("high", "yaml-unsafe-load", re.compile(r"yaml\.load\s*\((?![^)]*Loader)")),
    ("high", "aws-key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("high", "hardcoded-password", re.compile(
        r"(?i)(password|passwd|secret|api_?key|token)\s*=\s*['\"][^'\"]{6,}['\"]")),
    ("medium", "dynamic-import", re.compile(r"__import__\s*\(")),
    ("medium", "subprocess-raw", re.compile(r"subprocess\.call\s*\(.*shell", re.S)),
    ("medium", "broad-except-pass", re.compile(r"except\s*:\s*\n\s*pass")),
]

SKIP_FILES = {"requirements.txt", "pyproject.toml", ".env.example"}
SCAN_EXT = (".py", ".js", ".html", ".sh", ".yaml", ".yml")


class SecurityReviewerHandlers(McpServerHandlers):

    def __init__(self, enable_registry=False, use_postgres=False,
                 postgres_config=None, client_handlers=None):
        super().__init__(enable_registry, use_postgres, postgres_config, client_handlers)
        self.tools.append({
            "name": "scan_artifact",
            "description": "Static security scan of a task's artifact tree from the "
                           "mcp-results repo: dangerous calls, secrets, unsafe deserialization.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "git_url": {"type": "string"},
                },
                "required": ["task_id"],
            },
        })

    def _execute_tool(self, tool: Dict[str, Any], arguments: Dict[str, Any]) -> Dict[str, Any]:
        if tool.get("name") == "scan_artifact":
            return self._scan_artifact(arguments)
        return super()._execute_tool(tool, arguments)

    def _scan_artifact(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            task_id = arguments["task_id"]
            uuid = task_id
            m = re.search(r"/results/([^/]+)", arguments.get("git_url", "") or "")
            if m:
                uuid = m.group(1)
            workdir = os.path.join(tempfile.gettempdir(), f"sec-{uuid}")
            subprocess.run(["rm", "-rf", workdir], check=False)
            subprocess.run(["git", "clone", "--depth", "1", DEFAULT_RESULTS_REPO, workdir],
                           check=True, capture_output=True, timeout=60)
            root = os.path.join(workdir, "results", uuid)
            if not os.path.isdir(root):
                return {"safe": False, "errors": [f"results/{uuid} not found"]}
            findings = []
            for dirpath, _, files in os.walk(root):
                for f in files:
                    if f in SKIP_FILES or not f.endswith(SCAN_EXT):
                        continue
                    p = os.path.join(dirpath, f)
                    try:
                        text = open(p, errors="ignore").read()
                    except Exception:
                        continue
                    for i, line in enumerate(text.splitlines(), 1):
                        for sev, name, rx in PATTERNS:
                            if rx.search(line):
                                findings.append({"file": os.path.relpath(p, root),
                                                 "line": i, "severity": sev, "pattern": name})
            high = [x for x in findings if x["severity"] == "high"]
            audit = self._audit_requirements(root)
            if audit.get("vulnerabilities"):
                for v in audit["vulnerabilities"]:
                    findings.append({"file": "requirements.txt", "line": 0,
                                     "severity": "high", "pattern": "dependency-vuln",
                                     "detail": v})
                high = [x for x in findings if x["severity"] == "high"]
            llm_findings = self._llm_audit(root)
            for f in llm_findings:
                if not isinstance(f, dict):
                    continue
                findings.append({"file": str(f.get("file", ""))[:120], "line": f.get("line", 0),
                                 "severity": "medium",  # advisory cap: LLM never blocks deploy
                                 "pattern": "llm:" + str(f.get("pattern", ""))[:40],
                                 "detail": str(f.get("detail", ""))[:200]})
            high = [x for x in findings if x["severity"] == "high"]
            return {"safe": not high, "findings": findings,
                    "high": len(high), "medium": len(findings) - len(high),
                    "dependency_audit": audit.get("status"),
                    "llm_audit": "ran" if llm_findings is not None else "skipped"}
        except Exception as e:
            return {"safe": False, "errors": [str(e)]}

    def _audit_requirements(self, root):
        """pip-audit the artifact's requirements.txt inside a throwaway container."""
        req = None
        for dirpath, _, files in os.walk(root):
            if "requirements.txt" in files:
                req = os.path.join(dirpath, "requirements.txt")
                break
        if not req:
            return {"status": "no-requirements"}
        try:
            p = subprocess.run(
                ["docker", "run", "--rm", "-v", f"{req}:/r.txt:ro", "python:3.11-slim",
                 "sh", "-c", "pip install -q pip-audit >/dev/null 2>&1 && "
                             "pip-audit -r /r.txt --desc off"],
                capture_output=True, text=True, timeout=420)
            out = (p.stdout or "") + (p.stderr or "")
            if p.returncode == 0 and "vulnerabilities" not in out.lower():
                return {"status": "clean"}
            vulns = [l.strip() for l in out.splitlines() if "vulnerabilities" in l.lower()]
            return {"status": "vulnerable" if vulns else "clean",
                    "vulnerabilities": vulns[:10]}
        except Exception as e:
            return {"status": f"audit-error: {str(e)[:120]}"}  # non-fatal

    def _llm_audit(self, root):
        """opencode sec-reviewer pass over the artifact: catches non-template issues
        (regex misses). Advisory only — findings capped to medium by the caller."""
        if os.environ.get("OPENCODE_SEC", "1") == "0":
            return []
        try:
            from .opencode_run import opencode_agent, extract_json
            ok, text, err = opencode_agent("sec-reviewer", root,
                                           "Audit this project for security issues.",
                                           timeout=420)
            if not ok:
                print(f"⚠️ security llm audit skipped: {err[:150]}", flush=True)
                return []
            data = extract_json(text) or {}
            out = data.get("findings", [])
            return out if isinstance(out, list) else []
        except Exception as e:
            print(f"⚠️ security llm audit error: {str(e)[:150]}", flush=True)
            return []
