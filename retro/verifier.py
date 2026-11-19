#!/usr/bin/env python3
"""Retro M3: Verifier - canary over the live task stream for every applied
retro convention.

For each proposal applied via the applier (status='applied', commit_sha
set) the primary metric (done-without-rework rate, 7-day window) is
compared with the baseline captured at apply time. If enough tasks have
reached a terminal state since the change and the rate dropped by more
than DROP_TOLERANCE, the MOST RECENT such change is git-reverted (one
revert per night to avoid cascades), the proposal is marked 'reverted'
and a digest row notifies the bell. Changes that survive WATCH_DAYS are
'marked settled'. The verifier never touches gates/security - only
commits made by the retro applier.
"""
import json
import os
import subprocess
import sys

import psycopg2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from observer import DB  # noqa: E402
from applier import _baseline_metric  # noqa: E402

REPO = "/root/qwen/base"
MIN_TASKS = 5
DROP_TOLERANCE = 0.15
WATCH_DAYS = 14


def main():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("SET lock_timeout = 10000")
    cur.execute("ALTER TABLE retro_proposals ADD COLUMN IF NOT EXISTS commit_sha text")
    cur.execute("ALTER TABLE retro_proposals ADD COLUMN IF NOT EXISTS metric_before jsonb")
    cur.execute("ALTER TABLE retro_proposals ADD COLUMN IF NOT EXISTS applied_at timestamptz")
    conn.commit()

    cur.execute("SELECT id, title, commit_sha, metric_before::text, "
                "applied_at::timestamp AT TIME ZONE 'UTC' "
                "FROM retro_proposals WHERE status='applied' AND commit_sha IS NOT NULL "
                "AND applied_at > now() - (%s || ' days')::interval "
                "ORDER BY applied_at DESC", (str(WATCH_DAYS),))
    watched = cur.fetchall()

    # graduate old changes
    cur.execute("UPDATE retro_proposals SET status='settled', "
                "result=(result || ' | settled after watch window') "
                "WHERE status='applied' AND commit_sha IS NOT NULL "
                "AND applied_at < now() - (%s || ' days')::interval", (str(WATCH_DAYS),))
    if cur.rowcount:
        print(f"settled: {cur.rowcount}")

    cur.execute("SELECT count(*) FROM task_registry WHERE status IN "
                "('done','failed','needs_revision') AND created_at > now() - interval '7 days'")
    current = _baseline_metric(cur)
    reverted_any = False
    for pid, title, sha, mb_raw, applied in watched:
        if reverted_any:
            break  # one revert per night
        try:
            mb = json.loads(mb_raw) if isinstance(mb_raw, str) else mb_raw
        except Exception:
            continue
        if not mb or mb.get("rate") is None or current.get("rate") is None:
            continue
        cur.execute("SELECT count(*) FROM task_registry WHERE status IN "
                    "('done','failed','needs_revision') AND created_at > %s", (applied,))
        tasks_since = cur.fetchone()[0]
        if tasks_since < MIN_TASKS:
            continue
        if current["rate"] < mb["rate"] - DROP_TOLERANCE:
            r = subprocess.run(["git", "-C", REPO, "revert", "--no-edit", sha],
                               capture_output=True, text=True)
            if r.returncode != 0:
                cur.execute("UPDATE retro_proposals SET status='revert_failed', "
                            "result=%s WHERE id=%s",
                            (("git revert failed: " + (r.stderr or r.stdout)[-160]), pid))
                digest = (f"⚠️ Retro: авто-revert НЕ УДАЛСЯ для «{title}» "
                          f"(метрика {mb['rate']}→{current['rate']}). Нужен человек.")
            else:
                cur.execute("UPDATE retro_proposals SET status='reverted', result=%s "
                            "WHERE id=%s",
                            ((f"auto-reverted: rate {mb['rate']} -> {current['rate']} "
                              f"over {tasks_since} tasks"), pid))
                digest = (f"⚠️ Retro: авто-revert «{title}» — доля done без rework "
                          f"упала {mb['rate']} → {current['rate']} за {tasks_since} задач")
                reverted_any = True
            cur.execute("INSERT INTO retro_reports(digest, metrics) VALUES (%s, %s)",
                        (digest, json.dumps({"verifier": True, "proposal": pid})))
            print(digest)
    conn.commit()
    cur.close()
    conn.close()
    if not reverted_any:
        print(f"verifier ok: {len(watched)} watched, metric={current.get('rate')}")


if __name__ == "__main__":
    main()
