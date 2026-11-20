# documentation-engineer

MCP-сервер автодокументации задач (streamable-http, plain JSON-RPC 2.0 over HTTP).
Новый член команды: после прохождения гейтов задачи генерирует `docs/REQUIREMENTS.md`
и `docs/ARCHITECTURE.md` в results-дереве задачи и пушит их обратно. Регистрируется
в реестре агентов (`:3031`) с heartbeat каждые 30 с — появляется на табе **Team**
автоматически. Только stdlib, внешних зависимостей нет.

## Запуск

```bash
python main.py            # = python main.py serve — MCP-сервер на 0.0.0.0:$PORT (default 5000)
python main.py generate <task_id>   # разовая генерация docs (для хука IT Lead / отладки)
python main.py backfill --days 14   # дописать docs done-задачам без docs/ (для systemd-таймера)
```

### Переменные окружения

| Переменная | Default | Назначение |
|---|---|---|
| `PORT` | `5000` | порт HTTP-сервера (bind `0.0.0.0`) |
| `REGISTRY_URL` | `http://127.0.0.1:3031` | реестр агентов (таб Team) |
| `HEARTBEAT_INTERVAL` | `30` | период heartbeat/перерегистрации, сек |
| `MCP_ADVERTISE_HOST` | авто (IP из маршрута до внешнего хоста, иначе `127.0.0.1`) | хост в URL, рекламируемом реестру |
| `RESULTS_DIR` | `./results` | локальный checkout results-дерева |
| `RESULTS_REPO` | пусто | git-URL results-дерева; если задан — clone/pull перед генерацией |

Сервис может висеть под произвольным URL-префиксом (например `/task-id/mcp`):
маршруты сопоставляются по последнему сегменту пути.

## HTTP-эндпоинты

Полное самеописание: `GET /openapi.json`.

### GET /health

```json
{"status": "ok", "service": "documentation-engineer", "version": "1.0.0", "transport": "streamable-http"}
```

### GET /

Инфо-объект сервиса: `{"service", "version", "transport", "mcp_endpoint", "tools", "advertised_url", "registry", "results_dir"}`.

### POST /mcp — MCP streamable-http (JSON-RPC 2.0)

Поддерживаемые методы: `initialize`, `ping`, `tools/list`, `tools/call`, `notifications/*` (→ `202 Accepted`).
Ответы — `application/json` (SSE-поток на `GET /mcp` не поддерживается → `405`).

`tools/list`:

```json
{"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"generate_task_docs","inputSchema":{"type":"object","properties":{"task_id":{"type":"string"}},"required":["task_id"]}}]}}
```

`tools/call`:

```json
{"jsonrpc":"2.0","id":2,"method":"tools/call",
 "params":{"name":"generate_task_docs","arguments":{"task_id":"task-123"}}}
```

успех:

```json
{"jsonrpc":"2.0","id":2,"result":{"content":[{"type":"text","text":"{\"task_id\": \"task-123\", \"docs\": [\".../docs/REQUIREMENTS.md\", \".../docs/ARCHITECTURE.md\"], \"pushed_to_results\": false, \"status\": \"ok\", \"activity\": \"docs=ok\"}"}],"isError":false}}
```

сбой (задача не найдена и т.п.) — `isError: true`, текст `{"status":"skipped","activity":"docs=skipped","error":"..."}`;
сам сервер при этом не падает.

### POST /tools/generate_task_docs — REST-обёртка того же инструмента

Запрос: `{"task_id": "task-123"}`. Ответ `200`: `{"ok": true, "task_id": "...", "docs": [...], "pushed_to_results": bool, "status": "ok", "activity": "docs=ok"}`;
`400` некорректный id, `404` задача не найдена, `500` `{"ok": false, "activity": "docs=skipped", "error": "..."}`.

### Регистрация в реестре (:3031)

Реестр — MCP-сервер на `:3031` (как у vendored-копий qa-engineer/security).
Фоновый поток каждые `HEARTBEAT_INTERVAL` (30 с) вызывает
`POST {REGISTRY_URL}/mcp` с JSON-RPC `tools/call registry/register`:

```json
{"name": "registry/register", "arguments": {
  "id": "documentation-engineer-server-<advertise_host>-<PORT>",
  "name": "Documentation Engineer MCP Server on <advertise_host>:<PORT>",
  "description": "AI agent автодокументации задач: ...",
  "endpoint": "http://<advertise_host>:<PORT>/mcp",
  "capabilities": {"tools": ["generate_task_docs"]}}}
```

Повторный `registry/register` обновляет `last_seen` — то есть служит heartbeat;
агент виден через `tools/call registry/list` и появляется на табе **Team**.
`MCP_ADVERTISE_HOST` задаёт хост в `endpoint`, чтобы URL был доступен другим
контейнерам. Недоступный реестр только логируется — сервер работает; после
сбоя следующая итерация перерегистрируется.

## Структура results-дерева (что читается)

