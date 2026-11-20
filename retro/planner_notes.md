<!-- Learned planner notes (retro M2). Appended to the task-planning prompt
     at plan time. Keep entries short and operational. -->

Перед постановкой задачи кодеру зафиксируй MVP, точные acceptance criteria и out-of-scope; любые новые фичи/смены темы/LLM/NPU выноси в отдельный task после подтверждения пользователем; не передавай в coder расширяющиеся требования.

Before coding, define a frozen scope with explicit acceptance criteria and out-of-scope list; any new feature or UI change after task start must be split into a new task or approved change request, not added to the current task. [task-1794906501267, task-1795002226860] (retro #7)

Задачи-«новые члены команды» (MCP-серверы, systemd-агенты вроде documentation-engineer) НЕ помечать deploy_after_implementation: их рантайм — systemd-юнит mcp-<name>.service с регистрацией в реестре :3031, а не веб-контейнер на 3080. В acceptance указывать «сервис ставится как systemd unit и виден в Team», деплой-шаг для них лишний. [task-1795177573344]
