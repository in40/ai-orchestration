"""Task lifecycle: archive (hide, lossless) and delete (trash + purge).

archive: boolean column on task_registry; archived tasks are hidden in the
UI and excluded from retro metrics. Nothing is removed from disk.

delete (double confirm: caller must pass confirm == task_id):
- full row snapshot (task + selffix rows) into tasks_trash, then removed
- ephemeral disk state purged (workspaces, qa trees, screenshots, contracts)
- results/<task> removed from the results repo HEAD ("purge <task>" commit)
Products are unaffected: their mirrors live in ~/projects and GitHub.
Weekly history-level GC (filter-repo) is a separate, later step.
"""
import json
import os
import re
import shutil
import subprocess

RESULTS_LOCAL = "/tmp/mcp-vibe-coding-git/repo"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")
DISK_PURGE = ["/tmp/oc-builds/{task}", "/tmp/qa-{task}",
              os.environ.get("SHOTS_DIR", "/var/www/shots") + "/{task}", "/tmp/qa-contracts/{task}.json"]


def _sql(conn):
    cur = conn.cursor()
    cur.execute("ALTER TABLE task_registry ADD COLUMN IF NOT EXISTS "
                "archived boolean NOT NULL DEFAULT false")
    cur.execute("CREATE TABLE IF NOT EXISTS tasks_trash("
                "id serial PRIMARY KEY, task_id text, deleted_at timestamptz "
                "DEFAULT now(), snapshot jsonb)")
    conn.commit()
    cur.close()


def archive_task(conn, task_id, archived=True):
    _sql(conn)
    cur = conn.cursor()
    cur.execute("UPDATE task_registry SET archived=%s WHERE task_id=%s "
                "RETURNING task_id", (bool(archived), task_id))
    ok = cur.fetchone() is not None
    conn.commit()
    cur.close()
    return {"success": ok, "task_id": task_id, "archived": bool(archived)}


def _purge_disk(task_id):
    report = {}
    if not SAFE_ID.match(task_id):
        return {"error": "unsafe task id"}
    for pattern in DISK_PURGE:
        path = pattern.format(task=task_id)
        try:
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path)
                report[path] = "removed"
            elif os.path.exists(path):
                os.remove(path)
                report[path] = "removed"
            else:
                report[path] = "not_present"
        except OSError as e:
            report[path] = f"error: {e}"
    return report


def _purge_results(task_id):
    """git rm results/<task> in the local clone and push; no-op if absent."""
    if not SAFE_ID.match(task_id):
        return "skipped: unsafe task id"
    tree = os.path.join(RESULTS_LOCAL, "results", task_id)
    if not os.path.isdir(tree):
        return "not_present"
    run = lambda *a, **k: subprocess.run(list(a), cwd=RESULTS_LOCAL,
                                         capture_output=True, text=True, **k)
    run("git", "pull", "-q", "--rebase", "origin", "main")
    rm = run("git", "rm", "-r", "-q", "--", f"results/{task_id}")
    if rm.returncode != 0:
        return f"git rm failed: {rm.stderr[:120]}"
    c = run("git", "-c", "user.name=it-lead", "-c", "user.email=it-lead@local",
            "commit", "-q", "-m", f"purge {task_id}")
    if c.returncode != 0:
        return f"commit failed: {c.stderr[:120]}"
    p = run("git", "push", "-q", "origin", "main", timeout=300)
    return "purged" if p.returncode == 0 else f"push failed: {p.stderr[:120]}"


def delete_task(conn, task_id, confirm=""):
    _sql(conn)
    if confirm != task_id:
        return {"success": False,
                "error": f"confirm must equal the task id ({task_id})"}
    cur = conn.cursor()
    cur.execute("SELECT row_to_json(t) FROM (SELECT * FROM task_registry "
                "WHERE task_id=%s) t", (task_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        return {"success": False, "error": "task not found"}
    snapshot = {"task": row[0]}
    cur.execute("SELECT array_agg(row_to_json(s)) FROM (SELECT * FROM selffix "
                "WHERE task_id=%s) s", (task_id,))
    sf = cur.fetchone()
    if sf and sf[0]:
        snapshot["selffix"] = sf[0]
    cur.execute("INSERT INTO tasks_trash(task_id, snapshot) VALUES (%s, %s::jsonb)",
                (task_id, json.dumps(snapshot, default=str)))
    cur.execute("DELETE FROM selffix WHERE task_id=%s", (task_id,))
    cur.execute("DELETE FROM task_registry WHERE task_id=%s", (task_id,))
    conn.commit()
    cur.close()
    disk = _purge_disk(task_id)
    results = _purge_results(task_id)
    return {"success": True, "task_id": task_id, "trashed": True,
            "disk": disk, "results": results}
