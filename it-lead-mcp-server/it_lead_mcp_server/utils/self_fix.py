"""M6: self-fix pipeline - a complaint about the platform itself becomes a
rework over a SNAPSHOT of whitelisted code; the team fixes the copy, gates
run, and the resulting diff waits in the bell for a human. Approval merges
the files into the live repo (git commit) and hands the merge commit to the
retro verifier, which can auto-revert it if the health metric regresses.

Safety model:
- only AREAS paths are fixable; anything else is refused at file time AND
  re-checked at merge time from the actual diff
- the coder never sees the live repo: it works on a copy in results/
- merge is human-only (bell), revert is a git revert of the recorded commit
"""
import json
import os
import shutil
import subprocess
import threading
import time

REPO = os.environ.get("BASE_DIR", "/root/qwen/base")
RESULTS_LOCAL = "/tmp/mcp-vibe-coding-git/repo"
RESULTS_REPO = os.environ.get("MCP_GIT_REPO_URL",
    "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git")

AREAS = {
    "web-ui-frontend": {
        "live": "it-lead-mcp-server/web-ui/frontend",
        "include": ["src", "index.html", "package.json", "vite.config.js"],
        "restart": [],  # vite HMR picks frontend changes up live
    },
}

GUARDRAILS = (
    "SELF-FIX (M6). Работай только внутри выданных файлов, минимально и "
    "адресно. Не добавляй новых зависимостей, не меняй package.json без "
    "крайней необходимости, не трогай бэкенд. Финальная проверка: "
    "npm install (devDependencies обязательны) && npx vite build — зелёный.\n\n"
    "ЖАЛОБА ЗАКАЗЧИКА:\n")


def _sql(conn):
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS selffix("
                "id serial PRIMARY KEY, ts timestamptz DEFAULT now(), task_id text, "
                "area text, complaint text, status text DEFAULT 'fixing', "
                "diff text, diff_stat text, merge_commit text, metric_before jsonb, "
                "applied_at timestamptz, result text)")
    conn.commit()


def _git(*args, cwd=RESULTS_LOCAL):
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True)


def file_self_fix(conn, complaint, area, manager, log_activity=None):
    """Create the shadow task + snapshot, then kick the rework in background."""
    if area not in AREAS:
        return {"success": False, "error": f"unknown area {area!r}; allowed: {sorted(AREAS)}"}
    _sql(conn)
    tid = f"selffix-{int(time.time())}"
    tree_url = f"{RESULTS_REPO.rsplit('.git', 1)[0]}/tree/main/results/{tid}"
    cur = conn.cursor()
    cur.execute("INSERT INTO task_registry (task_id, title, description, submitter, "
                "submitter_type, status, metadata) VALUES "
                "(%s,%s,%s,'human_operator','human','done',%s::jsonb)",
                (tid, f"Self-fix: {area}", complaint[:2000],
                 json.dumps({"git_url": tree_url, "path": tree_url,
                             "storage_type": "git", "selffix_area": area})))
    cur.execute("INSERT INTO selffix(task_id, area, complaint) VALUES (%s,%s,%s)",
                (tid, area, complaint[:4000]))
    conn.commit()
    cur.close()

    def _run():
        try:
            _snapshot(tid, area)
            if log_activity:
                log_activity(tid, "selffix_snapshotted", agent="it-lead",
                             detail=f"area={area}")
            manager._trigger_rework_workflow(
                tid, GUARDRAILS + complaint, "", "medium")
        except Exception as e:
            c = manager.task_storage.connection
            with c.cursor() as cur2:
                cur2.execute("UPDATE selffix SET status='failed', result=%s "
                             "WHERE task_id=%s", (str(e)[:200], tid))
                c.commit()

    threading.Thread(target=_run, daemon=True).start()
    return {"success": True, "task_id": tid, "area": area,
            "message": "self-fix started; the diff will appear in the bell "
                       "when gates pass"}


