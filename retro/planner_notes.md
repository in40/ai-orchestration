<!-- Learned planner notes (retro M2). Appended to the task-planning prompt
     at plan time. Keep entries short and operational. -->

Перед постановкой задачи кодеру зафиксируй MVP, точные acceptance criteria и out-of-scope; любые новые фичи/смены темы/LLM/NPU выноси в отдельный task после подтверждения пользователем; не передавай в coder расширяющиеся требования.

Before coding, define a frozen scope with explicit acceptance criteria and out-of-scope list; any new feature or UI change after task start must be split into a new task or approved change request, not added to the current task. [task-1794906501267, task-1795002226860] (retro #7)

Задачи-«новые члены команды» (MCP-серверы, systemd-агенты вроде documentation-engineer) НЕ помечать deploy_after_implementation: их рантайм — systemd-юнит mcp-<name>.service с регистрацией в реестре :3031, а не веб-контейнер на 3080. В acceptance указывать «сервис ставится как systemd unit и виден в Team», деплой-шаг для них лишний. [task-1795177573344]

## Паспорт платформы (не спрашивать у заказчика — это известно)
- Стек: Python 3.13; web-ui backend — FastAPI+uvicorn :8000 (it-lead-mcp-server/web-ui/backend/main.py); фронт — React 18 + MUI 5 + Vite :5173 (web-ui/frontend/src); БД — PostgreSQL 127.0.0.1:5432 db=mcp_registry user=postgres; сервисы — MCP-агенты (JSON-RPC/streamable-http) под systemd mcp-*.service.
- Хосты: эта машина 192.168.51.215 (root); хост артефактов 192.168.51.187 (пользователь sorokin, ssh-ключ root'а).
- Results-репо: ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git; рабочие клоны: /tmp/mcp-vibe-coding-git/repo (IT Lead), /tmp/mcp-vibe-coding-git/docs-repo (documentation-engineer).
- GitHub: пользователь in40; PAT в /root/qwen/base/.env (GITHUB_TOKEN/PAT), в код/логи не светить.
- Инфра-задачи (GC, таймеры, systemd) выполняются: root@192.168.51.215, к .187 — по ssh sorokin@192.168.51.187.
- Спрашивать заказчика разрешается только про решения/предпочтения (имена, приватность, приоритеты), не про эти факты.

Devops-шаг (deploy) добавляй в workflow ТОЛЬКО если заказчик явно просит задеплоить/отдать ссылку URL. Артефакты-модули платформы (библиотеки, CLI, systemd-юниты, инструменты MCP) не деплоятся: их проверка — тесты/запуск в песочнице, а не контейнер на 3080. [task-1795202524381]

- Для UI-задач добавляй в критерии приёмки точные видимые подписи/иконки, поведение фильтров и копирования (только видимые строки), цветовую палитру и текст подсказок/примеров промптов; при отсутствии макета запроси уточнение. [task-1795002226860, task-1794906501267, task-1794842620157] (retro #9)
