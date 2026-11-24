#!/usr/bin/env python3
"""promote-service: turn a pipeline deliverable into an installable service.

The orchestration pipeline builds code and pushes it to the *results* repo
(results/<task>/), but a service only becomes installable on any host once it
is declared in the *orchestration* repo: a portable unit under systemd/ and an
entry in deploy/install.sh's UNITS array. That promotion step was manual, and
documentation-engineer slipped through it (code committed, unit hand-made on
prod only) - so fresh hosts ran 8 services while prod ran 9.

This tool closes that gap:

  promote  generate systemd/<unit>.service from a deliverable and add it to
           install.sh UNITS (idempotent). Optionally copy the code in and
           git-commit.
  check    structural gate: every unit is installed, every UNITS entry has a
           unit file, no port collisions, and (informational) every
           *-mcp-server/ dir has a unit. Non-zero exit under --strict so QA/CI
           can reject a deliverable that adds a service without wiring it.
  ports    show used/free MCP service ports.

Stdlib only; safe to run on any host. Nothing here hardcodes a LAN IP: units
derive MCP_ADVERTISE_HOST/RESULTS_REPO from the install .env.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Repo root = parent of scripts/ (this file lives in <repo>/scripts/).
DEFAULT_REPO = Path(__file__).resolve().parent.parent

# Canonical service port block. 3031 registry, 3060-3063 core, 3071-3074
# engineers. New promoted services take the next free port in 3075-3099.
PORT_MIN, PORT_MAX = 3031, 3099

UNIT_TEMPLATE = """[Unit]
Description={description}
Documentation=https://github.com/in40/ai-orchestration
After=network-online.target mcp-registry.service
Wants=mcp-registry.service

[Service]
Type=simple
WorkingDirectory=/root/qwen/base/{workdir}
EnvironmentFile=/root/qwen/base/.env

# Fixed service config
Environment=PORT={port}
Environment=REGISTRY_URL=http://127.0.0.1:3031
Environment=HEARTBEAT_INTERVAL=30
{extra_env}
# MCP_ADVERTISE_HOST and RESULTS_REPO are derived from the install .env
# (DEPLOYMENT_HOST / MCP_GIT_REPO_URL) so nothing host-specific is baked in.
ExecStart=/bin/bash -c 'source /root/qwen/base/.env 2>/dev/null || true; \\
    export MCP_ADVERTISE_HOST="${{MCP_ADVERTISE_HOST:-${{DEPLOYMENT_HOST:-}}}}"; \\
    export RESULTS_REPO="${{RESULTS_REPO:-${{MCP_GIT_REPO_URL:-}}}}"; \\
    exec {exec_cmd}'

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""


# ---------------------------------------------------------------- helpers ---
def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def units_on_disk(repo: Path) -> dict[str, Path]:
    """unit-name (mcp-foo) -> path, from systemd/*.service."""
    out = {}
    for f in sorted((repo / "systemd").glob("*.service")):
        out[f.stem] = f
    return out


def declared_units(repo: Path) -> list[str]:
    """Contents of the UNITS=( ... ) array in deploy/install.sh."""
    txt = read(repo / "deploy" / "install.sh")
    m = re.search(r"UNITS=\(([^)]*)\)", txt, re.DOTALL)
    if not m:
        return []
    return m.group(1).split()


# Units that are intentionally never installed by install.sh: mcp-master is a
# dev "start everything" aggregator; install.sh brings services up individually.
ALLOW_UNINSTALLED = {"mcp-master"}


def install_sh_text(repo: Path) -> str:
    return read(repo / "deploy" / "install.sh")


def unit_ports(repo: Path) -> dict[str, int]:
    """unit-name -> declared PORT, for collision detection."""
    out = {}
    for name, path in units_on_disk(repo).items():
        m = re.search(r"Environment=PORT=(\d+)", read(path))
        if m:
            out[name] = int(m.group(1))
    # units that pass --port on the command line instead of Environment=PORT
    for name, path in units_on_disk(repo).items():
        if name in out:
            continue
        m = re.search(r"--port (\$\{[A-Z_]+:-)?(\d+)", read(path))
        if m:
            out[name] = int(m.group(2))
    return out


def used_ports(repo: Path) -> set[int]:
    """Every 4-digit port referenced by any unit (broad, for free-port calc)."""
    used = set()
    for path in (repo / "systemd").glob("*.service"):
        for m in re.finditer(r"(?:--port |PORT=)(\d{4})", read(path)):
            used.add(int(m.group(1)))
    return used


def next_free_port(repo: Path) -> int:
    used = used_ports(repo)
    for p in range(3075, PORT_MAX + 1):
        if p not in used:
            return p
    for p in range(PORT_MIN, 3060):
        if p not in used:
            return p
    raise SystemExit("no free port in 3031-3099; free one up manually")


def code_dirs(repo: Path) -> list[str]:
    """Top-level *-mcp-server/ directories (candidate services)."""
    return sorted(
        d.name for d in repo.iterdir()
        if d.is_dir() and d.name.endswith("-mcp-server")
        and not d.name.startswith(".")
    )


