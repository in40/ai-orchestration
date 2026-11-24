# План: вычищаем hardcoded-фолбэки (remote-safety cleanup)

Цель: система на любом чужом хосте либо работает корректно, либо падает
громко с внятным сообщением. Никаких тихих дефолтов на нашу инфраструктуру
(.187 results-репо, .237/.105 LLM, /root/qwen/base, LAN-эвристики UI).

Принципы:
- env обязателен там, где значение специфично для инсталляции;
- ошибка — в момент использования (не импорта), текст: что задать и где;
- одна фаза = один коммит = один деплой на deploy-хост + smoke;
- откат фазы = git revert коммита.

Порядок: F → A → B → C → D → E (по убыванию пользовательского эффекта).

---

## Фаза F — фронтенд (ломает UX на любом не-основном хосте)

F1. `web-ui/frontend/src/components/Dashboard.jsx:26`
    `useWebSocket('ws://localhost:8000/ws')`
    → `const WS_URL = \`ws://${window.location.hostname}:${import.meta.env.VITE_BACKEND_PORT ?? 8000}/ws\``
    Проверить другие вызовы useWebSocket (grep) — все через ту же константу.

F2. `web-ui/frontend/src/components/TaskManagement.jsx:758`
    `disabled={!selectedTaskHistory.git_url.includes('192.168.51')}`
    → показывать кнопку для любого ssh/http git_url:
    `disabled={!/^(ssh|https?):\/\//.test(selectedTaskHistory.git_url || '')}`
    (ссылка «Git Server Web» уже строится replace'ом ssh://→http://).

F3. `npm ci && npm run build` в frontend; проверить, что vite-config не
    хардкодит API-base (grep localhost в frontend/src).

Тест: открыть дашборд deploy-хоста по IP с другой машины — live-обновления
идут (websocket подключился), кнопка Git Server Web активна на задаче с
ssh:// git_url.

## Фаза A — MCP_GIT_REPO_URL: убрать 15 фолбэков на .187

A1. Хелпер (дублируется в каждый сервис — сервисы независимы, это принятый
    паттерн репо):
    ```python
    def results_repo_url():
        url = (os.environ.get("MCP_GIT_REPO_URL") or "").strip()
        if not url:
            raise RuntimeError(
                "MCP_GIT_REPO_URL is not set - add the ssh url of the "
                "results repository to .env (e.g. ssh://user@host/home/user/mcp-results.git)")
        return url
    ```
A2. Точки замены (убрать литерал-дефолт, звать хелпер):
    - it-lead: `utils/task_assignment.py` 456, 689, 2162, 2922, 3227;
      `utils/self_fix.py:23` (хелпер в `utils/env_helpers.py`, импорт)
    - coder: `dependencies/vibe_coder.py` 406, 609, 652, 705, 1340, 1501
    - devops: `handlers/server_handlers.py:52` (DEFAULT_GIT_REPO_URL →
      функция), `server.py:289`
    - qa: `handlers/qa_engineer_handlers.py:21`
    - security: `handlers/security_handlers.py:15`
    - requirements: `requirement_engineer_handlers.py:130`
A3. `config.py`: GIT_SERVER_HOST/GIT_REPO_PATH/GIT_REPO_URL defaults (.187)
    → None + описание «set in .env»; проверить, кто их читает (легаси — если
    только reprocess/diagnose, поправить и их).
A4. Поведение при unset: задача доходит до build/push и падает с текстом
    хелпера в activity (не молча в чужой репо).

Тест: на deploy — `MCP_GIT_REPO_URL=` пусто в .env → задача failed с нашим
сообщением в status_reason; вернуть значение → E2E PASS.

## Фаза B — LLM-эндпоинты (.237:1234, .105)

B1. `config.py:150` LLM_PROVIDER_URL default → None (по образцу LLM_MODEL:
    «MUST be set in .env, no hardcoded default»).
B2. argparse в `it-lead/server.py:527`, `devops/server.py:520`,
    `requirements/requirement_engineer_server.py:447`: default=None;
    после parse: `if not args.llm_provider_url: parser.error("set LLM_PROVIDER_URL in .env or pass --llm-provider-url")`.
    Юниты подают ${LLM_PROVIDER_URL} из .env → при пустом значении сервис
    не стартует (было: тихие походы на мёртвый .237).
B3. `it-lead/handlers/server_handlers.py:18` конструктор default → None.
B4. `requirement_engineer_handlers.py:1157` — `http://192.168.51.237:1234/v1/models`
    → вывести из LLM_PROVIDER_URL (`url.rsplit('/chat/completions',1)[0] + '/models'`).
B5. coder `config.py:17` llm_base_url → env (LLM_BASE_URL или производная
    LLM_PROVIDER_URL), default None + проверка при использовании.
B6. `image-tools/image_tools_mcp.py:21` IMAGE_API_BASE → без дефолта;
    tool возвращает «IMAGE_API_BASE not set» per-call (фича опциональна).
B7. Утилиты `reprocess_submitted_tasks.py:31,36`, `diagnose_task_stuck.py:164`:
    читать env без литералов.

Тест: на deploy убрать LLM_PROVIDER_URL из .env → mcp-it-lead в failed с
нашим текстом; вернуть → всё active + E2E PASS.

## Фаза C — products mirror (.187)

C1. `products.py:22-23`: PROJECTS_SSH/PROJECTS_DIR default → None.
C2. `_mirror_url`/publish/import: если None → raise «products mirror not
    configured (set PROJECTS_SSH/PROJECTS_DIR)».
C3. `_sync_product_mirror` в task_assignment уже в try/except → лог и
    продолжение (задача не падает, зеркало просто выключено).

Тест: на deploy без PROJECTS_SSH задача с product_id проходит гейты, в
activity нет mirror-ошибки, ломающую статус; с заданным — mirror работает.

## Фаза D — postgres-пароль «postgres»

D1. `db_compat.connect(..., password=None)`: если password None →
    `os.environ.get("POSTGRES_PASSWORD")`; нет и там → пробовать без пароля
    (libpq), при отказе — штатный sqlite-fallback (уже логируется).
D2. Call-sites `os.environ.get("POSTGRES_PASSWORD", "postgres")` → без
    дефолта: task_storage (все копии), devops `_db_connect`, web-ui updater,
    registry копии, retro/_compat.
D3. Юниты `Environment="POSTGRES_PASSWORD=postgres"` НЕ трогаем: это
    документированный dev-дефолт, перебивается EnvironmentFile=.env;
    на sqlite-хостах безвреден.

Тест: PG-регрессия на основном хосте (задача до done); на deploy — sqlite
как сейчас.

## Фаза E — BASE_DIR default /root/qwen/base

E1. Точки: it-lead `human_interface_handlers.py:766,778`,
    `llm_task_planner.py:92`, `products.py:26`, `self_fix.py:20,250`,
    `task_assignment.py:788`; `retro/_compat.py`; `document-store/config.py`;
    корневой `config.py:264,269`.
E2. Шаблон: `os.environ.get("BASE_DIR") or str(Path(__file__).resolve().parents[N])`
    (N подбирается по файлу: it-lead utils → parents[3], retro → parents[1],
    document-store → parents[1]).
E3. Мёртвые утилиты с абсолютными путями (`add_git_endpoints.py`) — не
    чиним, удалить в финальной уборке если `git grep` не находит импортов.

Тест: на deploy запустить `retro/observer.py` и `reprocess_submitted_tasks.py`
из произвольного cwd без BASE_DIR — работают в /opt/ai-orchestration.

## Фаза G — явно НЕ трогаем (решение зафиксировано)

- `DEPLOYMENT_HOST` default `127.0.0.1` — loopback, безопасен.
- `"endpoint": "http://localhost:8081"` в example_tool скелетов — демо-данные.
- `config.py:44` NETWORK_DOMAIN `192.168.51.0/24` — SSRF-allowlist,
  env-переопределяем; сделать обязательным в след. итерации (не блокирует).
- systemd-юниты с /root/qwen/base — install.sh переписывает при установке.

## Финальная приёмка (после всех фаз)

1. `git grep -nE "192\.168\.[0-9]+\.[0-9]+" -- '*.py' ':!*test*' ':!*venv*'`
   → только config.py NETWORK_DOMAIN и комментарии.
2. `git grep -n 'mcp-results.git"' -- '*.py'` → пусто.
3. `git grep -n '/root/qwen/base' -- '*.py' ':!*test*'` → пусто.
4. `git grep -n 'localhost:8000' -- '*/frontend/src/*'` → пусто.
5. Полный прогон provision на обнулённом deploy + ревизия (8/8 реестр,
   retro-цепочка, TEAM, E2E done).
6. PG-регрессия на основном хосте (задача до done).

Оценка: F ~30 мин; A ~1 ч; B ~1 ч; C ~20 мин; D ~40 мин; E ~40 мин;
приёмка ~1 ч. Каждый коммит: `cleanup(x): ...` + строка в IMPROVEMENT_BACKLOG.md.

---

## СТАТУС: выполнено (F, A, B, C, D, E)

Все фазы закоммичены и проверены на обоих бэкендах:
- deploy (sqlite): E2E `cleanup-e2e-*` → done, QA PASS, артефакт запушен;
  реестр 8/8; retro-цепочка зелёная.
- основной хост (postgres): `pg-cleanup-*` → done, QA PASS; db_compat
  PG-путь проверен (password=None→env).

Пойманный по ходу регресс (исправлен): coder `llm_base_url` после фазы B
остался без значения (юнит экспортирует LLM_PROVIDER_URL, а не
LLM_BASE_URL) → generate_file давал '/chat/completions'. Теперь
деривится из LLM_PROVIDER_URL со снятием /chat/completions.

Приёмочные grep: в runtime-коде не осталось 192.168.* (кроме
config.NETWORK_DOMAIN — SSRF-allowlist, env-переопределяем),
mcp-results.git (кроме текстов ошибок/докстрок), localhost:8000 в
фронтенде — нет.

Остатки (вне runtime, осознанно не тронуты):
- `document-store-mcp-server/*` — удалён: это порт сервиса из другого проекта
  (`/root/qwen/ai_agent`, «smart ingestion»), занесённый сюда случайно
  (коммит `09cfa1f`) и никогда не работавший в оркестрации (юнита нет, deps не
  поставлены, пайплайн его не дёргает). Убран из репо и из install.sh UNITS.
- корневые одноразовые dev-скрипты `fix_*.py`, `patch_*.py`,
  `update_llm_prompts.py`, `trace_task.py`, `add_git_endpoints.py`,
  `check_state.py` — исторические миграционные tools, никем не
  импортируются; кандидаты на удаление (требуется решение).
