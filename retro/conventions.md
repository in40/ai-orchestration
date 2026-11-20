<!-- Learned coder conventions (retro M2). Each approved R1 proposal appends
     one bullet here; the text is injected into every build's AGENTS.md at
     build time. Revert = git revert the commit that added the line. -->

Не добавляй секреты, пароли и токены в код; используй переменные окружения или config placeholders. Не добавляй уязвимые/незапиненные зависимости и exec/eval/unsafe deserialization; перед сдачей проверь зависимости на известные уязвимости. (retro #3)

Перед сдачей выполни минимальный smoke-запуск/тесты и проверь, что артефакт полный и синтаксически валидный: баланс скобок, отсутствие заглушек и обрезанного кода; не отправляй фрагменты. (retro #2)

For JavaScript tasks, submit complete runnable code that satisfies every QA check, not only syntax: include all required files, exports, tests/fixtures, and no placeholders; run local syntax/lint and the task's acceptance command before handoff. [ui-dogfood-1795100260, selffix-1795107079] (retro #6)
