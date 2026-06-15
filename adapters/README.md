# Адаптеры под другие AI-стеки

⚠️ **alpha, вживую не протестировано.** Родной формат скиллов — Claude Code / Cowork
(см. корневой README и плагин в `../small-business-ru/`). Здесь — обёртки под другие стеки
для **трёх killer-скиллов** (`counterparty-guard`, `tax-calendar-proactive`,
`cross-source-verify`). Один источник логики (SKILL.md) → обёртки; тело не форкается,
меняется только способ установки и формат триггера.

Приоритет выкатки: **Claude (готов) → Codex / ChatGPT → Gemini → Cursor.**

## Codex (OpenAI CLI) — `codex/AGENTS.md`

Codex читает `AGENTS.md` как инструкции проекта. Скопируйте `codex/AGENTS.md` в корень
своего проекта (или объедините со своим). Скрипты сбора (`fetch_counterparty.py`,
`tax_calc.py`) запускаются Codex напрямую — расчёты идут кодом, как и задумано.

## ChatGPT / Custom GPT — `chatgpt/*.md`

Каждый файл — system prompt под отдельный Custom GPT (один GPT = один killer-скилл).
Вставьте содержимое в поле Instructions при создании GPT.
**Ограничение:** без включённого Code Interpreter ChatGPT не запустит Python-скрипты —
тогда расчёты делает сам по формулам в промпте либо просит принести выгрузку. Для
counterparty-guard и tax-calendar точность выше с Code Interpreter.

## Gemini (CLI) — `gemini/GEMINI.md`

Gemini CLI читает `GEMINI.md` как инструкции проекта и умеет запускать код. Скопируйте
`gemini/GEMINI.md` в корень проекта — три killer-протокола, скрипты запускаются.
(Веб-приложение Gemini без исполнения кода работает как ChatGPT без Code Interpreter.)

## Cursor / Windsurf — `cursor/*.mdc`

Три файла-правила. Скопируйте нужные в `.cursor/rules/` своего проекта. Cursor умеет
запускать код, поэтому скрипты сбора/расчёта работают.

## Что переносится, что меняется

| | Claude (родной) | Codex | ChatGPT |
|---|---|---|---|
| Тело логики (процесс, пороги, гейты, safety) | да | да | да |
| Запуск Python-скриптов | да | да | только с Code Interpreter |
| Установка | плагин-маркетплейс | `AGENTS.md` в репо | Instructions в Custom GPT |

Эмпирика в промптах обезличена (компания не называется, цифры округлены) — как в скиллах.
