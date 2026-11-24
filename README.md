# AI-orchestration

Конвейер мультиагентной разработки: **IT Lead → requirements → coder → QA →
security → devops + documentation** с web-дашбордом, колокольчиком уточнений,
реестром агентов (MCP) и ночным ретро-циклом. Прислал задачу через дашборд —
получил проверенный артефакт в git-репозитории результатов.

Работает на одном хосте (Debian 12+ / Ubuntu 24), PostgreSQL или SQLite.

## Установка на чистый хост (одна команда)

С управляющей машины, где есть ssh-root на целевой хост:

```bash
scp deploy/provision.sh root@ХОСТ:/tmp/
ssh root@ХОСТ "
  export LLM_PROVIDER_URL=http://LLM-ХОСТ:8081/v1/chat/completions
  export LLM_MODEL=имя-модели
  export MCP_GIT_REPO_URL=ssh://user@results-хост/home/user/mcp-results.git
  export RESULTS_SSH_KEY_B64=\$(base64 -w0 /path/to/ssh-ключ)   # опционально
  export DEPLOYMENT_HOST=публичный-ip-или-dns-хоста
  export USE_POSTGRES=false        # true = PostgreSQL
  bash /tmp/provision.sh"
```

`provision.sh` самодостаточен (единственный файл, который нужно перенести):
ставит git/curl/rsync из пакетного менеджера дистрибутива (apt/dnf/yum/apk),
клонирует этот репозиторий с GitHub, генерирует `.env` и `opencode.json`,
вызывает `deploy/install.sh` и в финале заводит self-E2E задачу через весь
конвейер. Успех — строка `E2E PASS - dashboard: http://ХОСТ:5173`.
Скрипт идемпотентен: повторный запуск = переконфигурация/апгрейд.

Пример готового запуска для своей сети — `deploy/provision.lan.example.sh`
(скопируйте и подставьте свои адреса; ключ держите вне git).

### Обязательные переменные

| Переменная | Что |
|---|---|
| `LLM_PROVIDER_URL` | OpenAI-совместимый chat endpoint (планировщик, гейты, ретро) |
| `LLM_MODEL` | модель для конвейера |
| `MCP_GIT_REPO_URL` | ssh-url git-репозитория артефактов (`results/<task>/`) |
| `DEPLOYMENT_HOST` | адрес хоста для публичных URL деплоев (иначе — первый IP) |
| `USE_POSTGRES` | `true` (по умолчанию) или `false` = SQLite без сервера БД |
| `RESULTS_SSH_KEY_B64` | base64 приватного ключа для results-репо; без него будет сгенерирован свой и выведен публичный — авторизуйте его на results-сервере |

Опционально: `SECURE_SEARCH_URL` (поиск для coder'а), `IMAGE_API_BASE`
(генерация картинок), `REPO_REF` (ветка, по умолчанию `v0.5.11`),
`ORCH_DIR` (каталог установки, по умолчанию `/opt/ai-orchestration`).

## Что поднимается (9 сервисов)

| Сервис | Порт | Роль |
|---|---|---|
| mcp-registry | 3031 | реестр агентов (heartbeat 30s, self-heal) |
| mcp-implementation-engineer | 3060 | coder (opencode или per-file fallback) |
| mcp-it-lead | 3061 | оркестратор конвейера |
| mcp-requirements-engineer | 3062 | декомпозиция требований |
| mcp-team-management | 3063 | состав команды |
| mcp-devops-release-engineer | 3071 | деплой артефактов (docker + nginx edge :3080) |
| mcp-qa-engineer | 3072 | QA-гейт (тесты, visual) |
| mcp-security-reviewer | 3073 | security-гейт |
| mcp-documentation-engineer | 3074 | авто-доки по задаче (arc42/Diátaxis) |
| web-ui | :8000 + :5173 | дашборд (backend + vite frontend) |

Плюс systemd-таймеры `mcp-retro-observer` (ночное ретро) и
`mcp-deployment-warden` (watchdog деплоев).

## Проверка после установки

```bash
curl -s localhost:8000/api/tasks | head -c 200     # web-ui backend
curl -s -X POST localhost:3061/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | head -c 200   # IT Lead
```

Дашборд: `http://DEPLOYMENT_HOST:5173` → создать задачу «python script,
prints date» → дождаться `done`.

## Далее

- [DEPLOY.md](DEPLOY.md) — требования к хосту, конфигурация `.env`, SQLite
  fallback, HTTPS для уведомлений, промоушен сервисов (`promote-service`),
  бэкап/откат.
- Структура: `systemd/` — юниты сервисов (единственный источник правды,
  ставятся `deploy/install.sh`); `deploy/provision.sh` — bootstrap хоста;
  `*-mcp-server/` — агенты; `it-lead-mcp-server/web-ui/` — дашборд;
  `scripts/promote_service.py` — превращение deliverable в ставящийся сервис.