def expected_unit_for_dir(dirname: str) -> str:
    stem = dirname[: -len("-mcp-server")]
    return f"mcp-{stem}"


def detect_exec(source: Path, port: int) -> tuple[str, list[str], str]:
    """Return (exec_cmd, warnings, mode) for a deliverable tree."""
    warns: list[str] = []
    has_pkg = (source / "mcp_std_server").is_dir()
    reqs = source / "requirements.txt"
    has_deps = False
    if reqs.is_file():
        for line in read(reqs).splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                has_deps = True
                break

    if has_pkg:
        # skeleton-based: python -m so install.sh rewrites to the venv python
        cmd = (
            "python -m mcp_std_server.server --transport streamable-http "
            f"--host 0.0.0.0 --port {port} --register-with-registry "
            "--registry-host 127.0.0.1 --registry-port 3031"
        )
        return cmd, warns, "skeleton"

    for entry in ("main.py", "app.py", "server.py"):
        if (source / entry).is_file():
            if has_deps:
                warns.append(
                    f"{entry} with requirements.txt deps: system python3 will "
                    "not see them. Prefer stdlib, or pass --exec with the "
                    "venv/module form (python -m ...) so install.sh wires it."
                )
            tail = "serve" if entry == "main.py" else ""
            cmd = f"python3 {entry}" + (f" {tail}" if tail else "")
            return cmd, warns, "script"

    raise SystemExit(
        f"cannot detect entrypoint in {source}: no mcp_std_server/ package and "
        "no main.py/app.py/server.py. Pass --exec explicitly."
    )


# ----------------------------------------------------------------- check ---
def cmd_check(args) -> int:
    repo = Path(args.repo_root).resolve()
    disk = units_on_disk(repo)
    declared = declared_units(repo)
    install_txt = install_sh_text(repo)
    ports = unit_ports(repo)
    dirs = code_dirs(repo)

    problems: list[str] = []
    notes: list[str] = []

    # 1. a unit exists but install.sh will never install it (the doc-eng bug)
    for name in disk:
        if name in declared:
            continue
        if name in ALLOW_UNINSTALLED:
            notes.append(f"{name}.service intentionally not installed (aggregator)")
        elif name in install_txt:
            notes.append(f"{name}.service installed conditionally by install.sh")
        else:
            problems.append(
                f"unit {name}.service is in systemd/ but NOT in install.sh UNITS "
                "(fresh hosts will not run it)"
            )
    # 2. install.sh references a unit that has no file
    for name in declared:
        if name not in disk:
            problems.append(
                f"install.sh UNITS lists {name} but systemd/{name}.service is missing"
            )
    # 3. port collisions
    seen: dict[int, str] = {}
    for name, port in sorted(ports.items(), key=lambda kv: kv[1]):
        if port in seen:
            problems.append(
                f"port {port} used by both {seen[port]} and {name}"
            )
        else:
            seen[port] = name
    # 4. informational: code dir with no matching unit
    for d in dirs:
        exp = expected_unit_for_dir(d)
        if exp not in disk:
            notes.append(f"{d}/ has no {exp}.service (is it a service? run promote)")

    report = {
        "units_on_disk": sorted(disk),
        "declared_units": declared,
        "ports": ports,
        "code_dirs": dirs,
        "problems": problems,
        "notes": notes,
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"repo: {repo}")
        print(f"units on disk: {len(disk)}  declared in install.sh: {len(declared)}")
        for p in problems:
            print(f"  PROBLEM: {p}")
        for n in notes:
            print(f"  note: {n}")
        if not problems and not notes:
            print("  OK: units and installer are consistent")

    # optional: scan a candidate deliverable for unwired new service
    if args.deliverable:
        dl = Path(args.deliverable).resolve()
        newsvc = dl.name.endswith("-mcp-server") or (dl / "mcp_std_server").is_dir() \
            or any((dl / e).is_file() for e in ("main.py", "app.py", "server.py"))
        if newsvc:
            exp = expected_unit_for_dir(dl.name) if dl.name.endswith("-mcp-server") \
                else f"mcp-{dl.name}"
            if exp not in disk:
                problems.append(
                    f"deliverable {dl.name} looks like a new service but has no "
                    f"{exp}.service -> run: promote-service promote --source {dl}"
                )
                print(f"  PROBLEM: {problems[-1]}")

    if args.strict and problems:
        return 1
    return 0


