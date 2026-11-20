import sys
sys.path.insert(0, "/root/qwen/base/mcp-std-coder/mcp-vibe-coding-agent")
from dependencies.vibe_coder import _resolve_extension

HTML = "<!DOCTYPE html>\n<html><head><title>x</title></head><body></body></html>"

def test_envelope_compound_language():
    assert _resolve_extension("html5, javascript") == ".html"

def test_plain_languages():
    assert _resolve_extension("python") == ".py"
    assert _resolve_extension("JavaScript") == ".js"
    assert _resolve_extension("js") == ".js"
    assert _resolve_extension("golang") == ".go"
    assert _resolve_extension("yml") == ".yaml"

def test_declared_python_but_html_code():
    assert _resolve_extension("python", HTML) == ".html"

def test_unknown_falls_back_to_sniff():
    assert _resolve_extension("cobol", HTML) == ".html"

def test_unknown_no_sniff_default_py():
    assert _resolve_extension("cobol", "some text") == ".py"

def test_none_language():
    assert _resolve_extension(None) == ".py"
    assert _resolve_extension("") == ".py"
