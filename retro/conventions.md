<!-- Learned coder conventions (retro M2). Each approved R1 proposal appends
     one bullet here; the text is injected into every build's AGENTS.md at
     build time. Revert = git revert the commit that added the line. -->

Не добавляй секреты, пароли и токены в код; используй переменные окружения или config placeholders. Не добавляй уязвимые/незапиненные зависимости и exec/eval/unsafe deserialization; перед сдачей проверь зависимости на известные уязвимости. (retro #3)
