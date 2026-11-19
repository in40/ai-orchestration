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

import psycopg2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPO = "/root/qwen/base"
TARGETS = {
    "agents_md": os.path.join(REPO, "retro/conventions.md"),
    "planner": os.path.join(REPO, "retro/planner_notes.md"),
}


def _db():
    from observer import DB
    return psycopg2.connect(**DB)


def apply_proposal(pid: int) -> dict:
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
            with open(TARGETS[ctype], "a") as f:
                f.write("\n" + patch.strip() + "\n")
            subprocess.run(["git", "-C", REPO, "add", TARGETS[ctype]], check=True)
            subprocess.run(["git", "-C", REPO, "commit", "-q",
                            "-m", f"feat(retro): approved convention - {title[:60]}"],
                           check=True)
            result = f"appended to {os.path.basename(TARGETS[ctype])}, committed"
        elif ctype == "hire":
            result = "hire task creation is queued (M4)"  # M2: approval recorded
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