# ---------------------------------------------------------------- promote ---
def cmd_promote(args) -> int:
    repo = Path(args.repo_root).resolve()
    source = Path(args.source).resolve()
    if not source.is_dir():
        raise SystemExit(f"source dir not found: {source}")

    name = args.name
    if not name and source.name.endswith("-mcp-server"):
        name = source.name[: -len("-mcp-server")]
    if not name:
        raise SystemExit("could not infer service name; pass --name")
    unit = f"mcp-{name}"
    workdir = f"{name}-mcp-server"
    port = args.port or next_free_port(repo)

    if args.exec:
        exec_cmd, warns, mode = args.exec, [], "custom"
    else:
        exec_cmd, warns, mode = detect_exec(source, port)
    for w in warns:
        print(f"WARN: {w}", file=sys.stderr)

    description = args.description or f"{name} MCP service"
    extra_env = ""
    if args.env:
        extra_env = "".join(f"Environment={e}\n" for e in args.env)

    unit_text = UNIT_TEMPLATE.format(
        description=description, workdir=workdir, port=port,
        exec_cmd=exec_cmd, extra_env=extra_env,
    )
    unit_path = repo / "systemd" / f"{unit}.service"

    # idempotency: don't clobber an existing unit unless --force
    unit_exists = unit_path.exists()
    if unit_exists and not args.force:
        print(f"exists: {unit_path} (use --force to overwrite)")
    else:
        print(f"--- would write {unit_path} ---" if args.dry_run else f"write {unit_path}")
        if not args.dry_run:
            unit_path.write_text(unit_text, encoding="utf-8")

    # patch install.sh UNITS
    install_path = repo / "deploy" / "install.sh"
    txt = read(install_path)
    if unit in declared_units(repo):
        print(f"install.sh: {unit} already in UNITS")
        new_txt = txt
    else:
        new_txt = re.sub(
            r"(UNITS=\([^)]*?)(\s*\))",
            lambda m: f"{m.group(1)} {unit}{m.group(2)}",
            txt, count=1, flags=re.DOTALL,
        )
        if new_txt == txt:
            raise SystemExit("could not locate UNITS array end in install.sh")
        print(f"install.sh: add {unit} to UNITS")
        if not args.dry_run:
            install_path.write_text(new_txt, encoding="utf-8")

    # optionally copy the deliverable code into the repo
    if args.copy:
        dest = repo / workdir
        if dest.exists() and not args.force:
            print(f"copy: {dest} exists (use --force to overwrite)")
        else:
            print(f"copy: {source} -> {dest}")
            if not args.dry_run:
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(
                    source, dest,
                    ignore=shutil.ignore_patterns(
                        "venv", ".venv", "__pycache__", "node_modules", ".git"),
                )

    print(f"\nmode={mode} port={port} unit={unit}")
    if args.dry_run:
        print("\n[dry-run] nothing written. unit preview:\n")
        print(unit_text)
        return 0

    if args.commit:
        paths = [f"systemd/{unit}.service", "deploy/install.sh"]
        if args.copy:
            paths.append(workdir)
        subprocess.run(["git", "-C", str(repo), "add", *paths], check=True)
        msg = (f"feat(install): promote {name} to an installed service\n\n"
               f"Generated portable unit systemd/{unit}.service (env-driven, "
               "no host hardcodes) and added it to install.sh UNITS so every "
               "host runs it.")
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", msg], check=True)
        print(f"committed: {msg.splitlines()[0]}")
        if args.push:
            subprocess.run(["git", "-C", str(repo), "push", "-q",
                            "origin", args.branch], check=True)
            print(f"pushed to {args.branch}")
    else:
        print("review, then: git add systemd/ deploy/install.sh && git commit")
    return 0


# ------------------------------------------------------------------ ports ---
def cmd_ports(args) -> int:
    repo = Path(args.repo_root).resolve()
    used = used_ports(repo)
    print("used ports:", sorted(used))
    free = [p for p in range(3075, PORT_MAX + 1) if p not in used]
    print("free (3075-3099):", free[:10])
    return 0


# ------------------------------------------------------------------- main ---
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="promote-service", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo-root", default=str(DEFAULT_REPO),
                    help="orchestration repo root (default: parent of scripts/)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="structural gate: units vs installer vs code")
    c.add_argument("--strict", action="store_true", help="exit 1 if problems (for CI/QA)")
    c.add_argument("--json", action="store_true", help="machine-readable report")
    c.add_argument("--deliverable", help="also scan a candidate deliverable dir")
    c.set_defaults(func=cmd_check)

    p = sub.add_parser("promote", help="generate unit + patch install.sh UNITS")
    p.add_argument("--source", required=True, help="deliverable dir (results/<task>/ or <name>-mcp-server/)")
    p.add_argument("--name", help="service short name (default: from source dir)")
    p.add_argument("--port", type=int, help="service port (default: next free)")
    p.add_argument("--exec", dest="exec", help="override ExecStart command body")
    p.add_argument("--description", help="unit Description")
    p.add_argument("--env", action="append", metavar="K=V",
                   help="extra Environment= line (repeatable)")
    p.add_argument("--copy", action="store_true", help="copy source into <repo>/<name>-mcp-server/")
    p.add_argument("--force", action="store_true", help="overwrite existing unit/dir")
    p.add_argument("--commit", action="store_true", help="git add + commit")
    p.add_argument("--push", action="store_true", help="with --commit: git push")
    p.add_argument("--branch", default="v0.5.11", help="branch for --push")
    p.add_argument("--dry-run", action="store_true", help="print, don't write")
    p.set_defaults(func=cmd_promote)

    sub.add_parser("ports", help="show used/free ports").set_defaults(func=cmd_ports)
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
