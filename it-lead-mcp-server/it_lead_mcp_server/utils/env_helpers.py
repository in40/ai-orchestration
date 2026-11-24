"""Env-dependent configuration helpers (no hardcoded infrastructure)."""
import os


def results_repo_url():
    """ssh-url of the results/artifacts repository. Required: a wrong silent
    default would push customer artifacts into someone else's repo."""
    url = (os.environ.get("MCP_GIT_REPO_URL") or "").strip()
    if not url:
        raise RuntimeError(
            "MCP_GIT_REPO_URL is not set - add the results repo url (ssh url, or a local path git can clone) "
            "repo to .env (e.g. ssh://user@host/home/user/mcp-results.git or /srv/mcp-results.git)")
    return url
