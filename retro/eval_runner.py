#!/usr/bin/env python3
"""Retro M3: golden eval runner (manual / pre-change baseline).

Submits the frozen tasks from retro/evals.json through the normal
pipeline and records outcomes in retro_eval_runs. The eval file is the
frozen yardstick: the retro system must never edit it (proposer prompt
forbids it; keep it that way in reviews). Usage:
    python3 retro/eval_runner.py [--base-url http://127.0.0.1:8000]
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from observer import DB, connect  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TERMINAL = ("done", "failed", "needs_revision")
TIMEOUT_S = 30 * 60


def run_one(base, spec):
    tid = f"eval-{spec['key']}-{int(time.time())}"
    r = requests.post(base + "/api/tasks/assign", json={
        "task_id": tid, "title": tid, "description": spec["description"],
        "assignee": "IT Lead", "priority": "medium",
        "context": {"deploy_after_implementation": spec["expect_deploy"]}}, timeout=60)
    ok = r.status_code == 200
    status, url = ("submit-failed", None) if not ok else (None, None)
    deadline = time.time() + TIMEOUT_S
    while status is None and time.time() < deadline:
        time.sleep(20)
        tasks = requests.get(base + "/api/tasks", timeout=15).json()
        t = next((x for x in (tasks if isinstance(tasks, list) else tasks.get("tasks", []))
                  if x.get("id") == tid), None)
        if t and t.get("status") in TERMINAL:
            status, url = t["status"], t.get("deployment_url")
    if status is None:
        status = "timeout"
    passed = status == "done" and (not spec["expect_deploy"] or bool(url))
    return {"task": tid, "key": spec["key"], "status": status,
            "deployment_url": url, "passed": passed}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = ap.parse_args()
    specs = json.load(open(os.path.join(HERE, "evals.json")))
    results = []
    for spec in specs:
        print("running", spec["key"], flush=True)
        res = run_one(args.base_url, spec)
        results.append(res)
        print(" ", res, flush=True)
    conn = connect(**DB)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS retro_eval_runs("
                "id serial PRIMARY KEY, ts timestamptz DEFAULT now(), results jsonb)")
    cur.execute("INSERT INTO retro_eval_runs(results) VALUES (%s)",
                (json.dumps(results, ensure_ascii=False),))
    conn.commit()
    cur.close()
    conn.close()
    passed = sum(1 for r in results if r["passed"])
    print(f"eval: {passed}/{len(results)} passed at "
          f"{datetime.now(timezone.utc).strftime('%H:%M:%S')}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
