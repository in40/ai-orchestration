#!/usr/bin/env python3
"""Retro M2: Proposer - turns the nightly snapshot into problem cards and
concrete, risk-classed improvement proposals.

Risk routing (mirrors the agreed design):
  R0 note       -> auto-appended to IMPROVEMENT_BACKLOG.md (docs only)
  R1 agents_md  -> append one convention bullet to retro/conventions.md
  R1 planner    -> append one note to retro/planner_notes.md
  R2 hire       -> needs human approval; on approval a pipeline task is created
R1/R2 wait in retro_proposals (status=proposed) and surface in the UI bell.
The proposer NEVER edits gates, security rules or its own scoring - and the
eval files are outside its reach by construction.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

import psycopg2
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from observer import DB, _j  # noqa: E402

REPO = "/root/qwen/base"
ALLOWED = {"note": "R0", "agents_md": "R1", "planner": "R1", "hire": "R2"}


def _env(name, default=""):
    try:
        for line in open(os.path.join(REPO, ".env")):
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return os.environ.get(name, default)


def gather_evidence(cur):
    ev = {"rework_issues": [], "gate_fails": [], "failures": [], "clarifications": []}
    cur.execute("SELECT task_id, status, status_reason, activity::text, metadata::text "
                "FROM task_registry WHERE created_at > now() - interval '7 days'")
    for tid, status, reason, act, md in cur.fetchall():
        for e in _j(act) or []:
            if not isinstance(e, dict):
                continue
            ev_, det = e.get("event", ""), str(e.get("detail") or "")[:160]
            if ev_ == "rework_requested":
                ev["rework_issues"].append(f"{tid}: {det}")
            elif ev_ in ("qa_gate", "security_gate", "visual_gate") and det.startswith("FAIL"):
                ev["gate_fails"].append(f"{tid} {ev_}: {det[:140]}")
        if status in ("needs_revision", "failed"):
            ev["failures"].append(f"{tid}: {(reason or '')[:160]}")
        for c in (_j(md) or {}).get("clarifications") or []:
            if isinstance(c, dict):
                ev["clarifications"].append(f"{c.get('field')} ({c.get('status')})")
    # M5 skill library: recurring patterns (>=2) are mandatory proposal fodder
    from collections import Counter
    norm = Counter(s.split(": ", 1)[-1][:60].lower()
                   for s in ev["rework_issues"] + ev["gate_fails"])
    ev["recurring"] = [f"{p} ×{c}" for p, c in norm.items() if c >= 2]
    return {k: v[:12] for k, v in ev.items()}


PROMPT = """You are the retro engineer of a multi-agent dev pipeline (planner -> coder \
(opencode) -> QA/security gates -> deploy). Below is the 7-day health snapshot and raw \
evidence. Propose AT MOST 3 improvements that address RECURRING, evidenced problems \
(not one-off noise). Primary health metric: share of tasks reaching done WITHOUT rework.

For each proposal return JSON with fields:
  title (short, Russian), problem (what hurts, with numbers), evidence (task ids/quotes),
  change_type: one of
    "note"      - observation for the backlog only (risk R0)
    "agents_md" - one bullet to append to coder conventions (risk R1)
    "planner"   - one note to append to the task-planner prompt (risk R1)
    "hire"      - a new team member/tool/blocking gate (risk R2)
  patch_text: for agents_md/planner - the exact single bullet/note (<=400 chars, \
operational, no diff syntax); for note - the backlog line; for hire - the role spec \
(what it does, where in the pipeline, how to evaluate it)
  rationale, expected_effect
Rules: never propose weakening or removing security/QA gates; never propose editing \
this retro system itself; prefer the smallest change that fixes the pattern; every \
item in evidence.recurring is a REPEAT pattern - for each one not already covered by \
conventions, you MUST emit an agents_md or planner proposal whose patch_text ends \
with provenance task ids; if the data shows no recurring problem and no repeat \
pattern, return {"proposals": []}.

SNAPSHOT:
%s

EVIDENCE:
%s

Return ONLY JSON: {"proposals": [...]}"""


def llm_propose(snapshot, evidence):
    url, model = _env("LLM_PROVIDER_URL"), _env("LLM_MODEL")
    r = requests.post(url, json={
        "model": model,
        "messages": [{"role": "user", "content":
                      PROMPT % (json.dumps(snapshot, ensure_ascii=False),
                                json.dumps(evidence, ensure_ascii=False))}],
        "temperature": 0.4}, timeout=240)
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", text, re.S)
    data = json.loads(m.group(0)) if m else {}
    out = []
    for p in data.get("proposals", [])[:3]:
        ct = p.get("change_type")
        if ct not in ALLOWED or not p.get("title") or not p.get("patch_text"):
            continue
        p["change_type"], p["risk"] = ct, ALLOWED[ct]
        p["patch_text"] = str(p["patch_text"])[:600]
        out.append(p)
    return out


def auto_apply_note(title, patch_text):
    line = f"\n## Retro note: {title}\n{patch_text}\n"
    with open(os.path.join(REPO, "IMPROVEMENT_BACKLOG.md"), "a") as f:
        f.write(line)
    subprocess.run(["git", "-C", REPO, "add", "IMPROVEMENT_BACKLOG.md"], check=True)
    subprocess.run(["git", "-C", REPO, "commit", "-q",
                    "-m", f"docs(retro): auto note - {title[:60]}"], check=True)


def main():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS retro_proposals("
                "id serial PRIMARY KEY, ts timestamptz DEFAULT now(), title text, "
                "problem text, evidence text, change_type text, risk text, "
                "patch_text text, rationale text, expected_effect text, "
                "status text DEFAULT 'proposed', result text)")
    conn.commit()
    cur.execute("SELECT metrics::text FROM retro_reports ORDER BY ts DESC LIMIT 1")
    row = cur.fetchone()
    if not row:
        print("no retro snapshot yet")
        return
    snapshot = _j(row[0]) or {}
    evidence = gather_evidence(cur)
    proposals = llm_propose(snapshot, evidence)
    created = 0
    for p in proposals:
        cur.execute("SELECT 1 FROM retro_proposals WHERE lower(title)=lower(%s) "
                    "AND ts > now() - interval '14 days' LIMIT 1", (p["title"],))
        if cur.fetchone():
            continue  # dedup: already proposed recently
        if p["change_type"] == "note":
            try:
                auto_apply_note(p["title"], p["patch_text"])
                status, result = "auto_applied", "appended to IMPROVEMENT_BACKLOG.md"
            except Exception as e:
                status, result = "apply_failed", str(e)[:200]
        else:
            status, result = "proposed", None
        cur.execute(
            "INSERT INTO retro_proposals(title, problem, evidence, change_type, risk, "
            "patch_text, rationale, expected_effect, status, result) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (p["title"], p.get("problem", ""), json.dumps(p.get("evidence", ""),
                                                           ensure_ascii=False),
             p["change_type"], p["risk"], p["patch_text"], p.get("rationale", ""),
             p.get("expected_effect", ""), status, result))
        created += 1
        print(f"[{p['risk']}/{p['change_type']}] {p['title']} -> {status}")
    conn.commit()
    cur.close()
    conn.close()
    print(f"proposals created: {created} at "
          f"{datetime.now(timezone.utc).strftime('%H:%M:%S')}")


if __name__ == "__main__":
    main()
