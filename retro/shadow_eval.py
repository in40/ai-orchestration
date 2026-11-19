#!/usr/bin/env python3
"""Retro M4: shadow-mode evaluation of a candidate agent.

Runs the candidate's verdict tool over N recent artifact trees and compares
with the verdict the real gate recorded for the same task (qa_gate or
security_gate events in the activity log). Agreement stats decide nothing
by themselves - promotion from advisory to blocking stays a human call made
through the bell, but this prints the evidence for it.

usage: shadow_eval.py --endpoint http://127.0.0.1:3099/mcp --tool review_artifact \
                      [--against security_gate] [--samples 5]

The candidate tool is called with {task_id, git_url} and must return JSON
containing one of: verdict "pass"/"fail", or boolean safe/valid/passed.
"""
import argparse
import json
import sys

import psycopg2
import requests

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from observer import DB, _j  # noqa: E402


def candidate_verdict(endpoint, tool, task_id, git_url):
    try:
        r = requests.post(endpoint, json={
            "jsonrpc": "2.0", "id": f"shadow-{task_id}", "method": "tools/call",
            "params": {"name": tool,
                       "arguments": {"task_id": task_id, "git_url": git_url}}},
            timeout=180)
        out = r.json().get("result", {})
        if isinstance(out, dict) and isinstance(out.get("result"), dict):
            out = out["result"]
        if not isinstance(out, dict):
            return None
        v = out.get("verdict")
        if isinstance(v, str):
            return v.strip().lower() in ("pass", "passed", "ok", "safe", "true")
        for k in ("safe", "valid", "passed"):
            if isinstance(out.get(k), bool):
                return out[k]
        return None
    except Exception as e:
        print(f"  candidate call failed: {str(e)[:100]}")
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--tool", required=True)
    ap.add_argument("--against", default="security_gate",
                    choices=["qa_gate", "security_gate", "visual_gate"])
    ap.add_argument("--samples", type=int, default=5)
    args = ap.parse_args()

    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("SELECT task_id, metadata::text, activity::text FROM task_registry "
                "WHERE metadata::jsonb ? 'git_url' ORDER BY created_at DESC LIMIT 40")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    tested = agree = 0
    for tid, md, act in rows:
        if tested >= args.samples:
            break
        git_url = (_j(md) or {}).get("git_url")
        if not git_url:
            continue
        actual = None
        for e in _j(act) or []:
            if isinstance(e, dict) and e.get("event") == args.against:
                actual = not str(e.get("detail") or "").startswith("FAIL")
        if actual is None:
            continue
        print(f"{tid}: actual({args.against})={actual} ...", flush=True)
        got = candidate_verdict(args.endpoint, args.tool, tid, git_url)
        if got is None:
            print("  candidate: no verdict")
            continue
        tested += 1
        ok = got == actual
        agree += ok
        print(f"  candidate={got} -> {'AGREE' if ok else 'DISAGREE'}")
    if tested:
        print(f"\nshadow agreement: {agree}/{tested} = {agree / tested:.0%} "
              f"(against {args.against}). Promotion to a blocking gate is a human "
              f"decision via the bell.")
    else:
        print("no comparable samples found")


if __name__ == "__main__":
    main()