def _snapshot(tid, area):
    spec = AREAS[area]
    live = os.path.join(REPO, spec["live"])
    dest = os.path.join(RESULTS_LOCAL, "results", tid)
    _git("pull", "-q")
    os.makedirs(dest, exist_ok=True)
    for item in spec["include"]:
        src = os.path.join(live, item)
        if not os.path.exists(src):
            continue
        target = os.path.join(dest, item)
        if os.path.isdir(src):
            shutil.copytree(src, target, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("node_modules", "dist"))
        else:
            shutil.copy2(src, target)
    _git("add", f"results/{tid}")
    _git("commit", "-q", "-m", f"[selffix] snapshot {area} of {tid}")
    push = _git("push", "-q")
    if push.returncode != 0:
        raise RuntimeError("snapshot push failed: " + push.stderr[:150])


def _area_diff(area, tid):
    """(diff_text, changed_files) between live area and the fixed tree."""
    spec = AREAS[area]
    live = os.path.join(REPO, spec["live"])
    fixed = os.path.join(RESULTS_LOCAL, "results", tid)
    _git("pull", "-q")
    parts, files = [], []
    for item in spec["include"]:
        l, r = os.path.join(live, item), os.path.join(fixed, item)
        if not os.path.exists(r):
            continue
        r2 = subprocess.run(
            ["git", "-C", REPO, "diff", "--no-index", "--",
             os.path.relpath(l, REPO), os.path.relpath(r, REPO)],
            capture_output=True, text=True)
        d = r2.stdout
        if d.strip():
            parts.append(d)
            for line in d.splitlines():
                if line.startswith("diff --git"):
                    files.append(line.split(" b/")[-1])
    text = "\n".join(parts)
    return (text[:200000], files)


def finalize(conn, task_id):
    """Called when a selffix rework finishes: compute the review diff.
    Returns 'review' | 'failed' | None (not a selffix task / already done)."""
    _sql(conn)
    cur = conn.cursor()
    cur.execute("SELECT area, status FROM selffix WHERE task_id=%s AND status='fixing'",
                (task_id,))
    row = cur.fetchone()
    if not row:
        conn.commit()
        cur.close()
        return None
    area = row[0]
    diff, files = _area_diff(area, task_id)
    outcome = "review"
    if not diff.strip():
        outcome = "failed"
        cur.execute("UPDATE selffix SET status='failed', result='no diff produced "
                    "by the rework' WHERE task_id=%s", (task_id,))
    else:
        stat = f"{len(files)} file(s): " + ", ".join(
            f.split(f"results/{task_id}/")[-1] for f in files[:10])
        cur.execute("UPDATE selffix SET status='review', diff=%s, diff_stat=%s "
                    "WHERE task_id=%s", (diff, stat[:500], task_id))
    conn.commit()
    cur.close()
    return outcome


def fail(conn, task_id, reason=""):
    """Mark an in-flight selffix as failed (rework died before finalize)."""
    _sql(conn)
    cur = conn.cursor()
    cur.execute("UPDATE selffix SET status='failed', result=%s "
                "WHERE task_id=%s AND status='fixing'",
                (("rework failed: " + str(reason)[:180]), task_id))
    conn.commit()
    n = cur.rowcount
    cur.close()
    return n > 0


def list_queue(conn, limit=10):
    _sql(conn)
    cur = conn.cursor()
    cur.execute("SELECT id, EXTRACT(EPOCH FROM ts), task_id, area, complaint, "
                "diff_stat, status FROM selffix "
                "WHERE status IN ('review','merged','settled','reverted','rejected','failed') "
                "ORDER BY (status='review') DESC, id DESC LIMIT %s", (limit,))
    rows = [{"id": r[0], "ts": float(r[1]), "task_id": r[2], "area": r[3],
             "complaint": (r[4] or "")[:200], "diff_stat": r[5], "status": r[6]}
            for r in cur.fetchall()]
    conn.commit()
    cur.close()
    return rows


def get_diff(conn, pid):
    cur = conn.cursor()
    cur.execute("SELECT diff FROM selffix WHERE id=%s", (pid,))
    row = cur.fetchone()
    conn.commit()
    cur.close()
    return row[0] if row else ""


