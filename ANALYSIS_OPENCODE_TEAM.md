# OpenCode как рантайм для членов команды — research + анализ
(2026-11-11. PoC на живой инфраструктуре + internet research.)

## TL;DR
Наши агенты — «мозг без рук»: каждый член команды это один big-call в LLM без
инструментов. OpenCode даёт каждому агенту tool-loop (read/write/bash/pytest)
со самотверификацией. PoC: `opencode run` на halogen за **17 с** написал код +
тесты + прогнал pytest до зелёных (4 шага). Литература: execution-feedback
агенты дают 3–5× к pass-rate против single-shot (SWE-bench). Рекомендуемый
порядок: B (repair-loop) → C (review-tools) → A (coder-with-hands) → D (serve).

## 1. Где у нас single-shot (карта вызовов)
| Агент | Вызов | Проблема |
|---|---|---|
| coder `generate_file` | 1 prompt → файл → git push | не видит соседей, не может проверить импорт, код «на веру» |
| coder `vibe_code_async` | 1 prompt → весь проект | то же, масштабнее |
| coder `patch_file` (repair) | 1 prompt + текст ошибки | не может воспроизвести ошибку, чинит вслепую |
| QA `plan_run_contract` | README → контракт | угадывает, не открывая entry points |
| security `scan_artifact` | regex + pip-audit | нет LLM-понимания (SQLi-класс мимо regex) |
| IT Lead planner / advisory review | 1 prompt, код 12K-блобом | ревью с обрезанным контекстом |

Наша E2E-история — это ровно классы отказов, которые ловит tool-loop:
tmplC SDK-mimicry (агент не мог открыть реальный SDK), tmpl9 runtime TypeError
(никто не запускал код до деплоя), interface drift (агенты не читали файлы
друг друга). Пайплайн компенсирует снаружи (retry, repair loop, QA gate), но
каждая компенсация = ещё один слепой LLM-вызов.

## 2. Что проверено живьём (не теория)
- opencode v2.2.7 установлен; halogen уже настроен как provider `hallogen`
  (192.168.51.105:8081/v1, model qwen3.8-next).
- **halogen нативно поддерживает tool_calls** (проверил: finish_reason=tool_calls,
  корректный JSON аргументов) — без этого opencode невозможен.
- **PoC**: `opencode run --model hallogen/qwen3.8-next --auto "add.py + тесты +
  pytest до зелёных"` → 17 s, 4 model steps, 3 tool calls, 5/5 tests green.
  Модель сама написала, сама запустила, сама подтвердила.
- `opencode run` флаги под наш кейс: `--agent` (профиль с permissions),
  `--session` (продолжить сессию — repair продолжает контекст генерации!),
  `--fork`, `--worktree` (изоляция), `--format json` (машинный парсинг),
  `--auto` (auto-approve не-запрещённого).
- `opencode serve` — HTTP API: POST /session, /session/:id/message (или
  prompt_async), /session/:id/diff, /event SSE, /session/:id/permissions/:id.
  OpenAPI на /doc. Идеально ложится в наши python-MCP-обёртки (requests).
- Кастомные агенты: `.opencode/agents/coder.md` — system prompt + model +
  `permissions` (deny edit/shell точечно) + `steps` (капа на цикл).
- Движки для разгрузки batch-1: в конфиге есть hallogen, fedora(lmstudio),
  vllm(:8000 — сейчас не отвечает), h100-t1/deckard (401 без ключа — живы,
  нужен auth). opencode позволяет **модель на агента**: coder на halogen,
  reviewer на deckard/h100.

## 3. Research-контекст
- Agentic loops с реальным внешним фидбеком (запуск тестов/кода) устойчиво
  повышают качество: лучшие системы 3–5× zero-shot на SWE-bench; OpenHands 72%,
  Mini-SWE-Agent 74% — и у того, и у другого единственный «инструмент» — bash.
  Само-рефлексия без внешнего чека почти не помогает (ai-tldr, dev.to).
- Обратная сторона (SWE-EVO, 2026): на длинных multi-file задачах агенты падают
  65%→21% — tool-loop не отменяет нужен хороший план. Наш planner+manifest
  остаётся; opencode усиливает именно исполнение.
