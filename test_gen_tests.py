import os, sys, tempfile
sys.path.insert(0, "/root/qwen/base/qa-engineer-mcp-server")
from mcp_std_server.handlers.qa_engineer_handlers import QaEngineerServerHandlers as Q

qa = Q.__new__(Q)

def make_tree(fails=False):
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "tests"))
    open(os.path.join(d, "tests", "test_ok.py"), "w").write(
        "def test_a():\n    assert 1 + 1 == 2\n")
    if fails:
        open(os.path.join(d, "tests", "test_bad.py"), "w").write(
            "def test_b():\n    assert 1 == 2\n")
    return d

def test_no_tests():
    d = tempfile.mkdtemp()
    r = qa._run_generated_tests(d, d, dict(os.environ))
    assert r == {"ran": False, "reason": "no tests generated"}, r

def test_passing():
    d = make_tree()
    r = qa._run_generated_tests(d, d, dict(os.environ))
    assert r["ran"] and r["passed"], r

def test_failing():
    d = make_tree(fails=True)
    r = qa._run_generated_tests(d, d, dict(os.environ))
    assert r["ran"] and not r["passed"] and "test_b" in r["output"], r
