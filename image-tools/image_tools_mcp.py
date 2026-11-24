#!/usr/bin/env python3
"""image-tools: stdio MCP facade for flux2-klein-4b on halogen-flash-server.

Exposes generate_image / edit_image to opencode agents WITHOUT letting them
touch the network themselves (agents keep curl/wget denied). PNGs are written
into the session workspace (the server process runs with cwd = workspace).
Deterministic by default: seed derived from prompt+filename when not given,
and always echoed back so the artifact README can record provenance.

Stdlib only; edits go through curl because the endpoint's multipart parser
only accepts what curl -F produces (verified against the live server).
"""
import base64
import json
import os
import subprocess
import sys
import urllib.request
import zlib

BASE = os.environ.get("IMAGE_API_BASE", "")


def _base():
    if not BASE:
        raise RuntimeError(
            "IMAGE_API_BASE is not set - add the image-generation API base "
            "url to .env (e.g. http://host:8081) to enable image tools")
    return BASE
MODEL = os.environ.get("IMAGE_API_MODEL", "flux2-klein-4b")

TOOLS = [
    {
        "name": "generate_image",
        "description": "Generate a PNG from a text prompt (flux2-klein-4b). Writes it to "
                       "the workspace-relative filename and returns path/bytes/size/seed. "
                       "Record prompt+seed in README under 'Generated assets'.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
                "filename": {"type": "string", "description": "workspace-relative .png path"},
                "size": {"type": "string",
                         "description": "WxH, default 512x512; 256x256 is NOT supported"},
                "seed": {"type": "integer",
                         "description": "optional; deterministic default from prompt+filename"},
            },
            "required": ["prompt", "filename"],
        },
    },
    {
        "name": "edit_image",
        "description": "Edit an existing workspace image per a text instruction "
                       "(flux2-klein-4b). Input is center-cropped to a square. "
                       "Returns output path and seed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "image_path": {"type": "string", "description": "workspace-relative input image"},
                "prompt": {"type": "string"},
                "filename": {"type": "string", "description": "output .png path, default <input>_edited.png"},
                "seed": {"type": "integer"},
            },
            "required": ["image_path", "prompt"],
        },
    },
]


def _safe(rel):
    p = os.path.normpath(str(rel))
    if os.path.isabs(p) or p.startswith("..") or not p.lower().endswith(".png"):
        raise ValueError("path must be a workspace-relative .png")
    return p


def _seed(args):
    s = args.get("seed")
    if isinstance(s, int):
        return s
    return zlib.crc32((str(args.get("prompt", ""))
                       + str(args.get("filename", ""))).encode()) & 0x7FFFFFFF


def generate(args):
    seed = _seed(args)
    body = {"model": MODEL, "prompt": args["prompt"],
            "size": args.get("size", "512x512"), "n": 1, "seed": seed}
    req = urllib.request.Request(_base() + "/v1/images/generations",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    out = json.loads(urllib.request.urlopen(req, timeout=240).read().decode())
    path = _safe(args["filename"])
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(base64.b64decode(out["data"][0]["b64_json"]))
    return {"path": path, "bytes": os.path.getsize(path), "size": body["size"],
            "seed": seed, "prompt": body["prompt"]}


def edit(args):
    src = _safe(args["image_path"])
    dst = _safe(args.get("filename") or src[:-4] + "_edited.png")
    seed = _seed(args)
    r = subprocess.run(["curl", "-s", "-m", "240", _base() + "/v1/images/edits",
                        "-F", f"model={MODEL}", "-F", f"image=@{src}",
                        "-F", f"prompt={args['prompt']}", "-F", f"seed={seed}"],
                       capture_output=True, text=True, timeout=260)
    out = json.loads(r.stdout or "{}")
    if "data" not in out:
        raise RuntimeError(str(out.get("error", r.stdout or r.stderr))[:200])
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    with open(dst, "wb") as f:
        f.write(base64.b64decode(out["data"][0]["b64_json"]))
    return {"path": dst, "bytes": os.path.getsize(dst), "seed": seed,
            "prompt": args["prompt"]}


def handle(msg):
    m = msg.get("method")
    if m == "initialize":
        return {"protocolVersion": msg.get("params", {}).get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "image-tools", "version": "1.0.0"}}
    if m == "tools/list":
        return {"tools": TOOLS}
    if m == "tools/call":
        name = msg["params"].get("name")
        args = msg["params"].get("arguments", {}) or {}
        try:
            res = generate(args) if name == "generate_image" else edit(args)
            return {"content": [{"type": "text", "text": json.dumps(res)}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"ERROR: {e}"}], "isError": True}
    if m == "ping":
        return {}
    return None


def main():
    # MCP stdio transport: one JSON-RPC message per line (newline-delimited).
    out = sys.stdout.buffer
    for line in sys.stdin.buffer:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue
        if "id" not in msg:  # notifications (initialized, cancelled, ...)
            continue
        try:
            res = handle(msg)
            if res is None:
                resp = {"jsonrpc": "2.0", "id": msg["id"],
                        "error": {"code": -32601, "message": str(msg.get("method"))}}
            else:
                resp = {"jsonrpc": "2.0", "id": msg["id"], "result": res}
        except Exception as e:
            resp = {"jsonrpc": "2.0", "id": msg["id"],
                    "error": {"code": -32603, "message": str(e)[:200]}}
        out.write(json.dumps(resp).encode() + b"\n")
        out.flush()


if __name__ == "__main__":
    main()
