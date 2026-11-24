"""Products: permanent homes for results the requestor chose to keep.

A product has a bare mirror repo on the artifact host (.187, same ssh access
as mcp-results) and, only after an explicit human action, a GitHub repo under
github.com/in40. Nothing here is ever called from a task pipeline: publishing
requires confirm='publish' (UI button / bell action by a human).

Ported from the team's prototype (task-1795202524381) onto platform rails:
postgres storage, mirrors on .187 via ssh, PAT from /root/qwen/base/.env.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

RESULTS_LOCAL = "/tmp/mcp-vibe-coding-git/repo"
SSH_TARGET = os.environ.get("PROJECTS_SSH") or None
PROJECTS_DIR = os.environ.get("PROJECTS_DIR") or None
GITHUB_OWNER = os.environ.get("GITHUB_OWNER", "in40")
GITHUB_API = "https://api.github.com"
PAT_FILE = os.environ.get("BASE_DIR", "/root/qwen/base") + "/.env"
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
GIT_ID = ["-c", "user.name=it-lead", "-c", "user.email=it-lead@pipeline.local"]

_pat_cache = None


def get_pat():
    global _pat_cache
    if _pat_cache is not None:
        return _pat_cache or None
    tok = os.environ.get("GITHUB_PAT", "").strip()
    if not tok and os.path.isfile(PAT_FILE):
        for line in open(PAT_FILE, errors="replace"):
            line = line.strip()
            if line and not line.startswith("#") and line.startswith("GITHUB_PAT="):
                tok = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    _pat_cache = tok
    return tok or None


def redact(text):
    text = str(text or "")
    pat = _pat_cache
    if pat:
        text = text.replace(pat, "***PAT***")
    text = re.sub(r"x-access-token:[^@\s/]+@", "x-access-token:***@", text)
    text = re.sub(r"github_pat_[A-Za-z0-9_]{20,}", "***PAT***", text)
    text = re.sub(r"ghp_[A-Za-z0-9]{36}", "***PAT***", text)
    return text


def _sql(conn):
    conn.cursor().execute(
        "CREATE TABLE IF NOT EXISTS products("
        "id serial PRIMARY KEY, name text UNIQUE, description text, "
        "mirror_url text, github_url text, visibility text DEFAULT 'private', "
        "status text DEFAULT 'draft', created_at timestamptz DEFAULT now(), "
        "published_at timestamptz, result text)")
    # upstream provenance: where an imported product came from, and whether we
    # can ever push back to it (third-party repos: pull-only, read-only)
    cur = conn.cursor()
    cur.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS upstream_url text")
    cur.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS "
                "upstream_readonly boolean NOT NULL DEFAULT false")
    conn.commit()


def _run(args, timeout=180, cwd=None):
    return subprocess.run(args, capture_output=True, text=True,
                          timeout=timeout, cwd=cwd)


def _ssh_git(args, timeout=180):
    if not SSH_TARGET:
        raise RuntimeError("products mirror not configured: set PROJECTS_SSH "
                           "(user@host) and PROJECTS_DIR in .env")
    return _run(["ssh", SSH_TARGET, "git", *args], timeout=timeout)


def _mirror_url(name):
    if not SSH_TARGET or not PROJECTS_DIR:
        raise RuntimeError("products mirror not configured: set PROJECTS_SSH "
                           "(user@host) and PROJECTS_DIR in .env")
    return f"ssh://{SSH_TARGET}{PROJECTS_DIR}/{name}.git"


def _mirror_has_commits(mirror_url):
    r = _run(["git", "ls-remote", "--heads", mirror_url], timeout=60)
    return r.returncode == 0 and bool(r.stdout.strip())


def list_products(conn):
    _sql(conn)
    cur = conn.cursor()
    cur.execute("SELECT id, name, description, mirror_url, github_url, "
                "visibility, status, EXTRACT(EPOCH FROM created_at), result, "
                "upstream_url, upstream_readonly "
                "FROM products ORDER BY id DESC")
    out = [{"id": r[0], "name": r[1], "description": r[2] or "",
            "mirror_url": r[3], "github_url": r[4], "visibility": r[5],
            "status": r[6], "created_at": float(r[7]), "result": r[8] or "",
            "upstream_url": r[9] or "", "upstream_readonly": bool(r[10])}
           for r in cur.fetchall()]
    conn.commit()
    cur.close()
    return out


def import_product(conn, name, description="", source_url="", seed_task_id="",
                   adopt_existing=False, readonly=False):
    _sql(conn)
    name = (name or "").strip()
    if not NAME_RE.match(name):
        return {"success": False,
                "error": f"name must match {NAME_RE.pattern}"}
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM products WHERE name=%s", (name,))
    if cur.fetchone() and not adopt_existing:
        cur.close()
        return {"success": False, "error": f"product {name!r} already exists"}

    mirror = _mirror_url(name)
    origin = "empty"
    if not adopt_existing or not _mirror_has_commits(mirror):
        init = _ssh_git(["init", "--bare", "-b", "main",
                         f"{PROJECTS_DIR}/{name}.git"])
        if init.returncode != 0:
            cur.close()
            return {"success": False, "error": redact(init.stderr)[:200]}
        if source_url:
            tmp = tempfile.mkdtemp(prefix="prod-import-")
            try:
                c = _run(["git", "clone", "--mirror", "--", source_url,
                          os.path.join(tmp, "m")], timeout=600)
                if c.returncode != 0:
                    return {"success": False, "error": redact(c.stderr)[:200]}
                p = _run(["git", "-C", os.path.join(tmp, "m"), "push", "--mirror",
                          mirror], timeout=600)
                if p.returncode != 0:
                    return {"success": False, "error": redact(p.stderr)[:200]}
                origin = f"source_url={source_url}"
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        elif seed_task_id:
            seed = os.path.join(RESULTS_LOCAL, "results", seed_task_id)
            if not os.path.isdir(seed):
                cur.close()
                return {"success": False,
                        "error": f"results/{seed_task_id} not found locally"}
            tmp = tempfile.mkdtemp(prefix="prod-seed-")
            try:
                work = os.path.join(tmp, "w")
                shutil.copytree(seed, work,
                                ignore=shutil.ignore_patterns(".git", "docs"))
                for cmd in (["init", "-b", "main"], ["add", "-A"],
                            GIT_ID + ["commit", "-m",
                                      f"seed {name} from results/{seed_task_id}"],
                            ["push", "--", mirror, "main:main"]):
                    r = _run(["git", *cmd], cwd=work)
                    if r.returncode != 0:
                        return {"success": False, "error": redact(r.stderr)[:200]}
                origin = f"seed_task_id={seed_task_id}"
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
    else:
        origin = "adopted existing mirror"

    cur.execute(
        "INSERT INTO products(name, description, mirror_url, status, "
        "upstream_url, upstream_readonly) "
        "VALUES (%s,%s,%s,'draft',%s,%s) ON CONFLICT (name) DO UPDATE SET "
        "description=EXCLUDED.description RETURNING id",
        (name, description, mirror, source_url or None, bool(readonly)))
    pid = cur.fetchone()[0]
    cur.execute("UPDATE products SET result=%s WHERE id=%s",
                (f"imported: {origin}"[:400], pid))
    conn.commit()
    cur.close()
    return {"success": True, "id": pid, "name": name, "mirror_url": mirror,
            "mirror_ready": _mirror_has_commits(mirror), "origin": origin}


def _github_create_repo(pat, repo, private, description):
    body = json.dumps({"name": repo, "description": description,
                       "private": bool(private), "auto_init": False}).encode()
    req = urllib.request.Request(
        GITHUB_API + "/user/repos", data=body, method="POST",
        headers={"Authorization": f"Bearer {pat}",
                 "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json",
                 "User-Agent": "it-lead-products"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode() or "{}")
        except Exception:
            payload = {}
        return e.code, payload


def publish_product(conn, product_id, github_repo, private=True, confirm="",
                    force=False):
    if confirm != "publish":
        return {"success": False,
                "error": "publish requires explicit human confirm='publish'"}
    _sql(conn)
    cur = conn.cursor()
    cur.execute("SELECT name, description, mirror_url, status, github_url "
                "FROM products WHERE id=%s", (product_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        return {"success": False, "error": "product not found"}
    name, desc, mirror, status, existing = row
    republish = bool(existing) and status == "published"
    if not _mirror_has_commits(mirror):
        cur.close()
        return {"success": False, "error": "mirror is empty — nothing to publish"}
    pat = get_pat()
    if not pat:
        cur.close()
        return {"success": False, "error": "GITHUB_PAT not configured"}

    if republish:
        m = re.search(r"github\.com/([^/]+)/([^/.]+)", existing)
        if not m:
            cur.close()
            return {"success": False, "error": f"bad github_url: {existing}"}
        owner, repo = m.group(1), m.group(2)
    else:
        github_repo = (github_repo or name).strip().removesuffix(".git")
        if "/" in github_repo:
            owner, _, repo = github_repo.partition("/")
        else:
            owner, repo = GITHUB_OWNER, github_repo
        code, payload = _github_create_repo(pat, repo, private,
                                            desc or f"product {repo}")
        if code == 422 and "already exists" in json.dumps(payload):
            pass  # reuse existing repo
        elif code not in (200, 201):
            cur.close()
            return {"success": False,
                    "error": f"github create failed {code}: {redact(json.dumps(payload))[:200]}"}

    tmp = tempfile.mkdtemp(prefix="prod-publish-")
    try:
        work = os.path.join(tmp, "w")
        c = _run(["git", "clone", "--", mirror, work], timeout=300)
        if c.returncode != 0:
            return {"success": False, "error": redact(c.stderr)[:200]}
        auth_url = f"https://x-access-token:{pat}@github.com/{owner}/{repo}.git"
        _run(["git", "-C", work, "remote", "add", "gh", auth_url])
        push_cmd = ["git", "-C", work, "push"] + (["--force"] if force else []) + ["gh", "HEAD:main"]
        p = _run(push_cmd, timeout=600)
        if p.returncode != 0:
            msg = redact(p.stderr)[:300]
            if not force and ("rejected" in msg or "fetch first" in msg):
                msg += (" — удалённый репозиторий содержит другую историю; "
                        "повторите с force=true, чтобы перезаписать")
            return {"success": False, "error": msg}
        url = f"https://github.com/{owner}/{repo}"
        cur.execute("UPDATE products SET github_url=%s, status='published', "
                    "visibility=%s, published_at=now(), result=%s WHERE id=%s",
                    (url, "private" if private else "public",
                     f"published to {url}", product_id))
        conn.commit()
        cur.close()
        return {"success": True, "github_url": url}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- upstream sync
# A mirror can have an upstream (imported source_url, or our own github_url).
# Sync is always human-triggered: check first (read-only diagnosis), then pull
# with an explicit mode. Every pull tags the mirror pre-sync-<ts> so any
# mistake is one rollback away. read-only upstreams are pull-only by design —
# nothing here ever pushes to upstream.

def _load_product(cur, product_id):
    cur.execute("SELECT name, mirror_url, upstream_url, github_url, "
                "upstream_readonly FROM products WHERE id=%s", (product_id,))
    return cur.fetchone()


def _upstream_branch(up_url):
    r = _run(["git", "ls-remote", "--symref", up_url, "HEAD"], timeout=60)
    m = re.search(r"refs/heads/(\S+)", r.stdout or "")
    return m.group(1) if m else "main"


def _prep_clone(mirror, up):
    """Clone mirror + add 'up' remote; returns (work, branch) or (None, err)."""
    tmp = tempfile.mkdtemp(prefix="prod-upsync-")
    work = os.path.join(tmp, "w")
    c = _run(["git", "clone", "--", mirror, work], timeout=600)
    if c.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        return None, redact(c.stderr)[:200]
    _run(["git", "-C", work, "remote", "add", "up", up], timeout=60)
    br = _upstream_branch(up)
    f = _run(["git", "-C", work, "fetch", "-q", "up", br], timeout=600)
    if f.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        return None, f"upstream fetch failed: {redact(f.stderr)[:150]}"
    return (work, br), None


def check_upstream(conn, product_id):
    """Read-only diagnosis: how do mirror and upstream differ?"""
    _sql(conn)
    cur = conn.cursor()
    row = _load_product(cur, product_id)
    conn.commit()
    cur.close()
    if not row:
        return {"success": False, "error": f"product {product_id} not found"}
    name, mirror, up_url, gh_url, ro = row
    up = up_url or gh_url or ""
    if not up:
        return {"success": False,
                "error": "нет upstream: импортируйте с source_url или опубликуйте"}
    prepped, err = _prep_clone(mirror, up)
    if err:
        return {"success": False, "error": err}
    work, br = prepped
    try:
        lr = _run(["git", "-C", work, "rev-list", "--left-right", "--count",
                   f"HEAD...up/{br}"], timeout=60)
        ahead, behind = (int(x) for x in lr.stdout.split())
        verdict = ("up_to_date" if not (ahead or behind) else
                   "behind" if behind and not ahead else
                   "ahead_only" if ahead and not behind else "diverged")
        up_commits = _run(["git", "-C", work, "log", "--oneline", "-n", "30",
                           f"HEAD..up/{br}"], timeout=60).stdout.splitlines()
        our_commits = _run(["git", "-C", work, "log", "--oneline", "-n", "30",
                            f"up/{br}..HEAD"], timeout=60).stdout.splitlines()
        diffstat = _run(["git", "-C", work, "diff", "--stat", "HEAD",
                         f"up/{br}"], timeout=120).stdout
        tags = _run(["git", "-C", work, "tag", "-l", "pre-sync-*",
                     "--sort=-refname"], timeout=60).stdout.splitlines()
        return {"success": True, "name": name, "upstream": up, "branch": br,
                "readonly": bool(ro), "verdict": verdict, "ahead": ahead,
                "behind": behind, "upstream_commits": up_commits,
                "our_commits": our_commits, "diffstat": diffstat[-3000:],
                "tags": tags[:10]}
    finally:
        shutil.rmtree(os.path.dirname(work), ignore_errors=True)


def pull_upstream(conn, product_id, mode="ff", confirm=""):
    """Apply upstream into the mirror. Modes: ff | merge | rebase | overwrite.
    overwrite (throw away our commits) requires confirm == product name.
    Always tags the mirror pre-sync-<ts> before touching main."""
    if mode not in ("ff", "merge", "rebase", "overwrite"):
        return {"success": False, "error": f"bad mode {mode!r}"}
    _sql(conn)
    cur = conn.cursor()
    row = _load_product(cur, product_id)
    conn.commit()
    if not row:
        cur.close()
        return {"success": False, "error": f"product {product_id} not found"}
    name, mirror, up_url, gh_url, ro = row
    up = up_url or gh_url or ""
    if not up:
        cur.close()
        return {"success": False, "error": "нет upstream у продукта"}
    if mode == "overwrite" and confirm != name:
        cur.close()
        return {"success": False,
                "error": f"overwrite теряет наши коммиты — введите имя продукта "
                         f"({name!r}) для подтверждения"}
    prepped, err = _prep_clone(mirror, up)
    if err:
        cur.close()
        return {"success": False, "error": err}
    work, br = prepped
    try:
        lr = _run(["git", "-C", work, "rev-list", "--left-right", "--count",
                   f"HEAD...up/{br}"], timeout=60)
        ahead, behind = (int(x) for x in lr.stdout.split())
        if behind == 0:
            return {"success": True, "detail": "уже актуально: новых коммитов "
                                               "в upstream нет"}
        if mode == "ff" and ahead > 0:
            return {"success": False,
                    "error": f"расхождение (наши {ahead}, их {behind}): "
                             "выберите merge, rebase или overwrite"}
        # insurance tag on the mirror BEFORE any change
        tag = f"pre-sync-{int(time.time())}"
        t = _run(["git", "-C", work, "tag", tag], timeout=60)
        _run(["git", "-C", work, "push", "--quiet", "origin", f"refs/tags/{tag}"],
             timeout=120)
        if t.returncode != 0:
            return {"success": False, "error": "не удалось поставить pre-sync тег"}

        def conflicts():
            return _run(["git", "-C", work, "diff", "--name-only",
                         "--diff-filter=U"], timeout=60).stdout.splitlines()

        if mode == "overwrite":
            p = _run(["git", "-C", work, "push", "--force", "origin",
                      f"up/{br}:main"], timeout=600)
            if p.returncode != 0:
                return {"success": False, "error": redact(p.stderr)[:200]}
            detail = f"overwrite: main = up/{br} ({behind} чужих коммитов принято как есть)"
        else:
            if mode == "ff":
                m = _run(["git", "-C", work, "merge", "--ff-only", f"up/{br}"],
                         timeout=300)
            elif mode == "merge":
                m = _run(["git", "-C", work, *GIT_ID, "merge", "--no-edit",
                          f"up/{br}"], timeout=300)
                if m.returncode != 0:
                    cf = conflicts()
                    _run(["git", "-C", work, "merge", "--abort"], timeout=60)
                    return {"success": False, "conflicts": cf,
                            "error": "конфликты merge — ничего не изменено; "
                                     "см. список файлов"}
            else:  # rebase
                m = _run(["git", "-C", work, *GIT_ID, "rebase", f"up/{br}"],
                         timeout=600)
                if m.returncode != 0:
                    cf = conflicts()
                    _run(["git", "-C", work, "rebase", "--abort"], timeout=60)
                    return {"success": False, "conflicts": cf,
                            "error": "конфликты rebase — ничего не изменено; "
                                     "см. список файлов"}
            if m.returncode != 0:
                return {"success": False, "error": redact(m.stderr)[:200]}
            push = ["git", "-C", work, "push"]
            if mode == "rebase":
                push.append("--force-with-lease")
            p = _run(push + ["origin", "HEAD:main"], timeout=600)
            if p.returncode != 0:
                return {"success": False, "error": redact(p.stderr)[:200]}
            detail = f"{mode}: подтянуто {behind} коммитов из up/{br}"
        cur.execute("UPDATE products SET result=%s WHERE id=%s",
                    (f"upstream sync ({mode}) {time.strftime('%Y-%m-%d %H:%M')}, "
                     f"откат: {tag}", product_id))
        conn.commit()
        cur.close()
        return {"success": True, "detail": detail, "rollback_tag": tag}
    finally:
        shutil.rmtree(os.path.dirname(work), ignore_errors=True)


def rollback_upstream(conn, product_id, tag):
    """Reset mirror main back to a pre-sync tag (undo a bad pull)."""
    if not re.match(r"^pre-sync-\d+$", tag or ""):
        return {"success": False, "error": "катиться можно только на pre-sync-* тег"}
    _sql(conn)
    cur = conn.cursor()
    row = _load_product(cur, product_id)
    conn.commit()
    cur.close()
    if not row:
        return {"success": False, "error": f"product {product_id} not found"}
    mirror = row[1]
    tmp = tempfile.mkdtemp(prefix="prod-rollback-")
    try:
        work = os.path.join(tmp, "w")
        c = _run(["git", "clone", "--", mirror, work], timeout=600)
        if c.returncode != 0:
            return {"success": False, "error": redact(c.stderr)[:200]}
        v = _run(["git", "-C", work, "rev-parse", "--verify", f"refs/tags/{tag}"],
                 timeout=60)
        if v.returncode != 0:
            return {"success": False, "error": f"тег {tag} не найден в зеркале"}
        p = _run(["git", "-C", work, "push", "--force", "origin",
                  f"{tag}^{{}}:main"], timeout=300)
        if p.returncode != 0:
            return {"success": False, "error": redact(p.stderr)[:200]}
        cur2 = conn.cursor()
        cur2.execute("UPDATE products SET result=%s WHERE id=%s",
                     (f"rollback к {tag}", product_id))
        conn.commit()
        cur2.close()
        return {"success": True, "detail": f"main зеркала откатан к {tag}"}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
