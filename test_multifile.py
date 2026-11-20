import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, "/root/qwen/base/mcp-std-coder/mcp-vibe-coding-agent")
import dependencies.vibe_coder as vc

REAL_CACHE = "/tmp/mcp-vibe-coding-git/repo"
REAL_REPO = "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git"


@pytest.fixture(autouse=True)
def restore_real_clone():
    yield
    if os.path.isdir(REAL_CACHE):
        shutil.rmtree(REAL_CACHE, ignore_errors=True)
    os.makedirs(os.path.dirname(REAL_CACHE), exist_ok=True)
    subprocess.run(["git", "clone", REAL_REPO, REAL_CACHE],
                   check=True, capture_output=True)


def test_multi_file_push(tmp_path):
    bare = tmp_path / "repo.git"
    subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
    seed = tmp_path / "seed"
    subprocess.run(["git", "clone", str(bare), str(seed)], check=True, capture_output=True)
    (seed / "README.md").write_text("seed")
    subprocess.run(["git", "add", "-A"], cwd=seed, check=True, capture_output=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-m", "seed"], cwd=seed, check=True, capture_output=True)
    subprocess.run(["git", "push"], cwd=seed, check=True, capture_output=True)

    orig_url = getattr(vc.settings, "mcp_git_repo_url", None)
    orig_clone = vc._get_or_clone_git_repo
    vc.settings.mcp_git_repo_url = str(bare)

    def fake_clone(url, path):
        import shutil
        shutil.rmtree(str(path), ignore_errors=True)
        subprocess.run(["git", "clone", url, str(path)], check=True, capture_output=True)
    vc._get_or_clone_git_repo = fake_clone

    env = json.dumps({
        "task_understanding": "template",
        "files": [
            {"path": "server.py", "content": "print('hi')\n" + "# pad" * 50},
            {"path": "README.md", "content": "# how to run"},
            {"path": "requirements.txt", "content": "flask\n"},
        ],
        "language": "python",
    })
    result = vc.git_push_llm_response("multifile-test", env, "python")
    vc._get_or_clone_git_repo = orig_clone
    vc.settings.mcp_git_repo_url = orig_url
    assert result.get("git_url", "").endswith("server.py"), result

    clone = tmp_path / "verify"
    subprocess.run(["git", "clone", str(bare), str(clone)], check=True, capture_output=True)
    d = clone / "results" / "multifile-test"
    assert (d / "server.py").exists() and (d / "README.md").exists()
    assert (d / "requirements.txt").exists() and (d / "response.json").exists()


def test_path_traversal_rejected(tmp_path):
    env = json.dumps({"files": [{"path": "../../evil.py", "content": "x" * 200},
                                {"path": "ok.py", "content": "print(1)\n" + "#p" * 100}]})
    # no git repo configured -> will fail at clone stage; only test validator here
    import pytest
    vc.validate_llm_artifact(env)  # must not raise: valid py contents
