import sys
sys.path.insert(0, "/root/qwen/base/qa-engineer-mcp-server")
from mcp_std_server.handlers.qa_engineer_handlers import QaEngineerServerHandlers

qa = QaEngineerServerHandlers.__new__(QaEngineerServerHandlers)

REPO_URL = "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git"

def test_validate_truncated_template():
    r = qa._validate_artifact({"task_id": "c2686db9-0060-4f8d-b9e5-ee8db973ac85"})
    assert not r["valid"] and "truncated" in r["errors"][0], r

def test_validate_good_html():
    r = qa._validate_artifact({"task_id": "607572f7-d636-46ba-8fef-602483ed7edc"})
    assert r["valid"], r

def test_smoke_html_game():
    r = qa._smoke_run({"task_id": "607572f7-d636-46ba-8fef-602483ed7edc"})
    assert r["passed"] and r["kind"] == "html", r

def test_smoke_truncated_fails():
    r = qa._smoke_run({"task_id": "c2686db9-0060-4f8d-b9e5-ee8db973ac85"})
    assert not r["passed"], r
