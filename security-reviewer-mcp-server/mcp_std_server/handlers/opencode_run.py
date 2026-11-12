"""opencode runner: HTTP transport to `opencode serve`, CLI subprocess fallback.

Transport choice (per call):
  1. OPENCODE_SERVE_URL + OPENCODE_SERVE_PASSWORD set and server healthy -> HTTP
  2. otherwise (or on HTTP failure with OPENCODE_FALLBACK=1, default) -> `opencode run` CLI
Sessions are bound to the workdir via session `location.directory`; a session
whose stored location differs from the requested workdir is recreated (heals
sessions poisoned by the pre-PWD-fix era).
"""
import json as _json
import os
import shutil
import subprocess
import time

import requests

_health = {"ok": None, "ts": 0.0}


def _serve_cfg():
    url = (os.environ.get("OPENCODE_SERVE_URL") or "").rstrip("/")
    pw = os.environ.get("OPENCODE_SERVE_PASSWORD") or ""
    return (url, pw) if url and pw else (None, None)


def _serve_up(timeout=3):
    cfg = _serve_cfg()
    if not cfg[0]:
        return None
    now = time.time()
    if _health["ok"] and now - _health["ts"] < 30:
        return cfg
    try:
        r = requests.get(cfg[0] + "/api/info", auth=("opencode", cfg[1]), timeout=timeout)
        _health.update(ok=(r.status_code == 200), ts=now)
    except Exception:
        _health.update(ok=False, ts=now)
    return cfg if _health["ok"] else None


def _via_serve(agent, workdir, prompt, session, timeout, model):
    """Returns (text, err)."""
    url, pw = _serve_cfg()
    auth = ("opencode", pw)
    prov, _, mid = (model or os.environ.get("OPENCODE_MODEL",
                    "hallogen/qwen3.8-next")).partition("/")
    sid = session if (session or "").startswith("ses") else \
        "ses-" + "".join(c for c in (session or str(int(time.time()))) if c.isalnum())[:40]
    workdir = os.path.abspath(str(workdir))
    hdr = {"Content-Type": "application/json"}
    body = {"id": sid, "title": agent, "agent": agent,
            "model": {"id": mid, "providerID": prov},
            "location": {"directory": workdir}}
    try:
        r = requests.post(url + "/api/session", auth=auth, headers=hdr,
                          timeout=15, data=_json.dumps(body))
        if r.status_code >= 400:
            g = requests.get(url + f"/api/session/{sid}", auth=auth, timeout=10)
            if g.status_code != 200:
                return None, f"session create rc={r.status_code}: {r.text[:150]}"
            # heal sessions bound to a different directory
            loc = ((g.json().get("data") or {}).get("location") or {}).get("directory")
            if loc and os.path.abspath(loc) != workdir:
                requests.delete(url + f"/api/session/{sid}", auth=auth, timeout=10)
                r = requests.post(url + "/api/session", auth=auth, headers=hdr,
                                  timeout=15, data=_json.dumps(body))
                if r.status_code >= 400:
                    return None, f"session recreate rc={r.status_code}"
        pre_n = len(requests.get(url + f"/api/session/{sid}/message",
                                 auth=auth, timeout=15).json().get("data", []))
        prompt_ts = time.time() * 1000 - 2000
        r = requests.post(url + f"/api/session/{sid}/prompt", auth=auth, headers=hdr,
                          timeout=30, data=_json.dumps({"text": prompt}))
        if r.status_code >= 400:
            return None, f"prompt rc={r.status_code}: {r.text[:150]}"
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(5)
            try:
                msgs = requests.get(url + f"/api/session/{sid}/message",
                                    auth=auth, timeout=15).json().get("data", [])
            except Exception:
                continue
            fresh = [m for m in msgs if (m.get("time") or {}).get("created", 0) >= prompt_ts]
            if len(msgs) <= pre_n and not fresh:
                continue
            idles = [m for m in fresh if m.get("type") == "idle"]
            if not idles:
                continue
            outcome = idles[-1].get("outcome")
            asst = [m for m in fresh if m.get("type") == "assistant"]
            if outcome != "succeeded" or not asst:
                return None, f"agent finished: {outcome or 'unknown'}"
            last = asst[-1]
            if last.get("error"):
                return None, "agent error: " + _json.dumps(last["error"])[:200]
            text = "\n".join(c.get("text", "") for c in last.get("content", [])
                             if c.get("type") == "text").strip()
            return (text, None) if text else (None, "agent returned empty text")
        return None, f"serve timeout after {timeout}s"
    except Exception as e:
        return None, f"serve error: {str(e)[:200]}"


def _via_cli(agent, workdir, prompt, session, timeout, model):
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


def opencode_agent(agent, workdir, prompt, session=None, timeout=420, model=None):
    """Run an opencode agent session in workdir. Returns (ok, text, err)."""
    if _serve_up():
        text, err = _via_serve(agent, workdir, prompt, session, timeout, model)
        if text is not None:
            return True, text, ""
        if os.environ.get("OPENCODE_FALLBACK", "1") == "0":
            return False, "", f"serve: {err}"
        # HTTP failed -> CLI fallback below
    ok, text, cerr = _via_cli(agent, workdir, prompt, session, timeout, model)
    return ok, text, cerr


def extract_json(text):
    """First {...} block in text -> dict, or None."""
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e <= s:
        return None
    try:
        return _json.loads(text[s:e + 1])
    except ValueError:
        return None
