"""DB compatibility layer: PostgreSQL when reachable, SQLite (JSON1) fallback.

Exposes a psycopg2-shaped API (connect() -> connection with .cursor() using
%s placeholders) so existing SQL keeps working. The few jsonb idioms this
codebase uses are translated to SQLite JSON1 functions:

    COALESCE(col,'[]'::jsonb) || %s::jsonb   -> jsonb_append(col, ?)
    COALESCE(col,'{}'::jsonb) || %s::jsonb   -> jsonb_merge(col, ?)
    col || %s::jsonb                          -> jsonb_merge(col, ?)
    jsonb_set(COALESCE(col,'{}'::jsonb), '{k}', %s::jsonb) -> jsonb_setx(col,'$.k',?)
    col::jsonb ->> 'k' / col ->> 'k'          -> json_extract(col, '$.k')
    col::jsonb ->  'k'                        -> json_extract(col, '$.k')
    jsonb_array_elements(x)                    -> json_each(x)
    ::jsonb                                    -> (stripped)

JSON columns are TEXT in sqlite; callers already tolerate str-or-dict.
Selection: USE_POSTGRES != false AND psycopg2 importable AND connect works,
otherwise sqlite at SQLITE_PATH (default $BASE_DIR/data/<database>.db).
"""
import json
import os
import re
import sqlite3


def _fn_append(base, item):
    try:
        arr = json.loads(base) if base else []
    except (TypeError, ValueError):
        arr = []
    if not isinstance(arr, list):
        arr = []
    try:
        it = json.loads(item)
    except (TypeError, ValueError):
        it = item
    if isinstance(it, list):
        arr.extend(it)
    else:
        arr.append(it)
    return json.dumps(arr)


def _fn_merge(base, patch):
    try:
        d = json.loads(base) if base else {}
    except (TypeError, ValueError):
        d = {}
    if not isinstance(d, dict):
        d = {}  # corrupted column value: start clean rather than fail the UPDATE
    try:
        p = json.loads(patch) if isinstance(patch, str) else patch
    except (TypeError, ValueError):
        p = None
    if isinstance(p, dict):
        d.update(p)
        return json.dumps(d)
    if isinstance(p, list):
        return json.dumps(p)
    return json.dumps(d)


def _fn_setx(doc, path, val):
    d = json.loads(doc) if doc else {}
    cur = d
    keys = [k for k in path.lstrip("$").split(".") if k]
    for k in keys[:-1]:
        cur = cur.setdefault(k, {})
    try:
        cur[keys[-1]] = json.loads(val)
    except (TypeError, ValueError):
        cur[keys[-1]] = val
    return json.dumps(d)


def _setx_repl(m):
    key = m.group(2).strip("{}")
    return "jsonb_setx(%s, '$.%s', ?)" % (m.group(1), key)


