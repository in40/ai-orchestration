"""
QA Engineer MCP Server handlers.

Validates and smoke-runs artifacts produced by the implementation engineer:
clones the mcp-results git repo, extracts code from the result envelope and
runs type-appropriate checks in subprocess sandboxes.
"""
import ast
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from typing import Dict, Any

from .server_handlers import McpServerHandlers

DEFAULT_RESULTS_REPO = os.environ.get(
    "MCP_GIT_REPO_URL", "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git")


class QaEngineerServerHandlers(McpServerHandlers):

    def __init__(self, enable_registry=False, use_postgres=False,
                 postgres_config=None, client_handlers=None):
        super().__init__(enable_registry, use_postgres, postgres_config, client_handlers)
        self._add_qa_tools()

    def _add_qa_tools(self):
        self.tools.append({
            "name": "validate_artifact",
            "description": "Clone a task's result from the mcp-results git repo and validate "
                           "the artifact (syntax, completeness, envelope integrity).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Async task UUID from the coder"},
                    "git_url": {"type": "string", "description": "Result tree URL or repo URL"},
                },
                "required": ["task_id"],
            },
        })
        self.tools.append({
            "name": "smoke_run",
            "description": "Execute a task's artifact in a sandbox: import python, serve+fetch "
                           "html, or perform an MCP initialize handshake for templates.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "git_url": {"type": "string"},
                    "kind": {"type": "string", "enum": ["auto", "python", "html", "mcp_template"]},
                },
                "required": ["task_id"],
            },
        })

    def _execute_tool(self, tool: Dict[str, Any], arguments: Dict[str, Any]) -> Dict[str, Any]:
        name = tool.get("name")
        if name == "validate_artifact":
            return self._validate_artifact(arguments)
        if name == "smoke_run":
            return self._smoke_run(arguments)
        return super()._execute_tool(tool, arguments)

    # ---- helpers ----

    def _fetch_result_dir(self, task_id: str, git_url: str) -> str:
        uuid = task_id
        m = re.search(r"results/([0-9a-f-]{36})", git_url or "")
        if m:
            uuid = m.group(1)
        workdir = os.path.join(tempfile.gettempdir(), f"qa-{uuid}")
        shutil.rmtree(workdir, ignore_errors=True)
        os.makedirs(workdir)
        subprocess.run(["git", "clone", "--depth", "1", DEFAULT_RESULTS_REPO, workdir],
                       check=True, capture_output=True, timeout=60)
        result_dir = os.path.join(workdir, "results", uuid)
        if not os.path.isdir(result_dir):
            raise FileNotFoundError(f"results/{uuid} not found in repo")
        return result_dir

    @staticmethod
    def _extract_code(result_dir: str):
        for fname in ("result.py", "result.js", "result.html"):
            path = os.path.join(result_dir, fname)
            if not os.path.exists(path):
                continue
            raw = open(path).read()
            lang = {"result.py": "python", "result.js": "javascript", "result.html": "html"}[fname]
            try:
                env = json.loads(raw)
                if isinstance(env, dict) and "code" in env:
                    lang = str(env.get("language", lang)).lower().split(",")[0].strip()
                    return env["code"], lang, None
            except json.JSONDecodeError as e:
                if raw.lstrip().startswith("{"):
                    return None, None, f"truncated envelope: {raw[:60]}... ({e.msg} line {e.lineno})"
            return raw, lang, None
        return None, None, "no result.py/result.js/result.html found"

    def _validate_artifact(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result_dir = self._fetch_result_dir(arguments["task_id"], arguments.get("git_url", ""))
            code, lang, err = self._extract_code(result_dir)
            if err:
                return {"valid": False, "errors": [err]}
            errors = []
            if not code or len(code.strip()) < 100:
                errors.append("code too short")
            low = (code or "").lstrip().lower()
            if low.startswith(("<!doctype html", "<html")):
                if "</html>" not in low:
                    errors.append("html missing closing tag")
                lang = "html"
            elif lang.startswith("py"):
                try:
                    ast.parse(code)
                except SyntaxError as e:
                    errors.append(f"python syntax error line {e.lineno}: {e.msg}")
            elif lang.startswith("java") and code.count("{") != code.count("}"):
                errors.append("unbalanced braces in javascript")
            return {"valid": not errors, "language": lang, "errors": errors,
                    "checks": ["envelope", "completeness", f"syntax:{lang}"]}
        except Exception as e:
            return {"valid": False, "errors": [str(e)]}

    def _smoke_run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result_dir = self._fetch_result_dir(arguments["task_id"], arguments.get("git_url", ""))
            code, lang, err = self._extract_code(result_dir)
            if err:
                return {"passed": False, "stage": "extract", "errors": [err]}
            kind = arguments.get("kind", "auto")
            if kind == "auto":
                low = code.lstrip().lower()
                if low.startswith(("<!doctype html", "<html")):
                    kind = "html"
                elif "mcp" in low and ("initialize" in low or "tools/list" in low):
                    kind = "mcp_template"
                else:
                    kind = "python"
            if kind == "html":
                return self._smoke_html(code)
            if kind == "python":
                return self._smoke_python(code)
            if kind == "mcp_template":
                return self._smoke_mcp_template(code)
            return {"passed": False, "stage": "kind", "errors": [f"unknown kind {kind}"]}
        except Exception as e:
            return {"passed": False, "stage": "fetch", "errors": [str(e)]}

    def _smoke_python(self, code: str) -> Dict[str, Any]:
        with tempfile.TemporaryDirectory() as td:
            open(os.path.join(td, "result.py"), "w").write(code)
            try:
                proc = subprocess.run(["python", "-c", "import result"], cwd=td,
                                      capture_output=True, timeout=30, text=True)
            except subprocess.TimeoutExpired:
                return {"passed": False, "stage": "import", "errors": ["import timeout 30s"]}
            ok = proc.returncode == 0
            return {"passed": ok, "kind": "python", "stage": "import",
                    "stderr": proc.stderr[-500:] if not ok else ""}

    def _smoke_html(self, code: str) -> Dict[str, Any]:
        import urllib.request
        with tempfile.TemporaryDirectory() as td:
            open(os.path.join(td, "index.html"), "w").write(code)
            port = self._free_port()
            proc = subprocess.Popen(["python", "-m", "http.server", str(port)],
                                    cwd=td, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                time.sleep(1.5)
                body = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5).read().decode()
                ok = "</html>" in body.lower()
                return {"passed": ok, "kind": "html", "stage": "serve", "bytes": len(body)}
            except Exception as e:
                return {"passed": False, "kind": "html", "stage": "serve", "errors": [str(e)]}
            finally:
                proc.terminate()
                proc.wait(timeout=5)

    def _smoke_mcp_template(self, code: str) -> Dict[str, Any]:
        import urllib.request
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "server.py")
            open(path, "w").write(code)
            port = self._free_port()
            proc = subprocess.Popen(["python", path, "--port", str(port)], cwd=td,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                time.sleep(3)
                payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                      "params": {"protocolVersion": "2024-11-05",
                                                 "capabilities": {},
                                                 "clientInfo": {"name": "qa", "version": "1"}}}).encode()
                req = urllib.request.Request(f"http://127.0.0.1:{port}/mcp", data=payload,
                                             headers={"Content-Type": "application/json"})
                resp = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
                ok = "result" in resp and "protocolVersion" in resp.get("result", {})
                return {"passed": ok, "kind": "mcp_template", "stage": "initialize",
                        "response": str(resp)[:300]}
            except Exception as e:
                return {"passed": False, "kind": "mcp_template", "stage": "initialize",
                        "errors": [str(e)]}
            finally:
                proc.terminate()
                proc.wait(timeout=5)

    @staticmethod
    def _free_port() -> int:
        import socket
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        return port
