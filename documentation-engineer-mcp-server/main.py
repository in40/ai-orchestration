#!/usr/bin/env python3
"""documentation-engineer — MCP-сервер автодокументации задач.

Streamable-HTTP MCP-сервер (plain JSON-RPC 2.0 over HTTP POST /mcp):
  * регистрируется в реестре агентов (REGISTRY_URL, по умолчанию :3031);
  * шлёт heartbeat каждые 30 секунд (HEARTBEAT_INTERVAL);
  * поддерживает MCP_ADVERTISE_HOST — хост, который рекламируется реестру
    (чтобы ссылка работала с других контейнеров, а не только с localhost);
  * инструмент generate_task_docs(task_id) клонирует/обновляет results-дерево,
    читает описание задачи, план planner'а, need_info/ответы заказчика,
    QA-контракт и финальный код, пишет results/<task>/docs/REQUIREMENTS.md и
    results/<task>/docs/ARCHITECTURE.md и пушит docs/ обратно в results-дерево.

Сбой генерации docs никогда не роняет сервер и не влияет на статус задачи:
инструмент возвращает isError + строку "docs=skipped", успешный путь — "docs=ok".

Режимы запуска (CLI):
  python main.py serve                 # запустить MCP-сервер (по умолчанию)
  python main.py generate <task_id>    # разовая генерация (для хука IT Lead)
  python main.py backfill [--days 14]  # дописать docs всем done-задачам без docs/
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Конфигурация (только переменные окружения, без секретов)
# ---------------------------------------------------------------------------

SERVICE_NAME = "documentation-engineer"
SERVICE_VERSION = "1.0.0"

PORT = int(os.environ.get("PORT", "5000"))
REGISTRY_URL = os.environ.get("REGISTRY_URL", "http://127.0.0.1:3031").rstrip("/")
HEARTBEAT_INTERVAL = int(os.environ.get("HEARTBEAT_INTERVAL", "30"))
MCP_ADVERTISE_HOST = os.environ.get("MCP_ADVERTISE_HOST", "").strip()
RESULTS_DIR = Path(os.environ.get("RESULTS_DIR", "results")).expanduser()
if not RESULTS_DIR.is_absolute():
    RESULTS_DIR = (Path.cwd() / RESULTS_DIR).resolve()
RESULTS_REPO = os.environ.get("RESULTS_REPO", "").strip()

# Поддерживаемые версии протокола MCP (streamable-http введён в 2025-03-26).
SUPPORTED_PROTOCOL_VERSIONS = ("2024-11-05", "2025-03-26", "2025-06-18")
DEFAULT_PROTOCOL_VERSION = "2025-06-18"

SESSION_ID = uuid.uuid4().hex

TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

CODE_SUFFIXES = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".go", ".rs", ".java",
    ".kt", ".c", ".h", ".cpp", ".hpp", ".rb", ".php", ".sh", ".sql",
}
EXCLUDED_DIR_NAMES = {
    ".git", "docs", "node_modules", "venv", ".venv", "__pycache__",
    ".pytest_cache", ".mypy_cache", "dist", "build", ".idea", ".vscode",
}

MAX_BODY_BYTES = 1_000_000


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[{ts}] {SERVICE_NAME}: {msg}", flush=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ---------------------------------------------------------------------------
# Реестр агентов (:3031): регистрация + heartbeat каждые 30 секунд
# Контракт реестра (как у vendored-копий qa-engineer/security): MCP JSON-RPC
# tools/call registry/register|list|unregister на {REGISTRY_URL}/mcp;
# повторный registry/register обновляет last_seen, т.е. служит heartbeat.
# ---------------------------------------------------------------------------

def advertise_host() -> str:
    """Хост, который рекламируется реестру (MCP_ADVERTISE_HOST > автоопределение)."""
    if MCP_ADVERTISE_HOST:
        return MCP_ADVERTISE_HOST
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def advertise_url() -> str:
    return f"http://{advertise_host()}:{PORT}/mcp"


def registry_call(tool: str, arguments: dict, timeout: float = 5.0) -> dict:
    body = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{REGISTRY_URL}/mcp", data=body,
        headers={"Content-Type": "application/json",
                 "User-Agent": f"{SERVICE_NAME}/{SERVICE_VERSION}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read() or b"{}")
    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(f"registry error: {payload['error'].get('message')}")
    return payload


def registration_payload() -> dict:
    host = advertise_host()
    return {
        "id": f"{SERVICE_NAME}-server-{host}-{PORT}",
        "name": f"Documentation Engineer MCP Server on {host}:{PORT}",
        "description": ("AI agent автодокументации задач: генерирует docs/REQUIREMENTS.md "
                        "и docs/ARCHITECTURE.md в results-дереве задачи (streamable-http MCP)"),
        "endpoint": f"http://{host}:{PORT}/mcp",
        "capabilities": {"tools": ["generate_task_docs"]},
    }


def registry_loop() -> None:
    """Фоновый поток: registry/register каждые HEARTBEAT_INTERVAL (register = heartbeat).

    Сбой реестра не должен влиять на работу сервера: ошибки только логируются.
    """
    ever_registered = False
    while True:
        try:
            registry_call("registry/register", registration_payload())
            if not ever_registered:
                ever_registered = True
                log(f"registered in registry {REGISTRY_URL} as {advertise_url()}")
        except Exception as exc:  # noqa: BLE001 — реестр может быть недоступен
            if ever_registered:
                log(f"registry heartbeat failed: {exc}")
            else:
                log(f"registry {REGISTRY_URL} unavailable: {exc}")
            ever_registered = False
        time.sleep(HEARTBEAT_INTERVAL)


# ---------------------------------------------------------------------------
# Results-дерево: клонирование/обновление и git push
# ---------------------------------------------------------------------------

def run_git(args: list, cwd: Path, timeout: float = 120.0) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=timeout
    )


def sync_results() -> bool:
    """Клонирует (или обновляет) results-дерево. Возвращает True, если есть git-копия.

    RESULTS_REPO клонируется в RESULTS_DIR.parent — сам RESULTS_DIR это
    подкаталог results/ внутри репозитория (задачи лежат в results/<task_id>).
    """
    repo_root = RESULTS_DIR.parent
    repo_root.mkdir(parents=True, exist_ok=True)
    if RESULTS_REPO:
        if not (repo_root / ".git").is_dir():
            if any(p != RESULTS_DIR for p in repo_root.iterdir()):
                log(f"repo root {repo_root} exists but is not a git clone; pulling skipped")
            else:
                log(f"cloning results tree {RESULTS_REPO} -> {repo_root}")
                try:
                    r = run_git(["clone", "--", RESULTS_REPO, str(repo_root)], repo_root.parent)
                    if r.returncode != 0:
                        log(f"git clone failed: {r.stderr.strip()[:300]}")
                except Exception as exc:  # noqa: BLE001
                    log(f"git clone error: {exc}")
        else:
            try:
                r = run_git(["pull", "--ff-only"], repo_root)
                if r.returncode != 0:
                    log(f"git pull failed: {r.stderr.strip()[:300]}")
            except Exception as exc:  # noqa: BLE001
                log(f"git pull error: {exc}")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return (repo_root / ".git").is_dir()


def push_docs(task_id: str) -> bool:
    """Коммитит и пушит docs/ задачи обратно в results-дерево (если это git-копия)."""
    repo_root = RESULTS_DIR.parent
    if not (repo_root / ".git").is_dir():
        return False
    rel = f"results/{task_id}/docs"
    try:
        r = run_git(["add", "--", rel], repo_root)
        if r.returncode != 0:
            log(f"git add failed: {r.stderr.strip()[:200]}")
            return False
        c = run_git(
            ["-c", "user.name=documentation-engineer", "-c", "user.email=documentation-engineer@local",
             "commit", "-m", f"docs: auto-documentation for {task_id}"],
            repo_root,
        )
        if c.returncode != 0:
            if "nothing to commit" in (c.stdout + c.stderr):
                log(f"docs for {task_id}: nothing new to commit")
                return True
            log(f"git commit failed: {(c.stdout + c.stderr).strip()[:200]}")
            return False
        p = run_git(["push"], repo_root)
        if p.returncode != 0:
            log(f"git push failed (docs committed locally): {p.stderr.strip()[:200]}")
            return False
        return True
    except Exception as exc:  # noqa: BLE001
        log(f"git push error: {exc}")
        return False


# ---------------------------------------------------------------------------
# Чтение входов задачи: описание, план, need_info/ответы, QA-контракт, код
# ---------------------------------------------------------------------------

def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def _load_json(path: Path):
    text = _read_text(path)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _first_existing(tdir: Path, names: list) -> Path | None:
    for name in names:
        p = tdir / name
        if p.is_file():
            return p
    return None


def _stringify(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return str(value)


def _split_items(text: str, limit: int = 40) -> list:
    """Разбивает произвольный текст на список содержательных пунктов."""
    text = (text or "").strip()
    if not text:
        return []
    items = []
    for line in text.splitlines():
        s = line.strip().strip("-*•\u2022 ").strip()
        s = re.sub(r"^\d+[.)]\s*", "", s)
        if len(s) >= 12:
            items.append(s)
        if len(items) >= limit:
            return items
    if items:
        return items
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) >= 12][:limit]


def _as_str_list(value) -> list:
    """Нормализует список строк из list/str/dict со стандартными ключами."""
    if value is None:
        return []
    if isinstance(value, str):
        return _split_items(value)
    if isinstance(value, dict):
        for key in ("items", "checks", "criteria", "acceptance", "requirements", "steps", "questions", "answers"):
            if key in value:
                return _as_str_list(value[key])
        return [f"{k}: {_stringify(v)}" for k, v in value.items()]
    if isinstance(value, list):
        out = []
        for el in value:
            if isinstance(el, dict):
                for key in ("answer", "question", "field", "title", "text", "description", "step", "check", "criterion"):
                    if key in el:
                        text = _stringify(el[key])
                        extra = ""
                        for k2 in ("why", "details", "expected", "answer"):
                            if k2 in el and k2 != key:
                                extra += f" — {k2}: {_stringify(el[k2])}"
                        if "field" in el and key != "field":
                            text = f"{_stringify(el['field'])}: {text}"
                        out.append(text + extra)
                        break
                else:
                    out.append(_stringify(el))
            else:
                out.append(_stringify(el))
        return [x for x in out if x]
    return [_stringify(value)]


def collect_inputs(tdir: Path) -> dict:
    inp: dict = {
        "task_meta": None, "description": "", "plan_items": [],
        "need_info_items": [], "answer_items": [], "qa_items": [],
        "code_files": [], "readme": "", "requirements_txt": "",
    }

    # 1. Описание задачи
    meta_path = _first_existing(tdir, ["task.json", "meta.json", "issue.json"])
    if meta_path:
        meta = _load_json(meta_path)
        if isinstance(meta, dict):
            inp["task_meta"] = meta
            for key in ("description", "task", "body", "summary", "title", "goal"):
                if meta.get(key):
                    inp["description"] = _stringify(meta[key])
                    break
    if not inp["description"]:
        desc_path = _first_existing(tdir, ["description.md", "task.md", "README.md"])
        if desc_path:
            inp["description"] = _read_text(desc_path)
            if desc_path.name == "README.md":
                inp["readme"] = inp["description"]

    # 2. План planner'а
    plan_path = _first_existing(tdir, ["plan.json", "plan.md", "planner_plan.json", "planner_plan.md"])
    if plan_path:
        plan = _load_json(plan_path)
        inp["plan_items"] = _as_str_list(plan)

    # 3. need_info + ответы заказчика (clarifications)
    ni_path = _first_existing(tdir, ["need_info.json", "questions.json", "need_info.md"])
    if ni_path:
        inp["need_info_items"] = _as_str_list(_load_json(ni_path))
    ans_path = _first_existing(tdir, ["answers.json", "clarifications.json", "need_info_answers.json", "answers.md"])
    if ans_path:
        inp["answer_items"] = _as_str_list(_load_json(ans_path))

    # 4. QA-контракт
    qa_path = _first_existing(tdir, ["qa_contract.json", "qa.json", "qa_contract.md", "qa.md", "acceptance.md"])
    if qa_path:
        inp["qa_items"] = _as_str_list(_load_json(qa_path))

    # 5. Финальный код
    for p in sorted(tdir.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in CODE_SUFFIXES:
            continue
        rel_parts = set(p.relative_to(tdir).parts[:-1])
        if rel_parts & EXCLUDED_DIR_NAMES:
            continue
        inp["code_files"].append(p)

    req_txt = tdir / "requirements.txt"
    if req_txt.is_file():
        inp["requirements_txt"] = _read_text(req_txt)
    readme = tdir / "README.md"
    if readme.is_file() and not inp["readme"]:
        inp["readme"] = _read_text(readme)
    return inp


# ---------------------------------------------------------------------------
# Статический анализ кода решения (stdlib: ast + regex)
# ---------------------------------------------------------------------------

ENV_RE = re.compile(r"""os\.(?:environ\.get|environ|getenv)\(\s*["']([A-Za-z_][A-Za-z0-9_]*)["']""")
JS_ENV_RE = re.compile(r"""process\.env\.([A-Za-z_][A-Za-z0-9_]*)""")
GO_ENV_RE = re.compile(r"""os\.Getenv\(\s*"([A-Za-z_][A-Za-z0-9_]*)"\s*\)""")
ROUTE_RES = [
    re.compile(r"""@(?:app|router|api)\.(?:get|post|put|delete|patch|route)\(\s*["']([^"']+)["']"""),
    re.compile(r"""self\.path\W{0,40}?["'](/[\w./<>{}-]*)["']"""),
    re.compile(r"""(?:add_route|add_url_rule|route)\(\s*["']([^"']+)["']"""),
]
ENTRY_NAMES = ("main.py", "app.py", "server.py", "index.js", "app.js", "server.js")


def analyze_py(path: Path) -> dict:
    info = {"doc": "", "funcs": [], "classes": [], "imports": set(), "env": set(), "routes": set()}
    src = _read_text(path)
    if not src:
        return info
    try:
        tree = ast.parse(src)
        info["doc"] = (ast.get_docstring(tree) or "").strip().splitlines()[0] if ast.get_docstring(tree) else ""
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                info["funcs"].append(node.name)
            elif isinstance(node, ast.ClassDef):
                info["classes"].append(node.name)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    info["imports"].add(a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                info["imports"].add(node.module.split(".")[0])
    except (SyntaxError, ValueError, RecursionError):
        pass
    info["env"] = set(ENV_RE.findall(src))
    for rx in ROUTE_RES:
        info["routes"].update(rx.findall(src))
    return info


def analyze_file(path: Path) -> dict:
    if path.suffix.lower() == ".py":
        return analyze_py(path)
    info = {"doc": "", "funcs": [], "classes": [], "imports": set(), "env": set(), "routes": set()}
    src = _read_text(path)
    first = src.splitlines()[0] if src else ""
    info["doc"] = re.sub(r"^[#/*\s]+", "", first)[:120]
    info["env"] = set(JS_ENV_RE.findall(src)) | set(GO_ENV_RE.findall(src))
    for rx in ROUTE_RES:
        info["routes"].update(rx.findall(src))
    return info


def third_party_deps(inp: dict) -> list:
    declared = []
    for line in (inp.get("requirements_txt") or "").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            declared.append(line)
    stdlib = getattr(sys, "stdlib_module_names", frozenset())
    local_modules = {p.stem for p in inp["code_files"] if p.suffix.lower() == ".py"}
    found = set()
    for p in inp["code_files"]:
        if p.suffix.lower() != ".py":
            continue
        for mod in analyze_py(p)["imports"]:
            if mod not in stdlib and mod not in local_modules and mod not in {"__future__"}:
                found.add(mod)
    return sorted(set(declared) | found)


# ---------------------------------------------------------------------------
# Рендер документации
# ---------------------------------------------------------------------------

def render_requirements(task_id: str, inp: dict) -> str:
    L = []
    L.append(f"# Требования к решению — {task_id}")
    L.append("")
    L.append(f"> Сгенерировано автоматически сервисом `{SERVICE_NAME}` {SERVICE_VERSION} ({_now_iso()}).")
    L.append("> Не редактируйте вручную: файл перезаписывается при повторной генерации.")
    L.append("")

    L.append("## 1. Постановка задачи")
    L.append("")
    L.append(inp["description"] or "_Описание задачи в results-дереве не найдено._")
    L.append("")

    L.append("## 2. Функциональные требования")
    L.append("")
    frs = list(inp["plan_items"]) or _split_items(inp["description"])
    if frs:
        for i, item in enumerate(frs, 1):
            L.append(f"- **FR-{i}.** {item}")
    else:
        L.append("_Функциональные требования не извлечены (нет описания и плана)._")
    L.append("")

    L.append("## 3. Нефункциональные требования")
    L.append("")
    nfrs = [
        "Код не содержит секретов, паролей и токенов; конфигурация — через переменные окружения.",
        "Ошибки обрабатываются без падения сервиса; сбои логируются.",
        "Сетевой сервис слушает 0.0.0.0, порт берётся из переменной окружения PORT (по умолчанию 5000).",
    ]
    env_all = set()
    for p in inp["code_files"]:
        env_all |= analyze_file(p)["env"]
    if "PORT" in env_all:
        nfrs.append("Порт сервиса задаётся переменной окружения PORT.")
    deps = third_party_deps(inp)
    if not deps:
        nfrs.append("Решение использует только стандартную библиотеку (нет сторонних зависимостей).")
    else:
        nfrs.append(f"Сторонние зависимости зафиксированы ({', '.join(deps[:10])}).")
    for item in inp["qa_items"]:
        low = item.lower()
        if any(k in low for k in ("производит", "нагруз", "security", "безопас", "доступн", "latency", "performance")):
            nfrs.append(item)
    for item in nfrs:
        L.append(f"- {item}")
    L.append("")

    L.append("## 4. Принятые допущения (clarifications)")
    L.append("")
    if inp["need_info_items"] or inp["answer_items"]:
        L.append("| # | Вопрос / потребность | Ответ заказчика |")
        L.append("|---|---------------------|-----------------|")
        n = max(len(inp["need_info_items"]), len(inp["answer_items"]))
        for i in range(n):
            q = inp["need_info_items"][i] if i < len(inp["need_info_items"]) else "—"
            a = inp["answer_items"][i] if i < len(inp["answer_items"]) else "—"
            q = q.replace("|", "\\|")
            a = a.replace("|", "\\|")
            L.append(f"| {i + 1} | {q} | {a} |")
    else:
        L.append("_Запросов need_info и уточнений заказчика не зафиксировано — решение принято по исходному описанию._")
    L.append("")

    L.append("## 5. Критерии приёмки")
    L.append("")
    acs = inp["qa_items"] or _split_items(inp["description"])
    if acs:
        for i, item in enumerate(acs, 1):
            L.append(f"- **AC-{i}.** {item}")
    else:
        L.append("- Задача считается принятой, если QA-контракт выполнен и решение прошло все гейты IT Lead.")
    L.append("")
    return "\n".join(L)


def render_architecture(task_id: str, inp: dict) -> str:
    L = []
    L.append(f"# Архитектура решения — {task_id}")
    L.append("")
    L.append(f"> Сгенерировано автоматически сервисом `{SERVICE_NAME}` {SERVICE_VERSION} ({_now_iso()}).")
    L.append("> Не редактируйте вручную: файл перезаписывается при повторной генерации.")
    L.append("")

    analyses = {p: analyze_file(p) for p in inp["code_files"]}
    entry = None
    for name in ENTRY_NAMES:
        for p in inp["code_files"]:
            if p.name == name:
                entry = p
                break
        if entry:
            break

    L.append("## 1. Обзор")
    L.append("")
    L.append(f"Исходных файлов в решении: {len(inp['code_files'])}."
             + (f" Точка входа — `{entry.relative_to(inp['_tdir'])}`." if entry and entry in analyses else ""))
    L.append("")

    L.append("## 2. Модули и их ответственность")
    L.append("")
    if inp["code_files"]:
        L.append("| Файл | Ответственность | Ключевые сущности |")
        L.append("|------|-----------------|-------------------|")
        for p in inp["code_files"]:
            a = analyses[p]
            ents = ", ".join(f"`{x}`" for x in (a["funcs"] + a["classes"])[:8]) or "—"
            desc = (a["doc"] or "—").replace("|", "\\|")
            L.append(f"| `{p.relative_to(inp['_tdir'])}` | {desc} | {ents} |")
    else:
        L.append("_Исходный код в results-дереве не найден._")
    L.append("")

    L.append("## 3. Потоки данных")
    L.append("")
    routes = set()
    for a in analyses.values():
        routes |= a["routes"]
    if routes:
        L.append(f"Внешний контур: клиент → HTTP (порт из `PORT`) → маршруты: {', '.join(f'`{r}`' for r in sorted(routes)[:15])}.")
    elif entry:
        L.append("Внешний контур: клиент → HTTP-сервис (порт из `PORT`) → точка входа → модули решения.")
    else:
        L.append("Точка входа не определена; поток данных описан в постановке задачи (раздел 1 REQUIREMENTS.md).")
    L.append("")
    L.append("Внутренний контур: входные данные задачи → обработка модулями → результат/ответ; "
             "журналирование — stdout/логи сервиса.")
    L.append("")

    L.append("## 4. Внешние зависимости")
    L.append("")
    deps = third_party_deps(inp)
    if deps:
        for d in deps:
            L.append(f"- `{d}`")
    else:
        L.append("_Только стандартная библиотека Python — сторонних зависимостей не обнаружено._")
    L.append("")

    L.append("## 5. Переменные окружения")
    L.append("")
    env_map = {}
    for p in inp["code_files"]:
        for var in analyze_file(p)["env"]:
            env_map.setdefault(var, set()).add(str(p.relative_to(inp["_tdir"])))
    if env_map:
        L.append("| Переменная | Где используется |")
        L.append("|------------|------------------|")
        for var in sorted(env_map):
            L.append(f"| `{var}` | {', '.join(sorted(env_map[var])[:4])} |")
    else:
        L.append("_Явных переменных окружения в коде не найдено._")
    L.append("")

    L.append("## 6. Схема развёртывания")
    L.append("")
    run_cmd = None
    for line in (inp.get("readme") or "").splitlines():
        s = line.strip().strip("`").strip()
        s = re.sub(r"^(?:run|запуск|start)\s*[:=]\s*", "", s, flags=re.IGNORECASE)
        if re.search(r"\b(python|uvicorn|flask|npm start|node|docker)\b", s) and len(s) < 120:
            run_cmd = s
            break
    if run_cmd:
        L.append(f"Запуск: `{run_cmd}` (порт — env `PORT`, по умолчанию 5000).")
    else:
        L.append("Запуск: `python main.py` (порт — env `PORT`, по умолчанию 5000).")
    L.append("")
    L.append("- Сервис слушает `0.0.0.0`, наружу публикуется только HTTP-эндпоинт.")
    L.append("- Результаты (включая `docs/`) коммитятся и пушатся обратно в results-дерево.")
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# generate_task_docs — основной инструмент
# ---------------------------------------------------------------------------

def generate_task_docs(task_id: str, sync: bool = True) -> dict:
    """Генерирует docs/REQUIREMENTS.md и docs/ARCHITECTURE.md для задачи task_id."""
    if not TASK_ID_RE.match(task_id or ""):
        raise ValueError(f"некорректный task_id: {task_id!r}")
    if sync:
        sync_results()
    tdir = RESULTS_DIR / task_id
    if not tdir.is_dir():
        raise FileNotFoundError(f"задача {task_id!r} не найдена в results-дереве {RESULTS_DIR}")

    inp = collect_inputs(tdir)
    inp["_tdir"] = tdir
    docs_dir = tdir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    req_path = docs_dir / "REQUIREMENTS.md"
    arch_path = docs_dir / "ARCHITECTURE.md"
    req_path.write_text(render_requirements(task_id, inp), encoding="utf-8")
    arch_path.write_text(render_architecture(task_id, inp), encoding="utf-8")

    pushed = push_docs(task_id)
    result = {
        "task_id": task_id,
        "docs": [str(req_path), str(arch_path)],
        "pushed_to_results": pushed,
        "status": "ok",
        "activity": "docs=ok",
    }
    log(f"task={task_id} docs=ok (pushed={pushed})")
    return result


# ---------------------------------------------------------------------------
# Backfill: задачи со статусом done за последние N дней без docs/
# ---------------------------------------------------------------------------

def task_status(tdir: Path) -> str:
    meta = _load_json(tdir / "task.json")
    if isinstance(meta, dict) and meta.get("status"):
        return str(meta["status"]).lower()
    for marker in ("STATUS", "status.txt", ".status"):
        p = tdir / marker
        if p.is_file():
            return _read_text(p).lower()
    if (tdir / "done").exists():
        return "done"
    return ""


def _recent(tdir: Path, days: int) -> bool:
    cutoff = time.time() - days * 86400
    try:
        newest = tdir.stat().st_mtime
        for p in tdir.rglob("*"):
            try:
                newest = max(newest, p.stat().st_mtime)
            except OSError:
                pass
        return newest >= cutoff
    except OSError:
        return False


def backfill(days: int = 14) -> list:
    """Дописывает docs задачам со статусом done за последние `days` дней, у которых нет docs/."""
    sync_results()
    processed = []
    if not RESULTS_DIR.is_dir():
        log(f"backfill: results-дерево {RESULTS_DIR} не найдено")
        return processed
    for tdir in sorted(RESULTS_DIR.iterdir()):
        if not tdir.is_dir() or tdir.name.startswith("."):
            continue
        if task_status(tdir) != "done":
            continue
        docs_ok = (tdir / "docs" / "REQUIREMENTS.md").is_file() and (tdir / "docs" / "ARCHITECTURE.md").is_file()
        if docs_ok or not _recent(tdir, days):
            continue
        try:
            generate_task_docs(tdir.name, sync=False)
            log(f"backfill activity: task={tdir.name} docs=ok")
            processed.append({"task_id": tdir.name, "activity": "docs=ok"})
        except Exception as exc:  # noqa: BLE001 — сбой docs не влияет на статус задачи
            log(f"backfill activity: task={tdir.name} docs=skipped ({exc})")
            processed.append({"task_id": tdir.name, "activity": "docs=skipped", "error": str(exc)})
    log(f"backfill done: {len(processed)} task(s) processed")
    return processed


# ---------------------------------------------------------------------------
# MCP: JSON-RPC 2.0 поверх HTTP (streamable-http, JSON-ответы)
# ---------------------------------------------------------------------------

TOOL_DEFS = [{
    "name": "generate_task_docs",
    "description": (
        "Генерирует автодокументацию к задаче: клонирует/обновляет results-дерево, "
        "читает описание задачи, план planner'а, need_info/ответы заказчика, QA-контракт "
        "и финальный код; пишет results/<task>/docs/REQUIREMENTS.md и ARCHITECTURE.md "
        "и пушит docs/ обратно в results-дерево. Сбой не влияет на статус задачи."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "Идентификатор задачи — имя каталога в results-дереве.",
            },
        },
        "required": ["task_id"],
        "additionalProperties": False,
    },
}]


def _rpc_error(req_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def handle_jsonrpc(req):
    """Обрабатывает одиночный запрос или batch. Возвращает (payload, is_notification_only)."""
    if isinstance(req, list):
        responses = []
        for item in req:
            out, _notif = _process_one(item)
            if out is not None:
                responses.append(out)
        if not responses:
            return None, True
        return responses, False
    out, notif = _process_one(req)
    return out, notif


def _process_one(req):
    if not isinstance(req, dict) or req.get("jsonrpc") != "2.0" or not req.get("method"):
        return _rpc_error(req.get("id") if isinstance(req, dict) else None, -32600, "Invalid Request"), False
    method = req["method"]
    req_id = req.get("id")
    params = req.get("params") or {}

    if method.startswith("notifications/"):
        return None, True

    try:
        if method == "initialize":
            requested = params.get("protocolVersion")
            version = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else DEFAULT_PROTOCOL_VERSION
            result = {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVICE_NAME, "version": SERVICE_VERSION},
                "instructions": (
                    "documentation-engineer: вызовите tools/call generate_task_docs(task_id) "
                    "после прохождения гейтов задачи, до перевода в done."
                ),
            }
            return {"jsonrpc": "2.0", "id": req_id, "result": result}, False

        if method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}, False

        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOL_DEFS}}, False

        if method == "tools/call":
            name = params.get("name")
            args = params.get("arguments") or {}
            if name != "generate_task_docs":
                return _rpc_error(req_id, -32602, f"unknown tool: {name}"), False
            task_id = str(args.get("task_id", ""))
            try:
                out = generate_task_docs(task_id)
                text = json.dumps(out, ensure_ascii=False, indent=2)
                return {"jsonrpc": "2.0", "id": req_id,
                        "result": {"content": [{"type": "text", "text": text}], "isError": False}}, False
            except Exception as exc:  # noqa: BLE001 — ошибка инструмента, не протокола
                return {"jsonrpc": "2.0", "id": req_id, "result": {
                    "content": [{"type": "text",
                                 "text": json.dumps({"status": "skipped", "activity": "docs=skipped",
                                                     "error": str(exc)}, ensure_ascii=False)}],
                    "isError": True}}, False

        return _rpc_error(req_id, -32601, f"Method not found: {method}"), False
    except Exception as exc:  # noqa: BLE001 — сервер не должен падать на запросе
        log(f"internal error handling {method}: {exc}")
        return _rpc_error(req_id, -32603, f"Internal error: {exc}"), False


