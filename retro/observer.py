#!/usr/bin/env python3
"""Retro M1: nightly read-only health snapshot of the agent team.

Computes metrics from the task registry (tasks, gates, reworks,
clarifications, stuck states), stores them in retro_reports and renders
a short digest that the UI bell shows to the requestor. No side effects
beyond inserting one row - this is the observation stage only (M2 adds
diagnosis/proposals).
"""
import json
import os
import time
from collections import Counter
from datetime import datetime, timedelta, timezone

import psycopg2


def _db_params():
    """Credentials from env or /root/qwen/base/.env (never hardcoded)."""
    pw = os.environ.get("POSTGRES_PASSWORD")
    if not pw:
        try:
            for line in open("/root/qwen/base/.env"):
                if line.startswith("POSTGRES_PASSWORD="):
                    pw = line.split("=", 1)[1].strip()
                    break
        except OSError:
            pass
    return dict(host="127.0.0.1", database="mcp_registry", user="postgres",
                password=pw or os.environ.get("PGPASSWORD", ""))


DB = _db_params()
ACTIVE = {"submitted", "in_progress", "review", "rework_in_progress", "awaiting_input"}
STUCK_HOURS = 6
WINDOW_DAYS = 7


def _j(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return None
    return v


def collect():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS retro_reports("
        "id serial PRIMARY KEY, ts timestamptz DEFAULT now(), "
        "digest text, metrics jsonb)")
    conn.commit()

    cur.execute(
        "SELECT task_id, status, status_reason, created_at, updated_at, "
        "metadata::text, activity::text FROM task_registry "
        "WHERE created_at > now() - (%s || ' days')::interval "
        "AND NOT COALESCE(archived, false)", (str(WINDOW_DAYS),))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    now = datetime.now(timezone.utc)
    m = {
        "window_days": WINDOW_DAYS, "total": len(rows),
        "by_status": Counter(), "done_no_rework": 0, "rework_requested": 0,
        "rework_done": 0, "rework_failed": 0,
        "gates": {}, "security_repairs": 0, "clarifications_pending": 0,
        "clarification_fields": Counter(), "stuck": [], "failures": [],
    }
    for tid, status, reason, created, updated, md, act in rows:
        m["by_status"][status] = m["by_status"].get(status, 0) + 1
        events = _j(act) or []
        ev_names = {e.get("event") for e in events if isinstance(e, dict)}
        if status == "done" and "rework_requested" not in ev_names:
            m["done_no_rework"] += 1
        m["rework_requested"] += len(ev_names & {"rework_requested"})
        m["rework_done"] += len(ev_names & {"rework_done"})
        m["rework_failed"] += len(ev_names & {"rework_failed"})
        for e in events:
            if not isinstance(e, dict):
                continue
            ev, det = e.get("event", ""), str(e.get("detail") or "")
            if ev in ("qa_gate", "security_gate", "visual_gate"):
                g = m["gates"].setdefault(ev, {"pass": 0, "fail": 0})
                g["fail" if det.startswith("FAIL") else "pass"] += 1
            if ev == "security_repair":
                m["security_repairs"] += 1
        cl = (_j(md) or {}).get("clarifications") or []
        for c in cl:
            if isinstance(c, dict) and c.get("status") == "pending":
                m["clarifications_pending"] += 1
                m["clarification_fields"][c.get("field", "?")] += 1
        try:
            upd = updated if updated.tzinfo else updated.replace(tzinfo=timezone.utc)
        except Exception:
            upd = now
        if status in ACTIVE and now - upd > timedelta(hours=STUCK_HOURS):
            m["stuck"].append(f"{tid} ({status}, {int((now - upd).total_seconds() // 3600)}h)")
        if status in ("needs_revision", "failed"):
            m["failures"].append(f"{tid}: {(reason or '')[:110]}")

    # digest (human-readable, Russian, for the bell)
    g = m["gates"]
    lines = [
        f"За {m['window_days']} дн: задач {m['total']}, done {m['by_status'].get('done', 0)}"
        f" (без rework {m['done_no_rework']}), rework {m['rework_requested']}"
        f" (успешных {m['rework_done']})",
        "Гейты: " + " · ".join(
            f"{k.replace('_gate', '')} pass {v['pass']}/fail {v['fail']}"
            for k, v in sorted(g.items())) + (
            f" · security-ремонтов {m['security_repairs']}" if m["security_repairs"] else ""),
        f"Clarifications: в ожидании {m['clarifications_pending']}"
        + (", частые поля: " + ", ".join(
            f"{f}×{n}" for f, n in m["clarification_fields"].most_common(3))
           if m["clarification_fields"] else ""),
    ]
    if m["stuck"]:
        lines.append("⚠️ Зависло: " + "; ".join(m["stuck"][:5]))
    if m["failures"]:
        lines.append("Провалы: " + " | ".join(m["failures"][:3]))
    m["by_status"] = dict(m["by_status"])
    m["clarification_fields"] = dict(m["clarification_fields"])
    return m, "\n".join(lines)


def main():
    if os.environ.get("USE_POSTGRES", "true").lower() in ("false", "0", "no"):
        # retro analytics query postgres jsonb directly; sqlite hosts skip
        # until the retro suite is ported (phase 2)
        print("retro: postgres disabled (USE_POSTGRES=false) - skipping")
        return
    m, digest = collect()
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("INSERT INTO retro_reports(digest, metrics) VALUES (%s, %s)",
                (digest, json.dumps(m, ensure_ascii=False)))
    conn.commit()
    cur.close()
    conn.close()
    print(digest)


if __name__ == "__main__":
    main()
