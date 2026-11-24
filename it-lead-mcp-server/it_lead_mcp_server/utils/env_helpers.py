"""Env-dependent configuration helpers (no hardcoded infrastructure)."""
import os


def results_repo_url():
    """ssh-url of the results/artifacts repository. Required: a wrong silent
    default would push customer artifacts into someone else's repo."""
    url = (os.environ.get("MCP_GIT_REPO_URL") or "").strip()
    if not url:
        raise RuntimeError(
            "MCP_GIT_REPO_URL is not set - add the ssh url of the results "
            "repository to .env (e.g. ssh://user@host/home/user/mcp-results.git)")
    return url