def approve(conn, pid):
    """Merge the reviewed diff into the live repo: copy only whitelisted
    changed files, commit, record the revert handle + baseline metric."""
    _sql(conn)
    cur = conn.cursor()
    cur.execute("SELECT task_id, area, status FROM selffix WHERE id=%s", (pid,))
    row = cur.fetchone()
    if not row or row[2] != "review":
        cur.close()
        return {"success": False, "error": "not in review state"}
    tid, area = row[0], row[1]
    spec = AREAS[area]
    live_root = os.path.join(REPO, spec["live"])
    fixed = os.path.join(RESULTS_LOCAL, "results", tid)
    diff, files = _area_diff(area, tid)
    prefix_live = os.path.relpath(live_root, REPO)
    allowed = tuple(spec["include"])
    copied = []
    for f in files:
        rel_fixed = f.split(f"results/{tid}/", 1)[-1]
        if not rel_fixed.startswith(allowed):
            cur.execute("UPDATE selffix SET status='rejected', result=%s WHERE id=%s",
                        (f"merge refused: {rel_fixed} outside whitelist", pid))
            conn.commit(); cur.close()
            return {"success": False, "error": f"{rel_fixed} outside whitelist"}
        src = os.path.join(fixed, rel_fixed)
        dst = os.path.join(live_root, rel_fixed)
        if os.path.isdir(os.path.dirname(dst)):
            shutil.copy2(src, dst)
            copied.append(os.path.join(prefix_live, rel_fixed))
    if not copied:
        cur.close()
        return {"success": False, "error": "nothing to copy"}
    subprocess.run(["git", "-C", REPO, "add", *copied], check=True)
    msg = f"fix(selffix): {area} fix from {tid} (human-approved)"
    subprocess.run(["git", "-C", REPO, "commit", "-q", "-m", msg], check=True)
    sha = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    subprocess.run(["git", "-C", REPO, "push", "-q", "origin", "v0.5.11"],
                   capture_output=True)
    import sys as _sys
    _bd = os.environ.get("BASE_DIR", "/root/qwen/base")
    if _bd + "/retro" not in _sys.path:
        _sys.path.insert(0, _bd + "/retro")
    from applier import _baseline_metric
    mb = _baseline_metric(cur)
    cur.execute("UPDATE selffix SET status='merged', merge_commit=%s, "
                "metric_before=%s::jsonb, applied_at=now(), result=%s WHERE id=%s",
                (sha, json.dumps(mb, ensure_ascii=False),
                 f"merged {len(copied)} file(s)", pid))
    # close the parked task row, else the nightly observer reports it as stuck
    cur.execute("UPDATE task_registry SET status='done', status_reason=%s, "
                "activity = COALESCE(activity,'[]'::jsonb) || jsonb_build_array(%s::jsonb) "
                "WHERE task_id=%s",
                (f"self-fix merged as {sha[:8]}",
                 json.dumps({"event": "selffix_merged", "agent": "it-lead",
                             "detail": sha[:8], "ts": time.time()}), tid))
    conn.commit()
    cur.close()
    return {"success": True, "merged": len(copied), "commit": sha[:8]}


def reject(conn, pid, reason=""):
    _sql(conn)
    cur = conn.cursor()
    cur.execute("SELECT task_id FROM selffix WHERE id=%s AND status='review'", (pid,))
    row = cur.fetchone()
    cur.execute("UPDATE selffix SET status='rejected', result=%s "
                "WHERE id=%s AND status='review'",
                (("rejected: " + reason[:180]), pid))
    if row:
        cur.execute("UPDATE task_registry SET status='needs_revision', status_reason=%s, "
                    "activity = COALESCE(activity,'[]'::jsonb) || jsonb_build_array(%s::jsonb) "
                    "WHERE task_id=%s",
                    (("self-fix rejected: " + reason[:150]),
                     json.dumps({"event": "selffix_rejected", "agent": "it-lead",
                                 "detail": reason[:150], "ts": time.time()}), row[0]))
    conn.commit()
    n = cur.rowcount
    cur.close()
    return {"success": n > 0}