# ---------------------------------------------------------------------------
# OpenAPI (самеописание сервиса)
# ---------------------------------------------------------------------------

OPENAPI = {
    "openapi": "3.0.3",
    "info": {
        "title": "documentation-engineer (MCP, streamable-http)",
        "version": SERVICE_VERSION,
        "description": (
            "MCP-сервер автодокументации задач. JSON-RPC 2.0 по адресу POST /mcp. "
            "Эндпоинты доступны и под произвольным URL-префиксом (совпадение по последнему сегменту пути)."
        ),
    },
    "paths": {
        "/health": {
            "get": {
                "summary": "Health check",
                "responses": {"200": {"description": "Сервис жив", "content": {"application/json": {
                    "example": {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}}}}},
            }
        },
        "/": {
            "get": {
                "summary": "Информация о сервисе",
                "responses": {"200": {"description": "Метаданные сервиса", "content": {"application/json": {}}}},
            }
        },
        "/openapi.json": {
            "get": {"summary": "Эта спецификация", "responses": {"200": {"description": "OpenAPI 3.0 JSON"}}},
        },
        "/mcp": {
            "post": {
                "summary": "MCP streamable-http endpoint (JSON-RPC 2.0)",
                "description": "Методы: initialize, ping, tools/list, tools/call(generate_task_docs), notifications/*.",
                "requestBody": {"required": True, "content": {"application/json": {
                    "schema": {"type": "object"},
                    "example": {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                "params": {"name": "generate_task_docs", "arguments": {"task_id": "task-123"}}}}}},
                "responses": {
                    "200": {"description": "JSON-RPC response", "content": {"application/json": {}}},
                    "202": {"description": "Принято (для notifications/*, тело отсутствует)"},
                },
            },
            "get": {"summary": "SSE-поток не поддерживается", "responses": {"405": {"description": "Method Not Allowed"}}},
        },
        "/tools/generate_task_docs": {
            "post": {
                "summary": "REST-обёртка инструмента generate_task_docs",
                "requestBody": {"required": True, "content": {"application/json": {
                    "schema": {"type": "object", "properties": {"task_id": {"type": "string"}},
                             "required": ["task_id"]}}}},
                "responses": {
                    "200": {"description": "Документация сгенерирована (docs=ok)", "content": {"application/json": {}}},
                    "400": {"description": "Некорректный task_id"},
                    "404": {"description": "Задача не найдена"},
                    "500": {"description": "docs=skipped (сбой не влияет на статус задачи)"},
                },
            }
        },
    },
}


