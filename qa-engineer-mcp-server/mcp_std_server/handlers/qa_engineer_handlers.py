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

        self.tools.append({
            "name": "plan_run_contract",
            "description": "Read a task's artifact tree and decide how to install, run and "
                           "health-check it (LLM reads README + entry files). Returns a run "
                           "contract consumed by smoke_run and by the deployer.",
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
        name = tool.get("name")
        if name == "validate_artifact":
            return self._validate_artifact(arguments)
        if name == "smoke_run":
            return self._smoke_run(arguments)
        if name == "plan_run_contract":
            return self._plan_run_contract(arguments)
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
                if isinstance(env, dict) and env.get("files"):
                    f0 = env["files"][0]
                    p = str(f0.get("path", ""))
                    lang = ("python" if p.endswith(".py") else
                            "html" if p.endswith((".html", ".htm")) else
                            "javascript" if p.endswith(".js") else lang)
                    return str(f0.get("content", "")), lang, None, None
                if isinstance(env, dict) and "code" in env:
                    lang = str(env.get("language", lang)).lower().split(",")[0].strip()
                    return env["code"], lang, None, None
            except json.JSONDecodeError as e:
                if raw.lstrip().startswith("{"):
                    return None, None, f"truncated envelope: {raw[:60]}... ({e.msg} line {e.lineno})", None
            return raw, lang, None, None
        # Tree of files (fan-out flow): primary = first code file, recursive
        code_files = []
        for root, _, files in os.walk(result_dir):
            code_files += [os.path.relpath(os.path.join(root, f), result_dir)
                           for f in files if f.endswith((".py", ".js", ".html", ".htm"))]
        if code_files:
            primary = sorted(code_files)[0]
            lang = {"py": "python", "js": "javascript"}.get(primary.rsplit(".", 1)[-1], "html")
            return open(os.path.join(result_dir, primary)).read(), lang, None, primary.replace("\\", "/")
        return None, None, "no result.py/result.js/result.html found", None

    def _llm_json(self, prompt: str):
        """Small LLM call returning a parsed JSON object, or None."""
        import requests as _rq
        url = os.environ.get("LLM_PROVIDER_URL", "")
        model = os.environ.get("LLM_MODEL", "")
        if not url or not model:
            return None
        try:
            r = _rq.post(url, json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2, "max_tokens": 2048,
                "reasoning_effort": "low"}, timeout=240)
            txt = r.json()["choices"][0]["message"]["content"]
            s, t = txt.find("{"), txt.rfind("}")
            if s == -1 or t <= s:
                return None
            return json.loads(txt[s:t + 1])
        except Exception as e:
            print(f"⚠️ QA LLM call failed: {e}")
            return None

    def _heuristic_contract(self, files):
        """Fallback contract when no LLM available: mirror legacy deployer heuristics."""
        if "index.html" in files:
            return {"kind": "static", "run": "", "cwd": "", "env": {},
                    "healthcheck": {"type": "static"}}
        main_pkg = next((f for f in files if f.endswith("__main__.py")), None)
        if main_pkg:
            pkg_dir = os.path.dirname(main_pkg)
            return {"kind": "service", "run": f"python -m {os.path.basename(pkg_dir)}",
                    "cwd": os.path.dirname(pkg_dir), "env": {"PORT": "5000"},
                    "healthcheck": {"type": "http", "url": "/mcp", "method": "POST",
                                    "port": 5000, "expect_substring": ""}}
        entry = next((f for f in files if f.endswith(".py") and not f.endswith("__init__.py")), None)
        if entry:
            return {"kind": "cli", "run": f"python {os.path.basename(entry)}",
                    "cwd": os.path.dirname(entry), "env": {},
                    "healthcheck": {"type": "process"}}
        return {"kind": "static", "run": "", "cwd": "", "env": {},
                "healthcheck": {"type": "static"}}

    def _plan_run_contract(self, arguments: Dict[str, Any], result_dir: str = None) -> Dict[str, Any]:
        try:
            cache_dir = os.path.join(tempfile.gettempdir(), "qa-contracts")
            cache = os.path.join(cache_dir, f"{arguments['task_id']}.json")
            if os.path.exists(cache):  # deterministic: one contract per task, reused by smoke+deploy
                try:
                    with open(cache) as f:
                        return {"valid": True, "contract": json.load(f)}
                except Exception:
                    pass
            if result_dir is None:
                result_dir = self._fetch_result_dir(arguments["task_id"], arguments.get("git_url", ""))
            files = []
            for root, _, fs in os.walk(result_dir):
                files += [os.path.relpath(os.path.join(root, f), result_dir) for f in fs]
            contract = None
            # opencode-first: explore agent reads the ACTUAL entry points
            if os.environ.get("OPENCODE_QA", "1") != "0":
                try:
                    from .opencode_run import opencode_agent, extract_json
                    ok, text, err = opencode_agent(
                        "contract-planner", result_dir,
                        "Determine the run contract for this artifact.",
                        session=f"ses-contract-{arguments['task_id']}", timeout=300)
                    contract = extract_json(text) if ok else None
                    if contract and not contract.get("kind"):
                        contract = None
                    if contract:
                        contract["source"] = "opencode"
                    else:
                        print(f"⚠️ contract opencode fell back: {err or 'bad json'}", flush=True)
                except Exception as e:
                    contract = None
                    print(f"⚠️ contract opencode error: {str(e)[:150]}", flush=True)
            if contract is None:
                readme = ""
                for f in sorted(files):
                    if f.lower().endswith("readme.md"):
                        readme = open(os.path.join(result_dir, f), errors="ignore").read()[:1500]
                        break
                cands = "\n\n".join(
                    f"--- {f} ---\n" + open(os.path.join(result_dir, f), errors="ignore").read()[:500]
                    for f in sorted(files) if f.endswith((".py", ".js", ".html")))[:6000]
                contract = self._llm_json(
                    "You are a release engineer. Decide how to install, run and health-check this "
                    "generated artifact on Linux.\n"
                    f"Files: {files}\nREADME excerpt:\n{readme}\nEntry candidates:\n{cands}\n\n"
                    'Respond ONLY JSON: {"install": "shell cmd or empty", '
                    '"run": "shell cmd starting the service/CLI, or empty for static", '
                    '"cwd": "dir relative to artifact root", "env": {"K":"V"}, '
                    '"kind": "service|cli|static", "healthcheck": {"type": "http|process|static", '
                    '"url": "path e.g. /mcp", "method": "POST|GET", "body": "json string or empty", '
                    '"expect_substring": "text expected in response or empty", "port": 5000}}\n'
                    "kind=service: run starts a server, healthcheck.type MUST be http with url/port, "
                    "polling http://127.0.0.1:PORT+url. "
                    "kind=cli: run must exit 0 quickly. kind=static: run empty, healthcheck static. "
                    "The server binds the port from env PORT.")
                if not contract or not contract.get("kind"):
                    contract = self._heuristic_contract(files)
                    contract["source"] = "heuristic"
                else:
                    contract["source"] = "llm"
            contract["task_id"] = arguments["task_id"]
            try:
                os.makedirs(cache_dir, exist_ok=True)
                with open(cache, "w") as f:
                    json.dump(contract, f)
            except Exception:
                pass
            return {"valid": True, "contract": contract}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def _run_generated_tests(self, result_dir, cwd, env):
        """If the artifact ships tests (tests/ dir or test_*.py), run them with pytest
        in the smoke venv. Returns {'ran': False} when no tests exist."""
        test_files = []
        for root, _, fs in os.walk(result_dir):
            test_files += [f for f in fs if f.startswith("test_") and f.endswith(".py")]
        if not test_files:
            return {"ran": False, "reason": "no tests generated"}
        venv = os.path.join(result_dir, ".qa_venv")
        py = os.path.join(venv, "bin", "python")
        if not os.path.exists(py):
            try:
                import sys as _sys
                subprocess.run([_sys.executable, "-m", "venv", venv],
                               check=True, capture_output=True, timeout=180)
            except Exception as e:
                return {"ran": True, "passed": False, "stage": "venv", "output": str(e)[:300]}
        try:
            chk = subprocess.run([py, "-m", "pytest", "--version"],
                                 capture_output=True, timeout=30)
            if chk.returncode != 0:
                raise RuntimeError("pytest missing")
        except Exception:
            subprocess.run([py, "-m", "pip", "install", "-q", "pytest"],
                           capture_output=True, timeout=300)
        try:
            p = subprocess.run([py, "-m", "pytest", "-q", "--no-header", "-x"], cwd=cwd,
                               env=env, capture_output=True, text=True, timeout=240)
            tail = ((p.stdout or "") + (p.stderr or ""))[-800:]
            return {"ran": True, "passed": p.returncode == 0, "output": tail}
        except subprocess.TimeoutExpired:
            return {"ran": True, "passed": False, "output": "pytest timeout 240s"}

    def _smoke_contract(self, contract: Dict[str, Any], result_dir: str) -> Dict[str, Any]:
        """Execute a run contract: install, run, health-check."""
        import urllib.request
        kind = contract.get("kind", "static")
        cwd = os.path.join(result_dir, str(contract.get("cwd") or ""))
        env = dict(os.environ)
        env.update({str(k): str(v) for k, v in (contract.get("env") or {}).items()})
        if contract.get("install"):
            venv = os.path.join(result_dir, ".qa_venv")
            try:
                import sys as _sys
                subprocess.run([_sys.executable, "-m", "venv", venv],
                               check=True, capture_output=True, timeout=180)
                venv_bin = os.path.join(venv, "bin")
                env["PATH"] = venv_bin + os.pathsep + env.get("PATH", "")
                env["VIRTUAL_ENV"] = venv
            except Exception as e:
                return {"passed": False, "stage": "venv", "errors": [str(e)[:200]]}
            try:
                p = subprocess.run(contract["install"], shell=True, executable="/bin/bash", cwd=cwd, env=env,
                                   capture_output=True, text=True, timeout=300)
                if p.returncode != 0:
                    return {"passed": False, "stage": "install", "stderr": p.stderr[-1500:]}
            except subprocess.TimeoutExpired:
                return {"passed": False, "stage": "install", "errors": ["install timeout"]}
        hc = contract.get("healthcheck") or {}
        run = contract.get("run") or ""
        if kind == "cli":
            try:
                p = subprocess.run(run, shell=True, executable="/bin/bash", cwd=cwd, env=env,
                                   capture_output=True, text=True, timeout=60)
                if p.returncode != 0:
                    return {"passed": p.returncode == 0, "kind": "cli", "stage": "run",
                            "stderr": p.stderr[-1500:]}
                tests = self._run_generated_tests(result_dir, cwd, env)
                if tests.get("ran") and not tests.get("passed"):
                    return {"passed": False, "kind": "cli", "stage": "tests", "tests": tests}
                return {"passed": True, "kind": "cli", "stage": "run", "tests": tests}
            except subprocess.TimeoutExpired:
                return {"passed": False, "kind": "cli", "stage": "run", "errors": ["timeout"]}
        if kind == "static":
            html_file = next((os.path.join(r, f) for r, _, fs in os.walk(result_dir)
                              for f in fs if f.endswith((".html", ".htm"))), None)
            if not html_file:
                return {"passed": False, "kind": "static", "stage": "find",
                        "errors": ["no html file found"]}
            return self._smoke_html(open(html_file, errors="ignore").read())
        # kind == service: http healthcheck regardless of what the contract said.
        # Always smoke on a FREE ephemeral port: stale servers on the default
        # port must not cause false failures.
        import socket as _sock
        try:
            _s = _sock.socket()
            _s.bind(("127.0.0.1", 0))
            port = _s.getsockname()[1]
            _s.close()
        except Exception:
            port = hc.get("port") or (contract.get("env") or {}).get("PORT") or 5000
        url_path = hc.get("url") or "/mcp"
        env["PORT"] = str(port)
        proc = subprocess.Popen(run, shell=True, executable="/bin/bash", cwd=cwd, env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.time() + 25
            last = ""
            while time.time() < deadline:
                if proc.poll() is not None:
                    return {"passed": False, "kind": "service", "stage": "startup",
                            "stderr": (proc.stderr.read() or "")[-1500:]}
                try:
                    url = f"http://127.0.0.1:{port}{url_path}"
                    body = hc.get("body") or ""
                    if not body and "mcp" in url_path:
                        body = ('{"jsonrpc":"2.0","id":1,"method":"initialize","params":'
                                '{"protocolVersion":"2024-11-05","capabilities":{},'
                                '"clientInfo":{"name":"qa","version":"1"}}}')
                    data = body.encode() if body else None
                    req = urllib.request.Request(
                        url, data=data,
                        headers={"Content-Type": "application/json"},
                        method=hc.get("method") or ("POST" if data else "GET"))
                    body = urllib.request.urlopen(req, timeout=3).read().decode()
                    if not hc.get("expect_substring") or hc["expect_substring"] in body:
                        if "mcp" in url_path:
                            # conformance: a real MCP service must answer tools/list
                            probe = ('{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}').encode()
                            try:
                                req2 = urllib.request.Request(url, data=probe, method="POST",
                                                              headers={"Content-Type": "application/json"})
                                body2 = urllib.request.urlopen(req2, timeout=5).read().decode()
                                if '"result"' not in body2:
                                    return {"passed": False, "kind": "service",
                                            "stage": "conformance",
                                            "errors": ["tools/list: " + body2[:200]]}
                            except Exception as e:
                                return {"passed": False, "kind": "service",
                                        "stage": "conformance", "errors": [str(e)]}
                        # artifact-provided verification client (contract by example)
                        cl = next((os.path.join(dp, f) for dp, _, fs in os.walk(result_dir)
                                   for f in fs if f == "client.py"), None)
                        if cl:
                            try:
                                import urllib.parse as _up
                                _p = _up.urlparse(url)
                                cp = subprocess.run(["python3", cl,
                                                     f"{_p.scheme}://{_p.netloc}"],
                                                    cwd=os.path.dirname(cl),
                                                    capture_output=True, text=True, timeout=60)
                                if cp.returncode != 0:
                                    return {"passed": False, "kind": "service", "stage": "client",
                                            "client_output": ((cp.stdout or "") + (cp.stderr or ""))[-500:]}
                            except Exception as e:
                                return {"passed": False, "kind": "service", "stage": "client",
                                        "client_output": str(e)[:200]}
                        tests = self._run_generated_tests(result_dir, cwd, env)
                        if tests.get("ran") and not tests.get("passed"):
                            return {"passed": False, "kind": "service", "stage": "tests",
                                    "tests": tests}
                        return {"passed": True, "kind": "service", "stage": "healthcheck",
                                "response": body[:200], "tests": tests}
                    last = body[:200]
                except Exception as e:
                    last = str(e)
                time.sleep(1)
            return {"passed": False, "kind": "service", "stage": "healthcheck", "errors": [last]}
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()

    def _validate_artifact(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result_dir = self._fetch_result_dir(arguments["task_id"], arguments.get("git_url", ""))
            code, lang, err, primary = self._extract_code(result_dir)
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
            code, lang, err, primary = self._extract_code(result_dir)
            if err:
                return {"passed": False, "stage": "extract", "errors": [err]}
            if primary is not None:
                # fan-out tree: contract-driven smoke (install/run/healthcheck decided per artifact)
                cr = self._plan_run_contract(arguments, result_dir=result_dir)
                if not cr.get("valid"):
                    return {"passed": False, "stage": "contract", "errors": [cr.get("error", "")]}
                contract = cr["contract"]
                result = self._smoke_contract(contract, result_dir)
                result["contract"] = contract
                return result
            kind = arguments.get("kind", "auto")
            if kind == "auto":
                low = code.lstrip().lower()
                if low.startswith(("<!doctype html", "<html")):
                    kind = "html"
                elif "mcp" in low and ("initialize" in low or "tools/list" in low):
                    kind = "mcp_template"
                elif lang.startswith("java") or "=>" in code or "const " in code:
                    kind = "javascript"
                else:
                    kind = "python"
            if kind == "html":
                return self._smoke_html(code)
            if kind == "javascript":
                return self._smoke_javascript(code)
            if kind == "python":
                return self._smoke_python(code, result_dir=result_dir, primary=primary)
            if kind == "mcp_template":
                return self._smoke_mcp_template(code)
            return {"passed": False, "stage": "kind", "errors": [f"unknown kind {kind}"]}
        except Exception as e:
            return {"passed": False, "stage": "fetch", "errors": [str(e)]}

    def _smoke_python(self, code: str, result_dir: str = None, primary: str = None) -> Dict[str, Any]:
        with tempfile.TemporaryDirectory() as td:
            if result_dir and primary:
                # multi-file tree: copy everything so package imports resolve
                for root, _, files in os.walk(result_dir):
                    dst = os.path.join(td, os.path.relpath(root, result_dir))
                    os.makedirs(dst, exist_ok=True)
                    for f in files:
                        shutil.copy(os.path.join(root, f), dst)
                mod = primary.rsplit(".", 1)[0].replace("/", ".")
                stmt = f"import {mod}"
            else:
                open(os.path.join(td, "result.py"), "w").write(code)
                stmt = "import result"
            try:
                proc = subprocess.run(["python", "-c", stmt], cwd=td,
                                      capture_output=True, timeout=30, text=True)
            except subprocess.TimeoutExpired:
                return {"passed": False, "stage": "import", "errors": ["import timeout 30s"]}
            ok = proc.returncode == 0
            return {"passed": ok, "kind": "python", "stage": "import",
                    "stderr": proc.stderr[-500:] if not ok else ""}

    def _smoke_javascript(self, code: str) -> Dict[str, Any]:
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "result.js")
            open(path, "w").write(code)
            try:
                proc = subprocess.run(["node", "--check", path],
                                      capture_output=True, timeout=30, text=True)
            except FileNotFoundError:
                return {"passed": True, "kind": "javascript", "stage": "node-missing",
                        "note": "node not installed; skipped"}
            except subprocess.TimeoutExpired:
                return {"passed": False, "kind": "javascript", "stage": "check",
                        "errors": ["node --check timeout"]}
            ok = proc.returncode == 0
            return {"passed": ok, "kind": "javascript", "stage": "node --check",
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