- Headless-практика: в CI `opencode run` по умолчанию разрешает edit/shell —
  значит для нас обязательны явные deny-правила (git push, сеть, .env) и
  `steps`-капа. Паттерн «orchestrator dispatchит sub-agents» (plan/review/
  implement) уже сложился в комьюнити-конфигах.

## 4. Варианты

### A. «Coder с руками» — fan-out → одна opencode-сессия на задачу
IT Lead вместо 6× `generate_file` готовит workspace `/tmp/oc/<task>/`
(manifest + AGENTS.md с нашими правилами), запускает
`opencode run --agent coder --session <task> --format json "реализуй manifest"`.
Агент пишет файлы, читает соседей, гоняет pytest/импорты, итератит до зелёных.
IT Lead коммитит workspace в results-repo (git push остаётся у нас — аудит).
QA/security/deploy гейты не меняются.
**Effort M, Value H.** Убивает классы tmplC/tmpl9/drift. Риск: шаги×контекст на
batch-1 (см. §5).

### B. Repair-loop через opencode (лучший value/effort)
`patch_file` → `opencode run --session <та же сессия генерации> --agent fixer
"ошибка: <traceback>"`. Агент воспроизводит, чинит, перепроверяет. Продолжение
сессии = контекст уже в истории, дешёвый prefill.
**Effort S-M, Value H.**

### C. Инструменты для QA/Security/Review (мелочь, быстро)
- `plan_run_contract`: explore-агент (read/grep, edit deny) читает реальные
  entry points вместо угадывания по README.
- security: LLM-аудит с grep/read поверх regex (ловит не-шаблонные дыры).
- advisory review: reviewer-агент на весь репо вместо 12K-блоба.
**Effort S каждый, Value M-H.**

### D. `opencode serve` как командный рантайм
Каждый MCP-член = тонкая python-обёртка над HTTP API opencode (session per
task). Бонус: полная транскрипция сессии на задачу → вшиваем sessionID в
наш activity log (см. 803c154) = идеальная наблюдаемость.
**Effort L, Value H** — но по сути A+B+C, собранные в инфраструктуру. Делать
после того, как A/B обкатаются на CLI.

### E. IT Lead = opencode-оркестратор
Замена хардкод-оркестрации LLM-сессией с MCP-инструментами реестра.
**Отложить**: детерминизм и стоимость, рановато.

## 5. Кросс-каттинг ограничения и митигации
1. **batch-1 GPU**: opencode шаг = полный ре--send контекста (system+tools
   ~8–12K + история). Замер: prefill ~840 t/s → шаг ≈ 10–15 с + decode.
   Сессия 15–25 шагов ≈ 3–10 мин GPU. СРАВНЕНИЕ: текущий fan-out под contention
   жрал 12–37 мин на ОДИН generate_file-вызов × 6 файлов + repair-петли.
   Net-то может быть и минус. Митигации: `steps: 20` капа; `reasoning_effort:low`
   через provider body; reviewer-агентов на другой движок (deckard/h100/vllm
   когда поднимется); `--auto` вместо интерактивных permissions.
2. **Безопасность**: coder-агент — deny `git push *`, deny сеть, deny `.env`,
   deny external_directory; push/деплой остаются у IT Lead.
3. **Детерминизм**: всё детерминированное (requirements-деривация, pip-audit,
   валидация артефактов, контракты) — оставляем, opencode только там, где
   нужен суждение+проверка.
4. **Качество промптов**: правила из строк промптов (bind 0.0.0.0, PORT, stdlib
   only, MCP-протокол) переезжают в AGENTS.md workspace — opencode подхватывает
   сам, единый источник правды.

## 6. Рекомендация
1. **B** (repair через opencode) — 1 день, измерим на следующем E2E.
2. **C** (три tool-агента) — по мере сил, риск минимальный.
3. **A** (coder-with-hands) — основной ход, после B/C; параллельно решаем
   second-engine вопрос (поднять vllm 35B-A3B или ключ на deckard).
4. **D** — когда A/B/C стабильны; **E** — не в этом цикле.
