"""Minimal opencode CLI runner: headless agent session -> final assistant text."""
import json as _json
import os
import shutil
import subprocess


def opencode_agent(agent, workdir, prompt, session=None, timeout=420,
                   model=None):
    """Run `opencode run --agent <agent>` in workdir. Returns (ok, text, err)."""
    binary = shutil.which("opencode") or "/root/.opencode/bin/opencode"
    if not os.path.exists(binary):
        return False, "", "opencode binary not found"
    cmd = [binary, "run", "--agent", agent,
           "--model", model or os.environ.get("OPENCODE_MODEL", "hallogen/qwen3.8-next"),
           "--auto", "--format", "json"]
    if session:
        cmd += ["--session", session]
    cmd.append(prompt)
    try:
        env = os.environ.copy()
        env["PWD"] = str(workdir)  # opencode CLI resolves project from $PWD, not getcwd
        p = subprocess.run(cmd, cwd=str(workdir), capture_output=True, text=True,
                           timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return False, "", f"opencode {agent} timeout {timeout}s"
    except Exception as e:
        return False, "", f"opencode spawn failed: {e}"
    if p.returncode != 0:
        return False, "", f"opencode rc={p.returncode}: {(p.stderr or p.stdout or '')[-300:]}"
    text = ""
    for line in (p.stdout or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = _json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "text" and ev.get("part", {}).get("text"):
            text = ev["part"]["text"]
    if not text.strip():
        return False, "", "opencode produced no text output"
    return True, text, ""


def extract_json(text):
    """First {...} block in text -> dict, or None."""
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e <= s:
        return None
    try:
        return _json.loads(text[s:e + 1])
    except ValueError:
        return None
