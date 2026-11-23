"""Retro M2: safe application of approved proposals.

Whitelist by change_type - the applier can only append to the two learned-
convention files (read at build/plan time, so no service restart is needed
and revert is a plain git revert), or open a pipeline task for R2 hires.
Gates, security rules and the retro system itself are not reachable here.
"""
import json
import os
import subprocess
import sys


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPO = os.environ.get("BASE_DIR", "/root/qwen/base")
TARGETS = {
    "agents_md": os.path.join(REPO, "retro/conventions.md"),
    "planner": os.path.join(REPO, "retro/planner_notes.md"),
}


def _db():
    from observer import DB, connect
    return connect(**DB)


def _baseline_metric(cur):
    """done-without-rework share over the last 7 days - the primary health
    metric (chosen so it cannot be gamed by suppressing gate failures)."""
    cur.execute("SELECT status, activity::text FROM task_registry "
                "WHERE created_at > now() - interval '7 days'")
    done = no_rework = 0
    for status, act in cur.fetchall():
        import json as _json
        try:
            events = _json.loads(act) if isinstance(act, str) else (act or [])
        except Exception:
            events = []
        if status == "done":
            done += 1
            if not any(isinstance(e, dict) and e.get("event") == "rework_requested"
                       for e in events):
                no_rework += 1
    return {"done": done, "done_no_rework": no_rework,
            "rate": round(no_rework / done, 3) if done else None}


def apply_proposal(pid: int, manager=None) -> dict:
    conn = _db()
    cur = conn.cursor()
    cur.execute("SELECT title, change_type, patch_text, status FROM retro_proposals "
                "WHERE id=%s", (pid,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"success": False, "error": f"proposal {pid} not found"}
    title, ctype, patch, status = row
    if status != "proposed":
        conn.close()
        return {"success": False, "error": f"proposal {pid} is {status}, not proposed"}
    try:
        if ctype in TARGETS:
            # M5: every learned convention carries provenance (which proposal,
            # i.e. which evidenced pain it came from) - the library is auditable
            if "retro #" not in patch:
                patch = patch.strip() + f" (retro #{pid})"
            with open(TARGETS[ctype], "a") as f:
                f.write("\n" + patch.strip() + "\n")
            subprocess.run(["git", "-C", REPO, "add", TARGETS[ctype]], check=True)
            subprocess.run(["git", "-C", REPO, "commit", "-q",
                            "-m", f"feat(retro): approved convention - {title[:60]}"],
                           check=True)
            sha = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"],
                                 capture_output=True, text=True).stdout.strip()
            result = f"appended to {os.path.basename(TARGETS[ctype])}, committed {sha[:8]}"
            cur.execute("UPDATE retro_proposals SET status='applied', result=%s, "
                        "commit_sha=%s, metric_before=%s::jsonb, applied_at=now() "
                        "WHERE id=%s",
                        (result, sha,
                         json.dumps(_baseline_metric(cur), ensure_ascii=False), pid))
            conn.commit()
            return {"success": True, "result": result}
        elif ctype == "hire":
            # M4: approval turns the R2 spec into a real pipeline task -
            # the team builds its own new member from the std skeleton.
            if manager is None:
                raise ValueError("hire approval requires the task manager")
            import re as _re
            import time as _t
            slug = _re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:30]
            tid = f"hire-{slug}-{int(_t.time())}"
            desc = ("Найм нового члена команды конвейера. Роль и спецификация:\n"
                    + patch +
                    "\n\nТребования к артефакту: MCP-сервер (stdio) на базе "
                    "mcp-std-skeleton (Python, stdlib), инструменты строго по "
                    "спецификации, self-test утилита (запускает сервер, дергает "
                    "tools/list и каждый инструмент, печатает PASS/FAIL), README с "
                    "инструкцией регистрации в mcp_registry и подключения к конвейеру "
                    "в advisory (shadow) режиме. Критерий приёмки: сам-тест зелёный и "
                    "описана метрика согласия с существующими гейтами.")
            manager.assign_and_forward_task(tid, desc, assignee="IT Lead",
                                            priority="medium",
                                            metadata={"is_hire_task": True})
            result = f"hire task {tid} created in the pipeline"
        else:
            raise ValueError(f"no applier for change_type {ctype}")
        cur.execute("UPDATE retro_proposals SET status='applied', result=%s WHERE id=%s",
                    (result, pid))
        conn.commit()
        return {"success": True, "result": result}
    except Exception as e:
        cur.execute("UPDATE retro_proposals SET status='apply_failed', result=%s WHERE id=%s",
                    (str(e)[:200], pid))
        conn.commit()
        return {"success": False, "error": str(e)[:200]}
    finally:
        cur.close()
        conn.close()


def reject_proposal(pid: int, reason: str = "") -> dict:
    conn = _db()
    cur = conn.cursor()
    cur.execute("UPDATE retro_proposals SET status='rejected', result=%s "
                "WHERE id=%s AND status='proposed'", ("rejected: " + reason[:180], pid))
    conn.commit()
    n = cur.rowcount
    cur.close()
    conn.close()
    return {"success": n > 0}
