"""Shared DB access for the retro suite: postgres via env credentials,
sqlite fallback through db_compat (same facade as the services).

BASE_DIR (from systemd EnvironmentFile / .env) locates both the it-lead
package (db_compat lives there) and the .env with POSTGRES_PASSWORD.
"""
import os
import sys

BASE = os.environ.get("BASE_DIR", "/root/qwen/base")
sys.path.insert(0, os.path.join(BASE, "it-lead-mcp-server"))
from it_lead_mcp_server.utils import db_compat  # noqa: E402


def _db_params():
    """Credentials from env or $BASE_DIR/.env (never hardcoded)."""
    pw = os.environ.get("POSTGRES_PASSWORD")
    if not pw:
        try:
            for line in open(os.path.join(BASE, ".env")):
                if line.startswith("POSTGRES_PASSWORD="):
                    pw = line.split("=", 1)[1].strip()
                    break
        except OSError:
            pass
    return dict(host="127.0.0.1", database="mcp_registry", user="postgres",
                password=pw or os.environ.get("PGPASSWORD", ""))


DB = _db_params()


def connect(**kw):
    """Returns (connection, backend) - psycopg2 or the sqlite facade.
    Accepts (and overrides with) the legacy psycopg2.connect(**DB) kwargs."""
    return db_compat.connect(**{**DB, **kw})