# ---------------------------------------------------------------------------
# HTTP-сервер
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = f"{SERVICE_NAME}/{SERVICE_VERSION}"

    def _send(self, code: int, obj=None, ctype: str = "application/json"):
        body = b"" if obj is None else json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _route(self) -> str:
        """Последний сегмент пути — сервис может висеть под произвольным префиксом."""
        path = urlparse(self.path).path.strip("/")
        return path.rsplit("/", 1)[-1] if path else ""

    def do_GET(self):  # noqa: N802
        route = self._route()
        if route == "health":
            self._send(200, {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION,
                             "transport": "streamable-http", "uptime_session": SESSION_ID})
        elif route == "openapi.json":
            self._send(200, OPENAPI)
        elif route == "":
            self._send(200, {
                "service": SERVICE_NAME, "version": SERVICE_VERSION,
                "transport": "streamable-http", "mcp_endpoint": "POST /mcp",
                "tools": [t["name"] for t in TOOL_DEFS],
                "advertised_url": advertise_url(), "registry": REGISTRY_URL,
                "results_dir": str(RESULTS_DIR),
            })
        elif route == "mcp":
            self._send(405, {"error": "SSE stream not supported; use POST /mcp"})
        else:
            self._send(404, {"error": "not found", "routes": ["/", "/health", "/openapi.json", "POST /mcp"]})

    def do_POST(self):  # noqa: N802
        route = self._route()
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        raw = self.rfile.read(min(length, MAX_BODY_BYTES)) if length else b""

        if route == "mcp":
            try:
                req = json.loads(raw.decode("utf-8")) if raw else None
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._send(200, _rpc_error(None, -32700, "Parse error"))
                return
            if req is None:
                self._send(200, _rpc_error(None, -32600, "Invalid Request"))
                return
            payload, notif_only = handle_jsonrpc(req)
            if notif_only and payload is None:
                self.send_response(202)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Mcp-Session-Id", SESSION_ID)
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if route == "generate_task_docs":
            try:
                body = json.loads(raw.decode("utf-8")) if raw else {}
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._send(400, {"ok": False, "error": "invalid JSON body"})
                return
            task_id = str((body or {}).get("task_id", ""))
            try:
                self._send(200, {"ok": True, **generate_task_docs(task_id)})
            except ValueError as exc:
                self._send(400, {"ok": False, "activity": "docs=skipped", "error": str(exc)})
            except FileNotFoundError as exc:
                self._send(404, {"ok": False, "activity": "docs=skipped", "error": str(exc)})
            except Exception as exc:  # noqa: BLE001
                self._send(500, {"ok": False, "activity": "docs=skipped", "error": str(exc)})
            return

        self._send(404, {"error": "not found", "routes": ["POST /mcp", "POST /tools/generate_task_docs"]})

    def log_message(self, fmt, *args):  # приглушаем стандартный лог http.server
        log(f"{self.address_string()} {fmt % args}")


def serve() -> None:
    sync_results()
    t = threading.Thread(target=registry_loop, name="registry-heartbeat", daemon=True)
    t.start()
    httpd = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    log(f"listening on 0.0.0.0:{PORT} (mcp: POST /mcp, advertised: {advertise_url()})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        log("stopped")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="documentation-engineer",
                                 description="MCP-сервер автодокументации задач")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("serve", help="запустить MCP-сервер (по умолчанию)")
    bp = sub.add_parser("backfill", help="дописать docs done-задачам без документации")
    bp.add_argument("--days", type=int, default=14, help="окно в днях (по умолчанию 14)")
    gp = sub.add_parser("generate", help="разовая генерация docs для задачи")
    gp.add_argument("task_id")
    args = ap.parse_args(argv)

    if args.cmd == "backfill":
        results = backfill(args.days)
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "generate":
        try:
            print(json.dumps(generate_task_docs(args.task_id), ensure_ascii=False, indent=2))
            return 0
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"status": "skipped", "activity": "docs=skipped", "error": str(exc)},
                             ensure_ascii=False))
            return 1
    serve()
    return 0


if __name__ == "__main__":
    sys.exit(main())
