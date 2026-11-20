import sys
sys.path.insert(0, "/root/qwen/base/it-lead-mcp-server")
sys.path.insert(0, "/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server")
from utils.task_assignment import TaskAssignmentManager as T

parse = T._parse_manifest_lines

def test_jsonl_clean():
    raw = '{"path": "a.py", "spec": "entry"}\n{"path": "README.md", "spec": "docs"}'
    assert parse(raw) == [{"path": "a.py", "spec": "entry"}, {"path": "README.md", "spec": "docs"}]

def test_skips_bad_lines_and_fences():
    raw = '```json\n{"path": "a.py", "spec": "x"}\n{broken line!!\n{"path": "b.py", "spec": "y"},'
    out = parse(raw)
    assert [e["path"] for e in out] == ["a.py", "b.py"]

def test_legacy_whole_json():
    raw = 'here you go:\n{"file_manifest": [{"path": "m.py", "spec": "s"}]}\nhope it helps'
    assert parse(raw) == [{"path": "m.py", "spec": "s"}]

def test_garbage_returns_none():
    assert parse("no json here at all") is None

def test_spec_with_quotes_survives_line_split():
    raw = '{"path": "a.py", "spec": "uses \\"quotes\\" inside"}'
    assert parse(raw)[0]["spec"] == 'uses "quotes" inside'