```
results/<task_id>/
  task.json | meta.json            # описание задачи (description/task/body/summary), status
  description.md | task.md         # альтернатива описанию
  plan.json | plan.md              # план planner'а
  need_info.json | questions.json  # запросы need_info
  answers.json | clarifications.json  # ответы заказчика
  qa_contract.json | qa.md | acceptance.md  # QA-контракт
  <исходники>                      # финальный код (.py/.js/.go/...; каталоги docs/, node_modules/ и т.п. игнорируются)
  docs/                            # КУДА: REQUIREMENTS.md, ARCHITECTURE.md (создаётся)
```

Всё опционально: отсутствующие входы документируются как «не найдено», генерация
не падает. `REQUIREMENTS.md` содержит постановку, функциональные (FR-*) и
нефункциональные требования, принятые допущения (таблица need_info→ответы) и
критерии приёмки (AC-* из QA-контракта). `ARCHITECTURE.md` — обзор, таблица
модулей и ответственности (docstrings/функции/классы через `ast`), потоки данных
(точка входа, HTTP-маршруты), внешние зависимости, переменные окружения
(скан `os.environ`/`process.env`/`os.Getenv`), схема развёртывания.
Если `RESULTS_DIR` — git-копия, `docs/` коммитится (`docs: auto-documentation for <task>`)
и пушится; ошибка push логируется и не считается сбоем задачи.

## Хук в IT Lead (fire-and-forget)

После прохождения гейтов, **перед** переводом задачи в `done`, IT Lead вызывает
инструмент асинхронно; сбой доков не влияет на статус задачи — в activity пишется
`docs=ok`/`docs=skipped`:

```python
import json, threading, urllib.request

def docs_hook(task_id: str, log_activity):          # не блокирует и не бросает
    def _fire():
        try:
            body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                    "params": {"name": "generate_task_docs", "arguments": {"task_id": task_id}}}
            req = urllib.request.Request("http://documentation-engineer:5000/mcp",
                                         data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=120)
            log_activity(f"task={task_id} docs=ok")
        except Exception as exc:
            log_activity(f"task={task_id} docs=skipped ({exc})")
    threading.Thread(target=_fire, daemon=True).start()
```

Либо без MCP-клиента: `subprocess.Popen(["python", "main.py", "generate", task_id])`
в контейнере агента (тот же контракт activity-строк).

## Backfill (systemd-таймер, ночью)

`/etc/systemd/system/documentation-engineer.service`:

```ini
[Unit]
Description=documentation-engineer MCP server
After=network-online.target

[Service]
ExecStart=/usr/bin/python3 /opt/documentation-engineer/main.py serve
Environment=PORT=5000
Environment=REGISTRY_URL=http://127.0.0.1:3031
Environment=MCP_ADVERTISE_HOST=documentation-engineer
Environment=RESULTS_REPO=git@example.internal:team/results.git
Environment=RESULTS_DIR=/var/lib/documentation-engineer/results
Restart=always

[Install]
WantedBy=multi-user.target
```

`documentation-engineer-backfill.service` + `documentation-engineer-backfill.timer`:

```ini
# documentation-engineer-backfill.service
[Unit]
Description=Backfill docs/ for done tasks (14 days)

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /opt/documentation-engineer/main.py backfill --days 14
Environment=RESULTS_REPO=git@example.internal:team/results.git
Environment=RESULTS_DIR=/var/lib/documentation-engineer/results
```

```ini
# documentation-engineer-backfill.timer
[Unit]
Description=Nightly docs backfill

[Timer]
OnCalendar=*-*-* 03:15:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl enable --now documentation-engineer.service documentation-engineer-backfill.timer
```

Backfill проходит по `RESULTS_DIR`, берёт задачи со статусом `done` (`task.json.status`,
`STATUS`/`status.txt`/`.status` файл или маркер `done/`) с активностью за последние
14 дней и без `docs/`, генерирует документацию, пишет в лог activity-строки
`task=<id> docs=ok|skipped`.

## Acceptance-критерии (как выполнены)

- Новая задача после done имеет `docs/REQUIREMENTS.md` + `docs/ARCHITECTURE.md` — хук IT Lead + `generate_task_docs`.
- `documentation-engineer` виден в Team — регистрация + heartbeat в реестр `:3031`, URL из `MCP_ADVERTISE_HOST`.
- Падение агента не мешает задаче дойти до done — ошибки инструмента возвращаются как `isError`/`docs=skipped`, сервер не падает; хук fire-and-forget.

## References

- MCP streamable-http transport (JSON-RPC поверх HTTP POST, `Mcp-Session-Id`, 202 для notifications, protocolVersion `2025-06-18`): https://modelcontextprotocol.io/specification/2025-06-18/basic/transports
- Контракт реестра (:3031) взят из живого сервиса окружения: `GET http://127.0.0.1:3031/openapi.json` и `tools/list` на `/mcp` — инструменты `registry/register|list|unregister`; формат записи (id/name/endpoint/capabilities/last_seen) скопирован с уже зарегистрированных vendored-агентов (qa-engineer :3072, security :3073).
