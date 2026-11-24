# Развёртывание AI-orchestration (single host)

## Быстрый старт (чистый хост, одна команда)
С управляющей машины (или вручную скопировав единственный файл deploy/provision.sh):
```
export LLM_PROVIDER_URL=http://<llm-host>:8081/v1/chat/completions LLM_MODEL=<model> \
       MCP_GIT_REPO_URL=ssh://<user>@<host>/home/<user>/mcp-results.git \
       DEPLOYMENT_HOST=<этот-хост> USE_POSTGRES=false
bash deploy/provision.sh
```
provision.sh сам ставит git/curl (apt/dnf/yum/apk), клонит репозиторий с GitHub,
генерирует .env и opencode.json, вызывает install.sh и в конце заводит
self-E2E задачу через весь конвейер (PASS = система жива).

Конвейер «IT Lead → coder → QA → security → devops» с web-дашбордом,
колокольчиком уточнений и ночным ретро-циклом.

## Требования к хосту
| Компонент | Зачем | Обязателен |
|---|---|---|
| python3.11+ (с `python-is-python3`), node 18+, nginx, postgres, git | стек сервисов; QA-gate вызывает `python` | да |
| OpenAI-совместимый LLM-эндпоинт (`LLM_PROVIDER_URL`, `LLM_MODEL`) | планировщик, гейты, ретро | да (сильная модель для coder-fallback) |
| [opencode](https://github.com/sst/opencode) CLI (`curl -fsSL https://opencode.ai/install | bash`) + `~/.config/opencode/opencode.json` | основной режим сборки coder'а | **да** |
| docker | запуск деплоев (devops + warden) | **да** |
| git-репозиторий результатов (`MCP_GIT_REPO_URL`, ssh-ключ для root И пользователя) | хранение артефактов | да |
| chromium (или chrome-headless-shell) | visual-gate и скриншоты: `HEADLESS_SHELL=/usr/bin/chromium` | рекомендовано |
| secure-search MCP (`SECURE_SEARCH_URL` в .env, подставляется в opencode.json) | поиск для coder'а | опционально |
| flux2-совместимый image API (`IMAGE_API_BASE`) | генерация картинок coder'ом | опционально |
| nginx edge :3080 | публичные URL деплоев | да |

## Установка
```
git clone https://github.com/in40/ai-orchestration && cd ai-orchestration
sudo ./deploy/install.sh /opt/ai-orchestration
# редактор откроет .env.example -> .env: заполните POSTGRES_*, LLM_*,
# MCP_GIT_REPO_URL, DEPLOYMENT_HOST, OPENCODE_PASSWORD — скрипт попросит повторить запуск
sudo ./deploy/install.sh /opt/ai-orchestration
```
Скрипт идемпотентен: повторный запуск после `git pull` = апгрейд.

## Что поднимается
`mcp-registry`, 5 агентских MCP-серверов, `mcp-it-lead` (оркестратор),
web-ui (:8000 backend + :5173 frontend), edge-proxy :3080,
`mcp-deployment-warden` (watchdog), `mcp-retro-observer.timer` (03:00).
Опционально `mcp-opencode-serve` (:4097) — если установлен opencode CLI.

## Конфигурация
Все настройки в `.env` (см. `.env.example`). Ключевые:
- `LLM_PROVIDER_URL` / `LLM_MODEL` — мозг конвейера
- `MCP_GIT_REPO_URL` — ssh-url репозитория артефактов (нужен ssh-доступ)
- `DEPLOYMENT_HOST` — адрес хоста для публичных URL деплоев
- `POSTGRES_*` — БД реестра задач (таблицы создаются сервисами); при
  `USE_POSTGRES=true` локальный кластер ставится/создаётся установщиком,
  не-локальный `POSTGRES_HOST` = внешний кластер (роль/БД создаёт админ,
  `POSTGRES_PASSWORD` обязателен)
- `USE_POSTGRES=false` — работать на SQLite вместо PostgreSQL (см. ниже)
- `SHOTS_DIR`, `HEADLESS_SHELL`, `IMAGE_API_BASE` — vision/generation

## SQLite fallback (без PostgreSQL)
`USE_POSTGRES=false` (или недоступный сервер) — весь стек работает на SQLite
(`SQLITE_PATH`, по умолчанию `$BASE_DIR/data/mcp_registry.db`, WAL).
Проверено боевым E2E: полный конвейер (plan→build→QA→security→docs→done),
clarifications, дашборд. Ограничение: retro-аналитика (`retro/*`) на SQLite
пропускается. Бэкап — копия файла `*.db` (+ `-wal`).

## Проверка
```
curl -s localhost:8000/api/tasks | head -c 200        # web-ui backend
curl -s -X POST localhost:3061/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | head -c 200   # IT Lead
```
Дашборд: `http://<DEPLOYMENT_HOST>:5173` → создать задачу «python script,
prints date» → дождаться done.

## Дашборд по HTTPS (рекомендовано)
Системные уведомления браузера работают только на secure-context:
```
openssl req -x509 -newkey rsa:2048 -keyout /root/certs/dash.key \
  -out /root/certs/dash.crt -days 3650 -nodes \
  -subj "/CN=<HOST>" -addext "subjectAltName=IP:<HOST>"
```
vite подхватит сертификаты автоматически (см. vite.config.js).

## Промоушен сервиса, собранного конвейером
Конвейер кладёт код в results-репо (`results/<task>/`), но сервис становится
ставящимся на любой хост только когда он задекларирован в оркестрационном репо:
`systemd/<name>.service` + строка в `deploy/install.sh` (`UNITS`). Раньше этот
шаг был ручным, и documentation-engineer через него провалился (юнит сделали
вручную только на проде → на свежих хостах 8 сервисов, на проде 9).

`scripts/promote_service.py` (stdlib-only) закрывает разрыв:
- `check` — структурный гейт: каждый юнит из `systemd/` ставится install.sh,
  каждая запись `UNITS` имеет файл юнита, нет коллизий портов; `*-mcp-server/`
  без юнита показывается как подсказка. `--strict` → exit 1 (для CI/QA),
  `--json` — машиночитаемо, `--deliverable DIR` — проверить заготовку.
- `promote --source <results/task|*-mcp-server/>` — генерит портируемый юнит
  (env-driven, без хардкодов хоста; `MCP_ADVERTISE_HOST`/`RESULTS_REPO` из
  `.env`) и добавляет его в `UNITS`. `--copy` кладёт код в репо, `--commit`/
  `--push` — git. Идемпотентно; `--dry-run` — предпросмотр.
- `ports` — занятые/свободные порты (новый сервис берёт следующий свободный от 3075).

```
python3 scripts/promote_service.py check --strict
python3 scripts/promote_service.py promote --source results/<task>/ \
    --name foo-engineer --copy --commit
./deploy/install.sh   # хост подхватит новый сервис
```
Юнит на `python3` подходит только stdlib-сервисам; при зависимостях передайте
`--exec "python -m <pkg>.server ..."` — install.sh перепишет `python -m` на venv.

## Безопасный рестарт сервисов
`mcp-implementation-engineer` держит долгие HTTP-запросы it-lead (opencode-сборка
— до часа). Рестарт юнита **обрывает активную сборку**: задача падает в `failed`
с `RemoteDisconnected` (проверено боем). Поэтому перед рестартом coder/it-lead:

```bash
# есть ли живые задачи?
curl -s localhost:8000/api/tasks | python3 -c "import json,sys; \
print([t['id']+'='+t['status'] for t in json.load(sys.stdin) \
if t['status'] in ('in_progress','review','rework_in_progress','awaiting_input')])"
```

Если есть активные — дождаться, либо остановить задачи (кнопка ■ Stop /
`cancel_task`). (Список сессий `GET :4097/api/session` для этой проверки не
годится: он показывает и давно простаивающие сессии без признака завершенности.)
Если рестарт назрел, а сборку жалко: workspace (`/tmp/oc-builds/<task>`) при
рестарте **не теряется** — после рестарта восстановить задачу в 1 клик:
`POST /api/tasks/<id>/restart {"from_step":"build"}` (резюм той же
opencode-сессии). web-ui backend, наоборот, перезапускать можно свободно —
его запросы короткие; порядок: `stop mcp-web-ui-watchdog` → `restart
mcp-web-ui-backend` → `start mcp-web-ui-watchdog`.

## Откат/бэкап
Код — git; состояние — `pg_dump mcp_registry` (или копия `data/*.db*` на SQLite);
конфиги — `.env`,
`~/.config/opencode`, `/etc/nginx`. Пример полного бэкапа:
`/root/backups/20261123-pre-open-hardening/RESTORE.md`.
