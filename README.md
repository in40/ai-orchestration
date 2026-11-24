# AI-orchestration

Конвейер мультиагентной разработки: **IT Lead → requirements → coder → QA →
security → devops + documentation** с web-дашбордом, колокольчиком уточнений,
реестром агентов (MCP) и ночным ретро-циклом. Прислал задачу через дашборд —
получил проверенный артефакт в git-репозитории результатов.

Работает на одном хосте (Debian 12+ / Ubuntu 24), PostgreSQL или SQLite.

## Установка

Ставится одним самодостаточным файлом `deploy/provision.sh`: он ставит
зависимости ОС (git/curl/rsync через apt/dnf/yum/apk), клонирует этот
репозиторий с GitHub, генерирует `.env` и `opencode.json`, вызывает
`deploy/install.sh` и в финале заводит self-E2E задачу через весь конвейер.
Идемпотентен: повторный запуск = переконфигурация/апгрейд.

### Вариант 1 — прямо на хосте (без управляющей машины)

Зайти на целевой хост по ssh под root и выполнить:

```bash
# 1. забрать установщик (единственный нужный файл)
curl -fsSL https://raw.githubusercontent.com/in40/ai-orchestration/v0.5.11/deploy/provision.sh -o /tmp/provision.sh
# нет curl? wget -O /tmp/provision.sh <тот же url>; совсем голо — скопировать
# файл любым способом (scp с ноутбука, paste)

# 2. настройки (см. таблицу ниже)
export LLM_PROVIDER_URL=http://LLM-ХОСТ:8081/v1/chat/completions
export LLM_MODEL=имя-модели
export MCP_GIT_REPO_URL=ssh://user@results-хост/home/user/mcp-results.git
export DEPLOYMENT_HOST=публичный-ip-этого-хоста  # опционально: по умолчанию
#                                    берётся первый IP хоста; нужен, если
#                                    адрес наружу другой (NAT, не-первый
#                                    интерфейс) или хотите DNS-имя
export USE_POSTGRES=false          # true = PostgreSQL
# если на хосте уже есть ключ для results-репо:
export RESULTS_SSH_KEY_B64=$(base64 -w0 /root/.ssh/id_ed25519)

# 3. запуск (от root)
bash /tmp/provision.sh
```

Готово через ~10–15 минут: `E2E PASS - dashboard: http://ХОСТ:5173`.

### Вариант 2 — удалённо с управляющей машины

```bash
scp deploy/provision.sh root@ХОСТ:/tmp/
ssh root@ХОСТ "bash -lc 'export LLM_PROVIDER_URL=... LLM_MODEL=... \
  MCP_GIT_REPO_URL=... DEPLOYMENT_HOST=... USE_POSTGRES=false; bash /tmp/provision.sh'"
```

Пример готового запуска для своей сети — `deploy/provision.lan.example.sh`
(скопируйте и подставьте свои адреса; ключ держите вне git).

### Вариант 3 — совсем вручную (без provision.sh)

Если нужен полный контроль каждого шага:

```bash
apt-get install -y git curl rsync      # или dnf/yum/apk
git clone https://github.com/in40/ai-orchestration && cd ai-orchestration
cp .env.example .env                   # заполнить LLM_*, MCP_GIT_REPO_URL,
                                       # DEPLOYMENT_HOST, POSTGRES_*
./deploy/install.sh                    # идемпотентен; повтор после git pull = апгрейд
```

Устанавливает то же самое, но без генерации `.env`/`opencode.json`,
ssh-ключа results-репо и self-E2E — см. разделы «Конфигурация» и «Проверка»
в [DEPLOY.md](DEPLOY.md).

### Переменные окружения

| Переменная | Что |
|---|---|
| `LLM_PROVIDER_URL` | OpenAI-совместимый chat endpoint (планировщик, гейты, ретро) |
| `LLM_MODEL` | модель для конвейера |
| `MCP_GIT_REPO_URL` | ssh-url git-репозитория артефактов (`results/<task>/`) |
| `DEPLOYMENT_HOST` | адрес хоста для публичных URL деплоев (иначе — первый IP) |
| `USE_POSTGRES` | `true` (по умолчанию) или `false` = SQLite без сервера БД |
| `POSTGRES_HOST` / `POSTGRES_PORT` / `POSTGRES_DB` / `POSTGRES_USER` | только при `USE_POSTGRES=true`; по умолчанию локальный кластер `127.0.0.1:5432/mcp_registry/postgres` — установщик сам ставит сервер и создаёт роль/БД. Не-локальный `POSTGRES_HOST` = **внешний** кластер: локальный сервер не ставится, роль и БД должны быть уже созданы вашим админом |
| `POSTGRES_PASSWORD` | для локального генерируется, если не задан; для **внешнего обязателен** |
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
