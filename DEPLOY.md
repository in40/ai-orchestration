# Развёртывание AI-orchestration (single host)

Конвейер «IT Lead → coder → QA → security → devops» с web-дашбордом,
колокольчиком уточнений и ночным ретро-циклом.

## Требования к хосту
| Компонент | Зачем | Обязателен |
|---|---|---|
| python3.11+, node 18+, nginx, postgres, git | стек сервисов | да |
| OpenAI-совместимый LLM-эндпоинт (`LLM_PROVIDER_URL`, `LLM_MODEL`) | планировщик, гейты, ретро | да (сильная модель для coder-fallback) |
| [opencode](https://github.com/sst/opencode) CLI + `~/.config/opencode/opencode.json` | основной режим сборки (сессия coder'а) | рекомендовано |
| git-репозиторий результатов (`MCP_GIT_REPO_URL`, ssh-ключ) | хранение артефактов | да |
| chrome-headless-shell | visual-gate и скриншоты (`HEADLESS_SHELL`) | опционально |
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
- `POSTGRES_*` — БД реестра задач (таблицы создаются сервисами)
- `SHOTS_DIR`, `HEADLESS_SHELL`, `IMAGE_API_BASE` — vision/generation

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

## Откат/бэкап
Код — git; состояние — `pg_dump mcp_registry`; конфиги — `.env`,
`~/.config/opencode`, `/etc/nginx`. Пример полного бэкапа:
`/root/backups/20261123-pre-open-hardening/RESTORE.md`.
