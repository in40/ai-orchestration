import sys
sys.path.insert(0, "/root/qwen/base/mcp-std-coder/mcp-vibe-coding-agent")
from dependencies.vibe_coder import validate_llm_artifact
import pytest

REPO = "/tmp/mcp-vibe-coding-git/repo/results"

def test_truncated_envelope_flappy1():
    raw = open(f"{REPO}/b1996a36-0b41-490d-add4-a680c5e0c31e/result.js").read()
    with pytest.raises(ValueError, match="invalid_artifact"):
        validate_llm_artifact(raw)

def test_truncated_envelope_template():
    raw = open(f"{REPO}/c2686db9-0060-4f8d-b9e5-ee8db973ac85/result.py").read()
    with pytest.raises(ValueError, match="invalid_artifact"):
        validate_llm_artifact(raw)

def test_complete_html_game():
    raw = open(f"{REPO}/607572f7-d636-46ba-8fef-602483ed7edc/result.html").read()
    validate_llm_artifact(raw)

def test_valid_python_envelope():
    import json
    code = "def hello():\n    return 'x' * 200\n" + "# pad" * 50
    env = json.dumps({"code": code, "language": "python"})
    validate_llm_artifact(env)

def test_broken_python_envelope():
    import json
    env = json.dumps({"code": "def broken(:\n" + "x" * 200, "language": "python"})
    with pytest.raises(ValueError, match="syntax error"):
        validate_llm_artifact(env)

def test_truncated_html():
    raw = "<!DOCTYPE html><html><body>" + "x" * 200
    with pytest.raises(ValueError, match="closing tag"):
        validate_llm_artifact(raw)

def test_empty():
    with pytest.raises(ValueError):
        validate_llm_artifact("")