class _Cursor:
    """Translates the codebase's postgres SQL idioms to sqlite on the fly."""

    _RE = [
        (re.compile(r"jsonb_set\(\s*COALESCE\((\w+),\s*'\{\}'::jsonb\),\s*'(\{[^']*\})',\s*%s::jsonb\s*(?:,\s*true)?\s*\)"),
         _setx_repl),
        (re.compile(r"jsonb_set\(\s*(\w+),\s*'(\{[^']*\})',\s*%s::jsonb\s*(?:,\s*true)?\s*\)"),
         _setx_repl),
        # COALESCE variants, tolerant of casts on either side:
        # COALESCE(col,'[]'::jsonb) || %s::jsonb / COALESCE(col::jsonb,'[]') || %s::jsonb
        (re.compile(r"COALESCE\((\w+)(?:::jsonb)?,\s*'\[\]'(?:::jsonb)?\)\s*\|\|\s*%s::jsonb"),
         lambda m: f"jsonb_append({m.group(1)}, ?)"),
        (re.compile(r"COALESCE\((\w+)(?:::jsonb)?,\s*'\{\}'(?:::jsonb)?\)\s*\|\|\s*%s::jsonb"),
         lambda m: f"jsonb_merge({m.group(1)}, ?)"),
        (re.compile(r"\b(\w+)(?:::jsonb)?\s*\|\|\s*%s::jsonb"),
         lambda m: f"jsonb_merge({m.group(1)}, ?)"),
        (re.compile(r"jsonb_array_elements\(([^)]+)\)"),
         lambda m: f"json_each({m.group(1)})"),
        (re.compile(r"\b(\w+)(?:::jsonb)? *->>? *'(\w+)'"),
         lambda m: f"json_extract({m.group(1)}, '$.{m.group(2)}')"),
        (re.compile(r"\b(\w+)(?:::jsonb)? *-> *'(\w+)'"),
         lambda m: f"json_extract({m.group(1)}, '$.{m.group(2)}')"),
        (re.compile(r"::jsonb"), lambda m: ""),
        (re.compile(r"\bSERIAL PRIMARY KEY\b"), lambda m: "INTEGER PRIMARY KEY AUTOINCREMENT"),
        (re.compile(r"\bVARCHAR\(\d+\)"), lambda m: "TEXT"),
        (re.compile(r"\bTIMESTAMP\b"), lambda m: "TEXT"),
        (re.compile(r"\bDOUBLE PRECISION\b"), lambda m: "REAL"),
        (re.compile(r"\bJSONB\b"), lambda m: "TEXT"),
        (re.compile(r"%s"), lambda m: "?"),
    ]

    def __init__(self, cur):
        self._c = cur

    def _t(self, sql):
        for rx, rep in _Cursor._RE:
            sql = rx.sub(rep, sql)
        # tripwire: a missed jsonb concat would silently TEXT-concatenate
        # ('}{') and corrupt the column in sqlite - fail loud instead
        if re.search(r"\|\|\s*\?", sql):
            raise ValueError("db_compat: untranslated jsonb concat in SQL: "
                             + " ".join(sql.split())[:200])
        return sql

    def execute(self, sql, params=None):
        return self._c.execute(self._t(sql), tuple(params) if params else ())

    def executemany(self, sql, seq):
        return self._c.executemany(self._t(sql), [tuple(p) for p in seq])

    def __getattr__(self, name):
        return getattr(self._c, name)


class _DictCursor(_Cursor):
    """Mimics psycopg2 RealDictCursor: rows come back as dicts."""

    def fetchone(self):
        r = self._c.fetchone()
        if r is None:
            return None
        return {d[0]: v for d, v in zip(self._c.description, r)}

    def fetchall(self):
        cols = [d[0] for d in self._c.description]
        return [{k: v for k, v in zip(cols, r)} for r in self._c.fetchall()]


class SqliteConn:
    """psycopg2-shaped wrapper over sqlite3 (WAL, busy_timeout, json funcs)."""

    def __init__(self, path):
        self._c = sqlite3.connect(path, timeout=30, check_same_thread=False)
        # autocommit (isolation_level=None): every statement commits instantly,
        # so a thread that reads without commit can never hold a write lock -
        # explicit .commit() calls elsewhere become harmless no-ops
        self._c.isolation_level = None
        self._c.execute("PRAGMA journal_mode=WAL")
        self._c.execute("PRAGMA busy_timeout=30000")
        self._c.create_function("jsonb_append", 2, _fn_append)
        self._c.create_function("jsonb_merge", 2, _fn_merge)
        self._c.create_function("jsonb_setx", 3, _fn_setx)
        self.backend = "sqlite"

    def cursor(self, cursor_factory=None, **kw):
        cur = _DictCursor(self._c.cursor()) if cursor_factory is not None else _Cursor(self._c.cursor())
        return cur

    def commit(self):
        self._c.commit()

    def rollback(self):
        self._c.rollback()

    def close(self):
        self._c.close()


def connect(host="localhost", port=5432, database="mcp_registry",
            user="postgres", password="***", verbose=True):
    """Returns (connection, backend) - backend is 'postgres' or 'sqlite'."""
    if os.environ.get("USE_POSTGRES", "true").lower() not in ("false", "0", "no"):
        try:
            import psycopg2
            conn = psycopg2.connect(host=host, port=port,
                                database=database, user=user, password=password)
            return conn, "postgres"
        except Exception as e:
            if verbose:
                print(f"[db_compat] postgres unavailable ({type(e).__name__}: {e}); using sqlite fallback")
    path = os.environ.get("SQLITE_PATH") or os.path.join(
        os.environ.get("BASE_DIR", "."), "data", f"{database}.db")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if verbose:
        print(f"[db_compat] sqlite database: {path}")
    return SqliteConn(path), "sqlite"
